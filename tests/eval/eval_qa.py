# -*- coding: utf-8 -*-
"""
医学问答评测脚本

评测指标：
- 准确率（Answer Accuracy）
- 关键词覆盖率（Keyword Coverage）
- 回答相关性（Relevance）

使用方法：
    python tests/eval/eval_qa.py
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / '.env')


def load_test_data(data_path: str) -> List[Dict]:
    """加载测试数据"""
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_keyword_coverage(answer: str, keywords: List[str]) -> float:
    """计算关键词覆盖率

    Args:
        answer: 模型回答
        keywords: 期望包含的关键词列表

    Returns:
        关键词覆盖率 (0-1)
    """
    if not keywords:
        return 1.0

    covered = sum(1 for kw in keywords if kw in answer)
    return covered / len(keywords)


def calculate_answer_quality(answer: str, expected: str) -> Dict[str, float]:
    """评估回答质量

    Args:
        answer: 模型回答
        expected: 期望回答

    Returns:
        质量指标字典
    """
    # 简单的相似度计算（基于共同词汇）
    answer_words = set(answer)
    expected_words = set(expected)

    if not expected_words:
        return {'similarity': 0.0, 'coverage': 0.0}

    # 计算词汇重叠率
    common_words = answer_words & expected_words
    similarity = len(common_words) / len(expected_words) if expected_words else 0.0

    # 计算长度合理性（回答不应过短或过长）
    len_ratio = len(answer) / len(expected) if expected else 0.0
    length_score = 1.0 - min(abs(len_ratio - 1.0), 1.0) * 0.5

    return {
        'similarity': similarity,
        'length_score': length_score,
        'answer_length': len(answer),
        'expected_length': len(expected)
    }


async def evaluate_single_qa(
    question: str,
    expected_answer: str,
    keywords: List[str],
    qa_service
) -> Dict:
    """评测单个问答样本

    Args:
        question: 问题
        expected_answer: 期望答案
        keywords: 关键词
        qa_service: QA 服务实例

    Returns:
        评测结果
    """
    try:
        # 调用 QA 服务
        result = await qa_service.answer_question(question)
        answer = result.get('answer', '')

        # 计算指标
        keyword_coverage = calculate_keyword_coverage(answer, keywords)
        quality = calculate_answer_quality(answer, expected_answer)

        return {
            'question': question,
            'expected_answer': expected_answer,
            'actual_answer': answer,
            'keywords': keywords,
            'keyword_coverage': keyword_coverage,
            'similarity': quality['similarity'],
            'length_score': quality['length_score'],
            'is_acceptable': keyword_coverage >= 0.5 and quality['similarity'] >= 0.3
        }
    except Exception as e:
        return {
            'question': question,
            'expected_answer': expected_answer,
            'actual_answer': '',
            'error': str(e),
            'keyword_coverage': 0.0,
            'similarity': 0.0,
            'is_acceptable': False
        }


async def run_evaluation(test_data: List[Dict], qa_service) -> Dict:
    """运行评测

    Args:
        test_data: 测试数据
        qa_service: QA 服务实例

    Returns:
        评测结果
    """
    results = []
    acceptable_count = 0

    for i, sample in enumerate(test_data):
        print(f"[INFO] 评测进度: {i + 1}/{len(test_data)}", end='\r')

        result = await evaluate_single_qa(
            question=sample['question'],
            expected_answer=sample['expected_answer'],
            keywords=sample.get('keywords', []),
            qa_service=qa_service
        )
        results.append(result)

        if result['is_acceptable']:
            acceptable_count += 1

    print()  # 换行

    # 计算总体指标
    accuracy = acceptable_count / len(test_data) if test_data else 0.0
    avg_keyword_coverage = sum(r['keyword_coverage'] for r in results) / len(results) if results else 0.0
    avg_similarity = sum(r['similarity'] for r in results) / len(results) if results else 0.0

    # 按类别统计
    category_stats = {}
    for sample, result in zip(test_data, results):
        category = sample.get('category', '未分类')
        if category not in category_stats:
            category_stats[category] = {'total': 0, 'acceptable': 0}
        category_stats[category]['total'] += 1
        if result['is_acceptable']:
            category_stats[category]['acceptable'] += 1

    category_metrics = {}
    for category, stats in category_stats.items():
        category_metrics[category] = {
            'accuracy': stats['acceptable'] / stats['total'] if stats['total'] > 0 else 0.0,
            'total': stats['total'],
            'acceptable': stats['acceptable']
        }

    return {
        'overall': {
            'accuracy': accuracy,
            'avg_keyword_coverage': avg_keyword_coverage,
            'avg_similarity': avg_similarity,
            'total_samples': len(test_data),
            'acceptable_count': acceptable_count
        },
        'by_category': category_metrics,
        'details': results
    }


def main():
    parser = argparse.ArgumentParser(description='医学问答评测')
    parser.add_argument('--data_path', type=str,
                        default=None,
                        help='评测数据路径')
    parser.add_argument('--output_path', type=str,
                        default=None,
                        help='评测结果保存路径')

    args = parser.parse_args()

    # 使用项目根目录作为基准
    eval_data_dir = Path(__file__).parent / 'eval_data'
    if args.data_path is None:
        args.data_path = str(eval_data_dir / 'qa_test.json')
    if args.output_path is None:
        args.output_path = str(Path(__file__).parent / 'eval_results_qa.json')

    # 加载测试数据
    print(f"[INFO] 加载评测数据: {args.data_path}")
    test_data = load_test_data(args.data_path)
    print(f"[INFO] 测试样本数: {len(test_data)}")

    # 初始化 QA 服务
    print("[INFO] 初始化 QA 服务...")

    # 直接使用环境变量初始化 LLM 客户端
    from openai import OpenAI

    api_key = os.getenv('DEEPSEEK_API_KEY')
    base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    model = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')

    if not api_key:
        print("[ERROR] 未找到 DEEPSEEK_API_KEY 环境变量")
        sys.exit(1)

    print(f"[INFO] 使用模型: {model}")
    client = OpenAI(api_key=api_key, base_url=base_url)

    class DirectQAService:
        """直接调用 LLM 的 QA 服务"""

        def __init__(self, client, model):
            self.client = client
            self.model = model
            self.system_prompt = """你是一个专业的医疗健康助手，专注于术后管理领域。
请根据用户的问题，提供准确、专业的医学建议。
回答应该：
1. 简洁明了
2. 基于医学常识
3. 包含关键信息
4. 必要时提醒用户咨询医生"""

        async def answer_question(self, question: str) -> Dict:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": question}
                    ],
                    max_tokens=500,
                    temperature=0.7
                )
                answer = response.choices[0].message.content
                return {'answer': answer}
            except Exception as e:
                print(f"[ERROR] LLM 调用失败: {e}")
                return {'answer': ''}

    qa_service = DirectQAService(client, model)

    # 运行评测
    print("[INFO] 开始评测...")
    results = asyncio.run(run_evaluation(test_data, qa_service))

    # 打印结果
    print("\n" + "=" * 60)
    print("医学问答评测结果")
    print("=" * 60)
    print(f"总体指标:")
    print(f"  准确率:          {results['overall']['accuracy']:.4f}")
    print(f"  平均关键词覆盖:  {results['overall']['avg_keyword_coverage']:.4f}")
    print(f"  平均相似度:      {results['overall']['avg_similarity']:.4f}")
    print(f"  总样本数:        {results['overall']['total_samples']}")
    print(f"  可接受回答数:    {results['overall']['acceptable_count']}")

    print(f"\n各类别指标:")
    for category, metrics in sorted(results['by_category'].items()):
        print(f"  {category}:")
        print(f"    准确率: {metrics['accuracy']:.4f} ({metrics['acceptable']}/{metrics['total']})")

    # 保存结果
    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    with open(args.output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[INFO] 评测结果已保存到: {args.output_path}")

    # 检查是否达到目标
    target_accuracy = 0.80
    if results['overall']['accuracy'] >= target_accuracy:
        print(f"\n[PASS] 准确率 ({results['overall']['accuracy']:.4f}) 达到目标 ({target_accuracy})")
    else:
        print(f"\n[FAIL] 准确率 ({results['overall']['accuracy']:.4f}) 未达到目标 ({target_accuracy})")


if __name__ == '__main__':
    main()
