from database.local_db_utils import DatabaseConnector

# 连接数据库
db = DatabaseConnector()
db.connect()

# 检查健康档案
print("=== 高风险患者健康档案 ===")
profile = db.get_patient_profile('test_user_3')
if profile:
    print(f"姓名: {profile['real_name']}")
    print(f"性别: {profile['gender']}")
    print(f"年龄: {profile['age']}")
    print(f"电话: {profile['phone']}")
    print(f"身高: {profile['height']}")
    print(f"体重: {profile['weight']}")
    print(f"血型: {profile['blood_type']}")
    print(f"病史: {profile['medical_history']}")
    print(f"过敏史: {profile['allergy_history']}")
    print(f"当前用药: {profile['current_medications']}")
    print(f"紧急联系人: {profile['emergency_contact']}")
    print(f"紧急电话: {profile['emergency_phone']}")
    print(f"健康阶段: {profile['health_stage']}")
else:
    print("健康档案未找到")

# 检查健康评估
print("\n=== 高风险患者健康评估 ===")
assessment = db.get_latest_health_assessment('test_user_3')
if assessment:
    print(f"风险等级: {assessment['risk_level']}")
    print(f"输入文本: {assessment['input_text']}")
    print(f"评估时间: {assessment['created_at']}")
else:
    print("健康评估未找到")

# 检查打卡记录
print("\n=== 高风险患者打卡记录 ===")
checkins = db.get_daily_checkins('test_user_3')
print(f"打卡记录数量: {len(checkins)}")
for checkin in checkins:
    print(f"日期: {checkin['checkin_date']}")
    print(f"  症状: {checkin['symptoms']}")
    print(f"  体温: {checkin['temperature']}")
    print(f"  血压: {checkin['blood_pressure']}")
    print(f"  血糖: {checkin['blood_sugar']}")
    print(f"  心率: {checkin['heart_rate']}")
    print(f"  睡眠: {checkin['sleep_status']}")
    print(f"  饮食: {checkin['diet_status']}")
    print(f"  运动: {checkin['exercise_status']}")
    print(f"  服药: {'是' if checkin['medication_taken'] else '否'}")
    print(f"  备注: {checkin['note']}")
    print(f"  异常: {'是' if checkin['abnormal_flag'] else '否'}")
    print(f"  异常原因: {checkin['abnormal_reason']}")
    print()

# 关闭数据库连接
db.close()
print("高风险患者数据检查完成")
