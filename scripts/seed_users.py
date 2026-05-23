import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.local_db_utils import DatabaseConnector
from database.password_utils import encrypt_password

db = DatabaseConnector()
db.connect()

# 三个测试用户：低风险、中风险、高风险
users = [
    {
        "username": "test_user",
        "password": "Test@123456",
        "profile": {
            "real_name": "张三",
            "gender": "男",
            "age": 45,
            "phone": "13800000001",
            "height": 172.0,
            "weight": 68.0,
            "blood_type": "A",
            "medical_history": "高血压病史5年，规律服药",
            "allergy_history": "无",
            "current_medications": "氨氯地平 5mg 每日一次",
            "emergency_contact": "张三家属",
            "emergency_phone": "13800000002",
            "health_stage": "长期管理"
        },
        "assessment": {
            "source_type": "text",
            "input_text": "近期身体状况良好，血压控制稳定，无明显不适",
            "risk_level": "low",
            "risk_reasons": "各项指标正常",
            "advice": "继续保持当前生活方式，定期复查",
            "need_hospital": 0
        }
    },
    {
        "username": "test_user_2",
        "password": "Test@123456",
        "profile": {
            "real_name": "李四",
            "gender": "女",
            "age": 58,
            "phone": "13900000001",
            "height": 160.0,
            "weight": 72.0,
            "blood_type": "B",
            "medical_history": "糖尿病史3年，2型",
            "allergy_history": "青霉素过敏",
            "current_medications": "二甲双胍 500mg 每日两次",
            "emergency_contact": "李四家属",
            "emergency_phone": "13900000002",
            "health_stage": "术后恢复"
        },
        "assessment": {
            "source_type": "text",
            "input_text": "近期血糖偏高，偶有头晕，食欲下降",
            "risk_level": "medium",
            "risk_reasons": "血糖控制不佳，血压偏高",
            "advice": "建议调整用药方案，加强血糖监测，注意饮食控制",
            "need_hospital": 0
        }
    },
    {
        "username": "test_user_3",
        "password": "Test@123456",
        "profile": {
            "real_name": "王五",
            "gender": "男",
            "age": 70,
            "phone": "13700000001",
            "height": 168.0,
            "weight": 80.0,
            "blood_type": "O",
            "medical_history": "冠心病史10年，心脏支架术后2年",
            "allergy_history": "磺胺类药物过敏",
            "current_medications": "阿司匹林 100mg、阿托伐他汀 20mg、美托洛尔 47.5mg",
            "emergency_contact": "王五家属",
            "emergency_phone": "13700000002",
            "health_stage": "急性期"
        },
        "assessment": {
            "source_type": "text",
            "input_text": "胸闷加重，夜间呼吸困难，血压持续偏高",
            "risk_level": "high",
            "risk_reasons": "心血管症状加重，血压控制差，心率偏快",
            "advice": "建议立即就医，调整治疗方案",
            "need_hospital": 1
        }
    }
]

for user in users:
    username = user["username"]
    password = user["password"]

    # 1. 创建用户账号
    encrypted_pwd = encrypt_password(password)
    try:
        cursor = db.connection.cursor()
        cursor.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE password = VALUES(password)",
            (username, encrypted_pwd, 0)
        )
        db.connection.commit()
        cursor.close()
        print(f"[OK] 用户 {username} 创建成功")
    except Exception as e:
        print(f"[ERR] 用户 {username} 创建失败: {e}")
        continue

    # 2. 创建健康档案
    p = user["profile"]
    ok = db.save_patient_profile(
        username=username,
        real_name=p["real_name"],
        gender=p["gender"],
        age=p["age"],
        phone=p["phone"],
        height=p["height"],
        weight=p["weight"],
        blood_type=p["blood_type"],
        medical_history=p["medical_history"],
        allergy_history=p["allergy_history"],
        current_medications=p["current_medications"],
        emergency_contact=p["emergency_contact"],
        emergency_phone=p["emergency_phone"],
        health_stage=p["health_stage"]
    )
    print(f"[{'OK' if ok else 'ERR'}] {username} 健康档案{'创建成功' if ok else '创建失败'}")

    # 3. 创建会话（health_assessments 外键依赖 chat_sessions）
    session_id = db.create_session(username, "健康评估会话")
    if not session_id:
        print(f"[ERR] {username} 会话创建失败，跳过健康评估")
        continue
    print(f"[OK] {username} 会话创建成功 (session_id={session_id})")

    # 4. 创建健康评估
    a = user["assessment"]
    ok = db.save_health_assessment(
        username=username,
        session_id=session_id,
        source_type=a["source_type"],
        input_text=a["input_text"],
        risk_level=a["risk_level"],
        risk_reasons=a["risk_reasons"],
        advice=a["advice"],
        need_hospital=a["need_hospital"]
    )
    print(f"[{'OK' if ok else 'ERR'}] {username} 健康评估{'创建成功' if ok else '创建失败'}")

db.close()
print("\n全部测试用户数据初始化完成")
