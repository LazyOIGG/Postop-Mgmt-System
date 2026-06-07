# 评测基准 (Evaluation Benchmark)

本目录包含术后管理系统的核心模块评测脚本和数据集。

## 目录结构

```
tests/eval/
├── eval_ner.py              # NER F1-score 评测
├── eval_qa.py               # 医学问答准确率评测
├── eval_routing.py          # Coordinator 路由准确率评测
├── eval_data/               # 评测数据集
│   ├── ner_test.json        # NER 评测数据
│   ├── qa_test.json         # 问答评测数据
│   └── routing_test.json    # 路由评测数据
└── README.md                # 本文件
```

## 评测指标

### 1. NER 评测 (eval_ner.py)

**目标**: 术后特有实体 F1-score > 0.85

**评测指标**:
- Precision（精确率）
- Recall（召回率）
- F1-score（F1 分数）

**运行方式**:
```bash
# 使用默认模型
python tests/eval/eval_ner.py

# 指定模型路径
python tests/eval/eval_ner.py --model_path model/ner_lora_finetuned
```

**评测实体类型**:
- 时间（术后第二天、今日等）
- 部位（伤口、切口等）
- 症状（红肿、疼痛、渗液等）
- 医疗器械（引流管、引流液等）
- 体征（体温、血压、心率等）
- 药品（阿莫西林、布洛芬等）
- 检查项目（血常规等）
- 并发症（切口感染等）

### 2. 医学问答评测 (eval_qa.py)

**目标**: 医学问答准确率 > 80%

**评测指标**:
- 准确率（Answer Accuracy）
- 关键词覆盖率（Keyword Coverage）
- 回答相似度（Similarity）

**运行方式**:
```bash
python tests/eval/eval_qa.py
```

**评测类别**:
- 术后护理（伤口护理、引流管管理等）
- 药品查询（用法、副作用等）
- 术后并发症（发热、感染等）
- 饮食指导（术后饮食注意事项）
- 紧急情况（何时需要就医）

### 3. 路由评测 (eval_routing.py)

**目标**: Coordinator 路由准确率 > 90%

**评测指标**:
- 路由准确率（Routing Accuracy）
- 各 Agent Precision/Recall
- 混淆矩阵（Confusion Matrix）

**运行方式**:
```bash
python tests/eval/eval_routing.py
```

**评测 Agent 类型**:
- `medical_qa`: 医学知识问答
- `health_assessment`: 健康风险评估
- `reminder`: 提醒管理
- `psychology`: 心理情绪问题
- `rehab_plan`: 康复计划管理

## 评测数据

### NER 测试数据格式
```json
{
  "text": "术后第二天伤口有少量渗液，引流管通畅",
  "entities": [
    {"start": 0, "end": 5, "type": "时间", "text": "术后第二天"},
    {"start": 5, "end": 7, "type": "部位", "text": "伤口"}
  ]
}
```

### QA 测试数据格式
```json
{
  "question": "术后伤口渗液正常吗？",
  "expected_answer": "术后少量渗液是正常现象...",
  "category": "术后护理",
  "keywords": ["渗液", "正常", "术后"]
}
```

### 路由测试数据格式
```json
{
  "input": "帮我查一下糖尿病的治疗方法",
  "expected_agent": "medical_qa",
  "category": "疾病查询"
}
```

## 评测结果

评测结果会保存为 JSON 文件：
- `tests/eval/eval_results_ner.json`
- `tests/eval/eval_results_qa.json`
- `tests/eval/eval_results_routing.json`

## 添加新的评测数据

1. 编辑对应的 JSON 文件
2. 按照上述格式添加新的测试样本
3. 重新运行评测脚本

## 持续集成

建议将评测脚本集成到 CI/CD 流程中：
```bash
# 在模型更新后运行全量评测
python tests/eval/eval_ner.py
python tests/eval/eval_qa.py
python tests/eval/eval_routing.py
```

## 注意事项

1. 评测数据应覆盖各种边界情况
2. 定期更新评测数据以反映实际使用场景
3. 关注各类别的均衡性，避免某些类别样本过少
4. 评测结果应作为模型迭代的重要参考
