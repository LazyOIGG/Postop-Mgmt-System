import mysql.connector

try:
    print("测试MySQL连接...")

    # 测试不带数据库的连接
    conn1 = mysql.connector.connect(
        host='localhost',
        user='root',
        password='GX3216379973.qq',
    )
    print("✅ MySQL服务器连接成功")
    conn1.close()

    # 测试带数据库的连接
    conn2 = mysql.connector.connect(
        host='localhost',
        user='root',
        password='GX3216379973.qq',
        database='rag'  # 使用默认的mysql数据库测试
    )
    print("✅ MySQL数据库连接成功")
    conn2.close()

except Exception as e:
    print(f"❌ 连接失败: {e}")
    print("\n可能的原因:")
    print("1. MySQL服务未启动")
    print("2. 用户名或密码错误")
    print("3. 端口被占用（默认3306）")
    print("4. 防火墙阻止连接")