# 全周期健康管理系统 — 后续功能更新计划

> 基于代码深度审查（2026-05-23），结合已有功能与新发现的改进方向，
> 按优先级分层推进，聚焦 **Vue3 前端对接** 和 **系统可靠性提升**。
>
> **前端说明**: 前端已确定采用 **Vue3 + Vite + Element Plus** 方案，正在开发中，
> 将完全替代 Streamlit。本计划中所有 API 设计均面向 Vue3 对接。

---

## 项目现状快照

| 维度       | 当前状态                                               | 关键缺口                                                      |
|----------|----------------------------------------------------|-----------------------------------------------------------|
| **认证系统** | 自定义 in-memory token（`secrets.token_urlsafe`），非 JWT | 重启丢失全部 token；Vue3 无法持久化；无刷新机制                             |
| **多智能体** | 5 Agent + Coordinator + 10 个工具                     | 工具集偏少；Coordinator 纯 LLM 路由无兜底；无可观测性                       |
| **对话记忆** | orchestrator 层 MySQL 加载 + LLM 摘要压缩                 | 仅进程内缓存；无 Redis；摘要丢失上下文                                    |
| **知识图谱** | 单跳 Cypher，14 种硬编码意图映射                              | 无 text2cypher；无多跳推理；Cypher 字符串拼接存在注入风险                    |
| **通知系统** | notifications 表已建；WebSocket 基础框架已有                 | 无 REST API 端点；ConnectionManager 仅支持单连接；无心跳                |
| **语音交互** | ASR 可用 (Fun-ASR)；TTS 接口存在                          | TTS 未在前端集成；无流式语音                                          |
| **前端**   | Streamlit 过渡中；**Vue3 + Element Plus 开发中**          | 后端 API 响应格式不统一；缺管理后台 API                                  |
| **测试**   | 零正式测试覆盖；仅 5 个手动连接测试脚本                              | 无 pytest、无 mock、无 CI                                      |
| **部署**   | 手动 `run.py` 启动                                     | 无 Docker、无 CI/CD                                          |
| **安全**   | SHA-256+盐值加密；CORS 全开                               | 33+ bare except；盐值在 password_utils 中硬编码生成；admin 密码 123456 |
| **运维**   | print 输出日志                                         | 无结构化日志、无监控、无健康检查深度                                        |

---

## P0 — 认证系统重构 + API 规范化（1.5 周）

> Vue3 前端的首要阻塞项。当前 in-memory token 在服务器重启后全部失效，
> Vue3 无法可靠持久化会话。必须在所有 API 对接前完成。

### 1. JWT 认证替换

**改动文件**:
- `app/core/security.py` — 替换 in-memory token 为 JWT
- `app/core/config.py` — 新增 `JWT_SECRET_KEY`, `JWT_ALGORITHM=HS256`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS`
- `app/api/v1/endpoints/auth.py` — 登录返回 access_token + refresh_token
- `requirements.txt` — 新增 `python-jose[cryptography]`

**核心设计**:
```python
# Token 结构
access_token:  { sub: username, is_admin: bool, exp: 30min, iat, jti }
refresh_token: { sub: username, type: "refresh", exp: 7d }

# API 端点
POST /api/v1/auth/login       → { access_token, refresh_token, token_type: "bearer" }
POST /api/v1/auth/register    → { access_token, refresh_token }
POST /api/v1/auth/refresh     → { access_token }  # 用 refresh_token 换新 access_token
POST /api/v1/auth/logout      → 将 jti 加入黑名单（Redis/内存）
GET  /api/v1/auth/me           → { username, is_admin, created_at }
```

**向后兼容**: 旧的 `user_tokens` 内存字典保留 1 个版本作为 fallback，打印 deprecation warning。

**Vue3 对接**:
- Axios 请求拦截器自动附加 `Authorization: Bearer <token>`
- 响应拦截器捕获 401 → 自动调用 `/auth/refresh` → 重放请求
- refresh_token 存 `httpOnly cookie` 或 `localStorage`

### 2. 统一响应格式

**新建文件**: `app/core/response.py`

```python
class ApiResponse:
    @staticmethod
    def success(data=None, message="操作成功"):
        return {"code": 200, "message": message, "data": data}

    @staticmethod
    def error(code=400, message="操作失败", data=None):
        return {"code": code, "message": message, "data": data}

    @staticmethod
    def paginated(items, total, page, size):
        return {
            "code": 200, "message": "success",
            "data": {"items": items, "total": total, "page": page, "size": size,
                     "pages": (total + size - 1) // size}
        }
```

**改动文件**: 所有 `app/api/v1/endpoints/*.py` — 统一使用 `ApiResponse`

### 3. 全局异常处理中间件

**改动文件**: `app/main.py`

```python
@app.middleware("http")
async def request_logging_middleware(request, call_call):
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id
    # ... 记录请求日志 ...

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    trace_id = getattr(request.state, "trace_id", "unknown")
    return JSONResponse(
        status_code=500,
        content=ApiResponse.error(500, "服务器内部错误", {"trace_id": trace_id})
    )
```

**验收标准**:
- [ ] Vue3 登录后 token 在页面刷新后仍有效
- [ ] access_token 过期后自动 refresh，用户无感
- [ ] 所有 API 返回 `{"code", "message", "data"}` 统一格式
- [ ] 未捕获异常返回 500 + trace_id，不暴露堆栈

---

## P1 — WebSocket 实时通信层（1.5 周）

> Vue3 需要 WebSocket 实现实时通知推送和聊天流式回复。
> 当前 WebSocket 实现存在多个问题需修复。

### 1. ConnectionManager 重构

**改动文件**: `app/api/v1/endpoints/chat.py` → 拆分为 `app/core/ws_manager.py`

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
        """发送到用户所有连接"""
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
            # 需要查询用户角色，或维护一个 doctors 集合
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

### 2. 通知 REST API

**新建文件**: `app/api/v1/endpoints/notifications.py`

```
GET    /api/v1/notifications/               — 通知列表 (?unread_only=true&page=1&size=20)
GET    /api/v1/notifications/unread-count    — 未读计数
POST   /api/v1/notifications/{id}/read      — 标记已读
POST   /api/v1/notifications/read-all       — 全部已读
DELETE /api/v1/notifications/{id}           — 删除通知
```

**改动文件**:
- `app/api/v1/api.py` — 注册 notifications 路由
- `database/local_db_utils.py` — 新增通知 CRUD 方法（notifications 表已存在于 `db_operation.py`）

### 3. WebSocket 消息协议

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

**验收标准**:
- [ ] Vue3 建立 WebSocket 连接后，医生发消息 → 患者端实时收到通知
- [ ] 高风险告警 → 所有在线医生端实时收到推送
- [ ] 同一用户多标签页均能收到消息
- [ ] 断线重连后，未读通知通过 HTTP API 补偿获取
- [ ] 30s 心跳保活，Nginx 代理下不超时断开

---

## P2 — 知识图谱增强（2 周）

> 当前仅支持硬编码意图映射的单跳查询，无法处理复杂医疗问题。
> Cypher 查询使用字符串拼接，存在注入风险。

### 1. Cypher 注入修复（安全优先）

**改动文件**: `app/services/kg_service.py`

**当前问题**:
```python
# 危险：字符串拼接
sql_q = "match (a:疾病{名称:'%s'}) return a.%s" % (entity, shuxing)
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
ALLOWED_PROPERTIES = {"疾病简介", "疾病病因", "预防措施", "治疗周期", ...}
if shuxing not in ALLOWED_PROPERTIES:
    raise ValueError(f"非法属性: {shuxing}")
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

### 3. 多跳推理

支持形如 "XX 药物对做完 YY 手术的病人有什么风险？" 的复合查询：

```cypher
MATCH path = (d:疾病 {名称: $disease})-[*1..3]->(r)
WHERE r:药物 OR r:症状 OR r:并发症
RETURN nodes(path), relationships(path)
LIMIT 50
```

**改动文件**:
- `app/services/kg_service.py` — 新增 `text_to_cypher()` 和 `multi_hop_query()`
- `app/agents/medical_qa_agent.py` — 集成 text2cypher 路径
- `app/core/config.py` — 新增 `KG_MAX_HOPS=3`, `KG_TEXT2CYPHER_ENABLED=True`

### 4. 知识图谱可视化 API（面向 Vue3）

**改动文件**: `app/api/v1/endpoints/kg.py`

```
POST /api/v1/kg/visualize      — 查询子图，返回 nodes + edges JSON
GET  /api/v1/kg/schema          — 返回图谱 schema（实体类型、关系类型）
GET  /api/v1/kg/search?q=      — 实体模糊搜索（用于 Vue3 搜索框自动补全）
GET  /api/v1/kg/diseases        — 疾病列表（已有，补充分页）
```

**响应格式**（适配 vis-network / D3.js）:
```json
{
  "nodes": [
    {"id": "n1", "label": "阿莫西林", "group": "药物", "properties": {...}},
    {"id": "n2", "label": "头痛", "group": "症状"}
  ],
  "edges": [
    {"from": "n1", "to": "n2", "label": "副作用", "type": "副作用"}
  ]
}
```

**Vue3 可视化方案**: 使用 `@vue-flow/core` 或 `vis-network` 渲染交互式图谱。

**验收标准**:
- [ ] "感冒用什么药" → 命中现有快速路径，响应 < 1s
- [ ] "吃了阿莫西林后头痛加重" → 触发 text2cypher，返回多跳结果
- [ ] 输入 `'; DROP TABLE; //` → 被安全过滤器拦截
- [ ] Vue3 端可渲染查询涉及的子图，支持拖拽/缩放/点击节点

---

## P3 — 基础设施补齐（2 周）

> 为后续功能扩展打地基：缓存、测试、容器化。

### 1. Redis 集成

**改动文件**:
- `requirements.txt` — 新增 `redis[hiredis]`
- `app/core/config.py` — 新增 `REDIS_URL` 配置
- `app/db/session.py` — 新增 Redis 连接管理（单例，带连接池）
- `app/core/security.py` — JWT 黑名单存 Redis（`SETEX jti:blacklist <exp> 1`）
- `app/agents/orchestrator.py` — 对话摘要缓存到 Redis

**提供回退**: 开发环境无 Redis 时自动降级为内存存储（`app/core/config.py` 中 `REDIS_URL` 为空时触发）。

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

## P4 — 安全加固（1 周）

> 消除已知安全风险，为生产部署做准备。

### 1. 密码安全

**改动文件**:
- `database/password_utils.py` — 确认盐值为每用户随机生成（当前已是随机盐值，需审查是否所有用户都有独立盐值）
- `database/db_operation.py` — `users` 表确认 `salt` 字段存在
- `scripts/seed_users.py` — 测试脚本密码从 `.env` 读取，不硬编码

### 2. 异常处理精细化

**改动文件**: 按优先级逐文件修复（33+ bare except）

| 优先级 | 文件                              | 问题                           |
|-----|---------------------------------|------------------------------|
| P0  | `app/services/kg_service.py`    | Neo4j 连接失败时 bare except 静默吞错 |
| P0  | `app/services/llm_service.py`   | LLM 调用失败影响所有 Agent           |
| P0  | `app/agents/orchestrator.py`    | 历史加载/摘要失败 bare except        |
| P1  | `app/api/v1/endpoints/chat.py`  | WebSocket 异常处理               |
| P1  | `app/services/image_service.py` | OCR 失败静默                     |
| P2  | 其余文件                            | 逐个修复                         |

**规则**:
- 每个 `except` 改为具体异常类型 + `logger.error()` 记录
- 添加请求级 `trace_id`（UUID），贯穿日志全链路

### 3. CORS 收紧

**改动文件**: `app/main.py`

```python
# 从 .env 读取，开发环境默认允许 Vite 端口
CORS_ORIGINS = settings.CORS_ORIGINS  # 新增配置项
# 开发: ["http://localhost:5173", "http://localhost:3000"]
# 生产: 从环境变量读取
```

### 4. Cypher 注入修复

见 P2 第 1 节。

**验收标准**:
- [ ] 无 bare except 残留
- [ ] 日志中每条请求可追溯到 trace_id
- [ ] CORS 仅允许配置的域名
- [ ] Vue3 开发服务器正常跨域请求后端

---

## P5 — 后端 API 完善（面向 Vue3）（2 周）

> Streamlit 时代前端逻辑与后端耦合在同一个 Python 进程中。
> Vue3 是纯前端 SPA，需要后端提供完整、规范的 RESTful API。

### 1. 补齐 Vue3 页面所需 API

| Vue3 页面 | 所需 API                                    | 当前状态   | 改动                    |
|---------|-------------------------------------------|--------|-----------------------|
| 登录/注册   | `POST /auth/login`, `POST /auth/register` | 已有     | P0 重构为 JWT            |
| 聊天      | `POST /chat` (SSE), `WS /agent/ws`        | 已有     | 统一响应；WebSocket 重构见 P1 |
| 会话列表    | CRUD + 分页                                 | 已有     | 补充分页参数                |
| 健康打卡    | `POST /checkin`, `GET /checkin`           | 已有     | 补充日期范围查询 + 分页         |
| 健康概览    | `GET /overview/dashboard`                 | 已有     | 补充图表数据格式              |
| 提醒中心    | CRUD + 分页                                 | 已有     | 补充分页+筛选（按类型、状态）       |
| 康复计划    | CRUD + 任务管理                               | 已有     | 补充进度百分比计算             |
| 健康档案    | `GET /profile`, `POST /profile`           | 已有     | 补充头像上传                |
| 知识图谱    | `POST /kg/visualize`, `GET /kg/schema`    | 需新建    | P2 中实现                |
| 通知      | `GET /notifications/...`                  | 需新建    | P1 中实现                |
| 医生面板    | 患者列表、告警、消息                                | 已有     | 补充风险排序+分页             |
| 管理后台    | 用户管理、系统统计                                 | **缺失** | **本阶段新建**             |

### 2. 管理后台 API（新建）

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
- `app/core/security.py` — 新增 `require_admin` 依赖注入
- `database/local_db_utils.py` — 新增管理查询方法

### 3. 数据导出 API

**新建文件**: `app/services/report_service.py`

```
GET /api/v1/reports/health-summary/{username}   — 个人健康周报/月报（PDF）
GET /api/v1/reports/doctor-patient-list          — 医生端患者数据导出（CSV）
```

### 4. SSE 流式聊天优化（Vue3 对接）

**改动文件**: `app/api/v1/endpoints/chat.py`

Vue3 使用 `EventSource` 或 `fetch + ReadableStream` 消费 SSE，需确保：
- SSE 格式严格遵循 `data: {...}\n\n`
- 流结束时发送 `data: [DONE]\n\n`
- 错误时发送 `data: {"type":"error","error":"..."}\n\n`
- 设置正确的 `Content-Type: text/event-stream` 和 `Cache-Control: no-cache`
- 添加 `X-Accel-Buffering: no` 防止 Nginx 缓冲

### 5. 文件上传 API

**新建文件**: `app/api/v1/endpoints/upload.py`

```
POST /api/v1/upload/image       — 图片上传（头像、报告图片）
POST /api/v1/upload/avatar      — 头像上传（裁剪+压缩）
```

**改动文件**:
- `app/core/config.py` — 新增 `UPLOAD_DIR`, `MAX_FILE_SIZE`
- `app/main.py` — 静态文件服务（`/uploads/`）

**验收标准**:
- [ ] Vue3 所有页面均有对应 API 端点
- [ ] 所有列表 API 支持分页（`?page=1&size=20`）
- [ ] 管理后台 API 可用（用户管理+系统统计+日志查看）
- [ ] SSE 流式聊天在 Vue3 中正常工作
- [ ] API 响应格式 100% 统一

---

## P6 — 智能预警与决策支持（3 周）

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
- `app/services/checkin_service.py` — 打卡后触发异步异常检测

### 2. 高危患者自动置顶

**改动文件**:
- `app/services/doctor_service.py` — 患者列表按风险等级排序
- API 返回中增加 `risk_level` 字段，Vue3 前端据此排序+颜色标记

### 3. 康复进度追踪

**改动文件**:
- `app/api/v1/endpoints/rehab_plan.py` — 新增进度 API
- `app/services/rehab_plan_service.py` — 康复进度计算逻辑（已完成任务数/总任务数）

**Vue3 前端展示**: Element Plus `ElProgress` 进度条 + `ElTimeline` 里程碑。

### 4. Agent 路由可观测性

**新建文件**: `app/services/agent_metrics.py`

记录每次路由决策的 agent、confidence、耗时，用于：
- 低置信度路由告警（confidence < 0.5 时记录日志）
- Agent 使用频率统计（供管理后台展示）
- 路由准确性人工标注接口

**验收标准**:
- [ ] 连续 3 天体温上升 → 医生端 WebSocket 收到告警
- [ ] 医生面板 API 返回按风险排序的患者列表
- [ ] 患者可查看康复计划完成进度
- [ ] 管理后台可查看 Agent 使用统计

---

## P7 — 模型优化与微调（4 周）

> 提升垂直领域准确率。

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

## P8 — 可观测性与运维（2 周）

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

## P9 — 长期演进方向（按需推进）

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

### 6. 多模态增强
- 医学影像分析（X光、CT）
- 连续语音对话（流式 ASR + TTS）
- 视频问诊

---

## 执行路线图

```
                    Week 1-2       Week 3-4       Week 5-6       Week 7-8       Week 9+
                    ──────────     ──────────     ──────────     ──────────     ─────────
Phase 1 (基础):     P0 认证重构    P1 WebSocket   P3 基础设施    P4 安全加固
                    + API 规范     + 通知 API     (Redis/测试    (bare except
                                                    /Docker)      /CORS)

Phase 2 (能力):     P2 KG增强      P5 API完善      P6 智能预警
                                        │
Phase 3 (优化):                         P7 模型微调     P8 可观测性

Phase 4 (演进):                                              P9 按需启动
```

> **并行策略**: P0/P2 可由两人并行（一人做认证+API规范，一人做 KG 增强）。
> P5 需要与 Vue3 前端开发紧密配合，建议前后端联调推进。

## 依赖关系

```
P0 认证重构 + API 规范 ──────────────────────┐
P1 WebSocket + 通知 API ─────────────────────┤
P2 KG增强 ───────────────────────────────────┤
P3 基础设施 (Redis) ──┬──────────────────────┼──→ P6 智能预警
                      ├──→ P4 安全加固       │
                      └──→ P5 API 完善       ├──→ P7 模型微调
                         (面向 Vue3)         └──→ P8 可观测性
P9 长期演进 ── 无硬依赖，按需启动
```

---

## 工作量估算

| 阶段     | 项目               | 预计工时       | 新建文件    | 改动文件    |
|--------|------------------|------------|---------|---------|
| P0     | 认证重构 + API 规范    | 1.5 周      | 1       | 10+     |
| P1     | WebSocket + 通知   | 1.5 周      | 2       | 5       |
| P2     | KG 增强            | 2 周        | 1       | 4       |
| P3     | 基础设施             | 2 周        | 15+     | 3       |
| P4     | 安全加固             | 1 周        | 0       | 15+     |
| P5     | API 完善 (Vue3 对接) | 2 周        | 4       | 10+     |
| P6     | 智能预警             | 3 周        | 2       | 6       |
| P7     | 模型微调             | 4 周        | 3       | 3       |
| P8     | 可观测性             | 2 周        | 1       | 全局      |
| **合计** |                  | **约 19 周** | **29+** | **50+** |

---

## 维护约定

- 每个 Phase 完成后更新本文档状态
- 已完成项标记 `~~删除线~~` 并注明日期
- 新需求通过 Issue 讨论后加入对应 Phase
- 每月回顾一次优先级，根据实际情况调整

---

*本文档基于代码深度审查生成，最后更新: 2026-05-23*
*已根据 Vue3 + Vite + Element Plus 前端方案调整*
