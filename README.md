# 术后管理系统 (Postop-Mgmt-System)

> **基于多智能体编排的KG-RAG医疗问答与康复管理系统**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-green.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.5-brightgreen.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 项目简介

术后管理系统是一个面向术后患者的专业医疗问答与康复管理平台。系统采用**多智能体协作架构**，集成**Neo4j医疗知识图谱**、**BERT/RoBERTa命名实体识别(NER)**与**DeepSeek大语言模型**，为患者提供智能化的术后康复指导、健康风险评估和个性化康复计划。

### 核心特性

- 🤖 **多智能体协作**: Coordinator + 5个专业Agent的编排模式
- 🧠 **KG-RAG管线**: 知识图谱增强的检索增强生成
- 🏥 **健康风险评估**: 三级风险评估体系
- 💊 **智能用药提醒**: 基于患者情况的个性化提醒
- 📊 **康复计划管理**: AI驱动的个性化康复方案
- 🎯 **NER实体识别**: RoBERTa+BiLSTM医疗实体识别模型
- 🔊 **多模态交互**: 支持语音输入和图像识别
- 🌐 **双端支持**: Vue前端(患者端+医生端) + Streamlit前端

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户界面层                              │
│     Vue前端 (患者端 + 医生端)  │  Streamlit前端              │
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
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Reminder     │  │ Psychology   │  │ RehabPlan    │       │
│  │   Agent      │  │   Agent      │  │   Agent      │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
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

### 后端

| 类别 | 技术 | 说明 |
|------|------|------|
| **大模型** | DeepSeek API | 兼容OpenAI接口的LLM服务 |
| **知识图谱** | Neo4j Community | Cypher查询语言，APOC插件 |
| **深度学习** | PyTorch + Transformers | RoBERTa + BiLSTM/RNN NER模型 |
| **后端框架** | FastAPI + Uvicorn | 异步高性能Web框架 |
| **数据库** | MySQL 8.0 | 用户认证与会话管理 |
| **缓存** | Redis 7 | 可选，用于Token黑名单和对话缓存 |
| **语音识别** | 阿里云Fun-ASR | 语音输入转文本 |
| **图像识别** | PaddleOCR | 医疗图像OCR识别 |
| **监控** | Prometheus + structlog | 指标监控与结构化日志 |

### 前端

| 类别 | 技术 | 说明 |
|------|------|------|
| **框架** | Vue 3.5 + TypeScript | Composition API |
| **构建工具** | Vite 8 | 快速开发与构建 |
| **UI组件库** | Element Plus 2.14 | 企业级UI组件 |
| **状态管理** | Pinia 3 | Vue官方状态管理 |
| **图表** | ECharts 6 | 数据可视化 |
| **HTTP客户端** | Axios 1.16 | 请求拦截与Token刷新 |

---

## 📂 目录结构

```
Postop-Mgmt-System/
├── app/                            # 后端核心代码
│   ├── agents/                     # 多智能体模块
│   │   ├── coordinator.py          # 协调者Agent
│   │   ├── medical_qa_agent.py     # 医学问答Agent
│   │   ├── health_agent.py         # 健康评估Agent
│   │   ├── reminder_agent.py       # 提醒Agent
│   │   ├── psychology_agent.py     # 心理辅导Agent
│   │   ├── rehab_plan_agent.py     # 康复计划Agent
│   │   └── tools/                  # Agent工具集
│   ├── api/v1/                     # API路由层
│   │   └── endpoints/              # 各功能端点
│   ├── core/                       # 核心配置
│   │   ├── config.py               # 配置管理
│   │   ├── security.py             # JWT认证
│   │   ├── ws_manager.py           # WebSocket管理
│   │   └── logging.py              # 结构化日志
│   ├── db/                         # 数据库连接
│   ├── models/                     # 数据模型
│   └── services/                   # 业务逻辑层 (20+服务)
├── data/                           # 医疗数据
│   ├── ent_aug/                    # 实体增强数据
│   └── guidelines/                 # 临床指南PDF
├── database/                       # 数据库工具
├── docs/                           # 项目文档
├── finetune_demo/                  # 模型微调演示
├── model/                          # 预训练模型
├── scripts/                        # 初始化脚本
│   ├── init_mysql.py               # MySQL初始化
│   ├── build_up_graph.py           # 知识图谱构建
│   ├── seed_users.py               # 种子用户数据
│   └── seed_checkins_*.py          # 打卡数据种子
├── tests/                          # 测试代码
│   ├── unit/                       # 单元测试
│   ├── eval/                       # 模型评估
│   └── scripts/                    # 测试脚本
├── static/                         # 静态文件
├── docker-compose.yml              # Docker编排
├── Dockerfile                      # 后端镜像
├── Dockerfile.vue                  # 前端镜像
├── nginx.conf                      # Nginx配置
├── requirements.txt                # Python依赖
├── requirements-ci.txt             # CI轻量依赖
├── run.py                          # 统一启动入口
└── run_backend.py                  # 仅启动后端
```

---

## 🚀 快速开始

### 方式一：Docker Compose (推荐)

```bash
# 克隆项目
git clone https://github.com/LazyOIGG/Postop-Mgmt-System.git
cd Postop-Mgmt-System

# 配置环境变量
cp .env.example .env
# 编辑 .env 填写必要配置

# 启动所有服务
docker-compose up -d

# 访问系统
# 前端: http://localhost
# API文档: http://localhost:8000/docs
```

### 方式二：本地开发

#### 1. 环境准备

**Python版本**: 3.11+

```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

#### 2. 配置环境变量

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
SECRET_KEY=your_random_secret_key_here
```

#### 3. 数据库初始化

确保MySQL和Neo4j服务已启动：

```bash
# 初始化MySQL数据库
python scripts/init_mysql.py

# 构建知识图谱
python scripts/build_up_graph.py

# 导入种子数据（可选）
python scripts/seed_users.py
```

#### 4. 启动后端

```bash
# 仅启动FastAPI后端
python run_backend.py

# 或使用uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 5. 启动Vue前端

```bash
# 进入前端目录
cd ../postop-mgmt-frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 6. 访问系统

| 服务 | 地址 | 说明 |
|------|------|------|
| **Vue前端** | http://localhost:5173 | 患者端/医生端 |
| **API文档** | http://localhost:8000/docs | Swagger UI |
| **健康检查** | http://localhost:8000/health | 系统状态 |
| **Prometheus** | http://localhost:8000/metrics | 监控指标 |

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
| **RehabPlanAgent** | 康复计划管理 | LLM + 工具调用 |

### 调度流程

```
用户输入 → CoordinatorAgent (LLM意图分析)
               │
   ┌───────────┼────────────┬──────────────┬──────────────┐
   ▼           ▼            ▼              ▼              ▼
MedicalQA  HealthAssessment  Reminder  Psychology  RehabPlan
医学问答    健康风险评估    用药复查提醒  心理辅导缓解  康复计划管理
(KG-RAG)   (规则+LLM)     (LLM)        (LLM)       (LLM+Tools)
```

---

## 🌐 Vue前端功能

### 患者端

| 功能 | 路由 | 说明 |
|------|------|------|
| 首页概览 | `/patient/home` | 健康数据总览 |
| AI问诊 | `/patient/chat` | 多模态智能聊天 |
| 每日打卡 | `/patient/checkin` | 健康数据记录 |
| 健康档案 | `/patient/profile` | 个人健康信息 |
| 康复中心 | `/patient/rehab/*` | 计划/任务/指标/日历/成就 |
| 医患消息 | `/patient/messages` | 与医生沟通 |

### 医生端

| 功能 | 路由 | 说明 |
|------|------|------|
| 仪表盘 | `/doctor/dashboard` | 统计/高风险/异常 |
| 患者管理 | `/doctor/patients` | 患者列表与详情 |
| 告警中心 | `/doctor/alerts` | 待处理/已处理告警 |
| 消息中心 | `/doctor/messages` | 医患消息 |
| 统计分析 | `/doctor/statistics` | 系统统计数据 |

### 技术特性

- **双Token机制**: access_token + refresh_token，支持无感刷新
- **SSE流式响应**: AI聊天实时输出
- **WebSocket推送**: 通知与告警实时推送
- **请求去重**: 相同GET请求自动取消前一个

---

## 📊 API端点

### 认证模块 `/api/v1/auth`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/login` | POST | 用户登录 |
| `/register` | POST | 用户注册 |
| `/refresh` | POST | 刷新Token |
| `/logout` | POST | 用户登出 |
| `/me` | GET | 获取当前用户 |

### 聊天模块 `/api/v1/chat` & `/api/v1/sessions`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/chat` | POST | 多智能体聊天（支持SSE流式） |
| `/sessions/create` | POST | 创建会话 |
| `/sessions/user/{username}` | GET | 获取用户会话列表 |
| `/sessions/{sessionId}/messages` | GET | 获取会话消息 |

### 健康模块 `/api/v1/health` & `/api/v1/profile`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health/assess/text` | POST | 文本健康评估 |
| `/health/assess/image` | POST | 图片健康评估 |
| `/health/assess/speech` | POST | 语音健康评估 |
| `/profile/me` | GET/POST | 个人档案管理 |

### 康复模块 `/api/v1/rehab-plan`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/generate` | POST | AI生成康复计划 |
| `/tasks/today` | GET | 今日任务 |
| `/tasks/complete` | POST | 完成任务 |
| `/{id}/calendar` | GET | 康复日历 |
| `/{id}/metrics` | GET/POST | 康复指标 |
| `/{id}/journals` | GET/POST | 康复日志 |
| `/{id}/achievements` | GET | 成就系统 |

### 医生端 `/api/v1/doctor`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/patients` | GET | 患者列表 |
| `/high-risk` | GET | 高风险患者 |
| `/abnormal-checkins` | GET | 异常打卡 |
| `/alerts` | GET | 告警列表 |
| `/alerts/process` | POST | 处理告警 |
| `/message` | POST | 发送消息 |

### 其他模块

| 模块 | 端点前缀 | 说明 |
|------|---------|------|
| 提醒 | `/api/v1/reminder` | 用药/复查提醒 |
| 通知 | `/api/v1/notifications` | 推送通知 |
| 统计 | `/api/v1/stats` | 数据统计 |
| 知识图谱 | `/api/v1/kg` | 疾病/药品/食物查询 |
| 多模态 | `/api/v1/multimodal` | OCR/STT/TTS |
| 文件上传 | `/api/v1/upload` | 图片/语音上传 |

---

## 🧪 测试

### 运行单元测试

```bash
# 运行所有测试
pytest tests/unit/

# 运行特定测试
pytest tests/unit/test_auth.py

# 运行并生成覆盖率报告
pytest tests/unit/ --cov=app --cov-report=html
```

### 测试脚本

```bash
# 测试DeepSeek API连接
python tests/scripts/test_deepseek.py

# 测试MySQL连接
python tests/scripts/test_mysql.py

# 测试语音识别
python tests/scripts/test_asr_recognition.py
```

### CI/CD

项目使用GitHub Actions进行持续集成：
- **触发条件**: push/PR 到 master/dev 分支
- **检查内容**: ruff lint + pytest 单元测试
- **依赖文件**: `requirements-ci.txt` (轻量版，不含ML库)

---

## 📈 监控与日志

### Prometheus指标

- `http_requests_total`: HTTP请求总数
- `http_request_duration_seconds`: 请求延迟

```bash
curl http://localhost:8000/metrics
```

### 结构化日志

- 开发环境: 彩色控制台输出
- 生产环境: JSON格式输出
- 请求级上下文: request_id, user

### 健康检查

```bash
curl http://localhost:8000/health
```

返回各组件状态：MySQL、Neo4j、Redis（可选）、LLM配置

---

## 🔧 环境变量说明

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `DEEPSEEK_API_KEY` | ✅ | - | DeepSeek API密钥 |
| `DEEPSEEK_BASE_URL` | ✅ | `https://api.deepseek.com` | API地址 |
| `DEEPSEEK_MODEL` | ✅ | `deepseek-chat` | 模型名称 |
| `NEO4J_URI` | ✅ | `bolt://localhost:7687` | Neo4j连接地址 |
| `NEO4J_USER` | ✅ | `neo4j` | Neo4j用户名 |
| `NEO4J_PASSWORD` | ✅ | - | Neo4j密码 |
| `MYSQL_HOST` | ✅ | `localhost` | MySQL主机 |
| `MYSQL_PORT` | ✅ | `3306` | MySQL端口 |
| `MYSQL_USER` | ✅ | `root` | MySQL用户名 |
| `MYSQL_PASSWORD` | ✅ | - | MySQL密码 |
| `MYSQL_DATABASE` | ✅ | `RAG` | 数据库名 |
| `SECRET_KEY` | ✅ | - | JWT签名密钥 |
| `ADMIN_USERNAME` | ❌ | `admin` | 管理员用户名 |
| `ADMIN_PASSWORD` | ❌ | - | 管理员密码 |
| `DASHSCOPE_API_KEY` | ❌ | - | 阿里云语音API |
| `REDIS_URL` | ❌ | - | Redis地址(可选) |
| `CORS_ORIGINS` | ❌ | `localhost:5173` | CORS白名单 |
| `DEBUG` | ❌ | `false` | 调试模式 |

完整配置请参考 [.env.example](.env.example)

---

## 📝 开发指南

### 代码规范

- 遵循PEP 8规范
- 使用ruff进行代码检查
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
- [x] 康复计划管理全流程
- [x] WebSocket实时通信
- [x] NER实体识别模型
- [x] 医生端功能
- [x] Vue前端（患者端+医生端）
- [x] 双Token认证机制
- [x] Docker容器化部署

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

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 [Issue](https://github.com/LazyOIGG/Postop-Mgmt-System/issues)
- 发送邮件至项目维护者

---

**最后更新**: 2026年6月27日
