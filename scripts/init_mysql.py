import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import sys

sys.stdout.reconfigure(encoding='utf-8')

def init_db():
    load_dotenv()
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "RAG")

    try:
        print("正在连接数据库...", flush=True)
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password
        )
        if conn.is_connected():
            cursor = conn.cursor()

            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"数据库 {database} 已就绪", flush=True)

            conn.database = database

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
            print("表 users 已就绪", flush=True)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS patient_reports (
              id INT AUTO_INCREMENT PRIMARY KEY,
              username VARCHAR(255) NOT NULL,
              file_name VARCHAR(255) NOT NULL,
              file_type VARCHAR(50),
              raw_ocr_text LONGTEXT,
              structured_json JSON,
              ocr_score DECIMAL(6,4) DEFAULT 0,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_username (username),
              INDEX idx_created_at (created_at),
              FOREIGN KEY (username) REFERENCES users(username)
                ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("表 patient_reports 已就绪", flush=True)

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
            print("表 chat_sessions 已就绪", flush=True)

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
            print("表 user_conversations 已就绪", flush=True)

            # 先删除旧表（如果存在）
            cursor.execute("DROP TABLE IF EXISTS health_assessments")
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_assessments (
              id INT AUTO_INCREMENT PRIMARY KEY,
              username VARCHAR(255) NOT NULL,
              session_id INT NOT NULL,
              source_type VARCHAR(50) NOT NULL,
              input_text LONGTEXT NOT NULL,
              risk_level VARCHAR(50) NOT NULL,
              risk_reasons LONGTEXT,
              advice LONGTEXT,
              need_hospital TINYINT DEFAULT 0,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_username (username),
              INDEX idx_session_id (session_id),
              INDEX idx_created_at (created_at),
              FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE,
              FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("表 health_assessments 已就绪", flush=True)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS patient_profiles (
              id INT AUTO_INCREMENT PRIMARY KEY,
              username VARCHAR(255) NOT NULL UNIQUE,
              real_name VARCHAR(100),
              gender VARCHAR(20),
              age INT,
              phone VARCHAR(50),
              height DECIMAL(5,2),
              weight DECIMAL(5,2),
              blood_type VARCHAR(20),
              medical_history TEXT,
              allergy_history TEXT,
              current_medications TEXT,
              emergency_contact VARCHAR(100),
              emergency_phone VARCHAR(50),
              health_stage VARCHAR(50) DEFAULT '长期管理',
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              INDEX idx_username (username),
              FOREIGN KEY (username) REFERENCES users(username)
                ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("表 patient_profiles 已就绪", flush=True)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_checkins (
              id INT AUTO_INCREMENT PRIMARY KEY,
              username VARCHAR(255) NOT NULL,
              checkin_date DATE NOT NULL,
              symptoms TEXT,
              temperature DECIMAL(4,1),
              blood_pressure VARCHAR(20),
              blood_sugar DECIMAL(5,2),
              heart_rate INT,
              sleep_status VARCHAR(100),
              diet_status VARCHAR(100),
              exercise_status VARCHAR(100),
              medication_taken TINYINT DEFAULT 0,
              note TEXT,
              abnormal_flag TINYINT DEFAULT 0,
              abnormal_reason TEXT,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              UNIQUE KEY uniq_user_date (username, checkin_date),
              INDEX idx_username (username),
              INDEX idx_checkin_date (checkin_date),
              FOREIGN KEY (username) REFERENCES users(username)
                ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("表 daily_checkins 已就绪", flush=True)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
              id INT AUTO_INCREMENT PRIMARY KEY,
              username VARCHAR(255) NOT NULL,
              reminder_type VARCHAR(50) NOT NULL,
              title VARCHAR(255) NOT NULL,
              description TEXT,
              reminder_date DATE NOT NULL,
              reminder_time TIME DEFAULT NULL,
              status VARCHAR(20) DEFAULT 'pending',
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              INDEX idx_username (username),
              INDEX idx_reminder_date (reminder_date),
              INDEX idx_status (status),
              FOREIGN KEY (username) REFERENCES users(username)
                ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("表 reminders 已就绪", flush=True)

            cursor.close()
            conn.close()
            print("数据库初始化完成!", flush=True)

    except Error as e:
        print(f"数据库初始化失败: {e}", flush=True)

if __name__ == "__main__":
    init_db()