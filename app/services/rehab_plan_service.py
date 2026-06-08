import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.db.session import db_instance
from app.services.llm_service import llm_service, LLMServiceError
from app.services.rehab_guideline_service import rehab_guideline_service


SYSTEM_PROMPT = """你是一名三甲医院康复医学科的主任医师，拥有20年临床康复经验。你擅长为不同手术类型的患者制定循证、个体化的分阶段康复方案。

## 你的专业原则

1. **循证医学为基础**：每个康复任务都应有明确的临床依据，参考《中国骨科大手术康复专家共识》《加速康复外科(ERAS)指南》等权威文献。

2. **高度个体化**：根据患者的手术类型、年龄、合并症、术前功能状态制定差异化方案。膝关节置换和髋关节置换的康复重点完全不同，不可泛泛而谈。

3. **任务必须具体可量化**：每条任务必须包含：
   - 具体动作/行为（不是"适当活动"而是"坐位下主动屈膝至90°"）
   - 量化参数（次数×组数、持续时间、距离、角度等）
   - 频率和时间（每天几次、什么时间做）
   - 安全边界/注意事项

4. **渐进式负荷**：康复任务应在阶段内有递进——同样一个动作，第1天和第7天的要求应该不同（增加次数、增加幅度、减少辅助等）。

5. **任务分类标准**：
   - medication：具体药物名称、剂量、用法、注意事项
   - exercise：具体动作名称、量化参数、进阶条件
   - diet：具体食物推荐/禁忌、营养素摄入量、餐次安排
   - review：复查项目、时间节点、目标指标

## 任务质量对照（反例→正例）

❌ "适当下床活动"
✅ "在助行器辅助下，于病房走廊平地行走50米，每天2次，步速以不引起气促为准"

❌ "做一些膝关节锻炼"
✅ "坐于床沿，患侧小腿自然下垂，主动缓慢屈膝至最大角度后保持10秒，再缓慢伸直，10次/组×3组/天"

❌ "注意饮食清淡"
✅ "每日蛋白质摄入≥1.2g/kg体重，推荐早餐1个鸡蛋+250ml牛奶，午餐/晚餐各100g瘦肉或鱼肉，避免油炸及辛辣食物"

❌ "按时吃药"
✅ "塞来昔布200mg 每日1次早餐后口服（镇痛抗炎），利伐沙班10mg 每日1次晚餐后口服（预防静脉血栓）"

输出格式为严格的 JSON，不要输出任何其他内容，不要使用 markdown 代码块包裹。"""

FALLBACK_PLAN = {
    "plan_title": "术后康复计划",
    "phases": [
        {
            "phase": "急性期",
            "duration_days": 14,
            "phase_goal": "控制术后疼痛与水肿，预防深静脉血栓和肺部感染，保护手术部位，开始早期安全活动",
            "daily_tasks": [
                {
                    "day": 1,
                    "tasks": [
                        {"type": "medication", "content": "术后镇痛药遵医嘱按时服用（常用：塞来昔布200mg每日1次或曲马多50mg每6小时按需），不可因怕成瘾而忍痛", "reminder_time": "08:00:00"},
                        {"type": "exercise", "content": "踝泵运动：平躺，双脚同时用力勾脚尖至最大角度保持5秒，再用力踩脚尖至最大角度保持5秒，20次/组，每小时清醒时做1组（每日约8-10组），预防深静脉血栓", "reminder_time": "09:00:00"},
                        {"type": "exercise", "content": "腹式深呼吸：平躺屈膝，鼻吸口呼，吸气时腹部鼓起，呼气时腹部内收，10次/组×3组/天，预防术后肺部感染", "reminder_time": "10:00:00"},
                        {"type": "diet", "content": "术后6小时麻醉清醒后可饮少量温水，无恶心呕吐后进食流质（米汤、藕粉），忌牛奶豆浆（易胀气）", "reminder_time": "12:00:00"},
                        {"type": "review", "content": "护士每4小时检查生命体征、伤口敷料有无渗血渗液、末梢血运及感觉运动功能", "reminder_time": "14:00:00"},
                    ]
                }
            ] + [
                {
                    "day": d,
                    "tasks": [
                        {"type": "medication", "content": "术后镇痛药遵医嘱服用；如有抗凝药（利伐沙班10mg每日1次或低分子肝素皮下注射）请在固定时间服用，不可随意停药", "reminder_time": "08:00:00"},
                        {"type": "exercise", "content": f"踝泵运动：20次/组，每小时清醒时1组；股四头肌等长收缩：平躺膝下垫小毛巾卷，大腿前侧用力收紧将膝窝下压床面，保持10秒后放松，15次/组×3组/天", "reminder_time": "09:00:00"},
                        {"type": "exercise", "content": f"床上坐起训练：摇高床头至半坐位(45-60°)，保持15分钟，每天2次，如出现头晕立即平卧 —— 术后第{d}天", "reminder_time": "10:00:00"} if d <= 3 else
                        {"type": "exercise", "content": f"床旁坐起+原地踏步：在护士或家属辅助下坐于床沿，双腿下垂5分钟后原地踏步30-50步，每天2次，如出现伤口剧痛或头晕立即停止 —— 术后第{d}天", "reminder_time": "10:00:00"},
                        {"type": "diet", "content": "高蛋白高维生素饮食：早餐1个鸡蛋+250ml牛奶+全麦面包2片，午餐/晚餐各100g瘦肉/鱼肉+200g蔬菜+150g米饭，全天饮水≥1500ml，忌辛辣油炸", "reminder_time": "07:30:00"},
                        {"type": "review", "content": "每3天更换伤口敷料一次，观察有无红肿热痛渗出 —— 术后第{d}天", "reminder_time": "09:00:00"} if d % 3 == 0 else
                        {"type": "other", "content": f"记录今日疼痛评分(0-10分)、手术部位肿胀程度、体温、排便情况", "reminder_time": "20:00:00"},
                    ]
                } for d in range(2, 15)
            ]
        },
        {
            "phase": "恢复期",
            "duration_days": 30,
            "phase_goal": "逐步恢复手术部位活动度和肌力，建立独立行走能力，回归居家日常生活",
            "daily_tasks": [
                {
                    "day": d,
                    "tasks": [
                        {"type": "medication", "content": "镇痛药用量逐步减少，转为按需服用；抗凝药继续按时服用至医生嘱停（通常术后2-4周）", "reminder_time": "08:00:00"},
                        {"type": "exercise", "content": f"主动关节活动度训练：坐位下主动活动手术邻近关节至最大角度，缓慢进行，每个方向15次×2组/天，以轻微牵拉感为度,不可暴力 — D{d}", "reminder_time": "09:00:00"},
                        {"type": "exercise", "content": f"渐进抗阻训练：弹力带/沙袋抗阻进行肌力训练，从最轻阻力开始，15次×3组/天，如能轻松完成则可增加下一级阻力 — D{d}", "reminder_time": "10:00:00"},
                        {"type": "exercise", "content": f"平地步行训练：{min(5 + d * 2, 30)}分钟/次×2次/天，步速以不引起明显疼痛为准，可使用助行器/手杖辅助逐步过渡至独立行走 — D{d}", "reminder_time": "15:00:00"},
                        {"type": "diet", "content": "每日蛋白质≥1.2g/kg体重，钙1000mg(相当于500ml牛奶+100g豆腐+100g绿叶菜)，维生素D 800IU，促进骨骼/软组织愈合", "reminder_time": "07:30:00"},
                        {"type": "review", "content": "术后第{d}天——建议到门诊复查：伤口愈合评估、手术部位X线/超声检查、康复进展评估", "reminder_time": "09:00:00"} if d % 7 == 0 else
                        {"type": "other", "content": f"记录今日活动量(步数/行走距离)、疼痛评分、关节活动度变化、有无异常症状", "reminder_time": "20:00:00"},
                    ]
                } for d in range(1, 31)
            ]
        },
        {
            "phase": "巩固期",
            "duration_days": 40,
            "phase_goal": "全面恢复肌力与功能，回归正常工作和社交活动，建立长期健康行为模式",
            "daily_tasks": [
                {
                    "day": d,
                    "tasks": [
                        {"type": "exercise", "content": f"综合力量训练：针对手术相关肌群进行中等强度抗阻训练(60-70%最大负荷)，使用弹力带/哑铃/自重，12-15次×3-4组，每周4-5天 — D{d}", "reminder_time": "09:00:00"},
                        {"type": "exercise", "content": f"有氧耐力训练：快走/功率自行车/椭圆机 {min(20 + d, 45)}分钟，心率控制在(220-年龄)×60-75%，每周5天 — D{d}", "reminder_time": "16:00:00"},
                        {"type": "diet", "content": "维持均衡饮食：每日蔬菜500g+水果200g+优质蛋白1.0-1.2g/kg+全谷物占主食1/2以上，限制添加糖和饱和脂肪", "reminder_time": "07:30:00"},
                        {"type": "review", "content": f"术后第{d}天——建议复查：功能评估(关节活动度+肌力+步态分析)，确认是否可回归工作/运动", "reminder_time": "09:00:00"} if d % 14 == 0 else
                        {"type": "other", "content": f"自我评估：记录本周功能改善(如行走距离增加、可上下楼梯级数、可完成的家务活动) —— D{d}", "reminder_time": "20:00:00"},
                    ]
                } for d in range(1, 41)
            ]
        }
    ],
    "notes": "【安全警示】1.如出现伤口红肿热痛加剧、发热>38.5℃、患肢明显肿胀或疼痛突然加重，请立即就医。2.康复训练应循序渐进，以轻微疲劳感为度，不可引起剧痛。3.所有训练在疼痛评分≤3/10范围内进行。4.用药请严格遵医嘱，不可自行调整或停用。",
    "expected_outcomes": "急性期结束：疼痛VAS≤3分、可独立完成床上活动和床旁转移；恢复期结束：独立步行>500米、关节活动度恢复至健侧70%以上；巩固期结束：回归正常工作和轻度运动"
}


def _get_surgery_specific_guidelines(surgery_type: str) -> str:
    """根据手术类型返回具体的康复指南"""
    guidelines = {
        "膝关节置换术": """
膝关节置换术(TKA)康复要点：
- 急性期(术后1-14天)：核心目标是消肿止痛、预防血栓、恢复股四头肌激活和被动伸膝
  运动重点：踝泵运动(每小时1组×20次)、股四头肌等长收缩(10次×3组/天)、被动/辅助主动伸膝(毛巾卷垫踝下)、CPM机(初始0-40°,每日增加5-10°)
  禁忌：避免膝关节过屈(>90°)、避免旋转动作、禁止跪姿
- 恢复期(术后2-6周)：核心目标是步态训练、主动屈膝至110°+、上下楼梯
  运动重点：靠墙半蹲(屈膝≤45°)、坐位伸膝抗阻、踏步训练、单腿站立平衡(扶稳)
- 巩固期(术后7-12周)：核心目标是恢复日常生活能力、肌力恢复至健侧80%+
  运动重点：功率自行车、靠墙静蹲(逐步加深角度)、上下楼梯训练(上健下患)""",

        "髋关节置换术": """
髋关节置换术(THA)康复要点：
- 急性期(术后1-14天)：核心目标是预防脱位、消肿、恢复髋周肌群激活
  运动重点：踝泵、臀肌等长收缩、股四头肌等长收缩、床上髋关节滑动(屈髋≤60°)
  禁忌：屈髋超过90°、内收过中线、内旋——这三个动作会导致脱位！
- 恢复期(术后2-6周)：核心目标是独立行走、上下楼梯、屈髋逐步增加
  运动重点：站立位髋外展(扶稳)、桥式运动、半蹲(屈髋≤70°)、功率自行车(坐高调至屈髋≤90°)
- 巩固期(术后7-12周)：核心目标是正常步态、回归轻度运动
  运动重点：弹力带抗阻训练、步行距离渐进增加、上下楼梯正常化""",

        "腰椎间盘手术": """
腰椎间盘术后康复要点：
- 急性期(术后1-14天)：核心目标是神经根水肿消退、切口愈合、预防神经根粘连
  运动重点：踝泵(防血栓)、腹式呼吸(减轻腹压)、直腿抬高(被动→主动)、床上轴向翻身
  禁忌：弯腰、扭转、坐超过30分钟、提>5kg重物
- 恢复期(术后2-6周)：核心目标是核心肌群激活、逐步恢复坐立行走
  运动重点：腹横肌激活(平躺缩腹)、鸟狗式(循序渐进)、靠墙半蹲、平地步行(从10分钟起)
- 巩固期(术后7-12周)：核心目标是核心稳定性、回归工作和轻度运动
  运动重点：平板支撑(从10秒×3组起)、侧桥、游泳(术后3个月后)、避免深蹲和硬拉""",

        "骨折内固定术": """
骨折内固定术后康复要点：
- 急性期(术后1-14天)：核心目标是固定保护、消肿、邻近关节被动活动
  运动重点：患肢抬高(高于心脏)、冰敷(每2-3小时×20分钟)、邻近关节主动活动、等长收缩
- 恢复期(术后2-8周)：核心目标是骨痂形成期保护下的渐进负重(遵医嘱)
  运动重点：在支具/石膏保护下的可控关节活动度训练、对侧肢体代偿训练
- 巩固期(术后8周+，需X线确认骨愈合)：逐步拆除外固定、恢复肌力和日常功能""",
    }

    return guidelines.get(surgery_type, f"""
{surgery_type}术后康复要点（通用框架）：
- 急性期(术后1-14天)：消肿镇痛、伤口护理、预防并发症(血栓/感染/关节僵硬)、保护手术部位
- 恢复期(术后2-6周)：逐步恢复手术部位功能、增加活动耐量、针对性肌力训练
- 巩固期(术后7-12周)：恢复日常生活和社会参与能力、建立长期自我管理习惯
""")


def _build_generation_prompt(surgery_type: str, profile: Optional[Dict]) -> List[Dict]:
    age = profile.get("age", "未知") if profile else "未知"
    gender = profile.get("gender", "未知") if profile else "未知"
    medical_history = profile.get("medical_history", "无") if profile else "无"
    allergy_history = profile.get("allergy_history", "无") if profile else "无"
    current_medications = profile.get("current_medications", "无") if profile else "无"
    health_stage = profile.get("health_stage", "长期管理") if profile else "长期管理"

    surgery_line = f"手术类型: {surgery_type}" if surgery_type else "手术类型: 无（非术后患者，制定通用健康管理计划）"
    title_example = f"{surgery_type}术后康复计划" if surgery_type else "个性化健康管理计划"
    surgery_guidelines = _get_surgery_specific_guidelines(surgery_type) if surgery_type else ""

    # RAG检索：从临床指南数据库检索该手术的循证指南
    rag_guidelines = ""
    if surgery_type:
        rag_guidelines = rehab_guideline_service.format_for_prompt(surgery_type)
        if not rag_guidelines:
            rag_guidelines = "（该手术类型暂无专项指南，请基于通用康复原则和高级提示制定方案）"

    user_content = f"""请为以下患者制定一份高度个体化、可执行的康复计划：

## 患者信息
{surgery_line}
年龄: {age}
性别: {gender}
病史: {medical_history}
过敏史: {allergy_history}
当前用药: {current_medications}
健康阶段: {health_stage}

## 手术特异性康复指南（高级提示）
{surgery_guidelines}

## 📚 循证临床指南（RAG检索 — 必须严格参考）
以下是从临床指南数据库中检索到的该手术类型循证康复方案。你必须依据这些指南来制定任务——包含的具体动作、量化参数(次数/角度/时间)和安全警告必须与指南一致。指南中明确禁止的动作绝对不能出现在任务中。

{rag_guidelines}

## 任务编制要求（非常重要）

### 1. 任务必须有递进性
同一阶段的每一天，任务内容应有所变化。例如：
- 第1天："在护士辅助下，于床旁坐起，双腿下垂，保持5分钟，每天2次"
- 第3天："扶助行器独立站起，原地踏步20步，每天3次"
- 第7天："扶助行器在病房走廊行走30米，每天2次"

### 2. 每个任务必须包含量化指标
- 运动类：次数×组数、持续时间、角度范围、距离、辅助级别（独立/辅助/被动）
- 饮食类：具体食物名称、份量、营养素目标
- 用药类：药物通用名和常见商品名、剂量、频次、服用时间点

### 3. 安全边界必须明确
每个运动任务标注"如出现____情况请暂停"。

### 4. 计划结构
- 急性期: 7-14天，根据手术创伤大小调整
- 恢复期: 14-30天，急性期结束后进入
- 巩固期: 30-60天

### 5. 每日至少3-5个不同任务
覆盖 medication、exercise、diet、review 等类别，确保全天有安排的康复活动。

## JSON输出格式（严格遵循）
{{
  "plan_title": "{title_example}",
  "phases": [
    {{
      "phase": "急性期",
      "duration_days": 14,
      "phase_goal": "本阶段核心目标（一句话描述）",
      "daily_tasks": [
        {{
          "day": 1,
          "tasks": [
            {{"type": "medication", "content": "具体药物+剂量+用法+注意事项", "reminder_time": "08:00:00"}},
            {{"type": "exercise", "content": "具体动作+量化参数+安全边界", "reminder_time": "10:00:00"}},
            {{"type": "diet", "content": "具体食物+份量+营养素目标", "reminder_time": "07:30:00"}},
            {{"type": "review", "content": "具体复查项目+目的", "reminder_time": "09:00:00"}}
          ]
        }}
      ]
    }}
  ],
  "notes": "总体的安全警示和注意事项",
  "expected_outcomes": "各阶段预期达到的康复目标"
}}"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]


def _parse_plan_json(text: str) -> Optional[Dict]:
    """尝试从 LLM 返回中解析 JSON，支持多种容错情况。"""
    text = text.strip()
    # 去掉 markdown 代码块
    if text.startswith("```"):
        lines = text.split("\n")
        # 去掉首行 ```json 和末行 ```
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试找到第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    return None


# 映射 LLM 可能返回的阶段名到数据库 ENUM 值
_PHASE_ALIASES = {
    "基础调整期": "急性期",
    "适应期": "急性期",
    "初期": "急性期",
    "习惯养成期": "恢复期",
    "恢复期": "恢复期",
    "巩固提升期": "巩固期",
    "巩固期": "巩固期",
    "维持期": "巩固期",
}


def _normalize_phase(phase_name: str) -> str:
    """将 LLM 返回的阶段名映射到数据库允许的 ENUM 值。"""
    if phase_name in ("急性期", "恢复期", "巩固期"):
        return phase_name
    return _PHASE_ALIASES.get(phase_name, "急性期")


class RehabPlanService:

    def async_generate_plan(self, username: str, surgery_type: str, plan_title: str = "") -> Dict:
        """同步版本：生成康复计划。用在 Agent tool 中。"""
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.generate_plan(username, surgery_type, plan_title))
        finally:
            loop.close()

    async def generate_plan(self, username: str, surgery_type: str, plan_title: str = "") -> Dict:
        """AI 生成康复计划并存储。"""
        # 1. 获取患者档案
        profile = db_instance.get_patient_profile(username)

        # 2. 构造 prompt，调用 LLM
        messages = _build_generation_prompt(surgery_type, profile)
        plan_data = None

        try:
            response = await llm_service.generate_completion_with_messages(messages)
            plan_data = _parse_plan_json(response)
        except LLMServiceError:
            pass

        # 解析失败则重试一次
        if plan_data is None:
            try:
                retry_messages = messages + [
                    {"role": "assistant", "content": response if 'response' in dir() else ""},
                    {"role": "user", "content": "请只输出合法的 JSON 对象，不要任何解释或标记。"}
                ]
                response2 = await llm_service.generate_completion_with_messages(retry_messages)
                plan_data = _parse_plan_json(response2)
            except (LLMServiceError, Exception):
                pass

        # 兜底方案
        if plan_data is None:
            plan_data = json.loads(json.dumps(FALLBACK_PLAN))
            if not plan_title:
                plan_title = f"{surgery_type}康复计划" if surgery_type else "健康管理计划"
            plan_data["plan_title"] = plan_title
        elif not plan_title and plan_data.get("plan_title"):
            plan_title = plan_data["plan_title"]

        if not plan_title:
            plan_title = f"{surgery_type}康复计划" if surgery_type else "健康管理计划"

        # 3. 存储计划
        generated_plan_text = json.dumps(plan_data, ensure_ascii=False, indent=2)
        plan_id = db_instance.save_rehab_plan(username, surgery_type, plan_title, generated_plan_text)
        if plan_id is None:
            return {"success": False, "error": "保存康复计划失败"}

        # 4. 存储每日任务 + 创建提醒
        start_date = datetime.now()
        all_tasks = []
        phases = plan_data.get("phases", [])

        for phase_info in phases:
            phase_name = _normalize_phase(phase_info.get("phase", "急性期"))
            daily_tasks = phase_info.get("daily_tasks", [])

            for day_info in daily_tasks:
                day_num = day_info.get("day", 1)
                task_date = (start_date + timedelta(days=day_num - 1)).strftime("%Y-%m-%d")

                for task in day_info.get("tasks", []):
                    task_type = task.get("type", "other")
                    task_content = task.get("content", "")
                    reminder_time = task.get("reminder_time")

                    # 创建提醒
                    reminder_id = None
                    if reminder_time:
                        reminder_id = db_instance.save_reminder(
                            username=username,
                            reminder_type="康复任务",
                            title=f"[{phase_name}] {task_content[:30]}",
                            description=task_content,
                            reminder_date=task_date,
                            reminder_time=reminder_time
                        )

                    db_instance.save_rehab_plan_task(
                        plan_id=plan_id,
                        username=username,
                        phase=phase_name,
                        task_day=day_num,
                        task_date=task_date,
                        task_type=task_type,
                        task_content=task_content,
                        reminder_id=reminder_id
                    )

                    all_tasks.append({
                        "phase": phase_name,
                        "task_day": day_num,
                        "task_date": task_date,
                        "task_type": task_type,
                        "task_content": task_content,
                        "reminder_id": reminder_id,
                        "status": "pending"
                    })

        return {
            "success": True,
            "plan_id": plan_id,
            "plan_title": plan_title,
            "surgery_type": surgery_type,
            "current_phase": "急性期",
            "phases": [p.get("phase") for p in phases],
            "total_tasks": len(all_tasks),
            "notes": plan_data.get("notes", ""),
            "generated_plan": plan_data
        }

    def get_user_plans(self, username: str, status: str = None) -> List[Dict]:
        return db_instance.get_rehab_plans(username, status)

    def get_plan_detail(self, plan_id: int) -> Optional[Dict]:
        plan = db_instance.get_rehab_plan(plan_id)
        if not plan:
            return None
        tasks = db_instance.get_rehab_plan_tasks(plan_id)
        # 按阶段分组
        phases = {}
        for t in tasks:
            phase = t.get("phase", "急性期")
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(t)
        plan["phases"] = phases
        return plan

    def get_today_tasks(self, username: str) -> List[Dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        return db_instance.get_today_rehab_tasks(username, today)

    def complete_task(self, username: str, task_id: int) -> Dict:
        task = db_instance.get_rehab_plan_task(task_id)
        if not task:
            return {"success": False, "error": "任务不存在"}
        if task.get("username") != username:
            return {"success": False, "error": "无权操作此任务"}

        ok = db_instance.update_rehab_task_status(task_id, "completed")
        if not ok:
            return {"success": False, "error": "更新任务状态失败"}

        # 同步提醒状态
        reminder_id = task.get("reminder_id")
        if reminder_id:
            db_instance.update_reminder_status(username, reminder_id, "completed")

        # 检查当前阶段是否全部完成
        plan = db_instance.get_rehab_plan(task["plan_id"])
        current_phase = plan.get("current_phase", "急性期") if plan else "急性期"
        stats = db_instance.get_rehab_plan_phase_task_stats(task["plan_id"], current_phase)
        phase_complete = stats.get("total", 0) > 0 and stats.get("total") == stats.get("completed")

        # 推荐下一个阶段
        phase_order = ["急性期", "恢复期", "巩固期"]
        next_phase = None
        if phase_complete and current_phase in phase_order:
            idx = phase_order.index(current_phase)
            if idx < len(phase_order) - 1:
                next_phase = phase_order[idx + 1]

        # 更新计划统计（完成率、连续打卡）
        db_instance.update_rehab_plan_stats(task["plan_id"])

        # 检查并触发成就
        from app.services.rehab_achievement_service import rehab_achievement_service
        ach_result = rehab_achievement_service.check_and_award(username, task["plan_id"])
        new_achievements = ach_result.get("new_achievements", [])

        return {
            "success": True,
            "task_id": task_id,
            "status": "completed",
            "phase_complete": phase_complete,
            "current_phase": current_phase,
            "next_phase": next_phase,
            "phase_stats": stats,
            "new_achievements": new_achievements
        }

    def cancel_plan(self, plan_id: int, username: str) -> bool:
        tasks = db_instance.get_rehab_plan_tasks(plan_id)
        for t in tasks:
            reminder_id = t.get("reminder_id")
            if reminder_id:
                db_instance.update_reminder_status(username, reminder_id, "cancelled")
        return db_instance.update_rehab_plan_status(plan_id, "cancelled")

    def advance_phase(self, plan_id: int, new_phase: str) -> bool:
        phase_order = ["急性期", "恢复期", "巩固期"]
        if new_phase not in phase_order:
            return False
        plan = db_instance.get_rehab_plan(plan_id)
        if not plan:
            return False
        current = plan.get("current_phase", "急性期")
        if current in phase_order and new_phase in phase_order:
            if phase_order.index(new_phase) < phase_order.index(current):
                return False  # 不能回退
        return db_instance.update_rehab_plan_phase(plan_id, new_phase)

    def get_dashboard_data(self, plan_id: int) -> Dict:
        plan = db_instance.get_rehab_plan(plan_id)
        if not plan:
            return {"success": False, "error": "计划不存在"}

        stats = db_instance.get_rehab_dashboard_stats(plan_id)
        today = __import__("datetime").datetime.now()
        year, month = today.year, today.month

        calendar_data = db_instance.get_rehab_calendar_data(plan_id, year, month)
        today_tasks = db_instance.get_today_rehab_tasks(
            plan.get("username"), today.strftime("%Y-%m-%d"))
        latest_metrics = db_instance.get_latest_metrics(plan_id)

        # 阶段统计
        phase_order = ["急性期", "恢复期", "巩固期"]
        phase_stats = {}
        for p in phase_order:
            stats_p = db_instance.get_rehab_plan_phase_task_stats(plan_id, p)
            phase_stats[p] = stats_p

        return {
            "success": True,
            "plan": plan,
            "stats": stats,
            "calendar": calendar_data,
            "today_tasks": today_tasks,
            "latest_metrics": latest_metrics,
            "phase_stats": phase_stats
        }

    def get_calendar_data(self, plan_id: int, year: int, month: int) -> Dict:
        data = db_instance.get_rehab_calendar_data(plan_id, year, month)
        return {"success": True, "calendar": data}


rehab_plan_service = RehabPlanService()
