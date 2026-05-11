# 术后管理系统 — 后续功能增加与优化规划

> 基于项目现状、代码审查发现及技术演进方向，按优先级排列。本文档为**活文档**，随项目推进持续更新。

---

## 项目现状总结

| 维度 | 当前状态 |
|------|---------|
| **架构** | FastAPI + Streamlit，多智能体编排 (Coordinator + 4 Agent) |
| **AI 能力** | DeepSeek LLM + Neo4j KG-RAG + RoBERTa NER |
| **多模态** | 语音识别 (Fun-ASR) + 图像/OCR + TTS (待修复) |
| **用户端** | 患者端 (port 8501) + 医生端 (port 8502) 已分离 |
| **数据库** | MySQL (用户/会话/打卡/提醒/健康档案) + Neo4j (医学知识图谱) |
| **运维** | 无缓存、无监控、Token 存进程内存 |
| **已知问题** | 约 33 处 bare except、TTS 参数解析 bug、硬编码密码残留 |

---

## 🔴 P0 — 安全与可靠性 (1-2 周)

### 1. 密码安全加固

**现状**：脚本中残留硬编码密码，盐值统一硬编码。

**计划**：
- 测试/检查脚本改为从 `.env` 读取数据库密码
- 密码盐值改为每用户独立随机生成，存入 `users` 表的新字段 `salt`
- 管理员账户改从 `.env` 读取 `ADMIN_USERNAME` / `ADMIN_PASSWORD`

### 2. Token 存储迁移到 Redis

**现状**：进程内存 Dict 存储 token，多 worker 不兼容，无 TTL 清理。

**计划**：
- 引入 `redis` / `aioredis` 依赖
- 将 `token_store: Dict` 替换为 Redis，`SETEX token value TTL`
- 添加 `redis` 配置项到 `.env` 和 `config.py`
- 向下兼容：提供 `MemoryTokenStore` 回退用于开发环境

### 3. LLM 服务异常处理

**现状**：`generate_completion` 异常时静默返回空字符串，`chat` 流式异常时混入正常回答。

**计划**：
- 定义 `LLMServiceError` 自定义异常
- `generate_completion` 异常时抛出，让调用方决定降级策略
- `chat` 流式异常时，在 SSE 中追加 `{"type":"error","error":"..."}` 事件
- 前端处理 `error` 事件，展示友好提示

---

## 🟠 P1 — 功能正确性 (2-3 周)

### 4. NER 模型加载失败降级

**现状**：BERT 加载失败时 fallback 到随机初始化 Embedding，输出无意义结果。

**计划**：
- 删除随机 fallback
- 模型加载失败时降级到 `_rule_recognize()` 规则匹配 + `_simple_recognize()` 关键词
- 添加 `[WARN]` 级别日志明确告知降级状态

### 5. OCR / 多模态错误处理修复

**现状**：OCR 异常时缺少 `message` 字段，调用方无法区分"没文字"和"出错了"。

**计划**：
- 所有多模态端点统一错误响应格式：`{"text": "", "message": str(e), "status": "error"}`
- 前端根据 `status` 字段区分展示

### 6. TTS 参数传递修复

**现状**：Streamlit 发送 `json={"text": ...}`，后端 `text: str` 从 query parameter 解析，TTS 静默失效。

**计划**：
- 后端改为 `text: str = Form(...)` 或 Pydantic `Body` model
- 前端同步调整请求方式

### 7. 健康评估路由合并

**现状**：`/health` 与 `/health-assessment` 功能高度重复，维护两套代码。

**计划**：
- 将 `health_assessment.py` 的 `_maybe_create_alert` 告警逻辑合并到 `health.py`
- 删除 `health_assessment.py`，从 `api.py` 移除注册
- 同步更新前端调用

---

## 🟡 P2 — 代码质量与架构 (2-3 周)

### 8. 异常处理精细化

**现状**：约 33 处 `bare except Exception`，静默吞没错误。

**计划**：
- 按影响优先级逐文件替换（优先级: kg.py > llm_service.py > image_service.py > stats.py）
- 每个 `except` 改为具体异常类型 + 日志记录
- 添加请求级别的 `trace_id` 用于全链路日志追踪

### 9. WebSocket ConnectionManager 清理

**现状**：`active_connections` 列表只写入不读取，无广播功能使用。

**计划**：
- 删除死代码，简化为 `accept` + `close`
- 或升级为真实广播：新消息/高风险告警推送到在线用户

### 10. 类型标注补全

**现状**：`agents/` 和 `services/` 中约 17 处方法缺少返回类型标注。

**计划**：
- 优先补全：`orchestrator.py` > `doctor_service.py` > `health_agent.py` > 其他
- CI 中引入 `mypy` 检查（宽松模式起步）

### 11. Streamlit 前端拆分与状态管理

**现状**：`streamlit_app.py` 约 1700+ 行，医生端虽已分离但仍共享大量逻辑。

**计划**：
- 提取通用组件到 `app/ui/components/`（auth、API client、chart helpers）
- 引入 `streamlit-session-state` 统一管理跨页面状态
- 患者端和医生端各自引用共享组件

---

## 🟢 P3 — 功能增强 (3-4 周)

### 12. 多轮对话记忆

**现状**：Agent 无上下文记忆，每次对话独立。

**计划**：
- 在 `orchestrator` 层引入对话历史管理（最近 N 轮）
- 使用摘要策略：超过 N 轮时自动压缩历史为摘要
- Redis 持久化会话上下文（与 P0.2 的 Redis 基础设施共用）
- 医生端可查看患者的完整对话历史

### 13. 知识图谱增强

**现状**：单层实体查询，不支持多跳推理。

**计划**：
- 引入 `text2cypher` 模块：LLM 自动生成优化后的 Cypher 查询
- 扩展实体关系类型（并发症、药物相互作用、饮食禁忌）
- 添加知识图谱可视化前端组件（Neo4j 内置可视化或 D3.js）
- 支持多跳推理："XX 药物对做完 YY 手术的病人有什么风险？"

### 14. Agent 工具调用 (Function Calling)

**现状**：Agent 仅返回文本，无法执行实际操作。

**计划**：
- 实现 Tool/Function 定义框架
- 首批工具：创建提醒、查询打卡历史、获取天气（影响伤口恢复）、药物查询
- Agent 支持多轮 tool calling，自动组合多个工具完成复杂任务
- 医生端工具：一键查看患者风险报告、批量发送复查提醒

### 15. 消息推送通知系统

**现状**：医生发消息后患者需在对话界面才能看到，无主动通知。

**计划**：
- 新增 `GET /notifications/unread` 和 `POST /notifications/read` 端点
- 前端添加未读消息角标 + 消息列表弹窗
- 长期扩展：对接微信公众号/小程序推送、邮件通知

### 16. 语音交互完善

**现状**：语音识别可用但不够稳定，无 TTS 输出。

**计划**：
- 修复 TTS 参数解析问题（P1.6）
- 前端添加语音输入按钮 + 实时波形反馈
- 语音输出流式播放（TTS 返回音频流，前端逐段播放）
- 支持方言识别增强（粤语、四川话等医疗场景常见方言）

---

## 🔵 P4 — 长期演进 (1-3 个月)

### 17. 模型垂直领域微调

**现状**：NER 和 LLM 均使用通用模型。

**计划**：
- **NER**：基于现有 RoBERTa 模型，使用标注的术后医疗数据做 LoRA 微调，提升术后特有实体提取准确率
- **LLM**：基于 `finetune_demo` 中已有的数据管线，对 DeepSeek/Qwen 等模型做 SFT，提升术后管理领域的回答质量
- 建立评测基准（医学问答准确率、NER F1-score 等）

### 18. 智能预警与决策支持

**现状**：健康评估基于固定阈值规则。

**计划**：
- 引入时序异常检测算法，分析患者打卡数据的趋势变化
- 基于历史数据训练风险预测模型（术后并发症早期预警）
- 医生端展示风险趋势图 + 一键查看异常患者详情
- 高危患者自动置顶在医生面板

### 19. 报告生成与管理

**现状**：无自动化报告功能。

**计划**：
- 患者个人健康周报/月报自动生成（PDF）
- 医生端批量导出患者数据
- 报告包含：体征趋势图、用药记录、风险等级变化、医生建议汇总

### 20. 多语言国际化

**现状**：仅支持中文。

**计划**：
- 前端文案国际化（i18n），支持中/英文切换
- LLM 多语言回答能力（利用 DeepSeek 多语言能力）
- 为拓展海外医疗机构合作做准备

### 21. 系统可观测性

**现状**：无日志聚合、无性能监控。

**计划**：
- 引入 `structlog` 结构化日志
- 接入 Prometheus + Grafana 监控（API 延迟、错误率、LLM 调用量/成本、NER 准确率）
- 添加分布式追踪（trace_id 贯穿请求全链路）

### 22. CI/CD 与测试体系

**现状**：无自动化 CI/CD，无单元测试。

**计划**：
- 添加 `pytest` 单元测试和集成测试
- 引入 GitHub Actions：lint (ruff/mypy) → test → build
- Docker Compose 一键部署（MySQL + Neo4j + Redis + API + 前端）
- 预提交 hook：代码格式检查 + 密钥扫描

---

## 📊 工作量估算汇总

| 优先级 | 项目数 | 预计改动文件 | 预计工时 | 依赖 |
|--------|--------|-------------|---------|------|
| 🔴 P0 | 3 | ~8 | 3-4h | 无 |
| 🟠 P1 | 4 | ~6 | 2-3h | P0 完成 |
| 🟡 P2 | 4 | ~15 | 3-4h | P1 完成 |
| 🟢 P3 | 5 | ~20 | 4-6h | Redis (P0.2) |
| 🔵 P4 | 6 | ~30+ | 2-3 月 | P3 完成 |

---

## 🗺️ 建议执行路线

```
Week 1-2    P0.1 密码安全 ▸ P0.2 Redis Token ▸ P0.3 LLM 异常处理
Week 3-4    P1.4 NER 降级 ▸ P1.5 OCR 修复 ▸ P1.6 TTS 修复 ▸ P1.7 路由合并
Week 5-6    P2.8 异常精细化 ▸ P2.9 WebSocket 清理 ▸ P2.10 类型标注 ▸ P2.11 前端拆分
Week 7-10   P3.12 多轮记忆 ▸ P3.13 知识图谱增强 ▸ P3.14 Agent 工具调用
Week 11-14  P3.15 推送通知 ▸ P3.16 语音交互
Week 15+    P4.17-22 长期演进 (可并行推进)
```

---

## 📝 维护约定

- 每个 P0/P1 项完成时同步更新本文档状态
- 每月最后一周回顾 Roadmap，根据实际情况调整优先级
- 新需求通过 Issue/PR 讨论后加入本文档
- 已完成项标记 `~~删除线~~` 并注明完成日期
