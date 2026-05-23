# 全周期健康管理系统 — 后续功能更新计划

> 基于代码深度审查（2026-05-23），结合已有 `PROJECT_ROADMAP.md` 与 `P3_WORK_DIVISION.md`，
> 聚焦**尚未实现的功能**和**新发现的改进方向**，按优先级分层推进。
>
> **前端说明**: 前端已确定采用 **Vue3 + Vite + Element Plus** 方案，将完全替代 Streamlit。
> 本计划中后端 API 设计均面向 Vue3 对接，Streamlit 仅作为过渡期原型保留。

---

## 项目现状快照

| 维度 | 当前状态 | 缺口 |
|------|---------|------|
| **多智能体** | 5 Agent + Coordinator + 工具调用框架 | 工具集偏少，无 Agent 可观测性 |
| **对话记忆** | orchestrator 层历史加载 + 摘要压缩 | 仅进程内，重启丢失；无 Redis 持久化 |
| **知识图谱** | 单跳 Cypher 查询 | 无 text2cypher、无多跳推理、无可视化 |
| **通知系统** | config 中有间隔配置，但无 API 端点 | 需新建完整通知模块 |
| **语音交互** | ASR 可用 (Fun-ASR) | TTS synthesize 存在但前端未集成 |
| **前端** | Streamlit 过渡中；**Vue3 + Element Plus 开发中**，将替代全部 Streamlit | 后端需补齐 Vue3 所需的完整 API |
| **测试** | 无 | 零测试覆盖 |
| **部署** | 手动启动 | 无 Docker、无 CI/CD |
| **安全** | JWT + 密码加密 | bare except 33 处、盐值硬编码、CORS 全开 |
| **运维** | 无 | 无结构化日志、无监控、无 Redis |

---

## P0 — 通知系统 + WebSocket 实时通信（1.5 周）

> 通知是医患协作的核心闭环。Vue3 前端需要 WebSocket 实现实时推送，
> 这是前后端对接的第一个阻塞项。

### 1. 通知 API 端点

**新建文件**: `app/api/v1/endpoints/notifications.py`

```
GET    /api/v1/notifications/              — 通知列表 (?unread_only=true&page=1&size=20)
GET    /api/v1/notifications/unread-count  — 未读计数
POST   /api/v1/notifications/{id}/read     — 标记已读
POST   /api/v1/notifications/read-all      — 全部已读
```

**改动文件**:
- `app/api/v1/api.py` — 注册 notifications 路由
- `database/db_operation.py` — `init_database_tables()` 新增 `notifications` 表
- `database/local_db_utils.py` — 新增通知 CRUD 方法

**数据库表**:
```sql
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    type ENUM('doctor_message','alert','reminder','system') NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    related_id INT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username_read (username, is_read)
);
```

### 2. WebSocket 实时通信层（Vue3 必需）

**新建文件**: `app/api/v1/endpoints/ws.py`

**核心设计**:
```python
# WebSocket 连接管理
class ConnectionManager:
    """按用户名管理 WebSocket 连接，支持多标签页"""
    active_connections: Dict[str, List[WebSocket]]

    async def connect(websocket, username)
    async def disconnect(websocket, username)
    async def send_to_user(username, message)     # 单播
    async def send_to_doctors(message)             # 广播到所有医生
```

**消息协议** (JSON):
```json
// 通知推送
{"type": "notification", "data": {"id": 1, "title": "...", "content": "...", "type": "alert"}}

// 聊天流式回复
{"type": "chat_chunk", "data": {"content": "...", "agent": "MedicalQA"}}
{"type": "chat_complete", "data": {"session_id": 123}}

// 高风险告警 (推送到医生端)
{"type": "risk_alert", "data": {"username": "patient1", "level": "high", "summary": "..."}}
```

**改动文件**:
- `app/main.py` — 注册 WebSocket 路由
- `app/api/v1/endpoints/chat.py` — 聊天流式回复走 WebSocket 通道
- `app/services/doctor_service.py` — 医生发消息时触发通知推送

**Vue3 对接要点**:
- Vue3 使用原生 WebSocket 或 `vue-use` 的 `useWebSocket`
- 断线自动重连 + 心跳保活 (30s ping/pong)
- 消息到达后更新 Element Plus 的 `ElBadge` 角标

### 3. 响应格式标准化

所有 API 统一响应格式，方便 Vue3 Axios 拦截器统一处理：

```json
// 成功
{"code": 200, "message": "success", "data": {...}}

// 分页
{"code": 200, "message": "success", "data": {"list": [...], "total": 100, "page": 1, "size": 20}}

// 错误
{"code": 400, "message": "错误描述", "data": null}
```

**改动文件**: `app/main.py` — 新增统一响应包装中间件

**验收标准**:
- [ ] Vue3 建立 WebSocket 连接后，医生发消息 → 患者端实时收到通知
- [ ] 高风险告警 → 所有在线医生端实时收到推送
- [ ] 断线重连后，未读通知通过 HTTP API 补偿获取
- [ ] 所有 API 返回统一格式

---

## P1 — 知识图谱增强（2 周）

> 当前仅支持硬编码意图映射的单跳查询，无法处理复杂医疗问题。

### 1. Text2Cypher 模块

**新建文件**: `app/services/text2cypher_service.py`

**核心流程**:
```
用户查询 → NER + Intent
             │
             ├─ 已知意图 (14种) → 现有硬编码映射 (快速路径，保留)
             └─ 未知/复杂意图 → text2cypher (LLM 生成 Cypher)
                                    │
                                    ├─ 安全校验 (仅允许 MATCH/RETURN/WHERE)
                                    └─ Neo4j 执行 → 结果注入 Prompt
```

**改动文件**:
- `app/services/kg_service.py` — 新增 `text_to_cypher()` 和 `multi_hop_query()` 方法
- `app/agents/medical_qa_agent.py` — 在 KG-RAG 管线中集成 text2cypher 路径
- `app/core/config.py` — 新增 `KG_MAX_HOPS=3`, `KG_TEXT2CYPHER_ENABLED=True`

### 2. 多跳推理

支持形如 "XX 药物对做完 YY 手术的病人有什么风险？" 的复合查询：

```cypher
MATCH path = (d:疾病 {名称: $disease})-[*1..3]->(r)
WHERE r:药物 OR r:症状 OR r:并发症
RETURN nodes(path), relationships(path)
LIMIT 50
```

### 3. 知识图谱可视化 API（面向 Vue3）

**改动文件**:
- `app/api/v1/endpoints/kg.py` — 新增可视化 API

```
POST /api/v1/kg/visualize      — 查询子图，返回 nodes + edges JSON
GET  /api/v1/kg/schema          — 返回图谱 schema (实体类型、关系类型)
GET  /api/v1/kg/search?q=      — 实体模糊搜索 (用于 Vue3 搜索框自动补全)
```

**响应格式** (适配 vis-network / D3.js):
```json
{
  "nodes": [
    {"id": "n1", "label": "阿莫西林", "group": "药物"},
    {"id": "n2", "label": "头痛", "group": "症状"}
  ],
  "edges": [
    {"from": "n1", "to": "n2", "label": "副作用", "type": "副作用"}
  ]
}
```

**Vue3 可视化方案**: 使用 `vis-network` 或 `@vue-flow/core` 渲染交互式图谱。

**验收标准**:
- [ ] "感冒用什么药" → 命中现有快速路径，响应 < 1s
- [ ] "吃了阿莫西林后头痛加重" → 触发 text2cypher，返回多跳结果
- [ ] 输入 `'; DROP TABLE; //` → 被安全过滤器拦截
- [ ] Vue3 端可渲染查询涉及的子图，支持拖拽/缩放/点击节点

---

## P2 — 基础设施补齐（2 周）

> 为后续功能扩展打地基：缓存、测试、容器化。

### 1. Redis 集成

**改动文件**:
- `requirements.txt` — 新增 `redis[hiredis]`
- `app/core/config.py` — 新增 `REDIS_URL` 配置
- `app/core/security.py` — Token 存储迁移到 Redis (`SETEX`)
- `app/db/session.py` — 新增 Redis 连接管理

**提供回退**: 开发环境无 Redis 时自动降级为内存存储。

### 2. 测试体系建设

**新建目录**: `tests/`

```
tests/
├── conftest.py              # 公共 fixtures (mock DB, mock LLM)
├── test_api/
│   ├── test_auth.py         # 认证端点测试
│   ├── test_chat.py         # 聊天端点测试
│   ├── test_notifications.py # 通知端点测试
│   └── test_health.py       # 健康评估测试
├── test_agents/
│   ├── test_coordinator.py  # 路由准确性测试
│   └── test_tools.py        # 工具调用测试
├── test_services/
│   ├── test_kg_service.py   # 知识图谱查询测试
│   └── test_ner_service.py  # NER 模型测试
└── test_db/
    └── test_local_db_utils.py  # 数据库操作测试
```

**目标覆盖率**: 核心业务逻辑 > 60%

### 3. Docker Compose 一键部署

**新建文件**:
- `Dockerfile` — Python 3.10 + 后端依赖
- `Dockerfile.vue` — Node 20 + Vue3 构建 + Nginx 静态服务
- `docker-compose.yml` — 全栈编排
- `.dockerignore`
- `nginx.conf` — 反向代理（Vue3 静态文件 + API 转发）

```yaml
services:
  # ── 后端 ──
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports: ["8000:8000"]
    depends_on: [mysql, neo4j, redis]
    environment:
      - MYSQL_HOST=mysql
      - NEO4J_URI=bolt://neo4j:7687
      - REDIS_URL=redis://redis:6379

  # ── Vue3 前端 ──
  frontend:
    build:
      context: ../vue-frontend     # Vue3 项目路径
      dockerfile: Dockerfile.vue
    ports: ["80:80"]
    depends_on: [api]

  # ── 基础设施 ──
  mysql:
    image: mysql:8.0
    volumes: ["mysql_data:/var/lib/mysql"]
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}

  neo4j:
    image: neo4j:5-community
    ports: ["7474:7474", "7687:7687"]
    volumes: ["neo4j_data:/data"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

volumes:
  mysql_data:
  neo4j_data:
```

**Nginx 配置** (`nginx.conf`):
```nginx
server {
    listen 80;

    # Vue3 静态文件
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;   # SPA 路由支持
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket 代理
    location /api/v1/ws {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 4. CI/CD 流水线

**新建文件**: `.github/workflows/ci.yml`

```
触发: push / PR to master
步骤:
  1. ruff lint (后端代码风格)
  2. mypy check (类型检查，宽松模式)
  3. pytest (后端单元测试)
  4. Docker build (验证镜像构建)
```

**验收标准**:
- [ ] `docker-compose up` 一键启动全部服务（后端 + Vue3 + MySQL + Neo4j + Redis）
- [ ] `pytest` 通过率 > 90%
- [ ] CI 流水线绿灯
- [ ] Vue3 通过 Nginx 反向代理正常访问 API

---

## P3 — 安全加固（1 周）

> 消除已知安全风险，为生产部署做准备。

### 1. 密码安全

**改动文件**:
- `database/password_utils.py` — 盐值改为每用户随机生成
- `database/db_operation.py` — `users` 表新增 `salt` 字段
- `scripts/` — 所有测试脚本密码改为从 `.env` 读取

### 2. 异常处理精细化

**改动文件**: 按优先级逐文件修复
- `app/services/kg_service.py` — 优先（影响知识图谱可用性）
- `app/services/llm_service.py` — 优先（影响所有 Agent）
- `app/services/image_service.py`
- `app/api/v1/endpoints/stats.py`
- 其余文件

**规则**:
- 每个 `except` 改为具体异常类型 + `logger.error()` 记录
- 添加请求级 `trace_id`（UUID），贯穿日志全链路

### 3. CORS 收紧

**改动文件**: `app/main.py`
- `allow_origins` 从 `["*"]` 改为显式列出允许的域名
- 开发环境允许 `http://localhost:5173`（Vite 默认端口）
- 生产环境通过 `.env` 配置 `CORS_ORIGINS`

```python
# 开发环境
CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]

# 生产环境 (从 .env 读取)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",")
```

### 4. LLM 异常处理

**改动文件**: `app/services/llm_service.py`
- 定义 `LLMServiceError` 自定义异常（已有，确保所有路径抛出）
- 流式异常时在 SSE/JSON 中追加 `{"type":"error","error":"..."}` 事件
- Vue3 前端统一处理错误事件

**验收标准**:
- [ ] 无 bare except 残留
- [ ] 日志中每条请求可追溯到 trace_id
- [ ] CORS 仅允许配置的域名
- [ ] Vue3 开发服务器正常跨域请求后端

---

## P4 — 后端 API 完善（面向 Vue3）（2 周）

> Streamlit 时代前端逻辑与后端耦合在同一个 Python 进程中。
> Vue3 是纯前端 SPA，需要后端提供完整、规范的 RESTful API。
> 本阶段补齐 Vue3 页面所需的全部 API 端点。

### 1. API 响应与分页规范

**新建文件**: `app/core/response.py`

```python
class ApiResponse:
    @staticmethod
    def success(data=None, message="success"):
        return {"code": 200, "message": message, "data": data}

    @staticmethod
    def error(code=400, message="error"):
        return {"code": code, "message": message, "data": None}

    @staticmethod
    def paginated(list_data, total, page, size):
        return {
            "code": 200, "message": "success",
            "data": {"list": list_data, "total": total, "page": page, "size": size}
        }
```

### 2. 补齐 Vue3 页面所需 API

**改动文件**: `app/api/v1/endpoints/` 下各文件

| Vue3 页面 | 所需 API | 当前状态 | 改动 |
|-----------|---------|---------|------|
| 登录/注册 | `POST /auth/login`, `POST /auth/register` | 已有 | 统一响应格式 |
| 聊天 | `POST /chat` (SSE 流式) | 已有 | 新增 WebSocket 通道 |
| 会话列表 | `GET /sessions`, `POST /sessions`, `DELETE /sessions/{id}` | 已有 | 补充分页 |
| 健康打卡 | `POST /checkin`, `GET /checkin/history` | 已有 | 补充日期范围查询 |
| 健康概览 | `GET /overview/trends`, `GET /overview/summary` | 已有 | 补充图表数据格式 |
| 提醒中心 | `GET /reminder`, `POST /reminder`, `PUT /reminder/{id}` | 已有 | 补充分页+筛选 |
| 康复计划 | `GET /rehab-plan`, `POST /rehab-plan` | 已有 | 补充进度更新 |
| 健康档案 | `GET /profile`, `PUT /profile` | 已有 | 补充头像上传 |
| 知识图谱 | `POST /kg/visualize`, `GET /kg/schema` | 需新建 | P1 中实现 |
| 通知 | `GET /notifications/...` | 需新建 | P0 中实现 |
| 医生面板 | `GET /doctor/patients`, `GET /doctor/patient/{id}` | 已有 | 补充风险排序+详情 |
| 管理后台 | 用户管理、系统统计、图谱管理 | **缺失** | **本阶段新建** |

### 3. 管理后台 API（新建）

**新建文件**: `app/api/v1/endpoints/admin.py`

```
GET    /api/v1/admin/users                    — 用户列表 (分页+搜索)
PUT    /api/v1/admin/users/{id}/status        — 启用/禁用用户
POST   /api/v1/admin/users/{id}/reset-password — 重置密码
GET    /api/v1/admin/stats/overview            — 系统统计概览
GET    /api/v1/admin/stats/agent-usage         — Agent 路由使用统计
GET    /api/v1/admin/stats/daily-active        — 日活用户趋势
```

**改动文件**:
- `app/api/v1/api.py` — 注册 admin 路由
- `app/core/security.py` — 新增管理员权限校验装饰器
- `database/local_db_utils.py` — 新增管理查询方法

### 4. 数据导出 API

**新建文件**: `app/services/report_service.py`

```
GET /api/v1/reports/health-summary/{username}  — 个人健康周报/月报 (PDF)
GET /api/v1/reports/doctor-patient-list         — 医生端患者数据导出 (CSV)
```

**依赖**: `reportlab` (PDF 生成)

### 5. SSE 流式聊天优化（Vue3 对接）

**改动文件**: `app/api/v1/endpoints/chat.py`

Vue3 使用 `EventSource` 或 `fetch + ReadableStream` 消费 SSE，需确保：
- SSE 格式严格遵循 `data: {...}\n\n`
- 流结束时发送 `data: [DONE]\n\n`
- 错误时发送 `data: {"type":"error","error":"..."}\n\n`
- 设置正确的 `Content-Type: text/event-stream` 和 `Cache-Control: no-cache`

**验收标准**:
- [ ] Vue3 所有页面均有对应 API 端点
- [ ] 所有列表 API 支持分页 (`?page=1&size=20`)
- [ ] 管理后台 API 可用（用户管理+系统统计）
- [ ] SSE 流式聊天在 Vue3 `EventSource` 中正常工作
- [ ] API 响应格式 100% 统一

---

## P5 — 智能预警与决策支持（3 周）

> 从被动问答升级为主动健康管理。

### 1. 时序异常检测

**新建文件**: `app/services/anomaly_service.py`

**核心逻辑**:
- 分析患者近 7 天打卡数据的体征趋势（体温、血压、血糖、心率）
- 基于滑动窗口 + Z-score 检测异常波动
- 异常触发自动告警 → 写入 notifications 表 → WebSocket 推送到医生端

**改动文件**:
- `app/agents/health_agent.py` — 集成异常检测结果
- `app/api/v1/endpoints/overview.py` — 新增趋势异常标注 API

### 2. 高危患者自动置顶

**改动文件**:
- `app/services/doctor_service.py` — 患者列表按风险等级排序
- API 返回中增加 `risk_level` 字段，Vue3 前端据此排序+颜色标记

### 3. 康复进度追踪

**改动文件**:
- `app/api/v1/endpoints/rehab_plan.py` — 新增进度更新 API
- `app/services/rehab_plan_service.py` — 康复进度计算逻辑

**Vue3 前端展示**: Element Plus `ElProgress` 进度条 + `ElTimeline` 里程碑

**验收标准**:
- [ ] 连续 3 天体温上升 → 医生端 WebSocket 收到告警
- [ ] 医生面板 API 返回按风险排序的患者列表
- [ ] 患者可查看康复计划完成进度

---

## P6 — 模型优化与微调（4 周）

> 提升垂直领域准确率。

### 1. NER 模型微调

**数据**: `data/ner_data_aug.txt` (已有增强数据)
**方法**: 基于现有 RoBERTa 模型做 LoRA 微调
**目标**: 术后特有实体（引流管、伤口状态、术后并发症）F1 > 0.85

**改动文件**:
- `finetune_demo/` — 复用已有微调管线
- `scripts/ner_finetune.py` — 新建微调脚本
- `app/services/ner_service.py` — 加载微调后模型

### 2. LLM SFT 微调

**数据**: `data/lora_data/` (已有)
**方法**: DeepSeek / Qwen SFT
**目标**: 术后管理领域回答准确率提升，减少幻觉

### 3. 评测基准

**新建文件**: `tests/eval/`

```
tests/eval/
├── eval_ner.py          # NER F1-score 评测
├── eval_qa.py           # 医学问答准确率评测
├── eval_data/           # 评测数据集
│   ├── ner_test.json
│   └── qa_test.json
└── README.md            # 评测说明
```

**验收标准**:
- [ ] NER F1-score 相比基线提升 > 5%
- [ ] 医学问答准确率 > 80%（基于评测集）

---

## P7 — 可观测性与运维（2 周）

### 1. 结构化日志

**改动文件**: 全局
- 引入 `structlog`，替换所有 `print()` 语句
- 统一日志格式: `timestamp | level | trace_id | module | message`
- 日志输出到文件 + 控制台

### 2. 性能监控

**新建文件**: `app/api/v1/endpoints/metrics.py`

```
GET /metrics  — Prometheus 格式指标
```

**指标**:
- API 请求延迟 (histogram)
- LLM 调用延迟 + Token 消耗
- NER 推理延迟
- 数据库查询延迟
- 活跃 WebSocket 连接数 (gauge)

### 3. 健康检查增强

**改动文件**: `app/main.py`
- `/health` 端点检查 MySQL + Neo4j + Redis + LLM API 连通性
- 返回各组件状态和延迟

**验收标准**:
- [ ] 日志中无 `print()` 残留
- [ ] `/metrics` 端点返回有效 Prometheus 指标
- [ ] `/health` 端点报告各组件状态

---

## P8 — 长期演进方向（按需推进）

> 以下功能根据实际需求择机启动，不设固定时间线。

### 1. 多语言国际化
- Vue3 前端 i18n（`vue-i18n`，中/英文切换）
- LLM 多语言回答（利用 DeepSeek 多语言能力）
- 适用场景：海外医疗机构合作

### 2. 移动端适配
- Vue3 本身支持响应式布局，配合 Element Plus 断点适配
- 可进一步封装为 PWA（离线缓存 + 桌面图标）
- 或使用 uni-app / Capacitor 打包为原生 App

### 3. 药物相互作用检测
- Neo4j 知识图谱中增加药物相互作用关系
- Agent 工具调用时自动检查用药冲突
- 高风险组合立即告警

### 4. 患者社区 / 互助模块
- 同病种患者匿名交流
- 康复经验分享
- 医生精选问答

### 5. 对接外部系统
- HIS/EMR 系统对接（HL7 FHIR）
- 微信公众号/小程序推送
- 医保结算接口

---

## 执行路线图

```
                    Week 1-2       Week 3-4       Week 5-6       Week 7+
                    ──────────     ──────────     ──────────     ─────────
Phase 1 (基础):     P0 通知+WS     P2 基础设施     P3 安全加固     稳定化
                    ┃              ┃              ┃
Phase 2 (能力):     P1 KG增强      P4 API完善      P5 智能预警
                    ┃              ┃              ┃
Phase 3 (优化):                                     P6 模型微调     P7 可观测性
                                                    ┃
Phase 4 (演进):                                              P8 按需启动
```

> **并行策略**: P0/P1 可由两人并行（一人做通知+WebSocket，一人做 KG 增强）。
> P4 需要与 Vue3 前端开发紧密配合，建议前后端联调推进。

## 依赖关系

```
P0 通知系统 + WebSocket ─────────────────┐
P1 KG增强 ───────────────────────────────┤
P2 基础设施 (Redis) ──┬──────────────────┼──→ P5 智能预警
                      ├──→ P3 安全加固   │
                      └──→ P4 API完善    ├──→ P6 模型微调
                         (面向 Vue3)     └──→ P7 可观测性
P8 长期演进 ── 无硬依赖，按需启动
```

---

## 工作量估算

| 阶段 | 项目 | 预计工时 | 新建文件 | 改动文件 |
|------|------|---------|---------|---------|
| P0 | 通知系统 + WebSocket | 1.5 周 | 2 | 5 |
| P1 | KG 增强 | 2 周 | 1 | 4 |
| P2 | 基础设施 | 2 周 | 15+ | 3 |
| P3 | 安全加固 | 1 周 | 0 | 10+ |
| P4 | API 完善 (Vue3 对接) | 2 周 | 3 | 10+ |
| P5 | 智能预警 | 3 周 | 1 | 5 |
| P6 | 模型微调 | 4 周 | 3 | 3 |
| P7 | 可观测性 | 2 周 | 1 | 全局 |
| **合计** | | **约 17.5 周** | **26+** | **40+** |

---

## 维护约定

- 每个 Phase 完成后更新本文档状态
- 已完成项标记 `~~删除线~~` 并注明日期
- 新需求通过 Issue 讨论后加入对应 Phase
- 每月回顾一次优先级，根据实际情况调整

---

*本文档由代码审查自动生成，最后更新: 2026-05-23*
*已根据 Vue3 + Vite + Element Plus 前端方案调整*
