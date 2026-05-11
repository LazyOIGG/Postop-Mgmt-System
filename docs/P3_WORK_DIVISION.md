# P3 功能增强 — 双人分工计划

> 基于项目代码深度探索结果，将 P3 五项功能拆分为两人并行工作量。
> 完整技术细节参见内部分析文档，本文档聚焦**任务分配**和**接口约定**。

---

## 分工总览

```
                         ┌─────────────────────────┐
                         │  Step 0: 共同前置 (1天)  │
                         │  LLM 消息格式重构        │
                         │  llm_service.py + base.py│
                         └────────────┬────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
┌─────────────────────────────┐     ┌─────────────────────────────┐
│     人员 A: Agent 系统       │     │    人员 B: 服务与前端         │
│                             │     │                             │
│  P3.12 多轮对话记忆          │     │  P3.13 知识图谱增强           │
│  P3.14 Agent 工具调用        │     │  P3.15 推送通知系统           │
│                             │     │  P3.16 语音交互完善           │
│  核心: Agent/LLM 层         │     │  核心: Service/API/UI 层     │
└─────────────────────────────┘     └─────────────────────────────┘
```

| 维度 | 人员 A | 人员 B |
|------|--------|--------|
| **职责范围** | Agent 智能层 | 服务与前端层 |
| **主要目录** | `app/agents/`, `app/services/llm_service.py` | `app/services/`, `app/api/`, `database/`, 前端 |
| **新建文件** | 7 个 (`tools/` 目录) | 2 个 (`notifications.py`, `notification_service.py`) |
| **修改文件** | 5 个 | 12 个 |
| **预估工时** | 4-5 天 | 4-5 天 |
| **可并行性** | Step 0 完成后即可独立推进 | Step 0 完成后即可独立推进 |

---

## Step 0: 共同前置 — LLM 消息格式重构

> **负责人: 人员 A** | **预估: 1 天** | **阻断项: 两人都依赖此步完成**

### 背景
当前 `BaseAgent._call_llm()` 将结构化 messages 扁平化为 `[system]: xxx\n[user]: xxx` 字符串再发给 LLM，导致 system role 丢失、无法支持多轮对话、无法使用 function calling。

### 改动文件

| 文件 | 改动内容 |
|------|---------|
| `app/services/llm_service.py` | 新增 `chat_with_messages(messages, model, stream)` 和 `generate_completion_with_messages(messages, model)` — 直接传递 OpenAI 格式 messages 列表 |
| `app/agents/base.py` | `_call_llm()` 改为调用新方法，不再扁平化；`_build_messages()` 保留结构 |

### 接口约定 (人员 B 依赖此接口)

```python
# llm_service.py — 新增的两个方法签名
class LLMService:
    async def chat_with_messages(
        self, messages: List[Dict[str, str]],  # [{"role":"system","content":...}, ...]
        model_choice: str = None,
        stream: bool = True
    ) -> AsyncGenerator[str, None]: ...

    async def generate_completion_with_messages(
        self, messages: List[Dict[str, str]],
        model_choice: str = None
    ) -> str: ...
```

### 验收标准
- [ ] 现有 `/chat` 端点流式/非流式均正常工作
- [ ] system prompt 正确传递给 DeepSeek（可检查日志）
- [ ] 旧方法保留并标记 deprecated

---

## 人员 A: Agent 系统（P3.12 + P3.14）

### 任务 A1: P3.12 多轮对话记忆

> **预估: 2 天** | **依赖: Step 0 完成**

#### 目标
Agent 能感知同一会话的历史对话，支持连续对话，超窗口自动摘要压缩。

#### 改动文件

| 文件 | 改动 |
|------|------|
| `app/agents/orchestrator.py` | `process()` / `process_stream()` 新增 `session_id` 参数；新增 `_load_conversation_history()` 和 `_summarize_history()` 方法 |
| `app/agents/base.py` | `_build_messages()` 新增 `history` 参数，插入到 system prompt 与 user input 之间 |
| `app/api/v1/endpoints/chat.py` | 传入 `session_id` 到 orchestrator |
| `app/core/config.py` | 新增 `MAX_CONVERSATION_HISTORY_TURNS=10`, `CONVERSATION_SUMMARY_THRESHOLD_CHARS=3000` |

#### 核心逻辑

```
Orchestrator.process(message, username, session_id)
  │
  ├─ 1. db_instance.get_session_messages(session_id, limit=20)
  ├─ 2. 中文字符总数 > 3000 → LLM 摘要压缩
  ├─ 3. agent.run(user_input, history=history)
  └─ 4. 返回结果 (由 chat endpoint 保存到 DB)
```

#### 验收标准
- [ ] 同一 Session 内连续对话，Agent 能引用上文内容
- [ ] 15+ 轮后历史自动压缩，不超 Token 限制
- [ ] SSE 流式响应正常
- [ ] 新对话（无 session_id）行为不变

---

### 任务 A2: P3.14 Agent 工具调用

> **预估: 2-3 天** | **依赖: Step 0 + A1 完成**

#### 目标
Agent 能通过 DeepSeek Function Calling 执行实际操作（创建提醒、查询数据等）。

#### 新建文件

```
app/agents/tools/
├── __init__.py           # 导出 Tool, ToolRegistry, 预注册工具
├── base.py               # Tool 数据类 (name, description, parameters, handler)
├── registry.py           # ToolRegistry (register, get_openai_tools, execute)
├── reminder_tools.py     # create_reminder, list_reminders, update_reminder_status
├── checkin_tools.py      # get_recent_checkins, get_checkin_trend
├── external_tools.py     # get_weather (预留)
└── medical_tools.py      # query_drug_info, query_disease_symptoms
```

#### 修改文件

| 文件 | 改动 |
|------|------|
| `app/agents/base.py` | 新增 `_call_llm_with_tools()` — tool call 循环（最多 3 轮） |
| `app/services/llm_service.py` | 新增 `chat_with_tools(messages, tools, model, stream)` |
| `app/agents/reminder_agent.py` | 挂载提醒工具，更新 system prompt 引导 LLM 使用工具 |
| `app/agents/medical_qa_agent.py` | 挂载医疗查询工具 |
| `app/agents/health_agent.py` | 挂载打卡查询工具 |
| `app/agents/orchestrator.py` | 将 ToolRegistry 注入到 Agent 调用中 |
| `app/core/config.py` | 新增 `MAX_TOOL_CALL_ROUNDS=3` |
| `database/local_db_utils.py` | `save_reminder()` 方法（如未实现则需补充） |

#### 工具注册接口约定

```python
# 各 Agent 通过类属性声明所需工具
class ReminderAgent(BaseAgent):
    tools = ["create_reminder", "list_reminders", "update_reminder_status"]

# Orchestrator 从 ToolRegistry 获取对应的 OpenAI tool schema
# 注入到 LLM 调用的 tools 参数
```

#### 核心流程

```
用户: "帮我创建明天上午9点吃阿莫西林的提醒"
  → ReminderAgent.run(user_input, tools=[...])
    → LLM (messages + tools) → tool_calls: [{name:"create_reminder", args:{...}}]
    → ToolRegistry.execute("create_reminder", args) → MySQL INSERT
    → LLM (messages + tool_result) → "已为您创建提醒..."
```

#### 验收标准
- [ ] "创建提醒" 对话 → MySQL `reminders` 表中出现新记录
- [ ] "查询打卡情况" → Agent 返回基于真实数据的总结
- [ ] Tool call 失败时 Agent 返回友好降级提示，不崩溃
- [ ] 非工具类问题（如普通闲聊）不触发多余的 tool call

---

## 人员 B: 服务与前端（P3.13 + P3.15 + P3.16）

### 任务 B1: P3.13 知识图谱增强

> **预估: 2 天** | **依赖: 无（可独立启动）**

#### 目标
支持多跳推理，引入 text2cypher，扩展关系类型，添加前端图谱可视化。

#### 改动文件

| 文件 | 改动 |
|------|------|
| `app/services/kg_service.py` | 修复 Cypher 注入；新增 `text_to_cypher()` 和 `multi_hop_query()`；升级 `generate_enhanced_prompt()` |
| `app/api/v1/endpoints/kg.py` | 新增 `POST /kg/visualize` (返回子图 JSON)，`GET /kg/schema` |
| `scripts/build_up_graph.py` | 新增关系类型：药物相互作用、术后并发症、药物禁忌 |
| `app/models/schemas.py` | 新增 `VisualizeRequest`, `SchemaResponse` 等模型 |
| `streamlit_app.py` | 新增知识图谱可视化组件 (pyvis) |
| `app/core/config.py` | 新增 `KG_MAX_HOPS=3`, `KG_VISUALIZE_MAX_NODES=50` |

#### 核心设计

```
用户查询 → NER + Intent
              │
              ├─ 简单查询 (14种已知意图) → 现有硬编码映射 (快速路径)
              └─ 复杂查询 → text_to_cypher (LLM 生成 Cypher)
                              │
                              ├─ 安全验证 (仅允许 MATCH/READ)
                              └─ Neo4j 执行 → 结果注入 Prompt

多跳查询:
  MATCH path = (a:疾病{名称:$name})-[*1..3]->(b)
  RETURN nodes(path), relationships(path)
```

#### 验收标准
- [ ] "感冒用什么药" → 命中现有快速路径
- [ ] "吃了阿莫西林后头痛加重" → 触发 text2cypher 多跳查询
- [ ] 输入 `'; DROP CONSTRAINT; //` → 被安全过滤器拦截
- [ ] 前端显示查询涉及的知识图谱子图

---

### 任务 B2: P3.15 推送通知系统

> **预估: 2 天** | **依赖: 可独立启动，建议 B1 后做**

#### 目标
未读消息角标、WebSocket 实时推送、提醒到期自动通知。

#### 新建文件

| 文件 | 内容 |
|------|------|
| `app/api/v1/endpoints/notifications.py` | 通知 CRUD API (列表/未读数/标记已读) |
| `app/services/notification_service.py` | NotificationService + 后台提醒调度器 |

#### 修改文件

| 文件 | 改动 |
|------|------|
| `database/db_operation.py` | `init_database_tables()` 新增 `notifications` 表 |
| `database/local_db_utils.py` | 新增 5 个通知相关 DB 方法 |
| `app/api/v1/endpoints/chat.py` | 新增 `ConnectionManager` 类；WebSocket 支持 `notification` 消息类型 |
| `app/services/doctor_service.py` | `send_message()` 中调用 `notification_service.notify_doctor_message()` |
| `app/models/schemas.py` | 新增 `NotificationResponse` 等模型 |
| `streamlit_app.py` | 侧边栏未读角标 + 通知列表弹窗 |
| `app/core/config.py` | 新增 `NOTIFICATION_CHECK_INTERVAL=60` |

#### 数据库新表

```sql
CREATE TABLE notifications (
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

#### API 端点

```
GET    /api/v1/notifications/              — 列表 (?unread_only=true)
GET    /api/v1/notifications/unread-count  — 未读数
POST   /api/v1/notifications/{id}/read     — 标记已读
POST   /api/v1/notifications/read-all      — 全部已读
```

#### 验收标准
- [ ] 医生发消息 → 患者端侧边栏出现未读角标
- [ ] 提醒到期 → 患者收到通知（WebSocket 推送或轮询可见）
- [ ] 高风险告警 → 医生端收到通知
- [ ] 点击角标 → 通知列表 → 已读后角标消失

---

### 任务 B3: P3.16 语音交互完善

> **预估: 1-2 天** | **依赖: 无（可独立启动）**

#### 目标
实现 TTS（文本转语音），修复 TTS 参数 bug，增强前端语音交互。

#### 改动文件

| 文件 | 改动 |
|------|------|
| `app/services/speech_service.py` | 实现 `synthesize()` — 对接 DashScope CosyVoice TTS |
| `app/api/v1/endpoints/multimodal.py` | 修复 TTS 端点：`text` 参数改为 Pydantic Body Model |
| `app/models/schemas.py` | 新增 `TTSRequest` 模型 |
| `streamlit_app.py` | 聊天输入框旁添加录音按钮 (ASR)；AI 回复旁添加朗读按钮 (TTS) |
| `app/core/config.py` | 新增 `TTS_VOICE="zhizun_zhixing_male"`, `TTS_ENABLED=True` |

#### TTS 核心实现

```python
# speech_service.py — 替换当前空桩
async def synthesize(self, text: str, voice: str = None) -> Optional[bytes]:
    from dashscope.audio.tts import SpeechSynthesizer
    result = SpeechSynthesizer.call(
        model='cosyvoice-v1',
        voice=voice or settings.TTS_VOICE,
        text=text,
        format='mp3'
    )
    return result.get_audio_data() if result.status_code == 200 else None
```

#### 前端改动

```
患者端 (streamlit_app.py):
  ┌──────────────────────────────────┐
  │  [🎤 录音]  [输入框............]  │  ← st.audio_input
  │                                  │
  │  AI: 您术后恢复良好...  [🔊 朗读] │  ← st.audio 播放 TTS
  └──────────────────────────────────┘
```

#### 验收标准
- [ ] 前端录音按钮 → 语音识别 → 文本正确填入输入框
- [ ] AI 回复旁朗读按钮 → TTS 语音正常播放
- [ ] TTS 服务不可用时朗读按钮静默隐藏，不影响功能
- [ ] 长文本 TTS 正常生成完整音频

---

## 文件冲突矩阵

标记两人可能同时修改的文件及协调方式：

| 文件 | 人员 A | 人员 B | 处理方式 |
|------|--------|--------|---------|
| `app/services/llm_service.py` | Step 0 改 | 不改 | A 先完成 |
| `app/agents/base.py` | Step 0 + P3.12 + P3.14 改 | 不改 | A 独占 |
| `app/core/config.py` | 加 3 项 | 加 6 项 | **分开区块添加，最后合并** |
| `app/models/schemas.py` | P3.14 加 Tool 相关 | P3.13/15/16 加各自模型 | **分开文件底部追加** |
| `streamlit_app.py` | 不改 | P3.13/15/16 改 | B 独占 |
| `app/agents/reminder_agent.py` | P3.14 改 | 不改 | A 独占 |
| `app/api/v1/endpoints/chat.py` | P3.12 改 | P3.15 改 | **A 先加 session_id，B 后加 ConnectionManager** |

> **config.py 和 schemas.py 冲突处理**: 各自在文件末尾追加配置/模型，合并时直接拼接即可。如遇冲突，按 A → B 顺序合并。

---

## 时间线建议

```
Day 1     │ 人员A: Step 0 LLM消息重构
          │ 人员B: 熟悉代码 + 准备 P3.13 数据

Day 2-3   │ 人员A: P3.12 多轮对话记忆
          │ 人员B: P3.13 知识图谱增强

Day 4-5   │ 人员A: P3.14 Agent 工具调用
          │ 人员B: P3.15 推送通知系统

Day 6     │ 人员A: 联调 + 修复
          │ 人员B: P3.16 语音交互完善

Day 7     │ 两人: 集成测试 + 验收
```

---

## 总验收清单

- [ ] Step 0: LLM 消息格式重构 — 流式/非流式均正常
- [ ] P3.12: 同一会话连续对话，Agent 能引用历史
- [ ] P3.13: 多跳 KG 查询正常，前端可视化可用
- [ ] P3.14: "创建提醒" 实际写入数据库
- [ ] P3.15: 通知角标 + 已读标记完整闭环
- [ ] P3.16: 录音→识别→答复→朗读 全链路可用
- [ ] 所有现有功能无回归 (向后兼容)
- [ ] 前端 `streamlit_app.py` 和 `doctor_app.py` 均正常运行
