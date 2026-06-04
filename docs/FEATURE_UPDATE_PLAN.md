你大# 全周期健康管理系统 — 后续功能更新计划

> **修订版**: 基于 2026-06-01 深度代码审查，全面更新了项目现状快照和各项完成状态。
>
> **分工说明**: 剩余工作平等分为 **A / B / C 三条并行开发线**，各线独立推进、互不阻塞。
>
> **前端说明**: 前端已确定采用 **Vue3 + Vite + Element Plus** 方案，正在开发中，
> 将完全替代 Streamlit。本计划中所有 API 设计均面向 Vue3 对接。
>
> **排除范围**: 康复计划模块（`rehab_plan_agent.py`、`rehab_plan_service.py`、`rehab_plan.py`、
> `rehab_plan_tools.py` 及相关数据库操作）已有其他开发者负责，**三条线均不涉及**。

---

## 项目现状快照 (2026-06-01 更新)

| 维度       | 当前状态                                               | 关键缺口                                                      |
|----------|----------------------------------------------------|-----------------------------------------------------------|
| **认证系统** | ✅ JWT 认证已实现 (`PyJWT`)，支持 access + refresh token | ⚠️ 黑名单/refresh token 存内存，重启丢失；无 Redis 持久化；CORS 全开 `*`；无 `require_admin` 依赖注入 |
| **多智能体** | ✅ 6 Agent (Coordinator + MedicalQA + Health + Reminder + Psychology + RehabPlan) + 12 个工具 | ⚠️ Coordinator 纯 LLM 路由无兜底重试；无路由可观测性指标 |
| **对话记忆** | ✅ orchestrator 层 MySQL 加载 + LLM 摘要压缩              | ⚠️ 仅进程内缓存；无 Redis；摘要丢失上下文；压缩策略简单 |
| **知识图谱** | ✅ Neo4j 连接正常，14 种意图映射 + 多跳查询 + schema API + 可视化 API | ⚠️ Cypher 字符串拼接存在注入风险；无 text2cypher；无参数化查询 |
| **通知系统** | ✅ notifications 表已建；REST API (列表/未读计数/标记已读)；WebSocket 基础推送 | ⚠️ ConnectionManager 仅支持单连接/用户；无心跳；无消息队列 |
| **健康评估** | ✅ 三级风险关键词 + 体温/血压正则 + LLM 建议生成              | ⚠️ 无时序异常检测；无滑动窗口/Z-score 分析 |
| **康复计划** | ✅ RehabPlan Agent + Service + API 全链路              | ⚠️ **已有其他开发者负责，本计划不涉及** |
| **医生端**   | ✅ 患者列表、告警、医患消息、通知推送                          | ⚠️ 无风险排序；分页不完善 |
| **文件上传** | ✅ 图片/语音上传 API (`/api/v1/upload`)                  | ⚠️ 无头像裁剪/压缩；无文件大小限制配置 |
| **语音交互** | ✅ ASR 可用 (Fun-ASR)；TTS 接口存在 (`CosyVoice`)       | ⚠️ TTS 未在前端集成；无流式语音对话 |
| **统一响应** | ✅ `ApiResponse` 类已实现 (ok/fail/paginated)           | ⚠️ 部分端点仍直接返回 dict 而非统一格式 |
| **全局异常** | ✅ HTTPException + RequestValidationError + Exception 处理器 | ⚠️ 请求级 trace_id 未实现 |
| **数据库**   | ✅ MySQL 连接池 + 完整 CRUD 操作                          | ⚠️ 全局单例 `db_instance` 无线程安全保障；连接复用逻辑需审查 |
| **前端**   | Streamlit 过渡中；**Vue3 + Element Plus 开发中**          | 后端部分 API 响应格式待统一；缺管理后台 API                                  |
| **测试**   | ❌ 零正式测试覆盖；仅 4 个手动连接测试脚本 (scripts/)               | 无 pytest、无 mock、无 CI                                      |
| **部署**   | ❌ 手动 `run.py` 启动                                     | 无 Docker、无 CI/CD                                          |
| **安全**   | ⚠️ SHA-256+盐值加密；CORS 全开 `*`                         | bare except 残留；盐值在 password_utils 中硬编码生成；SECRET_KEY 可能弱密码 |
| **运维**   | ⚠️ print 输出日志 + 基础 `logging`                         | 无结构化日志、无监控、无 Prometheus 指标                                        |

---

## ✅ 已完成

> 以下功能在 2026-05-25 的 "JWT认证重构 + ApiResponse统一响应 + 全局异常处理" 提交中已完成。

- [x] **JWT 认证替换**: `app/core/security.py` 使用 PyJWT 实现 access/refresh token 签发与验证
- [x] **统一响应格式**: `app/core/response.py` 提供 `ApiResponse.ok()`, `ApiResponse.fail()`, `ApiResponse.paginated()`
- [x] **全局异常处理**: `app/main.py` 包含 HTTPException, RequestValidationError, Exception 三级处理器
- [x] **多智能体架构**: 6 Agent + Coordinator + 12 个工具，编排完整
- [x] **通知 REST API**: `app/api/v1/endpoints/notifications.py` 已实现基本 CRUD
- [x] **知识图谱 API**: schema、可视化、多跳查询端点已有
- [x] **康复计划**: Agent + Service + API 全链路（**已有其他开发者负责**）
- [x] **文件上传**: `app/api/v1/endpoints/upload.py` 已实现
- [x] **医生端**: 患者列表、消息、告警端点已有

---

# 🅰️ A 线 — 基础设施与实时通信

> **负责人**: ___ | **预计工时**: ~6 周 | **关键词**: Redis、WebSocket、Docker、测试

> 本线聚焦 "地基"：让认证持久化、WebSocket 可靠、项目可容器化部署、有测试保障。
> 与其他两线**零文件冲突**，可完全并行。

---

## A1 — JWT 认证持久化 + CORS 收紧（0.5 周）

> JWT 本身已实现，但 token 黑名单和 refresh token 存内存，重启全部丢失。
> CORS 全开存在安全隐患。

### 1. JWT 黑名单 & Refresh Token 迁移到 Redis

**改动文件**:
- `app/core/security.py` — `_token_blacklist` 和 `_refresh_tokens` 迁移到 Redis
- `app/core/config.py` — 新增 `REDIS_URL` 配置
- `app/db/session.py` — 新增 Redis 连接管理（单例，带连接池）

**核心设计**:
```python
# Redis key 设计
jti:blacklist:{jti} → TTL = token 剩余过期时间
refresh:token:{jti} → username, TTL = REFRESH_TOKEN_EXPIRE_DAYS

# 回退机制: REDIS_URL 为空时降级为内存存储（开发环境兼容）
```

### 2. CORS 收紧

**改动文件**: `app/main.py`, `app/core/config.py`

```python
# 新增配置项
CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]
# 开发: 允许 Vue3 Vite 端口
# 生产: 从环境变量读取
```

### 3. Admin 权限依赖注入

**改动文件**: `app/core/security.py`

```python
def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
```

**验收标准**:
- [ ] 服务器重启后，已登录用户的 refresh token 仍有效
- [ ] CORS 仅允许配置的域名

---

## A2 — WebSocket 重构（1.5 周）

> Vue3 需要 WebSocket 实现实时通知推送和聊天流式回复。
> 当前 ConnectionManager 仅支持单连接，无心跳机制。

### 1. ConnectionManager 重构

**新建文件**: `app/core/ws_manager.py`
**改动文件**: `app/api/v1/endpoints/chat.py` — 导入新的 ws_manager

**当前问题**:
- `active_connections: Dict[str, WebSocket]` 仅支持单连接，多标签页会覆盖
- 无心跳机制，连接会因超时被 Nginx/代理断开
- 无消息队列，离线消息丢失

**新设计**:
```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}  # 支持多连接
        self._heartbeat_task = None

    async def connect(self, username: str, websocket: WebSocket):
        """支持同一用户多标签页连接"""
        await websocket.accept()
        self.active_connections.setdefault(username, []).append(websocket)

    def disconnect(self, username: str, websocket: WebSocket):
        conns = self.active_connections.get(username, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.active_connections.pop(username, None)

    async def send_to_user(self, username: str, data: dict):
        """发送到用户所有连接，自动清理死连接"""
        conns = self.active_connections.get(username, [])
        dead = []
        for ws in conns:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(username, ws)

    async def send_to_all_doctors(self, data: dict):
        """广播到所有在线医生"""
        for username, conns in self.active_connections.items():
            await self.send_to_user(username, data)

    async def heartbeat_loop(self, interval=30):
        """定期 ping 保持连接活跃"""
        while True:
            await asyncio.sleep(interval)
            for username, conns in list(self.active_connections.items()):
                for ws in list(conns):
                    try:
                        await ws.send_text('{"type":"ping"}')
                    except Exception:
                        self.disconnect(username, ws)
```

### 2. WebSocket 消息协议标准化

```json
// ── 通知推送 ──
{"type": "notification", "data": {"id": 1, "title": "...", "content": "...", "notification_type": "alert"}}

// ── 聊天流式回复 ──
{"type": "chat_start", "data": {"session_id": 123, "agent": "MedicalQA"}}
{"type": "chat_chunk", "data": {"content": "...", "agent": "MedicalQA"}}
{"type": "chat_complete", "data": {"session_id": 123}}

// ── 高风险告警 (推送到医生端) ──
{"type": "risk_alert", "data": {"username": "patient1", "level": "high", "summary": "..."}}

// ── 心跳 ──
{"type": "ping"}  // 服务端发送
{"type": "pong"}  // 客户端回复
```

### 3. 通知 API 补全

**改动文件**: `app/api/v1/endpoints/notifications.py`

现有端点:
- `GET /notifications/unread-count` ✅
- `GET /notifications` ✅
- `PUT /notifications/{id}/read` ✅
- `PUT /notifications/read-all` ✅

需补全:
- `DELETE /notifications/{id}` — 删除通知
- 分页支持 (`?page=1&size=20`)

**验收标准**:
- [ ] Vue3 建立 WebSocket 连接后，医生发消息 → 患者端实时收到通知
- [ ] 高风险告警 → 所有在线医生端实时收到推送
- [ ] 同一用户多标签页均能收到消息
- [ ] 断线重连后，未读通知通过 HTTP API 补偿获取
- [ ] 30s 心跳保活，Nginx 代理下不超时断开

---

## A3 — 基础设施补齐（2 周）

### 1. Redis 集成

**改动文件**:
- `requirements.txt` — 新增 `redis[hiredis]`
- `app/core/config.py` — 新增 `REDIS_URL` 配置
- `app/db/session.py` — 新增 Redis 连接管理（单例，带连接池）
- `app/core/security.py` — JWT 黑名单存 Redis（已在 A1 完成）
- `app/agents/orchestrator.py` — 对话摘要缓存到 Redis

**提供回退**: 开发环境无 Redis 时自动降级为内存存储。

### 2. 测试体系建设

**新建目录**: `tests/`

```
tests/
├── conftest.py              # 公共 fixtures (mock DB, mock LLM, test client)
├── test_api/
│   ├── test_auth.py         # 登录/注册/token 刷新测试
│   ├── test_chat.py         # 聊天 SSE + WebSocket 测试
│   ├── test_notifications.py # 通知 CRUD + WebSocket 推送测试
│   ├── test_health.py       # 健康评估测试
│   ├── test_checkin.py      # 打卡测试
│   └── test_doctor.py       # 医生端 API 测试
├── test_agents/
│   ├── test_coordinator.py  # 路由准确性测试（20 条典型输入）
│   ├── test_medical_qa.py   # 医学问答 Agent 测试
│   └── test_tools.py        # 工具调用测试
├── test_services/
│   ├── test_kg_service.py   # 知识图谱查询测试（mock Neo4j）
│   ├── test_ner_service.py  # NER 模型测试
│   └── test_health_service.py # 风险评估规则测试
└── test_db/
    └── test_local_db_utils.py  # 数据库操作测试
```

**目标覆盖率**: 核心业务逻辑 > 60%

**新增依赖**: `pytest`, `pytest-asyncio`, `httpx`（FastAPI TestClient）

### 3. Docker Compose 一键部署

**新建文件**:
- `Dockerfile` — Python 3.10 + 后端依赖
- `Dockerfile.vue` — Node 20 + Vue3 构建 + Nginx 静态服务
- `docker-compose.yml` — 全栈编排
- `.dockerignore`
- `nginx.conf` — 反向代理（Vue3 静态文件 + API 转发 + WebSocket 代理）

```yaml
services:
  api:
    build: .
    ports: ["8000:8000"]
    depends_on: [mysql, neo4j, redis]
    env_file: .env

  frontend:
    build:
      context: ../vue-frontend
      dockerfile: Dockerfile.vue
    ports: ["80:80"]
    depends_on: [api]

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

### 4. CI/CD 流水线

**新建文件**: `.github/workflows/ci.yml`

```
触发: push / PR to master
步骤:
  1. ruff check (代码风格)
  2. pytest (后端单元测试)
  3. Docker build (验证镜像构建)
```

**验收标准**:
- [ ] `docker-compose up` 一键启动全部服务
- [ ] `pytest` 通过率 > 90%
- [ ] CI 流水线绿灯
- [ ] Vue3 通过 Nginx 反向代理正常访问 API + WebSocket

---

## A4 — 可观测性与运维（2 周）

### 1. 结构化日志

**改动文件**: 全局
- 引入 `structlog`，替换所有 `print()` 语句
- 统一日志格式: `timestamp | level | trace_id | module | message`
- 日志输出到文件 + 控制台
- `app/main.py` — 日志中间件记录请求耗时

### 2. 性能监控

**新建文件**: `app/api/v1/endpoints/metrics.py`

```
GET /metrics  — Prometheus 格式指标
```

**指标**:
- API 请求延迟（histogram）
- LLM 调用延迟 + Token 消耗
- NER 推理延迟
- 数据库查询延迟
- 活跃 WebSocket 连接数（gauge）
- Agent 路由分布（counter per agent）

### 3. 健康检查增强

**改动文件**: `app/main.py`

```python
@app.get("/health")
async def health_check():
    checks = {
        "mysql": await check_mysql(),
        "neo4j": await check_neo4j(),
        "redis": await check_redis(),
        "llm": await check_llm_api(),
    }
    status = "healthy" if all(c["ok"] for c in checks.values()) else "degraded"
    return {"status": status, "checks": checks, "timestamp": datetime.now().isoformat()}
```

**验收标准**:
- [ ] 日志中无 `print()` 残留
- [ ] `/metrics` 端点返回有效 Prometheus 指标
- [ ] `/health` 端点报告各组件状态和延迟

---

### 🅰️ A 线文件清单汇总

| 操作   | 文件                                                  |
|------|-----------------------------------------------------|
| 新建   | `app/core/ws_manager.py`                            |
| 新建   | `tests/` 目录及 13 个测试文件                             |
| 新建   | `Dockerfile`, `Dockerfile.vue`, `docker-compose.yml` |
| 新建   | `.dockerignore`, `nginx.conf`                       |
| 新建   | `.github/workflows/ci.yml`                          |
| 新建   | `app/api/v1/endpoints/metrics.py`                   |
| 改动   | `app/core/security.py`                              |
| 改动   | `app/core/config.py`                                |
| 改动   | `app/db/session.py`                                 |
| 改动   | `app/main.py`                                       |
| 改动   | `app/api/v1/endpoints/chat.py`                      |
| 改动   | `app/api/v1/endpoints/notifications.py`             |
| 改动   | `app/agents/orchestrator.py`                        |
| 改动   | `requirements.txt`                                  |
| 全局改动 | 所有含 `print()` 的文件（结构化日志替换）                       |

---

# 🅱️ B 线 — 知识图谱安全与 API 层

> **负责人**: ___ | **预计工时**: ~6 周 | **关键词**: Cypher 安全、Text2Cypher、管理后台、API 统一

> 本线聚焦 "安全 + API 完善"：修复注入风险、补全新 API 端点、统一响应格式。
> 与其他两线**零文件冲突**，可完全并行。

---

## B1 — 知识图谱安全加固 + Text2Cypher（2 周）

### 1. Cypher 注入修复（安全优先）

**改动文件**: `app/services/kg_service.py`

**当前问题**:
```python
# 危险：字符串拼接 (第26行)
sql_q = "match (a:疾病{名称:'%s'}) return a.%s" % (entity, shuxing)
# 危险：字符串拼接 (第39行)
sql_q = "match (a:疾病{名称:'%s'})-[r:%s]->(b:%s) return b.名称" % (entity, lianxi, target)
```

**修复方案**: 全部改为参数化查询
```python
# 安全：参数化
result = self.client.run(
    "MATCH (a:疾病 {名称: $name}) RETURN a." + validated_property,
    name=entity
)
```

属性名白名单校验：
```python
ALLOWED_PROPERTIES = {"疾病简介", "疾病病因", "预防措施", "治疗周期", "治愈概率", ...}
ALLOWED_RELATIONSHIPS = {"疾病使用药品", "疾病宜吃食物", "疾病忌吃食物", ...}

if shuxing not in ALLOWED_PROPERTIES:
    raise ValueError(f"非法属性: {shuxing}")
if lianxi not in ALLOWED_RELATIONSHIPS:
    raise ValueError(f"非法关系: {lianxi}")
```

### 2. Text2Cypher 模块

**新建文件**: `app/services/text2cypher_service.py`

**核心流程**:
```
用户查询 → NER + Intent
             │
             ├─ 已知意图 (14种) → 现有硬编码映射 (快速路径，保留)
             └─ 未知/复杂意图 → text2cypher (LLM 生成 Cypher)
                                    │
                                    ├─ 安全校验 (仅允许 MATCH/RETURN/WHERE/WITH)
                                    ├─ 参数化提取实体值
                                    └─ Neo4j 执行 → 结果注入 Prompt
```

**安全校验**:
```python
def validate_cypher(cypher: str) -> bool:
    """仅允许只读操作"""
    forbidden = ["CREATE", "DELETE", "DETACH", "SET", "REMOVE", "MERGE", "DROP"]
    upper = cypher.upper()
    return not any(kw in upper for kw in forbidden)
```

**改动文件**:
- `app/services/kg_service.py` — 新增 `text_to_cypher()` 和安全校验
- `app/agents/medical_qa_agent.py` — 集成 text2cypher 路径
- `app/core/config.py` — 新增 `KG_MAX_HOPS=3`, `KG_TEXT2CYPHER_ENABLED=True`

### 3. 知识图谱搜索 API 补全

**改动文件**: `app/api/v1/endpoints/kg.py`

```
GET  /api/v1/kg/search?q=      — 实体模糊搜索（用于 Vue3 搜索框自动补全）
GET  /api/v1/kg/diseases        — 疾病列表（补充分页）
```

**验收标准**:
- [ ] "感冒用什么药" → 命中现有快速路径，响应 < 1s
- [ ] "吃了阿莫西林后头痛加重" → 触发 text2cypher，返回多跳结果
- [ ] 输入 `'; DROP TABLE; //` → 被安全过滤器拦截
- [ ] Vue3 端可渲染查询涉及的子图，支持拖拽/缩放/点击节点

---

## B2 — 安全加固（1 周）

### 1. 密码安全

**改动文件**:
- `database/password_utils.py` — 确认盐值为每用户随机生成
- `database/db_operation.py` — `users` 表确认 `salt` 字段存在
- `scripts/seed_users.py` — 测试脚本密码从 `.env` 读取，不硬编码
- `.env.example` — 标注 SECRET_KEY 最小长度要求

### 2. 异常处理精细化

**改动文件**: 按优先级逐文件修复 bare except

| 优先级 | 文件                              | 问题                           |
|-----|---------------------------------|------------------------------|
| P0  | `app/services/kg_service.py`    | Neo4j 连接失败时部分 except 静默吞错 |
| P0  | `app/services/llm_service.py`   | LLM 调用失败影响所有 Agent           |
| P0  | `app/agents/orchestrator.py`    | 历史加载/摘要失败异常处理              |
| P1  | `app/api/v1/endpoints/chat.py`  | WebSocket 异常处理               |
| P1  | `app/services/image_service.py` | OCR 失败静默                     |
| P1  | `run.py`                        | 多处 bare except (第19、40、43行)  |
| P2  | 其余文件                            | 逐个修复                         |

**规则**:
- 每个 `except` 改为具体异常类型 + `logger.error()` 记录
- 添加请求级 `trace_id`（UUID），贯穿日志全链路

**验收标准**:
- [ ] 无 bare except 残留
- [ ] 日志中每条请求可追溯到 trace_id

---

## B3 — 后端 API 完善（面向 Vue3）（2 周）

> Vue3 是纯前端 SPA，需要后端提供完整、规范的 RESTful API。

### 1. 管理后台 API（新建）

**新建文件**: `app/api/v1/endpoints/admin.py`

```
GET    /api/v1/admin/users                     — 用户列表（分页+搜索+角色筛选）
PUT    /api/v1/admin/users/{username}/status    — 启用/禁用用户
POST   /api/v1/admin/users/{username}/reset-password — 重置密码
DELETE /api/v1/admin/users/{username}           — 删除用户
GET    /api/v1/admin/stats/overview             — 系统统计概览
GET    /api/v1/admin/stats/agent-usage          — Agent 路由使用统计
GET    /api/v1/admin/stats/daily-active         — 日活用户趋势
GET    /api/v1/admin/logs                       — 系统日志（分页+级别筛选）
```

**改动文件**:
- `app/api/v1/api.py` — 注册 admin 路由
- `database/local_db_utils.py` — 新增管理查询方法

### 2. 数据导出 API

**新建文件**: `app/services/report_service.py`

```
GET /api/v1/reports/health-summary/{username}   — 个人健康周报/月报（PDF）
GET /api/v1/reports/doctor-patient-list          — 医生端患者数据导出（CSV）
```

### 3. SSE 流式聊天优化（Vue3 对接）

**改动文件**: `app/api/v1/endpoints/chat.py`

Vue3 使用 `EventSource` 或 `fetch + ReadableStream` 消费 SSE，需确保：
- SSE 格式严格遵循 `data: {...}\n\n`
- 流结束时发送 `data: [DONE]\n\n`
- 错误时发送 `data: {"type":"error","error":"..."}\n\n`
- 设置正确的 `Content-Type: text/event-stream` 和 `Cache-Control: no-cache`
- 添加 `X-Accel-Buffering: no` 防止 Nginx 缓冲

### 4. 现有 API 响应格式统一

**改动文件**: 所有 `app/api/v1/endpoints/*.py`

部分端点仍直接返回 `{"success": True, ...}` 而非使用 `ApiResponse`：
- `notifications.py` — 直接返回 dict
- `chat.py` — 混合使用
- 需全面检查并统一

### 5. 补齐现有 API 分页

**改动文件**:
- `app/api/v1/endpoints/sessions.py` — 会话列表分页
- `app/api/v1/endpoints/checkin.py` — 打卡记录分页 + 日期范围查询
- `app/api/v1/endpoints/reminder.py` — 提醒列表分页 + 按类型/状态筛选
- `app/api/v1/endpoints/doctor.py` — 患者列表分页 + 风险排序

**验收标准**:
- [ ] Vue3 所有页面均有对应 API 端点
- [ ] 所有列表 API 支持分页（`?page=1&size=20`）
- [ ] 管理后台 API 可用（用户管理+系统统计+日志查看）
- [ ] SSE 流式聊天在 Vue3 中正常工作
- [ ] API 响应格式 100% 统一

---

## B4 — Agent 路由可观测性（1 周）

**新建文件**: `app/services/agent_metrics.py`

记录每次路由决策的 agent、confidence、耗时，用于：
- 低置信度路由告警（confidence < 0.5 时记录日志）
- Agent 使用频率统计（供管理后台展示）
- 路由准确性人工标注接口

**改动文件**:
- `app/agents/orchestrator.py` — 记录路由指标
- `app/api/v1/endpoints/admin.py` — 暴露 Agent 使用统计端点（在 B3 中已新建）

**验收标准**:
- [ ] 管理后台可查看 Agent 使用统计
- [ ] 低置信度路由自动记录日志

---

### 🅱️ B 线文件清单汇总

| 操作 | 文件                                              |
|------|-------------------------------------------------|
| 新建 | `app/services/text2cypher_service.py`           |
| 新建 | `app/api/v1/endpoints/admin.py`                 |
| 新建 | `app/services/report_service.py`                |
| 新建 | `app/services/agent_metrics.py`                 |
| 改动 | `app/services/kg_service.py`                    |
| 改动 | `app/agents/medical_qa_agent.py`                |
| 改动 | `app/agents/orchestrator.py`                    |
| 改动 | `app/core/config.py`                            |
| 改动 | `app/api/v1/api.py`                             |
| 改动 | `app/api/v1/endpoints/chat.py`                  |
| 改动 | `app/api/v1/endpoints/notifications.py`         |
| 改动 | `app/api/v1/endpoints/sessions.py`              |
| 改动 | `app/api/v1/endpoints/checkin.py`               |
| 改动 | `app/api/v1/endpoints/reminder.py`              |
| 改动 | `app/api/v1/endpoints/doctor.py`                |
| 改动 | `app/api/v1/endpoints/kg.py`                    |
| 改动 | `database/local_db_utils.py`                    |
| 改动 | `database/password_utils.py`                    |
| 改动 | `app/services/llm_service.py`                   |
| 改动 | `app/services/image_service.py`                 |
| 改动 | `run.py`                                        |
| 改动 | `.env.example`                                  |

---

# 🅲 C 线 — 智能预警与模型优化

> **负责人**: ___ | **预计工时**: ~7 周 | **关键词**: 异常检测、NER 微调、LLM SFT、评测

> 本线聚焦 "智能"：让系统从被动问答升级为主动预警，同时提升模型准确率。
> 与其他两线**零文件冲突**，可完全并行。

---

## C1 — 智能预警系统（3 周）

### 1. 时序异常检测

**新建文件**: `app/services/anomaly_service.py`

**核心逻辑**:
- 分析患者近 7 天打卡数据的体征趋势（体温、血压、血糖、心率）
- 基于滑动窗口 + Z-score 检测异常波动
- 异常触发自动告警 → 写入 notifications 表 → WebSocket 推送到医生端

**改动文件**:
- `app/agents/health_agent.py` — 集成异常检测结果
- `app/api/v1/endpoints/overview.py` — 新增趋势异常标注 API
- `app/services/checkin_service.py` — 打卡后触发异步异常检测

### 2. 高危患者自动置顶

**改动文件**:
- `app/services/doctor_service.py` — 患者列表按风险等级排序
- `app/api/v1/endpoints/doctor.py` — API 返回中增加 `risk_level` 字段
- `database/local_db_utils.py` — 查询支持风险排序

**Vue3 前端展示**: 前端据此排序 + 颜色标记。

### 3. 健康趋势分析增强

**改动文件**:
- `app/services/overview_service.py` — 趋势数据增加异常标注
- `app/api/v1/endpoints/overview.py` — 返回异常区间标记

**验收标准**:
- [ ] 连续 3 天体温上升 → 医生端 WebSocket 收到告警
- [ ] 医生面板 API 返回按风险排序的患者列表
- [ ] 趋势图数据包含异常标注点

---

## C2 — 模型优化与微调（4 周）

### 1. NER 模型微调

**数据**: `data/ner_data_aug.txt`（已有增强数据）
**方法**: 基于现有 RoBERTa 模型做 LoRA 微调
**目标**: 术后特有实体（引流管、伤口状态、术后并发症）F1 > 0.85

**改动文件**:
- `finetune_demo/` — 复用已有微调管线
- `scripts/ner_finetune.py` — 新建微调脚本
- `app/services/ner_service.py` — 加载微调后模型

### 2. LLM SFT 微调

**数据**: `data/lora_data/`（已有）
**方法**: DeepSeek / Qwen SFT
**目标**: 术后管理领域回答准确率提升，减少幻觉

### 3. 评测基准

**新建目录**: `tests/eval/`

```
tests/eval/
├── eval_ner.py          # NER F1-score 评测
├── eval_qa.py           # 医学问答准确率评测
├── eval_routing.py      # Coordinator 路由准确率评测
├── eval_data/           # 评测数据集
│   ├── ner_test.json
│   ├── qa_test.json
│   └── routing_test.json
└── README.md
```

**验收标准**:
- [ ] NER F1-score 相比基线提升 > 5%
- [ ] 医学问答准确率 > 80%（基于评测集）
- [ ] Coordinator 路由准确率 > 90%

---

### 🅲 C 线文件清单汇总

| 操作 | 文件                                         |
|------|--------------------------------------------|
| 新建 | `app/services/anomaly_service.py`          |
| 新建 | `scripts/ner_finetune.py`                  |
| 新建 | `tests/eval/` 目录及 6 个文件                   |
| 改动 | `app/agents/health_agent.py`               |
| 改动 | `app/services/checkin_service.py`          |
| 改动 | `app/services/doctor_service.py`           |
| 改动 | `app/services/overview_service.py`         |
| 改动 | `app/api/v1/endpoints/overview.py`         |
| 改动 | `app/api/v1/endpoints/doctor.py`           |
| 改动 | `app/services/ner_service.py`              |
| 改动 | `database/local_db_utils.py`               |
| 改动 | `finetune_demo/`                           |

---

# 📊 三线并行总览

## 工时对比

| 线路 | 阶段               | 预计工时 | 新建文件 | 改动文件 |
|------|-------------------|---------|---------|---------|
| 🅰️  | A1 JWT持久化+CORS  | 0.5 周  | 0       | 3       |
| 🅰️  | A2 WebSocket 重构   | 1.5 周  | 1       | 2       |
| 🅰️  | A3 基础设施          | 2 周    | 15+     | 3       |
| 🅰️  | A4 可观测性          | 2 周    | 1       | 全局     |
| 🅰️  | **小计**           | **6 周** | **17+** | **10+** |
| 🅱️  | B1 KG安全+Text2Cypher | 2 周  | 1       | 3       |
| 🅱️  | B2 安全加固          | 1 周    | 0       | 10+     |
| 🅱️  | B3 API完善          | 2 周    | 2       | 8+      |
| 🅱️  | B4 Agent可观测性     | 1 周    | 1       | 2       |
| 🅱️  | **小计**           | **6 周** | **4**   | **20+** |
| 🅲   | C1 智能预警          | 3 周    | 1       | 6       |
| 🅲   | C2 模型微调+评测      | 4 周    | 4       | 3       |
| 🅲   | **小计**           | **7 周** | **5**   | **9**   |

## 文件冲突检查

```
🅰️ 线独占文件: ws_manager.py, tests/, Dockerfile, docker-compose.yml, .github/, metrics.py
🅱️ 线独占文件: text2cypher_service.py, admin.py, report_service.py, agent_metrics.py
🅲 线独占文件: anomaly_service.py, ner_finetune.py, tests/eval/

共用文件（需协调）:
  - app/core/config.py        → 🅰️ 加 REDIS_URL / 🅱️ 加 KG 配置项（无冲突，不同字段）
  - app/core/security.py      → 🅰️ 独占
  - app/agents/orchestrator.py → 🅰️ 加 Redis 缓存 / 🅱️ 加指标记录（不同函数，协调即可）
  - database/local_db_utils.py → 🅱️ 加管理查询 / 🅲 加风险排序查询（不同函数，协调即可）
  - requirements.txt          → 三线各自添加依赖（追加不冲突）
```

## 执行时间线

```
            Week 1    Week 2    Week 3    Week 4    Week 5    Week 6    Week 7
            ──────    ──────    ──────    ──────    ──────    ──────    ──────
🅰️ A线:     A1        A2 ──────  A3 ──────  A3续      A4 ──────  A4续
🅱️ B线:     B1 ──────  B1续      B2        B3 ──────  B3续      B4
🅲 C线:      C1 ──────  C1续 ────── C1续     C2 ──────  C2续 ────── C2续 ──────

三线完全并行，互不阻塞。唯一需协调的是 config.py 新增配置项和 orchestrator.py 改动。
```

## 依赖关系（线内）

```
🅰️ A线: A1 (Redis) → A3 (测试需要 Redis)   A2 (WebSocket) 与 A1/A3 可并行
🅱️ B线: B1 (KG安全) → B2 (安全加固)         B3 (API完善) 与 B1/B2 可并行
🅲 C线:  C1 (预警) 与 C2 (模型) 可并行
```

---

## 排除范围确认

以下模块**三条线均不涉及**，由其他开发者负责：

| 文件                         | 说明                 |
|------------------------------|----------------------|
| `app/agents/rehab_plan_agent.py`   | 康复计划 Agent         |
| `app/services/rehab_plan_service.py` | 康复计划服务           |
| `app/api/v1/endpoints/rehab_plan.py` | 康复计划 API           |
| `app/agents/tools/rehab_plan_tools.py` | 康复计划工具           |
| `database/local_db_utils.py` 中康复计划相关方法 | 如 `save_rehab_*`, `get_rehab_*` |

---

## 维护约定

- 每条线独立创建 `feature/track-a`, `feature/track-b`, `feature/track-c` 分支开发
- 完成后提交 PR 到 `master`
- 共用文件的改动需在 PR 描述中说明修改范围，避免 merge 冲突
- 已完成项标记 ✅ 并注明日期
- 每两周三线同步一次进度，调整优先级

---

*本文档基于代码深度审查生成*
*初版: 2026-05-23 | 最后更新: 2026-06-01*
*已根据实际代码状态更新完成标记*
*已排除康复计划模块（由其他开发者负责）*
