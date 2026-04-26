# 术后管理系统 (Postop-Mgmt-System)

> **核心架构**: 基于 **KG-RAG** (Knowledge Graph Retrieval-Augmented Generation) 模式，集成 **Neo4j 医疗知识图谱**、**BERT/RoBERTa 命名实体识别 (NER)** 与 **DeepSeek 大语言模型**。

本项目是一个模块化设计的专业术后管理与医疗问答系统，旨在通过结构化的医疗知识图谱为大模型提供精准事实，解决大模型在医疗领域的“幻觉”问题。

***

## 🛠️ 技术栈

- **大模型**: DeepSeek API (兼容 OpenAI 接口)
- **知识图谱**: Neo4j Community (Cypher 查询语言)
- **深度学习**: PyTorch + Transformers (RoBERTa + BiLSTM/RNN)
- **后端框架**: FastAPI + Uvicorn + WebSocket
- **前端界面**: Streamlit
- **数据库**: MySQL (用户认证与会话管理)

***

## 📂 目录结构说明

```text
.
├── app/                    # 后端核心代码
│   ├── api/v1/             # API 路由层 (认证、聊天、会话、图谱、统计、多模态)
│   ├── core/               # 核心配置 (Settings) 与安全逻辑 (JWT/Auth)
│   ├── db/                 # 数据库连接与 Session 管理
│   ├── models/             # Pydantic 数据模型 (Schemas)
│   └── services/           # 业务逻辑层 (LLM, KG, NER, Intent, Speech, Image)
├── data/                   # 医疗领域原始数据、图谱导入数据及 Lora 微调数据
├── database/               # MySQL 底层工具类与密码加密工具
├── legacy/                 # 旧版代码归档与迁移参考文件
├── model/                  # 预训练模型权重 (RoBERTa) 与配置文件
├── scripts/                # 初始化脚本 (MySQL初始化、图谱构建、测试工具)
├── tmp_data/               # 运行过程中的临时缓存文件 (如 tag2idx)
├── .env                    # 个人配置环境变量 (需根据模板创建)
├── requirements.txt        # 项目依赖项
├── run.py                  # 项目统一启动入口 (FastAPI + Streamlit)
└── streamlit_app.py        # Streamlit 前端交互界面
```

***

## 📋 Service 服务介绍

### 核心服务模块

| 服务名称 | 模块文件 | 功能描述 |
|---------|---------|--------|
| **大语言模型服务** | `llm_service.py` | 封装 DeepSeek API 调用，处理聊天响应生成与流式输出 |
| **知识图谱服务** | `kg_service.py` | 管理 Neo4j 连接，执行 Cypher 查询，提供医疗知识检索 |
| **命名实体识别** | `ner_service.py` | 使用 RoBERTa 模型识别医疗文本中的实体（疾病、症状、药品等） |
| **意图识别服务** | `intent_service.py` | 分析用户问题意图，确定查询类型（如疾病简介、治疗方法等） |
| **语音服务** | `speech_service.py` | 集成阿里云语音识别 API，支持语音输入转文本 |
| **图像服务** | `image_service.py` | 处理医疗图像分析，支持 OCR 识别与图像理解 |

### 业务服务模块

| 服务名称 | 模块文件 | 功能描述 |
|---------|---------|--------|
| **健康评估服务** | `health_assessment_service.py` | 基于用户输入进行健康风险评估，生成风险等级与建议 |
| **打卡服务** | `checkin_service.py` | 管理用户每日健康打卡数据，包括症状、体征记录 |
| **提醒服务** | `reminder_service.py` | 处理用户医疗提醒，支持定时提醒与状态管理 |
| **医生服务** | `doctor_service.py` | 提供医生端功能，包括患者管理与异常情况监控 |
| **仪表盘服务** | `dashboard_service.py` | 生成系统统计数据与可视化仪表盘 |
| **概览服务** | `overview_service.py` | 提供用户健康概览与数据汇总 |

***

## ⚙️ 个人配置 (必备)

在协作开发前，请在根目录下创建 `.env` 文件，并配置以下个人私有参数
### 注意：若新增设置项，需在提交说明中说明，并将新的格式填入下面（不要暴露api key）

```env
# 基础设置
PROJECT_NAME="术后管理系统API"
VERSION="1.0.0"
API_V1_STR="/api/v1"

# 1. DeepSeek API 配置 (必填)
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 2. Neo4j 知识图谱配置 (必填)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=
NEO4J_NAME=neo4j

# 3. MySQL 数据库配置 (必填)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=RAG

# 4. 模型路径配置
BERT_MODEL_PATH="./model/chinese-roberta-wwm-ext"
NER_MODEL_WEIGHTS="model/best_roberta_rnn_model_ent_aug.pt"
TAG2IDX_PATH="tmp_data/tag2idx.npy"

# 5. 安全配置 (建议修改)
SECRET_KEY=yoursupersecretkeyhere
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 6. 预留多模态接口
SPEECH_API_KEY=
IMAGE_API_KEY=

# 7. 阿里云百炼 Fun-ASR 配置 (可选，用于多模态功能)
DASHSCOPE_API_KEY=

# 8. 智谱AI配置 (可选，用于finetune_demo)
ZHIPUAI_API_KEY=
```

***

## 🚀 项目启动步骤

### 1. 环境准备

推荐使用 Python 3.10.11 ：

```bash
pip install -r requirements.txt
```

### 2. 数据库初始化

确保 MySQL 服务已启动，运行脚本创建库、表结构（记得往里面填MySQL密码）：

```bash
python scripts/init_mysql.py
```

### 3. 构建知识图谱

确保 Neo4j 服务已启动且 APOC 插件已安装，运行脚本导入医疗数据（也要换密码，只要看到Ncy182...就替换为自己密码）：

```bash
python scripts/build_up_graph.py
```

### 4. 一键启动系统

执行根目录下的启动脚本，系统会自动开启后端 API 和前端界面，并打开浏览器：

```bash
python run.py
```

- **前端地址**: `http://localhost:8501`
- **API 文档**: `http://localhost:8000/docs`

***

## 📅 后续工作计划 (Roadmap)

- [ ] **多模态集成**:
  - 集成语音识别 (STT) 与合成 (TTS) 功能，支持语音问答。
  - 集成医疗报告 OCR 识别，支持图片化验单分析。
- [ ] **知识图谱增强**:
  - 引入更复杂的实体关系，支持多跳推理问答。
  - 优化 Cypher 生成算法，提升图谱检索的准确率。
- [ ] **模型优化**:
  - 基于提供的 `lora_data` 对大模型进行垂直领域微调 (SFT)。
  - 进一步提升 NER 模型对复杂长句的提取能力。
- [ ] **性能监控**:
  - 引入 Redis 缓存常用查询结果。
  - 完善系统的日志追踪与性能监控面板。

***

## 🤝 协作规范

- **代码规范**: 请遵循 PEP 8 规范，注释采用简洁的中文风格。
- **分支管理**: 建议在 `feature/` 分支开发新功能，完成后提交 PR。
- **控制台输出**: 统一使用标准化前缀：`[INFO] ℹ️`, `[SUCCESS] ✅`, `[WARN] ⚠️`, `[ERROR] ❌`。
- **警告**: 上传代码前必须先把所有密码和Token key删掉


***

## ⚠️ 免责声明

本系统仅用于科研与工程演示，所提供的术后建议不构成专业医疗诊断，实际病情请务必咨询专业医师。