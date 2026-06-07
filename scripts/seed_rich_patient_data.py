"""
插入丰富病患数据脚本
包含：6 名患者（低/中/高风险各 2 名），每人 14 天打卡记录 + 健康档案 + 健康评估 + 提醒 + 告警

用法: python scripts/seed_rich_patient_data.py
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.local_db_utils import DatabaseConnector
from database.password_utils import encrypt_password
from app.services.checkin_service import checkin_service

db = DatabaseConnector()
db.connect()

TODAY = datetime.now().date()
START_DATE = TODAY - timedelta(days=13)  # 14 天数据

# ────────────────────────────────────────────────────────
# 患者数据定义
# ────────────────────────────────────────────────────────

PATIENTS = [
    # ── 低风险患者 ──────────────────────────────────────
    {
        "username": "patient_sunli",
        "password": "sunli2026",
        "profile": {
            "real_name": "孙丽",
            "gender": "女",
            "age": 32,
            "phone": "13810001001",
            "height": 165.0,
            "weight": 55.0,
            "blood_type": "A",
            "medical_history": "阑尾炎术后1个月",
            "allergy_history": "无",
            "current_medications": "头孢克肟 200mg 每日两次",
            "emergency_contact": "孙丽丈夫",
            "emergency_phone": "13810001002",
            "health_stage": "术后恢复",
        },
        # 14 天打卡：恢复良好，指标稳定
        "checkins": [
            {"symptoms": "伤口轻微疼痛", "temperature": 36.8, "blood_pressure": "115/75", "blood_sugar": 5.1, "heart_rate": 72, "sleep": "良好", "diet": "正常", "exercise": "散步30分钟", "med": True, "note": "恢复顺利"},
            {"symptoms": "无不适", "temperature": 36.5, "blood_pressure": "112/73", "blood_sugar": 5.0, "heart_rate": 70, "sleep": "良好", "diet": "正常", "exercise": "散步40分钟", "med": True, "note": "精神好"},
            {"symptoms": "无不适", "temperature": 36.6, "blood_pressure": "118/76", "blood_sugar": 5.3, "heart_rate": 68, "sleep": "良好", "diet": "正常", "exercise": "散步30分钟", "med": True, "note": ""},
            {"symptoms": "轻微疲劳", "temperature": 36.7, "blood_pressure": "116/74", "blood_sugar": 5.2, "heart_rate": 74, "sleep": "一般", "diet": "正常", "exercise": "轻度活动", "med": True, "note": "工作有点累"},
            {"symptoms": "无不适", "temperature": 36.4, "blood_pressure": "110/70", "blood_sugar": 4.9, "heart_rate": 69, "sleep": "良好", "diet": "正常", "exercise": "散步45分钟", "med": True, "note": "状态佳"},
            {"symptoms": "无不适", "temperature": 36.6, "blood_pressure": "114/72", "blood_sugar": 5.1, "heart_rate": 71, "sleep": "良好", "diet": "正常", "exercise": "散步30分钟", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.5, "blood_pressure": "113/71", "blood_sugar": 5.0, "heart_rate": 70, "sleep": "良好", "diet": "正常", "exercise": "正常活动", "med": True, "note": "恢复良好"},
            {"symptoms": "无不适", "temperature": 36.7, "blood_pressure": "116/75", "blood_sugar": 5.2, "heart_rate": 72, "sleep": "良好", "diet": "正常", "exercise": "散步40分钟", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.5, "blood_pressure": "112/72", "blood_sugar": 5.0, "heart_rate": 68, "sleep": "良好", "diet": "正常", "exercise": "正常活动", "med": True, "note": "已恢复正常工作"},
            {"symptoms": "无不适", "temperature": 36.6, "blood_pressure": "115/74", "blood_sugar": 5.1, "heart_rate": 70, "sleep": "良好", "diet": "正常", "exercise": "散步30分钟", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.4, "blood_pressure": "111/70", "blood_sugar": 4.8, "heart_rate": 67, "sleep": "良好", "diet": "正常", "exercise": "正常活动", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.5, "blood_pressure": "113/72", "blood_sugar": 5.0, "heart_rate": 69, "sleep": "良好", "diet": "正常", "exercise": "散步30分钟", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.6, "blood_pressure": "114/73", "blood_sugar": 5.1, "heart_rate": 71, "sleep": "良好", "diet": "正常", "exercise": "正常活动", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.5, "blood_pressure": "112/71", "blood_sugar": 4.9, "heart_rate": 68, "sleep": "良好", "diet": "正常", "exercise": "正常活动", "med": True, "note": "复查一切正常"},
        ],
        "assessment": {
            "input_text": "术后恢复良好，伤口已愈合，无发热无疼痛，食欲和睡眠正常",
            "risk_level": "低风险",
            "risk_reasons": "各项指标稳定，恢复顺利",
            "advice": "继续保持，可逐步增加运动量，按时服药至疗程结束",
            "need_hospital": 0,
        },
        "reminders": [
            {"type": "用药提醒", "title": "头孢克肟 200mg", "desc": "早餐后服用", "time": "08:30"},
            {"type": "用药提醒", "title": "头孢克肟 200mg", "desc": "晚餐后服用", "time": "18:30"},
            {"type": "复查提醒", "title": "术后1个月复查", "desc": "普外科门诊复查伤口恢复情况", "time": "09:00"},
        ],
    },
    {
        "username": "patient_zhangwei",
        "password": "zhangwei2026",
        "profile": {
            "real_name": "张伟",
            "gender": "男",
            "age": 28,
            "phone": "13820002001",
            "height": 178.0,
            "weight": 72.0,
            "blood_type": "O",
            "medical_history": "半月板修复术后2周",
            "allergy_history": "花粉过敏",
            "current_medications": "布洛芬 400mg 按需服用",
            "emergency_contact": "张伟母亲",
            "emergency_phone": "13820002002",
            "health_stage": "术后恢复",
        },
        "checkins": [
            {"symptoms": "膝关节肿胀", "temperature": 37.0, "blood_pressure": "120/80", "blood_sugar": 5.0, "heart_rate": 75, "sleep": "一般", "diet": "正常", "exercise": "卧床休息", "med": True, "note": "冰敷后缓解"},
            {"symptoms": "膝关节轻微肿胀", "temperature": 36.8, "blood_pressure": "118/78", "blood_sugar": 5.1, "heart_rate": 72, "sleep": "一般", "diet": "正常", "exercise": "卧床休息", "med": True, "note": ""},
            {"symptoms": "肿胀减轻", "temperature": 36.7, "blood_pressure": "119/77", "blood_sugar": 4.9, "heart_rate": 70, "sleep": "良好", "diet": "正常", "exercise": "轻微活动", "med": True, "note": "好转"},
            {"symptoms": "轻微不适", "temperature": 36.6, "blood_pressure": "116/76", "blood_sugar": 5.0, "heart_rate": 71, "sleep": "良好", "diet": "正常", "exercise": "轻微活动", "med": False, "note": ""},
            {"symptoms": "无不适", "temperature": 36.5, "blood_pressure": "117/75", "blood_sugar": 4.8, "heart_rate": 68, "sleep": "良好", "diet": "正常", "exercise": "散步15分钟", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.6, "blood_pressure": "115/74", "blood_sugar": 5.0, "heart_rate": 70, "sleep": "良好", "diet": "正常", "exercise": "散步20分钟", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.5, "blood_pressure": "118/76", "blood_sugar": 4.9, "heart_rate": 69, "sleep": "良好", "diet": "正常", "exercise": "散步20分钟", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.6, "blood_pressure": "116/75", "blood_sugar": 5.1, "heart_rate": 72, "sleep": "良好", "diet": "正常", "exercise": "散步30分钟", "med": False, "note": ""},
            {"symptoms": "无不适", "temperature": 36.4, "blood_pressure": "114/73", "blood_sugar": 4.8, "heart_rate": 67, "sleep": "良好", "diet": "正常", "exercise": "散步30分钟", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.5, "blood_pressure": "115/74", "blood_sugar": 5.0, "heart_rate": 69, "sleep": "良好", "diet": "正常", "exercise": "正常活动", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.6, "blood_pressure": "117/76", "blood_sugar": 5.1, "heart_rate": 71, "sleep": "良好", "diet": "正常", "exercise": "正常活动", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.5, "blood_pressure": "116/75", "blood_sugar": 4.9, "heart_rate": 68, "sleep": "良好", "diet": "正常", "exercise": "正常活动", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.6, "blood_pressure": "118/77", "blood_sugar": 5.0, "heart_rate": 70, "sleep": "良好", "diet": "正常", "exercise": "正常活动", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.5, "blood_pressure": "115/74", "blood_sugar": 4.9, "heart_rate": 68, "sleep": "良好", "diet": "正常", "exercise": "正常活动", "med": True, "note": "恢复良好"},
        ],
        "assessment": {
            "input_text": "膝关节肿胀已消退，可以正常行走，偶尔运动后轻微酸胀",
            "risk_level": "低风险",
            "risk_reasons": "术后恢复良好，活动能力逐步恢复",
            "advice": "继续康复训练，避免剧烈运动，定期复查",
            "need_hospital": 0,
        },
        "reminders": [
            {"type": "用药提醒", "title": "布洛芬 400mg", "desc": "疼痛时服用，饭后", "time": "12:00"},
            {"type": "复查提醒", "title": "术后1个月复查", "desc": "骨科门诊复查膝关节恢复", "time": "10:00"},
        ],
    },

    # ── 中风险患者 ──────────────────────────────────────
    {
        "username": "patient_lina",
        "password": "lina2026",
        "profile": {
            "real_name": "李娜",
            "gender": "女",
            "age": 55,
            "phone": "13830003001",
            "height": 160.0,
            "weight": 68.0,
            "blood_type": "B",
            "medical_history": "胆囊切除术后3周，糖尿病史5年",
            "allergy_history": "磺胺类药物过敏",
            "current_medications": "二甲双胍 500mg 每日两次，头孢地尼 100mg 每日三次",
            "emergency_contact": "李娜女儿",
            "emergency_phone": "13830003002",
            "health_stage": "术后恢复",
        },
        # 14 天打卡：血糖偏高，偶有波动
        "checkins": [
            {"symptoms": "轻微腹胀", "temperature": 37.0, "blood_pressure": "135/88", "blood_sugar": 7.8, "heart_rate": 82, "sleep": "一般", "diet": "控制饮食", "exercise": "轻度活动", "med": True, "note": "术后还有点不适"},
            {"symptoms": "腹胀减轻", "temperature": 36.9, "blood_pressure": "132/85", "blood_sugar": 7.2, "heart_rate": 80, "sleep": "一般", "diet": "控制饮食", "exercise": "轻度活动", "med": True, "note": ""},
            {"symptoms": "轻微头晕", "temperature": 37.1, "blood_pressure": "138/90", "blood_sugar": 8.1, "heart_rate": 85, "sleep": "一般", "diet": "一般", "exercise": "无", "med": True, "note": "血糖偏高"},
            {"symptoms": "无不适", "temperature": 36.8, "blood_pressure": "130/84", "blood_sugar": 7.0, "heart_rate": 78, "sleep": "良好", "diet": "控制饮食", "exercise": "散步20分钟", "med": True, "note": ""},
            {"symptoms": "轻微乏力", "temperature": 37.0, "blood_pressure": "136/88", "blood_sugar": 7.5, "heart_rate": 83, "sleep": "一般", "diet": "一般", "exercise": "轻度活动", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.7, "blood_pressure": "128/82", "blood_sugar": 6.8, "heart_rate": 76, "sleep": "良好", "diet": "控制饮食", "exercise": "散步30分钟", "med": True, "note": "血糖好转"},
            {"symptoms": "无不适", "temperature": 36.9, "blood_pressure": "134/86", "blood_sugar": 7.3, "heart_rate": 80, "sleep": "一般", "diet": "控制饮食", "exercise": "轻度活动", "med": True, "note": ""},
            {"symptoms": "轻微恶心", "temperature": 37.2, "blood_pressure": "140/92", "blood_sugar": 8.5, "heart_rate": 88, "sleep": "一般", "diet": "食欲差", "exercise": "无", "med": True, "note": "不太舒服"},
            {"symptoms": "恶心缓解", "temperature": 36.8, "blood_pressure": "132/85", "blood_sugar": 7.1, "heart_rate": 79, "sleep": "良好", "diet": "正常", "exercise": "散步15分钟", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.7, "blood_pressure": "130/83", "blood_sugar": 6.9, "heart_rate": 77, "sleep": "良好", "diet": "控制饮食", "exercise": "散步20分钟", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.9, "blood_pressure": "135/87", "blood_sugar": 7.4, "heart_rate": 81, "sleep": "一般", "diet": "控制饮食", "exercise": "轻度活动", "med": True, "note": ""},
            {"symptoms": "轻微乏力", "temperature": 37.0, "blood_pressure": "138/90", "blood_sugar": 7.8, "heart_rate": 84, "sleep": "一般", "diet": "一般", "exercise": "无", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.8, "blood_pressure": "132/84", "blood_sugar": 7.0, "heart_rate": 78, "sleep": "良好", "diet": "控制饮食", "exercise": "散步20分钟", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.7, "blood_pressure": "130/82", "blood_sugar": 6.8, "heart_rate": 76, "sleep": "良好", "diet": "控制饮食", "exercise": "散步25分钟", "med": True, "note": ""},
        ],
        "assessment": {
            "input_text": "胆囊切除术后恢复中，但血糖控制不太稳定，偶尔偏高，有时头晕乏力",
            "risk_level": "中风险",
            "risk_reasons": "血糖波动较大，血压偶有偏高，术后恢复期合并糖尿病",
            "advice": "加强血糖监测，调整饮食结构，按时服药，如持续偏高建议内分泌科会诊",
            "need_hospital": 0,
        },
        "reminders": [
            {"type": "用药提醒", "title": "二甲双胍 500mg", "desc": "早餐后服用", "time": "08:00"},
            {"type": "用药提醒", "title": "二甲双胍 500mg", "desc": "晚餐后服用", "time": "18:00"},
            {"type": "用药提醒", "title": "头孢地尼 100mg", "desc": "三餐后服用", "time": "08:00"},
            {"type": "复查提醒", "title": "术后1个月复查", "desc": "肝胆外科复查+血糖检查", "time": "09:00"},
        ],
    },
    {
        "username": "patient_chenming",
        "password": "chenming2026",
        "profile": {
            "real_name": "陈明",
            "gender": "男",
            "age": 62,
            "phone": "13840004001",
            "height": 170.0,
            "weight": 78.0,
            "blood_type": "AB",
            "medical_history": "胃大部切除术后1个月，高血压病史8年",
            "allergy_history": "海鲜过敏",
            "current_medications": "氨氯地平 5mg 每日一次，奥美拉唑 20mg 每日一次",
            "emergency_contact": "陈明妻子",
            "emergency_phone": "13840004002",
            "health_stage": "长期管理",
        },
        # 14 天打卡：血压波动，体重下降
        "checkins": [
            {"symptoms": "食欲差", "temperature": 36.7, "blood_pressure": "148/95", "blood_sugar": 5.8, "heart_rate": 80, "sleep": "一般", "diet": "少食多餐", "exercise": "轻度活动", "med": True, "note": "吃不多"},
            {"symptoms": "轻微头晕", "temperature": 36.8, "blood_pressure": "152/98", "blood_sugar": 5.6, "heart_rate": 83, "sleep": "一般", "diet": "少食多餐", "exercise": "无", "med": True, "note": "血压偏高"},
            {"symptoms": "食欲差，乏力", "temperature": 36.9, "blood_pressure": "155/100", "blood_sugar": 5.9, "heart_rate": 86, "sleep": "差", "diet": "食欲差", "exercise": "无", "med": True, "note": ""},
            {"symptoms": "乏力", "temperature": 36.7, "blood_pressure": "145/93", "blood_sugar": 5.5, "heart_rate": 78, "sleep": "一般", "diet": "少食多餐", "exercise": "轻度活动", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.6, "blood_pressure": "140/90", "blood_sugar": 5.4, "heart_rate": 76, "sleep": "良好", "diet": "正常", "exercise": "散步15分钟", "med": True, "note": "好转"},
            {"symptoms": "轻微腹胀", "temperature": 36.8, "blood_pressure": "142/92", "blood_sugar": 5.7, "heart_rate": 79, "sleep": "一般", "diet": "少食多餐", "exercise": "轻度活动", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.6, "blood_pressure": "138/88", "blood_sugar": 5.3, "heart_rate": 74, "sleep": "良好", "diet": "正常", "exercise": "散步20分钟", "med": True, "note": ""},
            {"symptoms": "头晕", "temperature": 36.9, "blood_pressure": "158/102", "blood_sugar": 6.0, "heart_rate": 88, "sleep": "差", "diet": "食欲差", "exercise": "无", "med": True, "note": "今天不舒服"},
            {"symptoms": "头晕减轻", "temperature": 36.7, "blood_pressure": "148/96", "blood_sugar": 5.6, "heart_rate": 82, "sleep": "一般", "diet": "少食多餐", "exercise": "轻度活动", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.6, "blood_pressure": "140/90", "blood_sugar": 5.4, "heart_rate": 76, "sleep": "良好", "diet": "正常", "exercise": "散步20分钟", "med": True, "note": ""},
            {"symptoms": "轻微乏力", "temperature": 36.8, "blood_pressure": "145/94", "blood_sugar": 5.7, "heart_rate": 80, "sleep": "一般", "diet": "少食多餐", "exercise": "轻度活动", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.7, "blood_pressure": "138/88", "blood_sugar": 5.3, "heart_rate": 75, "sleep": "良好", "diet": "正常", "exercise": "散步20分钟", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.6, "blood_pressure": "142/91", "blood_sugar": 5.5, "heart_rate": 77, "sleep": "良好", "diet": "正常", "exercise": "散步25分钟", "med": True, "note": ""},
            {"symptoms": "无不适", "temperature": 36.7, "blood_pressure": "140/89", "blood_sugar": 5.4, "heart_rate": 76, "sleep": "良好", "diet": "正常", "exercise": "散步25分钟", "med": True, "note": ""},
        ],
        "assessment": {
            "input_text": "胃切除术后恢复较慢，食欲差体重下降，血压控制不稳定时有头晕",
            "risk_level": "中风险",
            "risk_reasons": "血压波动明显，营养摄入不足，术后恢复较慢",
            "advice": "调整降压药方案，少食多餐保证营养，必要时营养科会诊",
            "need_hospital": 0,
        },
        "reminders": [
            {"type": "用药提醒", "title": "氨氯地平 5mg", "desc": "早餐后服用", "time": "08:00"},
            {"type": "用药提醒", "title": "奥美拉唑 20mg", "desc": "早餐前30分钟空腹服用", "time": "07:30"},
            {"type": "复查提醒", "title": "术后2个月复查", "desc": "胃肠外科复查+血压监测", "time": "09:30"},
        ],
    },

    # ── 高风险患者 ──────────────────────────────────────
    {
        "username": "patient_wangqiang",
        "password": "wangqiang2026",
        "profile": {
            "real_name": "王强",
            "gender": "男",
            "age": 68,
            "phone": "13850005001",
            "height": 175.0,
            "weight": 85.0,
            "blood_type": "A",
            "medical_history": "冠状动脉搭桥术后2周，糖尿病史10年，高血压病史15年",
            "allergy_history": "碘造影剂过敏",
            "current_medications": "阿司匹林 100mg、氯吡格雷 75mg、阿托伐他汀 40mg、美托洛尔 47.5mg、胰岛素 早12U晚8U",
            "emergency_contact": "王强儿子",
            "emergency_phone": "13850005002",
            "health_stage": "急性期",
        },
        # 14 天打卡：指标持续恶化，连续异常
        "checkins": [
            {"symptoms": "胸闷，气短", "temperature": 37.2, "blood_pressure": "155/100", "blood_sugar": 9.5, "heart_rate": 95, "sleep": "差", "diet": "食欲差", "exercise": "卧床", "med": True, "note": "搭桥术后第3天"},
            {"symptoms": "胸闷", "temperature": 37.5, "blood_pressure": "160/105", "blood_sugar": 10.2, "heart_rate": 98, "sleep": "差", "diet": "食欲差", "exercise": "卧床", "med": True, "note": "不太舒服"},
            {"symptoms": "胸闷加重，出汗", "temperature": 38.1, "blood_pressure": "168/110", "blood_sugar": 11.5, "heart_rate": 105, "sleep": "差", "diet": "食欲差", "exercise": "卧床", "med": True, "note": "需要关注"},
            {"symptoms": "胸闷，呼吸困难", "temperature": 38.5, "blood_pressure": "172/115", "blood_sugar": 12.1, "heart_rate": 110, "sleep": "差", "diet": "几乎不进食", "exercise": "卧床", "med": True, "note": "情况不太好"},
            {"symptoms": "胸闷，咳嗽", "temperature": 38.3, "blood_pressure": "165/108", "blood_sugar": 11.0, "heart_rate": 102, "sleep": "差", "diet": "食欲差", "exercise": "卧床", "med": True, "note": ""},
            {"symptoms": "胸闷减轻", "temperature": 37.8, "blood_pressure": "158/102", "blood_sugar": 9.8, "heart_rate": 96, "sleep": "一般", "diet": "少食", "exercise": "床边活动", "med": True, "note": "稍好转"},
            {"symptoms": "轻微胸闷", "temperature": 37.5, "blood_pressure": "152/98", "blood_sugar": 8.9, "heart_rate": 90, "sleep": "一般", "diet": "少食多餐", "exercise": "轻度活动", "med": True, "note": ""},
            {"symptoms": "胸闷加重", "temperature": 38.6, "blood_pressure": "175/118", "blood_sugar": 12.8, "heart_rate": 115, "sleep": "差", "diet": "食欲差", "exercise": "卧床", "med": True, "note": "反复了"},
            {"symptoms": "胸闷，气促", "temperature": 38.8, "blood_pressure": "178/120", "blood_sugar": 13.2, "heart_rate": 118, "sleep": "差", "diet": "几乎不进食", "exercise": "卧床", "med": True, "note": "需要就医"},
            {"symptoms": "呼吸困难", "temperature": 39.0, "blood_pressure": "180/122", "blood_sugar": 13.5, "heart_rate": 120, "sleep": "差", "diet": "无法进食", "exercise": "卧床", "med": False, "note": "情况严重"},
            {"symptoms": "胸闷，发热", "temperature": 38.7, "blood_pressure": "170/115", "blood_sugar": 12.0, "heart_rate": 108, "sleep": "差", "diet": "少食", "exercise": "卧床", "med": True, "note": ""},
            {"symptoms": "胸闷", "temperature": 38.2, "blood_pressure": "162/108", "blood_sugar": 10.5, "heart_rate": 100, "sleep": "一般", "diet": "少食多餐", "exercise": "床边活动", "med": True, "note": ""},
            {"symptoms": "轻微胸闷", "temperature": 37.8, "blood_pressure": "155/102", "blood_sugar": 9.2, "heart_rate": 94, "sleep": "一般", "diet": "少食多餐", "exercise": "轻度活动", "med": True, "note": ""},
            {"symptoms": "胸闷", "temperature": 38.0, "blood_pressure": "160/105", "blood_sugar": 10.0, "heart_rate": 98, "sleep": "一般", "diet": "少食", "exercise": "轻度活动", "med": True, "note": ""},
        ],
        "assessment": {
            "input_text": "搭桥术后恢复不理想，反复胸闷气促，发热，血糖血压控制很差",
            "risk_level": "高风险",
            "risk_reasons": "术后感染征象，血糖严重失控，血压持续过高，心率偏快",
            "advice": "建议立即住院治疗，完善感染指标检查，调整胰岛素方案和降压方案",
            "need_hospital": 1,
        },
        "reminders": [
            {"type": "用药提醒", "title": "阿司匹林 100mg", "desc": "早餐后服用", "time": "08:00"},
            {"type": "用药提醒", "title": "氯吡格雷 75mg", "desc": "早餐后服用", "time": "08:00"},
            {"type": "用药提醒", "title": "胰岛素 早12U", "desc": "早餐前注射", "time": "07:30"},
            {"type": "用药提醒", "title": "胰岛素 晚8U", "desc": "晚餐前注射", "time": "17:30"},
            {"type": "复查提醒", "title": "心内科复查", "desc": "术后2周心功能评估", "time": "08:30"},
        ],
    },
    {
        "username": "patient_zhaohong",
        "password": "zhaohong2026",
        "profile": {
            "real_name": "赵红",
            "gender": "女",
            "age": 72,
            "phone": "13860006001",
            "height": 158.0,
            "weight": 62.0,
            "blood_type": "O",
            "medical_history": "髋关节置换术后1周，骨质疏松症，慢性肾功能不全",
            "allergy_history": "布洛芬过敏",
            "current_medications": "低分子肝素 4000U 每日一次，碳酸钙 D3 每日一次，骨化三醇 0.25μg 每日一次",
            "emergency_contact": "赵红女儿",
            "emergency_phone": "13860006002",
            "health_stage": "急性期",
        },
        # 14 天打卡：伤口感染，指标恶化
        "checkins": [
            {"symptoms": "伤口疼痛", "temperature": 37.3, "blood_pressure": "145/90", "blood_sugar": 6.2, "heart_rate": 82, "sleep": "差", "diet": "一般", "exercise": "卧床", "med": True, "note": "术后第1天"},
            {"symptoms": "伤口疼痛，肿胀", "temperature": 37.5, "blood_pressure": "148/92", "blood_sugar": 6.5, "heart_rate": 85, "sleep": "差", "diet": "一般", "exercise": "卧床", "med": True, "note": ""},
            {"symptoms": "伤口红肿", "temperature": 37.8, "blood_pressure": "150/95", "blood_sugar": 6.8, "heart_rate": 88, "sleep": "差", "diet": "食欲差", "exercise": "卧床", "med": True, "note": "伤口不太对"},
            {"symptoms": "伤口红肿加重，发热", "temperature": 38.2, "blood_pressure": "155/98", "blood_sugar": 7.2, "heart_rate": 92, "sleep": "差", "diet": "食欲差", "exercise": "卧床", "med": True, "note": "伤口有渗液"},
            {"symptoms": "发热，伤口渗液", "temperature": 38.5, "blood_pressure": "158/100", "blood_sugar": 7.5, "heart_rate": 95, "sleep": "差", "diet": "食欲差", "exercise": "卧床", "med": True, "note": "需要换药"},
            {"symptoms": "发热", "temperature": 38.8, "blood_pressure": "160/102", "blood_sugar": 7.8, "heart_rate": 98, "sleep": "差", "diet": "少食", "exercise": "卧床", "med": True, "note": "持续发热"},
            {"symptoms": "发热，寒战", "temperature": 39.2, "blood_pressure": "162/105", "blood_sugar": 8.0, "heart_rate": 102, "sleep": "差", "diet": "食欲差", "exercise": "卧床", "med": True, "note": "高热"},
            {"symptoms": "高热，伤口剧痛", "temperature": 39.5, "blood_pressure": "165/108", "blood_sugar": 8.5, "heart_rate": 108, "sleep": "差", "diet": "无法进食", "exercise": "卧床", "med": True, "note": "情况严重"},
            {"symptoms": "高热，意识模糊", "temperature": 39.8, "blood_pressure": "168/110", "blood_sugar": 8.8, "heart_rate": 112, "sleep": "差", "diet": "无法进食", "exercise": "卧床", "med": False, "note": "需要紧急处理"},
            {"symptoms": "发热", "temperature": 39.0, "blood_pressure": "158/102", "blood_sugar": 7.8, "heart_rate": 100, "sleep": "差", "diet": "少食", "exercise": "卧床", "med": True, "note": "用药后稍好转"},
            {"symptoms": "低热", "temperature": 38.0, "blood_pressure": "152/98", "blood_sugar": 7.0, "heart_rate": 92, "sleep": "一般", "diet": "少食多餐", "exercise": "床边活动", "med": True, "note": ""},
            {"symptoms": "轻微发热", "temperature": 37.5, "blood_pressure": "148/95", "blood_sugar": 6.5, "heart_rate": 86, "sleep": "一般", "diet": "一般", "exercise": "轻度活动", "med": True, "note": "好转"},
            {"symptoms": "伤口仍有渗液", "temperature": 37.8, "blood_pressure": "150/96", "blood_sugar": 6.8, "heart_rate": 88, "sleep": "一般", "diet": "一般", "exercise": "轻度活动", "med": True, "note": ""},
            {"symptoms": "低热，乏力", "temperature": 37.6, "blood_pressure": "148/94", "blood_sugar": 6.6, "heart_rate": 85, "sleep": "一般", "diet": "一般", "exercise": "轻度活动", "med": True, "note": ""},
        ],
        "assessment": {
            "input_text": "髋关节置换术后伤口感染，持续高热，伤口红肿有渗液，食欲差",
            "risk_level": "高风险",
            "risk_reasons": "术后伤口感染，持续高热不退，合并肾功能不全，营养状况差",
            "advice": "立即住院抗感染治疗，伤口清创换药，监测肾功能，加强营养支持",
            "need_hospital": 1,
        },
        "reminders": [
            {"type": "用药提醒", "title": "低分子肝素 4000U", "desc": "每日皮下注射", "time": "20:00"},
            {"type": "用药提醒", "title": "碳酸钙 D3", "desc": "餐后服用", "time": "12:00"},
            {"type": "复查提醒", "title": "伤口换药", "desc": "每日伤口换药观察", "time": "10:00"},
            {"type": "复查提醒", "title": "血常规+肾功能复查", "desc": "监测感染指标和肾功能", "time": "08:00"},
        ],
    },
]


def create_user(username: str, password: str) -> bool:
    """创建用户账号"""
    encrypted_pwd = encrypt_password(password)
    try:
        cursor = db.connection.cursor()
        cursor.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE password = VALUES(password)",
            (username, encrypted_pwd, 0),
        )
        db.connection.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"[ERR] 用户 {username} 创建失败: {e}")
        return False


def create_profile(username: str, profile: dict) -> bool:
    """创建健康档案"""
    return db.save_patient_profile(
        username=username,
        real_name=profile["real_name"],
        gender=profile["gender"],
        age=profile["age"],
        phone=profile["phone"],
        height=profile["height"],
        weight=profile["weight"],
        blood_type=profile["blood_type"],
        medical_history=profile["medical_history"],
        allergy_history=profile["allergy_history"],
        current_medications=profile["current_medications"],
        emergency_contact=profile["emergency_contact"],
        emergency_phone=profile["emergency_phone"],
        health_stage=profile["health_stage"],
    )


def create_checkins(username: str, checkins: list) -> int:
    """创建 14 天打卡记录，返回成功数"""
    ok_count = 0
    for i, c in enumerate(checkins):
        checkin_date = (START_DATE + timedelta(days=i)).strftime("%Y-%m-%d")
        data = {
            "temperature": c["temperature"],
            "blood_pressure": c["blood_pressure"],
            "blood_sugar": c["blood_sugar"],
            "heart_rate": c["heart_rate"],
            "symptoms": c["symptoms"],
        }
        analysis = checkin_service.analyze_checkin(data)

        result = db.save_daily_checkin(
            username=username,
            checkin_date=checkin_date,
            symptoms=c["symptoms"],
            temperature=c["temperature"],
            blood_pressure=c["blood_pressure"],
            blood_sugar=c["blood_sugar"],
            heart_rate=c["heart_rate"],
            sleep_status=c["sleep"],
            diet_status=c["diet"],
            exercise_status=c["exercise"],
            medication_taken=1 if c["med"] else 0,
            note=c["note"],
            abnormal_flag=analysis["abnormal_flag"],
            abnormal_reason=analysis["abnormal_reason"],
        )
        if result:
            ok_count += 1
    return ok_count


def create_assessment(username: str, assessment: dict) -> bool:
    """创建健康评估"""
    session_id = db.create_session(username, "健康评估会话")
    if not session_id:
        return False

    return db.save_health_assessment(
        username=username,
        session_id=session_id,
        source_type="text",
        input_text=assessment["input_text"],
        risk_level=assessment["risk_level"],
        risk_reasons=assessment["risk_reasons"],
        advice=assessment["advice"],
        need_hospital=assessment["need_hospital"],
    )


def create_reminders(username: str, reminders: list) -> int:
    """创建提醒，返回成功数"""
    ok_count = 0
    for r in reminders:
        result = db.save_reminder(
            username=username,
            reminder_type=r["type"],
            title=r["title"],
            description=r["desc"],
            reminder_date=str(TODAY),
            reminder_time=r["time"] + ":00" if r["time"] else None,
        )
        if result:
            ok_count += 1
    return ok_count


def create_alerts(username: str, profile: dict, assessment: dict):
    """为高风险患者创建告警记录"""
    if assessment["risk_level"] != "高风险":
        return
    db.create_alert_notification(
        username=username,
        real_name=profile["real_name"],
        risk_level=assessment["risk_level"],
        risk_reasons=assessment["risk_reasons"],
        advice=assessment["advice"],
        source_type="text",
    )


# ────────────────────────────────────────────────────────
# 主流程
# ────────────────────────────────────────────────────────
print("=" * 60)
print("  丰富病患数据插入脚本")
print("=" * 60)

total_ok = 0
total_fail = 0

for p in PATIENTS:
    username = p["username"]
    print(f"\n── 处理患者: {p['profile']['real_name']} ({username}) ──")

    # 1. 创建用户
    if create_user(username, p["password"]):
        print(f"  [OK] 用户创建成功")
    else:
        print(f"  [ERR] 用户创建失败，跳过")
        total_fail += 1
        continue

    # 2. 创建健康档案
    if create_profile(username, p["profile"]):
        print(f"  [OK] 健康档案创建成功")
    else:
        print(f"  [ERR] 健康档案创建失败")
        total_fail += 1
        continue

    # 3. 创建打卡记录
    checkin_ok = create_checkins(username, p["checkins"])
    print(f"  [OK] 打卡记录: {checkin_ok}/{len(p['checkins'])} 条")

    # 4. 创建健康评估
    if create_assessment(username, p["assessment"]):
        print(f"  [OK] 健康评估创建成功 ({p['assessment']['risk_level']})")
    else:
        print(f"  [ERR] 健康评估创建失败")

    # 5. 创建提醒
    reminder_ok = create_reminders(username, p["reminders"])
    print(f"  [OK] 提醒: {reminder_ok}/{len(p['reminders'])} 条")

    # 6. 高风险患者创建告警
    create_alerts(username, p["profile"], p["assessment"])
    if p["assessment"]["risk_level"] == "高风险":
        print(f"  [OK] 告警记录已创建")

    total_ok += 1

db.close()

print("\n" + "=" * 60)
print(f"  完成! 成功: {total_ok}, 失败: {total_fail}, 总计: {len(PATIENTS)}")
print("=" * 60)
