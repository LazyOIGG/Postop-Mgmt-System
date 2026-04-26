import mysql.connector
from mysql.connector import Error

# 数据库配置
config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'GX3216379973.qq',
    'database': 'RAG'
}

try:
    # 连接数据库
    connection = mysql.connector.connect(**config)
    
    if connection.is_connected():
        print("成功连接到数据库")
        
        # 获取游标
        cursor = connection.cursor()
        
        # 查看 health_assessments 表结构
        print("\n健康评估表结构:")
        cursor.execute("DESCRIBE health_assessments")
        columns = cursor.fetchall()
        for column in columns:
            print(f"{column[0]}: {column[1]}")
        
        # 查看是否存在 system_logs 和 api_access_logs 表
        print("\n检查其他表是否存在:")
        tables_to_check = ['system_logs', 'api_access_logs']
        for table in tables_to_check:
            cursor.execute(f"SHOW TABLES LIKE '{table}'")
            result = cursor.fetchone()
            if result:
                print(f"表 {table} 存在")
            else:
                print(f"表 {table} 不存在")
        
        cursor.close()
        connection.close()
        print("\n数据库连接已关闭")
        
except Error as e:
    print(f"数据库连接错误: {e}")
