from database.local_db_utils import DatabaseConnector
from app.services.checkin_service import checkin_service

# 连接数据库
db = DatabaseConnector()
db.connect()

# 第一条打卡记录
checkin1 = {
    "checkin_date": "2026-04-20",
    "symptoms": "轻微头晕",
    "temperature": 37.5,
    "blood_pressure": "138/90",
    "blood_sugar": 6.2,
    "heart_rate": 88,
    "sleep_status": "一般",
    "diet_status": "一般",
    "exercise_status": "无",
    "medication_taken": True,
    "note": "有点不舒服"
}

# 分析打卡数据
analysis1 = checkin_service.analyze_checkin(checkin1)
print(f"第一条打卡分析: {analysis1}")

# 保存第一条打卡记录
result1 = db.save_daily_checkin(
    username='test_user_2',
    checkin_date=checkin1['checkin_date'],
    symptoms=checkin1['symptoms'],
    temperature=checkin1['temperature'],
    blood_pressure=checkin1['blood_pressure'],
    blood_sugar=checkin1['blood_sugar'],
    heart_rate=checkin1['heart_rate'],
    sleep_status=checkin1['sleep_status'],
    diet_status=checkin1['diet_status'],
    exercise_status=checkin1['exercise_status'],
    medication_taken=1 if checkin1['medication_taken'] else 0,
    note=checkin1['note'],
    abnormal_flag=analysis1['abnormal_flag'],
    abnormal_reason=analysis1['abnormal_reason']
)
print(f"第一条打卡保存结果: {result1}")

# 第二条打卡记录
checkin2 = {
    "checkin_date": "2026-04-21",
    "symptoms": "头晕、食欲下降",
    "temperature": 38.1,
    "blood_pressure": "145/95",
    "blood_sugar": 6.5,
    "heart_rate": 92,
    "sleep_status": "较差",
    "diet_status": "一般",
    "exercise_status": "无",
    "medication_taken": True,
    "note": "建议观察"
}

# 分析打卡数据
analysis2 = checkin_service.analyze_checkin(checkin2)
print(f"第二条打卡分析: {analysis2}")

# 保存第二条打卡记录
result2 = db.save_daily_checkin(
    username='test_user_2',
    checkin_date=checkin2['checkin_date'],
    symptoms=checkin2['symptoms'],
    temperature=checkin2['temperature'],
    blood_pressure=checkin2['blood_pressure'],
    blood_sugar=checkin2['blood_sugar'],
    heart_rate=checkin2['heart_rate'],
    sleep_status=checkin2['sleep_status'],
    diet_status=checkin2['diet_status'],
    exercise_status=checkin2['exercise_status'],
    medication_taken=1 if checkin2['medication_taken'] else 0,
    note=checkin2['note'],
    abnormal_flag=analysis2['abnormal_flag'],
    abnormal_reason=analysis2['abnormal_reason']
)
print(f"第二条打卡保存结果: {result2}")

# 关闭数据库连接
db.close()
print("中风险患者打卡数据插入完成")
