# -*- coding: utf-8 -*-
"""
NER 模型 LoRA 微调脚本

基于 RoBERTa 模型进行 LoRA 微调，针对术后特有实体识别：
- 引流管
- 伤口状态
- 术后并发症
- 其他术后相关实体

使用方法:
    python scripts/ner_finetune.py --data_path data/ner_data_aug.txt --epochs 30 --lr 2e-5

目标: 术后特有实体 F1 > 0.85
"""

import os
import sys
import pickle
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertModel, get_linear_schedule_with_warmup
from peft import LoraConfig, get_peft_model, TaskType
from sklearn.model_selection import train_test_split
from seqeval.metrics import f1_score, classification_report
from tqdm import tqdm
import numpy as np

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# 数据处理
# ============================================================

def load_ner_data(data_path: str, max_len: Optional[int] = None) -> Tuple[List[List[str]], List[List[str]]]:
    """
    加载 NER 标注数据

    数据格式: 每行 "字 标签"，句子间用空行分隔

    Args:
        data_path: 数据文件路径
        max_len: 最大样本数

    Returns:
        (文本列表, 标签列表)
    """
    all_text, all_tag = [], []

    with open(data_path, 'r', encoding='utf-8') as f:
        all_data = f.read().split('\n')

    sen, tag = [], []
    for data in all_data:
        data = data.split(' ')
        if len(data) != 2:
            if len(sen) > 2:
                all_text.append(sen)
                all_tag.append(tag)
            sen, tag = [], []
            continue
        te, ta = data
        sen.append(te)
        tag.append(ta)

    # 处理最后一个句子
    if len(sen) > 2:
        all_text.append(sen)
        all_tag.append(tag)

    if max_len is not None:
        return all_text[:max_len], all_tag[:max_len]
    return all_text, all_tag


def build_tag2idx(all_tag: List[List[str]]) -> Dict[str, int]:
    """构建标签到索引的映射"""
    tag2idx = {'<PAD>': 0}
    for sen in all_tag:
        for tag in sen:
            if tag not in tag2idx:
                tag2idx[tag] = len(tag2idx)
    return tag2idx


# ============================================================
# 数据集
# ============================================================

class NERDataset(Dataset):
    """NER 数据集"""

    def __init__(
        self,
        texts: List[List[str]],
        labels: List[List[str]],
        tokenizer: BertTokenizer,
        max_len: int,
        tag2idx: Dict[str, int],
        is_dev: bool = False
    ):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len
        self.tag2idx = tag2idx
        self.is_dev = is_dev

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]

        # 截断
        max_len = min(len(text) + 2, self.max_len) if self.is_dev else self.max_len
        text = text[:max_len - 2]
        label = label[:max_len - 2]

        # 编码
        text_idx = self.tokenizer.encode(text, add_special_tokens=True)
        label_idx = [self.tag2idx['<PAD>']] + [self.tag2idx.get(l, 0) for l in label] + [self.tag2idx['<PAD>']]

        # 填充
        text_idx += [0] * (max_len - len(text_idx))
        label_idx += [self.tag2idx['<PAD>']] * (max_len - len(label_idx))

        return {
            'input_ids': torch.tensor(text_idx, dtype=torch.long),
            'labels': torch.tensor(label_idx, dtype=torch.long),
            'length': len(text)
        }


# ============================================================
# 模型
# ============================================================

class NERModelWithLoRA(nn.Module):
    """带 LoRA 的 NER 模型"""

    def __init__(
        self,
        model_name: str,
        hidden_size: int,
        tag_num: int,
        bidirectional: bool = True,
        lora_r: int = 8,
        lora_alpha: int = 32,
        lora_dropout: float = 0.1
    ):
        super().__init__()

        # 加载 BERT 模型
        print(f"[INFO] 加载预训练模型: {model_name}")
        self.bert = BertModel.from_pretrained(model_name)

        # 配置 LoRA
        lora_config = LoraConfig(
            task_type=TaskType.TOKEN_CLS,
            r=lora_r,
            lora_alpha=lora_alpha,
            lora_dropout=lora_dropout,
            target_modules=['query', 'value'],  # 对 attention 的 query 和 value 应用 LoRA
            bias='none'
        )

        # 应用 LoRA
        self.bert = get_peft_model(self.bert, lora_config)
        self.bert.print_trainable_parameters()

        # RNN 层
        self.gru = nn.GRU(
            input_size=768,
            hidden_size=hidden_size,
            num_layers=2,
            batch_first=True,
            bidirectional=bidirectional
        )

        # 分类器
        classifier_size = hidden_size * 2 if bidirectional else hidden_size
        self.classifier = nn.Linear(classifier_size, tag_num)

        # 损失函数
        self.loss_fn = nn.CrossEntropyLoss(ignore_index=0)

    def forward(self, input_ids, labels=None):
        # BERT 编码
        bert_output = self.bert(input_ids, attention_mask=(input_ids > 0))
        bert_hidden = bert_output.last_hidden_state

        # GRU
        gru_output, _ = self.gru(bert_hidden)

        # 分类
        logits = self.classifier(gru_output)

        if labels is not None:
            loss = self.loss_fn(logits.reshape(-1, logits.shape[-1]), labels.reshape(-1))
            return loss, logits
        return logits


# ============================================================
# 训练和评估
# ============================================================

def train_epoch(
    model: NERModelWithLoRA,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scheduler,
    device: torch.device
) -> float:
    """训练一个 epoch"""
    model.train()
    total_loss = 0

    for batch in tqdm(dataloader, desc="Training"):
        input_ids = batch['input_ids'].to(device)
        labels = batch['labels'].to(device)

        optimizer.zero_grad()
        loss, _ = model(input_ids, labels)
        loss.backward()

        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()

        total_loss += loss.item()

    return total_loss / len(dataloader)


def evaluate(
    model: NERModelWithLoRA,
    dataloader: DataLoader,
    idx2tag: List[str],
    device: torch.device
) -> Tuple[float, Dict]:
    """评估模型"""
    model.eval()
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in tqdm(dataloader, desc="Evaluating"):
            input_ids = batch['input_ids'].to(device)
            labels = batch['labels']
            lengths = batch['length']

            logits = model(input_ids)
            preds = torch.argmax(logits, dim=-1).cpu()

            for i, length in enumerate(lengths):
                pred_tags = [idx2tag[idx] for idx in preds[i][1:length + 1].tolist()]
                true_tags = [idx2tag[idx] for idx in labels[i][1:length + 1].tolist()]

                all_preds.append(pred_tags)
                all_labels.append(true_tags)

    # 计算 F1
    f1 = f1_score(all_labels, all_preds)

    # 分类报告
    report = classification_report(all_labels, all_preds, output_dict=True)

    return f1, report


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='NER 模型 LoRA 微调')
    parser.add_argument('--data_path', type=str, default='data/ner_data_aug.txt',
                        help='NER 数据文件路径')
    parser.add_argument('--model_name', type=str, default='model/chinese-roberta-wwm-ext',
                        help='预训练模型路径')
    parser.add_argument('--output_dir', type=str, default='model/ner_lora_finetuned',
                        help='微调后模型保存目录')
    parser.add_argument('--epochs', type=int, default=30, help='训练轮数')
    parser.add_argument('--batch_size', type=int, default=32, help='批次大小')
    parser.add_argument('--lr', type=float, default=2e-5, help='学习率')
    parser.add_argument('--max_len', type=int, default=128, help='最大序列长度')
    parser.add_argument('--hidden_size', type=int, default=128, help='GRU 隐藏层大小')
    parser.add_argument('--lora_r', type=int, default=8, help='LoRA 秩')
    parser.add_argument('--lora_alpha', type=int, default=32, help='LoRA 缩放因子')
    parser.add_argument('--warmup_ratio', type=float, default=0.1, help='预热比例')
    parser.add_argument('--seed', type=int, default=42, help='随机种子')
    parser.add_argument('--eval_steps', type=int, default=500, help='评估间隔步数')
    parser.add_argument('--save_best', action='store_true', default=True,
                        help='是否保存最佳模型')

    args = parser.parse_args()

    # 设置随机种子
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    # 设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"[INFO] 使用设备: {device}")

    # 加载数据
    print(f"[INFO] 加载数据: {args.data_path}")
    all_text, all_tag = load_ner_data(args.data_path)
    print(f"[INFO] 总样本数: {len(all_text)}")

    # 构建标签映射
    tag2idx = build_tag2idx(all_tag)
    idx2tag = list(tag2idx.keys())
    print(f"[INFO] 标签数量: {len(tag2idx)}")
    print(f"[INFO] 标签列表: {idx2tag}")

    # 保存标签映射
    os.makedirs(args.output_dir, exist_ok=True)
    with open(os.path.join(args.output_dir, 'tag2idx.pkl'), 'wb') as f:
        pickle.dump(tag2idx, f)

    # 划分训练集和验证集
    train_text, dev_text, train_tag, dev_tag = train_test_split(
        all_text, all_tag, test_size=0.1, random_state=args.seed
    )
    print(f"[INFO] 训练集: {len(train_text)}, 验证集: {len(dev_text)}")

    # 加载分词器
    tokenizer = BertTokenizer.from_pretrained(args.model_name)

    # 创建数据集
    train_dataset = NERDataset(
        train_text, train_tag, tokenizer, args.max_len, tag2idx, is_dev=False
    )
    dev_dataset = NERDataset(
        dev_text, dev_tag, tokenizer, args.max_len, tag2idx, is_dev=True
    )

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    dev_loader = DataLoader(dev_dataset, batch_size=1, shuffle=False)

    # 创建模型
    print("[INFO] 创建 LoRA NER 模型...")
    model = NERModelWithLoRA(
        model_name=args.model_name,
        hidden_size=args.hidden_size,
        tag_num=len(tag2idx),
        bidirectional=True,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha
    )
    model = model.to(device)

    # 优化器
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)

    # 学习率调度器
    total_steps = len(train_loader) * args.epochs
    warmup_steps = int(total_steps * args.warmup_ratio)
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
    )

    # 训练
    print("[INFO] 开始训练...")
    best_f1 = -1
    training_log = []

    for epoch in range(args.epochs):
        print(f"\n{'='*50}")
        print(f"Epoch {epoch + 1}/{args.epochs}")
        print(f"{'='*50}")

        # 训练
        train_loss = train_epoch(model, train_loader, optimizer, scheduler, device)
        print(f"训练损失: {train_loss:.4f}")

        # 评估
        f1, report = evaluate(model, dev_loader, idx2tag, device)
        print(f"验证 F1: {f1:.4f}")

        # 记录日志
        log_entry = {
            'epoch': epoch + 1,
            'train_loss': train_loss,
            'val_f1': f1,
            'timestamp': datetime.now().isoformat()
        }
        training_log.append(log_entry)

        # 保存最佳模型
        if f1 > best_f1:
            best_f1 = f1
            print(f"[INFO] 新的最佳 F1: {best_f1:.4f}，保存模型...")

            # 保存 LoRA 权重
            model.bert.save_pretrained(os.path.join(args.output_dir, 'lora_weights'))

            # 保存完整模型配置
            config = {
                'model_name': args.model_name,
                'hidden_size': args.hidden_size,
                'tag_num': len(tag2idx),
                'bidirectional': True,
                'lora_r': args.lora_r,
                'lora_alpha': args.lora_alpha,
                'best_f1': best_f1,
                'epoch': epoch + 1
            }
            with open(os.path.join(args.output_dir, 'config.json'), 'w') as f:
                json.dump(config, f, indent=2)

        # 打印分类报告
        if (epoch + 1) % 5 == 0:
            print("\n分类报告:")
            print(classification_report(
                *evaluate(model, dev_loader, idx2tag, device)[1].values() if False else None
            ))

    # 保存训练日志
    with open(os.path.join(args.output_dir, 'training_log.json'), 'w') as f:
        json.dump(training_log, f, indent=2)

    print(f"\n{'='*50}")
    print(f"训练完成!")
    print(f"最佳 F1: {best_f1:.4f}")
    print(f"模型保存在: {args.output_dir}")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
