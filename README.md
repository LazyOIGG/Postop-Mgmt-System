# 术后管理系统 (Postop-Mgmt-System)

> **基于多智能体编排的KG-RAG医疗问答与康复管理系统**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.52-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 项目简介

术后管理系统是一个面向术后患者的专业医疗问答与康复管理平台。系统采用**多智能体协作架构**，集成**Neo4j医疗知识图谱**、**BERT/RoBERTa命名实体识别(NER)**与**DeepSeek大语言模型**，为患者提供智能化的术后康复指导、健康风险评估和个性化康复计划。

### 核心特性

- 🤖 **多智能体协作**: Coordinator + 4个专业Agent的编排模式
- 🧠 **KG-RAG管线**: 知识图谱增强的检索增强生成
- 🏥 **健康风险评估**: 三级风险评估体系
- 💊 **智能用药提醒**: 基于患者情况的个性化提醒
- 📊 **康复计划管理**: AI驱动的个性化康复方案
- 🎯 **NER实体识别**: RoBERTa+BiLSTM医疗实体识别模型
- 🔊 **多模态交互**: 支持语音输入和图像识别

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户界面层                              │
│         Streamlit前端 (患者端 + 医生端)                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      API网关层                               │
│              FastAPI + WebSocket + SSE                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   多智能体编排层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Coordinator  │──│ MedicalQA    │──│ Health       │       │
│  │   Agent      │  │   Agent      │  │   Agent      │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                │                  │                │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ Reminder     │  │ Psychology   │                         │
│  │   Agent      │  │   Agent      │                         │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      服务层                                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │ LLM     │ │ KG      │ │ NER     │ │ Speech  │          │
│  │ Service │ │ Service │ │ Service │ │ Service │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      数据层                                  │
│     MySQL          Neo4j           Redis                    │
│   (用户数据)     (知识图谱)        (缓存)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 技术栈

| 类别 | 技术 | 说明 |
|------|------|------|
| **大模型** | DeepSeek API | 兼容OpenAI接口的LLM服务 |
| **知识图谱** | Neo4j Community | Cypher查询语言，APOC插件 |
| **深度学习** | PyTorch + Transformers | RoBERTa + BiLSTM/RNN NER模型 |
| **后端框架** | FastAPI + Uvicorn | 异步高性能Web框架 |
| **前端界面** | Streamlit | 快速构建数据应用 |
| **数据库** | MySQL | 用户认证与会话管理 |
| **缓存** | Redis | 可选，用于查询结果缓存 |
| **语音识别** | 阿里云Fun-ASR | 语音输入转文本 |
| **图像识别** | PaddleOCR | 医疗图像OCR识别 |

---

## 📂 目录结构

```
Postop-Mgmt-System/
├── app/                        # 后端核心代码
│   ├── agents/                 # 多智能体模块
│   │   ├── coordinator.py      # 协调者Agent
│   │   ├── medical_qa_agent.py # 医学问答Agent
│   │   ├── health_agent.py     # 健康评估Agent
│   │   ├── reminder_agent.py   # 提醒Agent
│   │   ├── psychology_agent.py # 心理辅导Agent
│   │   └── tools/              # Agent工具集
│   ├── api/v1/                 # API路由层
│   │   └── endpoints/          # 各功能端点
│   ├── core/                   # 核心配置
│   │   ├── config.py           # 配置管理
│   │   ├── security.py         # JWT认证
│   │   └── ws_manager.py       # WebSocket管理
│   ├── db/                     # 数据库连接
│   ├── models/                 # 数据模型
│   └── services/               # 业务逻辑层
│       ├── llm_service.py      # LLM服务
│       ├── kg_service.py       # 知识图谱服务
│       ├── ner_service.py      # NER服务
│       ├── rehab_plan_service.py # 康复计划服务
│       └── ...                 # 其他服务
├── data/                       # 医疗数据
│   ├── medical_new_2.json      # 医疗知识数据
│   ├── ner_data_aug.txt        # NER训练数据
│   └── guidelines/             # 临床指南PDF
├── database/                   # 数据库工具
│   ├── db_operation.py         # 数据库操作
│   ├── local_db_utils.py       # 本地数据库工具
│   └── migrations/             # 数据库迁移
├── model/                      # 预训练模型
│   └── chinese-roberta-wwm-ext/ # RoBERTa模型
├── scripts/                    # 初始化脚本
│   ├── init_mysql.py           # MySQL初始化
│   ├── build_up_graph.py       # 知识图谱构建
│   ├── ingest_guideline.py     # 指南数据导入
│   ├── seed_users.py           # 种子用户数据
│   └── ner_finetune.py         # NER模型微调
├── tests/                      # 测试代码
│   ├── test_auth.py            # 认证测试
│   ├── test_health.py          # 健康模块测试
│   ├── test_ws_manager.py      # WebSocket测试
│   └── scripts/                # 测试脚本
├── static/                     # 静态文件
├── .env                        # 环境变量配置
├── .env.example                # 环境变量模板
├── requirements.txt            # Python依赖
├── run.py                      # 统一启动入口
├── streamlit_app.py            # 患者端前端
└── streamlit_doctor_app.py     # 医生端前端
```

---

## 🚀 快速开始

### 1. 环境准备

**Python版本**: 推荐 3.10.11

```bash
# 克隆项目
git clone https://github.com/LazyOIGG/Postop-Mgmt-System.git
cd Postop-Mgmt-System

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制环境变量模板并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下必要参数：

```env
# DeepSeek API配置
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# Neo4j配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# MySQL配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=RAG

# 安全配置
SECRET_KEY=your_secret_key_here
```

### 3. 数据库初始化

确保MySQL和Neo4j服务已启动：

```bash
# 初始化MySQL数据库
python scripts/init_mysql.py

# 构建知识图谱
python scripts/build_up_graph.py

# 导入种子数据（可选）
python scripts/seed_users.py
```

### 4. 启动系统

```bash
# 一键启动（推荐）
python run.py

# 或分别启动
# 启动后端
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 启动患者端
streamlit run streamlit_app.py --server.port 8501

# 启动医生端
streamlit run streamlit_doctor_app.py --server.port 8502
```

### 5. 访问系统

- **患者端界面**: http://localhost:8501
- **医生端界面**: http://localhost:8502
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

---

## 🤖 多智能体架构

### Agent职责

| Agent | 触发场景 | 核心技术 |
|-------|---------|---------|
| **CoordinatorAgent** | 所有用户输入 | LLM语义路由 |
| **MedicalQAAgent** | 医学知识问答 | NER + Neo4j KG + LLM |
| **HealthAssessmentAgent** | 健康风险评估 | 三级风险关键词 + LLM |
| **ReminderAgent** | 用药/复查提醒 | LLM对话 |
| **PsychologyAgent** | 心理辅导 | LLM共情对话 |

### 调度流程

```
用户输入 → CoordinatorAgent (LLM意图分析)
               │
   ┌───────────┼────────────┬──────────────┐
   ▼           ▼            ▼              ▼
MedicalQA  HealthAssessment  Reminder  Psychology
医学问答    健康风险评估    用药复查提醒  心理辅导缓解
(KG-RAG)   (规则+LLM)     (LLM)        (LLM)
```

---

## 📊 API端点

### 核心端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `POST /api/v1/chat` | POST | 多智能体聊天（支持SSE流式） |
| `GET /api/v1/chat/agent/ws` | WebSocket | 多智能体实时WebSocket |
| `GET /api/v1/health` | GET | 健康检查 |
| `GET /docs` | GET | API文档（Swagger UI） |

### 功能模块

| 模块 | 端点前缀 | 说明 |
|------|---------|------|
| 认证 | `/api/v1/auth` | 用户注册、登录、Token刷新 |
| 健康 | `/api/v1/health` | 健康评估、风险分析 |
| 康复 | `/api/v1/rehab/*` | 康复计划、运动、日记、成就 |
| 提醒 | `/api/v1/reminder` | 用药提醒、复查提醒 |
| 医生 | `/api/v1/doctor` | 医生端功能 |
| 统计 | `/api/v1/stats` | 数据统计与可视化 |

---

## 🧪 测试

### 运行单元测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_auth.py

# 运行并生成覆盖率报告
pytest tests/ --cov=app --cov-report=html
```

### 测试脚本

测试脚本位于 `tests/scripts/` 目录：

```bash
# 测试DeepSeek API连接
python tests/scripts/test_deepseek.py

# 测试MySQL连接
python tests/scripts/test_mysql.py

# 测试语音识别
python tests/scripts/test_asr_recognition.py
```

---

## 📈 性能监控

### Prometheus指标

系统集成了Prometheus监控指标：

- `http_requests_total`: HTTP请求总数
- `http_request_duration_seconds`: 请求延迟

访问 `/metrics` 端点获取指标数据。

### 健康检查

```bash
curl http://localhost:8000/health
```

返回各组件状态：
- MySQL连接状态
- Neo4j连接状态
- Redis连接状态（可选）
- LLM配置状态

---

## 🔧 配置说明

### 环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API密钥 |
| `NEO4J_URI` | ✅ | Neo4j连接地址 |
| `NEO4J_PASSWORD` | ✅ | Neo4j密码 |
| `MYSQL_HOST` | ✅ | MySQL主机地址 |
| `MYSQL_PASSWORD` | ✅ | MySQL密码 |
| `SECRET_KEY` | ✅ | JWT密钥 |
| `DASHSCOPE_API_KEY` | ❌ | 阿里云语音API（可选） |

### 模型配置

```env
# RoBERTa模型路径
BERT_MODEL_PATH=./model/chinese-roberta-wwm-ext

# NER模型权重
NER_MODEL_WEIGHTS=model/best_roberta_rnn_model_ent_aug.pt

# 标签映射
TAG2IDX_PATH=tmp_data/tag2idx.npy
```

---

## 📝 开发指南

### 代码规范

- 遵循PEP 8规范
- 注释采用中文风格
- 使用结构化日志（structlog）

### 分支管理

```bash
# 创建功能分支
git checkout -b feature/your-feature

# 提交PR
git push origin feature/your-feature
```

### 控制台输出规范

```python
# 使用标准化前缀
print("[INFO] ℹ️ 信息消息")
print("[SUCCESS] ✅ 成功消息")
print("[WARN] ⚠️ 警告消息")
print("[ERROR] ❌ 错误消息")
```

---

## 🚧 开发路线

### ✅ 已完成

- [x] 多智能体架构搭建
- [x] KG-RAG管线实现
- [x] 健康风险评估系统
- [x] 康复计划管理
- [x] WebSocket实时通信
- [x] NER实体识别模型
- [x] 医生端功能

### 🔄 进行中

- [ ] 心理辅导Agent知识增强
- [ ] 多轮对话记忆优化
- [ ] 康复计划AI优化

### 📋 计划中

- [ ] 语音交互完善
- [ ] 知识图谱多跳推理
- [ ] Redis缓存优化
- [ ] 移动端适配

---

## ⚠️ 免责声明

本系统仅用于科研与工程演示，所提供的术后建议不构成专业医疗诊断。实际病情请务必咨询专业医师。

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 👥 贡献者

感谢所有为本项目做出贡献的开发者！

---

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 [Issue](https://github.com/LazyOIGG/Postop-Mgmt-System/issues)
- 发送邮件至项目维护者

---

**最后更新**: 2026年6月27日