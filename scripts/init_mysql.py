import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

def init_db():
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "RAG")

    try:
        # 1. 连接到 MySQL
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password
        )
        if conn.is_connected():
            cursor = conn.cursor()
            
            # 2. 创建数据库
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"✅ 数据库 {database} 已就绪")
            
            # 3. 切换到数据库
            conn.database = database
            
            # 4. 创建表
            # Users 表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
              id INT AUTO_INCREMENT PRIMARY KEY,
              username VARCHAR(255) UNIQUE NOT NULL,
              password VARCHAR(255) NOT NULL,
              is_admin TINYINT DEFAULT 0,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              INDEX idx_username (username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ 表 users 已就绪")
            
            # Chat Sessions 表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
              session_id INT AUTO_INCREMENT PRIMARY KEY,
              username VARCHAR(255) NOT NULL,
              session_title VARCHAR(255) DEFAULT '新对话',
              start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              INDEX idx_username (username),
              FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ 表 chat_sessions 已就绪")
            
            # Conversations 表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_conversations (
              id INT AUTO_INCREMENT PRIMARY KEY,
              session_id INT NOT NULL,
              username VARCHAR(255) NOT NULL,
              role ENUM('user', 'assistant') NOT NULL,
              content TEXT NOT NULL,
              entities TEXT,
              intents TEXT,
              knowledge TEXT,
              timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_session_id (session_id),
              INDEX idx_username (username),
              FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE ON UPDATE CASCADE,
              FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ 表 user_conversations 已就绪")
            
            cursor.close()
            conn.close()
            print("✨ 数据库初始化完成！")
            
    except Error as e:
        print(f"❌ 数据库初始化失败: {e}")

if __name__ == "__main__":
    init_db()
