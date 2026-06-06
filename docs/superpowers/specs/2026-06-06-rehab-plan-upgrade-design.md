# 康复计划模块全面升级 — 设计文档

> **日期**: 2026-06-06
> **状态**: 设计已确认，待实现
> **技术栈**: Vue 3 + Element Plus + ECharts + Pinia | FastAPI + MySQL + LLM

---

## 1. 目标与范围

对《患者全周期康复系统》的康复计划模块进行全面升级，从"简陋的三阶段任务列表"升级为包含 **日历热力图、量化指标追踪、运动指导库、康复日志、游戏化成就、医生协作面板、AI动态调整** 的全功能康复管理子系统。

### 1.1 核心升级点

| # | 模块 | 当前状态 | 目标状态 |
|---|------|---------|---------|
| 1 | 阶段管理 | 固定三阶段线性推进 | 可配置多阶段 + Gantt时间线 |
| 2 | 数据可视化 | 仅圆点进度条 | 折线图/雷达图/环形图/热力图 |
| 3 | 时间管理 | 仅"今日任务" | 月/周/日三级日历 + 热力图 |
| 4 | 指标追踪 | 无 | 疼痛VAS/ROM/肌力/生命体征 |
| 5 | 运动指导 | 文字描述 | 分类视频/动图/图文分步教程 |
| 6 | 康复日志 | 无 | 富文本+照片+语音+问答 |
| 7 | 成就系统 | 无 | 徽章/连击/里程碑/积分 |
| 8 | 医生协作 | 医生完全看不到 | 查看/调整/反馈患者康复计划 |

### 1.2 排除范围

- 不涉及现有 A/B/C 三条并行开发线的任何文件
- 不修改 `app/agents/rehab_plan_agent.py` 的 Agent 路由逻辑（仅扩展）
- 不修改现有认证/权限体系
- 运动视频的实时姿态检测（如 MediaPipe 骨骼追踪）不在本期范围

---

## 2. 架构方案：多视图模块架构

从单文件 `RehabPlanView.vue` 拆分为独立子模块，每个功能对应独立路由和视图。

### 2.1 路由结构

**患者端：**
```
/patient/rehab                   → RehabLayout（左侧竖导航 + router-view）
  /patient/rehab/                → RehabDashboard（总览仪表盘）
  /patient/rehab/calendar        → RehabCalendar（日历视图）
  /patient/rehab/metrics         → RehabMetrics（量化指标）
  /patient/rehab/exercises       → RehabExercise（运动指导库）
  /patient/rehab/journal         → RehabJournal（康复日志）
  /patient/rehab/achievements    → RehabAchievements（成就系统）
```

**医生端（新增）：**
```
/doctor/patient/:username/rehab  → PatientRehabView（患者康复全貌）
  /doctor/patient/:username/rehab/overview   → 康复概览
  /doctor/patient/:username/rehab/plan       → 查看/调整计划
  /doctor/patient/:username/rehab/progress   → 指标趋势图表
```

### 2.2 文件结构

```
src/
├── views/rehab/
│   ├── RehabLayout.vue              # 子模块总布局
│   ├── RehabDashboard.vue           # 总览仪表盘
│   ├── RehabCalendar.vue            # 智能康复日历
│   ├── RehabMetrics.vue             # 量化指标追踪
│   ├── RehabExercise.vue            # 运动指导库
│   ├── RehabJournal.vue             # 康复日志
│   ├── RehabAchievements.vue        # 成就系统
│   └── doctor/
│       └── PatientRehabView.vue     # 医生端总览
├── components/rehab/
│   ├── RehabSideNav.vue             # 康复子导航
│   ├── PhaseTimeline.vue            # Gantt式阶段时间线
│   ├── MetricChart.vue              # 可复用图表组件
│   ├── CalendarHeatmap.vue          # 日历热力图
│   ├── ExerciseCard.vue             # 运动卡片
│   ├── ExercisePlayer.vue           # 视频播放+图文
│   ├── JournalEditor.vue            # 日志编辑器
│   ├── AchievementBadge.vue         # 成就徽章
│   ├── StreakCounter.vue            # 连续打卡
│   ├── PainScaleInput.vue           # VAS评分选择器
│   ├── ROMTracker.vue               # ROM输入/展示
│   ├── PlanAdjustPanel.vue          # 医生调整面板
│   └── AchievementPopup.vue         # 成就弹出动画
├── composables/
│   ├── useRehabPlan.ts              # 计划状态
│   ├── useRehabMetrics.ts           # 指标逻辑
│   ├── useRehabCalendar.ts          # 日历逻辑
│   └── useAchievements.ts           # 成就逻辑
├── services/
│   └── rehabPlan.ts                 # 扩展 API 调用
└── stores/
    └── rehab.ts                     # Pinia 状态管理
```

### 2.3 新增依赖

```json
{
  "dependencies": {
    "@vuepic/vue-datepicker": "^latest",
    "video.js": "^latest",
    "swiper": "^latest"
  }
}
```

ECharts 已存在于项目中（`echarts` + `vue-echarts`），图表需求完全覆盖。

---

## 3. 数据库 Schema

### 3.1 新增表

#### rehab_metrics — 量化指标追踪

```sql
CREATE TABLE rehab_metrics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    plan_id INT NOT NULL,
    username VARCHAR(50) NOT NULL,
    metric_date DATE NOT NULL,
    metric_type ENUM('pain_vas', 'rom_flexion', 'rom_extension', 'muscle_strength',
                     'weight', 'temperature', 'blood_pressure_sys', 'blood_pressure_dia',
                     'heart_rate', 'sleep_hours', 'wound_status', 'swelling_level',
                     'walking_distance', 'custom') NOT NULL,
    metric_value DECIMAL(10,2),
    metric_unit VARCHAR(20),
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_metric (plan_id, metric_date, metric_type),
    FOREIGN KEY (plan_id) REFERENCES rehab_plans(id)
);
```

#### rehab_exercises — 运动指导库

```sql
CREATE TABLE rehab_exercises (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(100) NOT NULL,
    category ENUM('stretching', 'strength', 'balance', 'mobility', 'breathing', 'other'),
    difficulty ENUM('easy', 'medium', 'hard'),
    target_body_part VARCHAR(50),
    surgery_type_tag VARCHAR(50),
    video_url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    image_urls JSON,
    description TEXT,
    steps JSON,
    duration_minutes INT,
    repetitions INT,
    precautions TEXT,
    phase_suitable ENUM('急性期','恢复期','巩固期'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### rehab_journals — 康复日志

```sql
CREATE TABLE rehab_journals (
    id INT PRIMARY KEY AUTO_INCREMENT,
    plan_id INT NOT NULL,
    username VARCHAR(50) NOT NULL,
    journal_date DATE NOT NULL,
    mood ENUM('great','good','okay','bad','terrible'),
    pain_level TINYINT CHECK(pain_level BETWEEN 0 AND 10),
    content TEXT,
    photo_urls JSON,
    voice_url VARCHAR(500),
    sleep_quality TINYINT CHECK(sleep_quality BETWEEN 1 AND 5),
    appetite TINYINT CHECK(appetite BETWEEN 1 AND 5),
    energy_level TINYINT CHECK(energy_level BETWEEN 1 AND 5),
    questions_for_doctor TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_journal (plan_id, journal_date),
    FOREIGN KEY (plan_id) REFERENCES rehab_plans(id)
);
```

#### achievement_defs + user_achievements — 成就系统

```sql
CREATE TABLE achievement_defs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(30) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(200),
    icon_url VARCHAR(500),
    category ENUM('streak','milestone','compliance','recovery','special'),
    condition_json JSON,
    points INT DEFAULT 10
);

CREATE TABLE user_achievements (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    plan_id INT NOT NULL,
    achievement_id INT NOT NULL,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_achievement (username, plan_id, achievement_id),
    FOREIGN KEY (achievement_id) REFERENCES achievement_defs(id)
);
```

### 3.2 扩展现有表

```sql
-- rehab_plans 新增
ALTER TABLE rehab_plans ADD COLUMN plan_type ENUM('ai_generated','template','custom') DEFAULT 'ai_generated';
ALTER TABLE rehab_plans ADD COLUMN target_metrics JSON;
ALTER TABLE rehab_plans ADD COLUMN total_completion_rate DECIMAL(5,2) DEFAULT 0;
ALTER TABLE rehab_plans ADD COLUMN current_streak INT DEFAULT 0;
ALTER TABLE rehab_plans ADD COLUMN longest_streak INT DEFAULT 0;
ALTER TABLE rehab_plans ADD COLUMN last_checkin_date DATE;
ALTER TABLE rehab_plans ADD COLUMN surgery_date DATE;
ALTER TABLE rehab_plans ADD COLUMN doctor_feedback JSON;

-- rehab_tasks 新增
ALTER TABLE rehab_tasks ADD COLUMN exercise_id INT;
ALTER TABLE rehab_tasks ADD COLUMN completed_at TIMESTAMP;
ALTER TABLE rehab_tasks ADD COLUMN patient_note TEXT;
ALTER TABLE rehab_tasks ADD COLUMN difficulty_rating TINYINT CHECK(difficulty_rating BETWEEN 1 AND 5);
```

---

## 4. API 端点设计

### 4.1 指标

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/rehab-plan/{plan_id}/metrics` | 记录/更新当日指标 |
| `GET` | `/api/v1/rehab-plan/{plan_id}/metrics?type=&from=&to=` | 获取指标历史 |
| `GET` | `/api/v1/rehab-plan/{plan_id}/metrics/latest` | 最新指标快照 |

### 4.2 运动库

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/rehab-exercises?phase=&category=&surgery=` | 运动库列表 |
| `GET` | `/api/v1/rehab-exercises/{id}` | 运动详情 |
| `GET` | `/api/v1/rehab-exercises/recommended` | AI推荐 |

### 4.3 日志

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/rehab-plan/{plan_id}/journals` | 创建日志 |
| `GET` | `/api/v1/rehab-plan/{plan_id}/journals?from=&to=` | 日志列表 |
| `GET` | `/api/v1/rehab-plan/{plan_id}/journals/{journal_id}` | 日志详情 |
| `PUT` | `/api/v1/rehab-plan/{plan_id}/journals/{journal_id}` | 编辑日志 |

### 4.4 成就

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/rehab-plan/{plan_id}/achievements` | 已获成就 |
| `GET` | `/api/v1/rehab-achievements/defs` | 所有成就定义 |

### 4.5 仪表盘

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/rehab-plan/{plan_id}/dashboard` | 聚合仪表盘数据 |
| `GET` | `/api/v1/rehab-plan/{plan_id}/calendar?month=` | 月度日历数据 |

### 4.6 医生端

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/doctor/patients/{username}/rehab` | 患者康复全貌 |
| `PUT` | `/api/v1/doctor/patients/{username}/rehab/plan` | 调整计划 |
| `POST` | `/api/v1/doctor/patients/{username}/rehab/feedback` | 发送反馈 |

### 4.7 现有端点保留

现有 7 个端点 (`generate`, `GET /`, `GET /tasks/today`, `GET /{id}`, `POST /tasks/complete`, `PUT /{id}/phase`, `DELETE /{id}`) 全部保留，向后兼容。

---

## 5. UI/UX 规格

### 5.1 RehabDashboard（总览仪表盘）

三行网格布局：
- **顶部统计栏**：连续打卡天数、总完成率（环形图）、当前阶段信息
- **中部日历热力图**：当月每日完成情况，绿=全完成、黄=部分完成、灰=未打卡
- **底部双栏**：今日任务列表 + 本周指标趋势迷你折线图

### 5.2 RehabCalendar（智能康复日历）

- 月/周/日三视图切换
- 日期格子上用颜色标注该日任务完成状态
- 点击具体日期展开当日任务详情 + 指标快照 + 日志摘要

### 5.3 RehabMetrics（量化指标追踪）

- 顶部标签切换不同指标类型（疼痛VAS / ROM / 肌力 / 自定义）
- 主图表区：折线图展示指标趋势，标注目标线和异常点
- 底部：今日记录表单 + 历史记录列表

### 5.4 RehabExercise（运动指导库）

- 搜索栏 + 筛选标签（阶段/类别/难度）
- 卡片网格展示运动，每卡片含缩略图/动图、标题、时长、难度
- 点击进入详情：视频播放器 + 分步图文指导 + 注意事项
- AI推荐区域：基于当前阶段和手术类型推荐

### 5.5 RehabJournal（康复日志）

- 顶部：心情选择器 + VAS疼痛滑块 + 睡眠/食欲/精力星级
- 中部：富文本编辑器（支持加粗/斜体/列表）
- 底部：照片上传区（多张，自动生成对比图）+ 语音按钮
- 问题框：填写想咨询医生的问题

### 5.6 RehabAchievements（成就系统）

- 分值总览 + 等级
- 按类别分区展示成就徽章（已获亮色/未获灰色+锁定图标）
- 点击徽章查看获取条件和获得日期
- 新成就获得时：屏幕中央弹出动画 + 音效

### 5.7 医生端 PatientRehabView

- 顶部患者信息 + 关键数据摘要
- 子标签：康复概览 / 计划详情 / 指标趋势 / 日志
- 指标趋势折线图支持多指标叠加
- 异常自动高亮标注
- 操作按钮：调整计划、发送反馈、标记关注

---

## 6. 状态管理

### 6.1 Pinia Store: `useRehabStore`

```typescript
// 核心数据
activePlan, todayTasks, allTasks

// 仪表盘
dashboardData, calendarData

// 指标（按类型缓存，5分钟TTL）
metricsHistory: Record<string, MetricPoint[]>
latestMetrics: Record<string, MetricPoint>

// 运动库
exercises, recommendedExercises

// 日志
journals, currentJournal

// 成就
userAchievements, allAchievementDefs
newAchievements: AchievementDef[]  // 待展示的弹窗成就
```

### 6.2 缓存策略

- 仪表盘聚合数据：请求 `/dashboard` 单次获取
- 图表数据：切换到对应页面时懒加载，Store 缓存 5 分钟
- 运动库：按筛选条件缓存
- 成就弹窗：任务完成/指标录入后，后端返回 `new_achievements`，前端即时弹出

---

## 7. 后端服务层设计

### 7.1 新建服务

| 服务文件 | 职责 |
|---------|------|
| `app/services/rehab_metrics_service.py` | 指标 CRUD + 趋势聚合 |
| `app/services/rehab_exercise_service.py` | 运动库管理 + 推荐 |
| `app/services/rehab_journal_service.py` | 日志 CRUD |
| `app/services/rehab_achievement_service.py` | 成就定义 + 检查/授予 |
| `app/services/rehab_doctor_service.py` | 医生端聚合查询 |

### 7.2 扩展现有服务

`app/services/rehab_plan_service.py` 新增方法：
- `get_dashboard_data(plan_id)` — 聚合仪表盘数据
- `get_calendar_data(plan_id, month)` — 月度日历聚合
- `check_and_award_achievements(plan_id, username)` — 触发成就检查

### 7.3 AI扩展

`rehab_plan_agent.py` 的工具扩展：
- `recommend_exercises(surgery_type, phase, metrics)` — 基于指标推荐运动
- `adjust_plan(plan_id, reason, adjustments)` — 医生触发AI辅助调整
- `generate_journal_prompt(journal_entries)` — 基于日志生成AI洞察

---

## 8. 实现顺序

| 阶段 | 内容 | 预估 |
|------|------|------|
| **P1** | 数据库迁移 + 后端基础 API（指标/日志/运动库） | 2天 |
| **P2** | RehabLayout + RehabDashboard（总览仪表盘） | 1.5天 |
| **P3** | RehabCalendar（日历热力图） | 1天 |
| **P4** | RehabMetrics（指标图表） | 1天 |
| **P5** | RehabExercise（运动库） | 1.5天 |
| **P6** | RehabJournal（康复日志） | 1天 |
| **P7** | RehabAchievements（成就系统） | 1天 |
| **P8** | 医生端 PatientRehabView | 1.5天 |
| **P9** | AI增强（推荐/调整） + 联调测试 | 1.5天 |

**总计预估：约 12 天**

---

## 9. 参考项目

| 项目 | 可参考内容 |
|------|-----------|
| [Sisyphus](https://github.com/Sisyphus-Training/Sisyphus) | 康复运动库设计、患者档案集成 |
| [Workout.cool](https://github.com/workoutcool/workout-cool) | 训练计划UI、视频演示、进度图表 |
| [atomic-habits-tracker](https://github.com/Elliottjh/atomic-habits-tracker) | 日历热力图、习惯分析面板 |
| [Habit Tracker Web App](https://github.com/TheUnknown550/Habit-Tracker-Web-App) | 成就徽章、打卡动画、统计仪表盘 |
| [RehabFlow](https://devpost.com/software/rehabflow) | AI康复计划、游戏化XP/等级 |
| [MedHealth](https://github.com/yerramsettysuchita/MedHealth---Advanced-Health-Care-Portal) | 患者/医生双面板、Chart.js图表 |

---

*本文档基于与用户的四轮迭代确认生成，所有设计已获批准。*
