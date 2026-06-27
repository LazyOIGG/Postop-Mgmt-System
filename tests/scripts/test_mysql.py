import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

try:
    print("测试MySQL连接...")

    host = os.getenv("MYSQL_HOST", "localhost")
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "RAG")

    conn1 = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
    )
    print("✅ MySQL服务器连接成功")
    conn1.close()

    conn2 = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )
    print("✅ MySQL数据库连接成功")
    conn2.close()

except Exception as e:
    print(f"❌ 连接失败: {e}")
    print("\n可能的原因:")
    print("1. MySQL服务未启动")
    print("2. 用户名或密码错误（检查 .env 文件）")
    print("3. 端口被占用（默认3306）")
    print("4. 防火墙阻止连接")
