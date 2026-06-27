import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("MYSQL_HOST", "localhost")
user = os.getenv("MYSQL_USER", "root")
password = os.getenv("MYSQL_PASSWORD", "")
database = os.getenv("MYSQL_DATABASE", "RAG")

try:
    connection = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )

    if connection.is_connected():
        print("成功连接到数据库")

        cursor = connection.cursor()

        print("\n健康评估表结构:")
        cursor.execute("DESCRIBE health_assessments")
        columns = cursor.fetchall()
        for column in columns:
            print(f"{column[0]}: {column[1]}")

        print("\n检查其他表是否存在:")
        tables_to_check = ["system_logs", "api_access_logs", "alert_notifications", "doctor_messages"]
        for table in tables_to_check:
            cursor.execute(f"SHOW TABLES LIKE '{table}'")
            result = cursor.fetchone()
            if result:
                print(f"  ✅ 表 {table} 存在")
            else:
                print(f"  ❌ 表 {table} 不存在")

        cursor.close()
        connection.close()
        print("\n数据库连接已关闭")

except Error as e:
    print(f"数据库连接错误: {e}")
    print("请检查 .env 文件中的 MySQL 配置")
