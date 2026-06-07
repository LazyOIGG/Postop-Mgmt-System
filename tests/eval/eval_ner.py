# -*- coding: utf-8 -*-
"""
NER 模型评测脚本

评测指标：
- Precision（精确率）
- Recall（召回率）
- F1-score（F1 分数）

使用方法：
    python tests/eval/eval_ner.py --model_path model/ner_lora_finetuned
    python tests/eval/eval_ner.py  # 使用默认模型
"""

import os
import sys
import json
import pickle
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import torch
from transformers import BertTokenizer

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def load_test_data(data_path: str) -> List[Dict]:
    """加载测试数据"""
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_entities_from_text(text: str, ner_result: Dict) -> List[Dict]:
    """从 NER 结果中提取实体列表

    Args:
        text: 原始文本
        ner_result: NER 服务返回的结果 {类型: 实体文本}

    Returns:
        实体列表 [{type, text, start, end}, ...]
    """
    entities = []
    for ent_type, ent_text in ner_result.items():
        # 查找实体在文本中的位置
        start = text.find(ent_text)
        if start != -1:
            entities.append({
                'type': ent_type,
                'text': ent_text,
                'start': start,
                'end': start + len(ent_text)
            })
    return entities


def calculate_entity_level_metrics(
    predicted: List[Dict],
    expected: List[Dict]
) -> Tuple[int, int, int]:
    """计算实体级别的 TP, FP, FN

    Args:
        predicted: 预测的实体列表
        expected: 真实的实体列表

    Returns:
        (TP, FP, FN)
    """
    # 将实体转换为集合进行比较
    pred_set = set()
    for ent in predicted:
        pred_set.add((ent['type'], ent['text']))

    true_set = set()
    for ent in expected:
        true_set.add((ent['type'], ent['text']))

    tp = len(pred_set & true_set)
    fp = len(pred_set - true_set)
    fn = len(true_set - pred_set)

    return tp, fp, fn


def calculate_metrics(tp: int, fp: int, fn: int) -> Dict[str, float]:
    """计算 Precision, Recall, F1"""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'tp': tp,
        'fp': fp,
        'fn': fn
    }


def evaluate_by_type(results: List[Dict]) -> Dict[str, Dict[str, float]]:
    """按实体类型统计评测结果"""
    type_stats = {}

    for result in results:
        for ent_type in set(list(result.get('pred_types', {}).keys()) +
                           [e['type'] for e in result.get('expected_entities', [])]):
            if ent_type not in type_stats:
                type_stats[ent_type] = {'tp': 0, 'fp': 0, 'fn': 0}

            expected_entities = result.get('expected_entities', [])

            # 统计该类型的 TP, FP, FN
            pred_set = set()
            for ent in result.get('predicted_entities', []):
                if ent['type'] == ent_type:
                    pred_set.add(ent['text'])

            true_set = set()
            for ent in expected_entities:
                if ent['type'] == ent_type:
                    true_set.add(ent['text'])

            tp = len(pred_set & true_set)
            fp = len(pred_set - true_set)
            fn = len(true_set - pred_set)

            type_stats[ent_type]['tp'] += tp
            type_stats[ent_type]['fp'] += fp
            type_stats[ent_type]['fn'] += fn

    # 计算各类型的指标
    type_metrics = {}
    for ent_type, stats in type_stats.items():
        type_metrics[ent_type] = calculate_metrics(stats['tp'], stats['fp'], stats['fn'])

    return type_metrics


class SimpleNERModel:
    """简化的 NER 模型封装，用于评测"""

    def __init__(self, model_dir: str = None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.tokenizer = None
        self.idx2tag = []
        self.rule = None
        self.tfidf_r = None
        self._load_model(model_dir)

    def _load_model(self, model_dir: str = None):
        """加载 NER 模型"""
        # 直接导入 ner_model 模块，避免触发 services/__init__.py
        import importlib.util
        ner_model_path = PROJECT_ROOT / 'app' / 'services' / 'ner_model.py'
        spec = importlib.util.spec_from_file_location("ner_model", ner_model_path)
        self.zwk = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.zwk)

        # 默认路径
        if model_dir is None:
            model_dir = str(PROJECT_ROOT / 'model')

        tag2idx_path = PROJECT_ROOT / 'tmp_data' / 'tag2idx.npy'
        model_weights_path = PROJECT_ROOT / 'model' / 'best_roberta_rnn_model_ent_aug.pt'
        bert_model_path = str(PROJECT_ROOT / 'model' / 'chinese-roberta-wwm-ext')

        # 加载标签映射（项目训练脚本内部生成，来源可信）
        if tag2idx_path.exists():
            with open(tag2idx_path, 'rb') as f:
                tag2idx = pickle.load(f)
            self.idx2tag = list(tag2idx)
            print(f"[INFO] 标签数量: {len(tag2idx)}")

        # 加载分词器
        self.tokenizer = BertTokenizer.from_pretrained(bert_model_path)
        print("[INFO] 分词器加载成功")

        # 加载模型
        if model_weights_path.exists():
            self.model = self.zwk.Bert_Model(bert_model_path, hidden_size=128, tag_num=len(tag2idx), bi=True)
            self.model.load_state_dict(torch.load(model_weights_path, map_location=self.device, weights_only=True))
            self.model = self.model.to(self.device).eval()
            print("[INFO] NER 模型加载成功")

        # 加载规则和 TF-IDF 对齐（需要切换到项目根目录）
        original_dir = os.getcwd()
        try:
            os.chdir(PROJECT_ROOT)
            self.rule = self.zwk.rule_find()
            self.tfidf_r = self.zwk.tfidf_alignment()
            print("[INFO] 规则和 TF-IDF 对齐加载成功")
        except Exception as e:
            print(f"[WARN] 规则/TF-IDF 加载失败: {e}")
            self.rule = None
            self.tfidf_r = None
        finally:
            os.chdir(original_dir)

    def recognize(self, query: str) -> Dict:
        """执行实体识别"""
        if self.model is None or self.tokenizer is None:
            return {}

        try:
            # 切换到项目根目录（规则匹配需要读取 data/ent_aug/ 文件）
            original_dir = os.getcwd()
            os.chdir(PROJECT_ROOT)
            try:
                result = self.zwk.get_ner_result(
                    self.model, self.tokenizer, query,
                    self.rule, self.tfidf_r, self.device, self.idx2tag
                )
                return result
            finally:
                os.chdir(original_dir)
        except Exception as e:
            print(f"[WARN] 识别异常: {e}")
            return {}


def main():
    parser = argparse.ArgumentParser(description='NER 模型评测')
    parser.add_argument('--data_path', type=str,
                        default=None,
                        help='评测数据路径')
    parser.add_argument('--model_path', type=str,
                        default=None,
                        help='模型路径（可选，默认使用项目 model 目录）')
    parser.add_argument('--output_path', type=str,
                        default=None,
                        help='评测结果保存路径')

    args = parser.parse_args()

    # 使用项目根目录作为基准
    eval_data_dir = Path(__file__).parent / 'eval_data'
    if args.data_path is None:
        args.data_path = str(eval_data_dir / 'ner_test.json')
    if args.output_path is None:
        args.output_path = str(Path(__file__).parent / 'eval_results_ner.json')

    # 加载测试数据
    print(f"[INFO] 加载评测数据: {args.data_path}")
    test_data = load_test_data(args.data_path)
    print(f"[INFO] 测试样本数: {len(test_data)}")

    # 初始化 NER 模型
    print("[INFO] 初始化 NER 模型...")
    ner_model = SimpleNERModel(args.model_path)

    # 评测
    print("[INFO] 开始评测...")
    results = []
    total_tp, total_fp, total_fn = 0, 0, 0

    for i, sample in enumerate(test_data):
        text = sample['text']
        expected_entities = sample['entities']

        # 执行 NER
        ner_result = ner_model.recognize(text)
        predicted_entities = extract_entities_from_text(text, ner_result)

        # 计算指标
        tp, fp, fn = calculate_entity_level_metrics(predicted_entities, expected_entities)
        total_tp += tp
        total_fp += fp
        total_fn += fn

        results.append({
            'text': text,
            'expected_entities': expected_entities,
            'predicted_entities': predicted_entities,
            'ner_raw_result': ner_result,
            'tp': tp,
            'fp': fp,
            'fn': fn
        })

        # 打印进度
        if (i + 1) % 10 == 0:
            print(f"[INFO] 已处理 {i + 1}/{len(test_data)} 样本")

    # 计算总体指标
    overall_metrics = calculate_metrics(total_tp, total_fp, total_fn)

    # 按类型统计
    type_metrics = evaluate_by_type(results)

    # 打印结果
    print("\n" + "=" * 60)
    print("NER 评测结果")
    print("=" * 60)
    print("总体指标:")
    print(f"  Precision: {overall_metrics['precision']:.4f}")
    print(f"  Recall:    {overall_metrics['recall']:.4f}")
    print(f"  F1-score:  {overall_metrics['f1']:.4f}")
    print(f"  TP: {total_tp}, FP: {total_fp}, FN: {total_fn}")

    print("\n各类型指标:")
    for ent_type, metrics in sorted(type_metrics.items()):
        print(f"  {ent_type}:")
        print(f"    P={metrics['precision']:.4f}, R={metrics['recall']:.4f}, F1={metrics['f1']:.4f}")

    # 保存结果
    output = {
        'overall': overall_metrics,
        'by_type': type_metrics,
        'details': results,
        'config': {
            'data_path': args.data_path,
            'model_path': args.model_path,
            'test_samples': len(test_data)
        }
    }

    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    with open(args.output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[INFO] 评测结果已保存到: {args.output_path}")

    # 检查是否达到目标
    target_f1 = 0.85
    if overall_metrics['f1'] >= target_f1:
        print(f"\n[PASS] F1-score ({overall_metrics['f1']:.4f}) 达到目标 ({target_f1})")
    else:
        print(f"\n[FAIL] F1-score ({overall_metrics['f1']:.4f}) 未达到目标 ({target_f1})")


if __name__ == '__main__':
    main()
