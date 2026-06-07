# -*- coding: utf-8 -*-
"""
Coordinator 路由准确率评测脚本

评测指标：
- 路由准确率（Routing Accuracy）
- 各类别准确率（Per-class Accuracy）
- 混淆矩阵（Confusion Matrix）

使用方法：
    python tests/eval/eval_routing.py
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def load_test_data(data_path: str) -> List[Dict]:
    """加载测试数据"""
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def evaluate_single_routing(
    input_text: str,
    expected_agent: str,
    coordinator
) -> Dict:
    """评测单个路由样本

    Args:
        input_text: 用户输入
        expected_agent: 期望路由到的 agent
        coordinator: Coordinator 实例

    Returns:
        评测结果
    """
    try:
        # 调用 Coordinator
        response = await coordinator.run(input_text)
        predicted_agent = response.content

        # 判断是否正确
        is_correct = predicted_agent == expected_agent

        return {
            'input': input_text,
            'expected': expected_agent,
            'predicted': predicted_agent,
            'is_correct': is_correct,
            'metadata': response.metadata if hasattr(response, 'metadata') else {}
        }
    except Exception as e:
        return {
            'input': input_text,
            'expected': expected_agent,
            'predicted': None,
            'is_correct': False,
            'error': str(e)
        }


async def run_evaluation(test_data: List[Dict], coordinator) -> Dict:
    """运行评测

    Args:
        test_data: 测试数据
        coordinator: Coordinator 实例

    Returns:
        评测结果
    """
    results = []
    correct_count = 0

    # 混淆矩阵
    confusion_matrix = defaultdict(lambda: defaultdict(int))
    # 各类别统计
    category_stats = defaultdict(lambda: {'total': 0, 'correct': 0})

    for i, sample in enumerate(test_data):
        print(f"[INFO] 评测进度: {i + 1}/{len(test_data)}", end='\r')

        result = await evaluate_single_routing(
            input_text=sample['input'],
            expected_agent=sample['expected_agent'],
            coordinator=coordinator
        )
        results.append(result)

        if result['is_correct']:
            correct_count += 1

        # 更新混淆矩阵
        expected = result['expected']
        predicted = result['predicted'] or 'error'
        confusion_matrix[expected][predicted] += 1

        # 更新类别统计
        category = sample.get('category', '未分类')
        category_stats[category]['total'] += 1
        if result['is_correct']:
            category_stats[category]['correct'] += 1

    print()  # 换行

    # 计算总体准确率
    accuracy = correct_count / len(test_data) if test_data else 0.0

    # 计算各类别准确率
    agent_stats = defaultdict(lambda: {'total': 0, 'correct': 0, 'precision': 0.0, 'recall': 0.0})
    for result in results:
        expected = result['expected']
        predicted = result['predicted'] or 'error'
        agent_stats[expected]['total'] += 1
        if result['is_correct']:
            agent_stats[expected]['correct'] += 1

    # 计算 Precision 和 Recall
    for agent_name in agent_stats:
        stats = agent_stats[agent_name]
        stats['recall'] = stats['correct'] / stats['total'] if stats['total'] > 0 else 0.0

        # 计算 Precision：预测为该类别的样本中，真正属于该类别的比例
        predicted_as_agent = sum(1 for r in results if r['predicted'] == agent_name)
        stats['precision'] = stats['correct'] / predicted_as_agent if predicted_as_agent > 0 else 0.0

    # 计算类别准确率
    category_metrics = {}
    for category, stats in category_stats.items():
        category_metrics[category] = {
            'accuracy': stats['correct'] / stats['total'] if stats['total'] > 0 else 0.0,
            'total': stats['total'],
            'correct': stats['correct']
        }

    return {
        'overall': {
            'accuracy': accuracy,
            'total_samples': len(test_data),
            'correct_count': correct_count
        },
        'by_agent': {k: dict(v) for k, v in agent_stats.items()},
        'by_category': category_metrics,
        'confusion_matrix': {k: dict(v) for k, v in confusion_matrix.items()},
        'details': results
    }


def main():
    parser = argparse.ArgumentParser(description='Coordinator 路由评测')
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
        args.data_path = str(eval_data_dir / 'routing_test.json')
    if args.output_path is None:
        args.output_path = str(Path(__file__).parent / 'eval_results_routing.json')

    # 加载测试数据
    print(f"[INFO] 加载评测数据: {args.data_path}")
    test_data = load_test_data(args.data_path)
    print(f"[INFO] 测试样本数: {len(test_data)}")

    # 初始化 Coordinator
    print("[INFO] 初始化 Coordinator...")
    try:
        from app.agents.coordinator import CoordinatorAgent
        coordinator = CoordinatorAgent()
    except Exception as e:
        print(f"[ERROR] 无法初始化 Coordinator: {e}")
        sys.exit(1)

    # 运行评测
    print("[INFO] 开始评测...")
    results = asyncio.run(run_evaluation(test_data, coordinator))

    # 打印结果
    print("\n" + "=" * 60)
    print("Coordinator 路由评测结果")
    print("=" * 60)
    print(f"总体指标:")
    print(f"  路由准确率:  {results['overall']['accuracy']:.4f}")
    print(f"  总样本数:    {results['overall']['total_samples']}")
    print(f"  正确路由数:  {results['overall']['correct_count']}")

    print(f"\n各 Agent 指标:")
    for agent_name, metrics in sorted(results['by_agent'].items()):
        print(f"  {agent_name}:")
        print(f"    Precision: {metrics['precision']:.4f}")
        print(f"    Recall:    {metrics['recall']:.4f}")
        print(f"    样本数:    {metrics['total']}")

    print(f"\n各类别指标:")
    for category, metrics in sorted(results['by_category'].items()):
        print(f"  {category}:")
        print(f"    准确率: {metrics['accuracy']:.4f} ({metrics['correct']}/{metrics['total']})")

    print(f"\n混淆矩阵:")
    # 打印表头
    agents = sorted(set(list(results['confusion_matrix'].keys()) +
                        [k for v in results['confusion_matrix'].values() for k in v.keys()]))
    header = "Actual\\Predict"
    print(f"  {header:<15}", end='')
    for agent in agents:
        print(f"{agent:<15}", end='')
    print()

    for actual in agents:
        print(f"  {actual:<15}", end='')
        for predicted in agents:
            count = results['confusion_matrix'].get(actual, {}).get(predicted, 0)
            print(f"{count:<15}", end='')
        print()

    # 保存结果
    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    with open(args.output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[INFO] 评测结果已保存到: {args.output_path}")

    # 检查是否达到目标
    target_accuracy = 0.90
    if results['overall']['accuracy'] >= target_accuracy:
        print(f"\n[PASS] 路由准确率 ({results['overall']['accuracy']:.4f}) 达到目标 ({target_accuracy})")
    else:
        print(f"\n[FAIL] 路由准确率 ({results['overall']['accuracy']:.4f}) 未达到目标 ({target_accuracy})")


if __name__ == '__main__':
    main()
