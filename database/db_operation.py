# db_operation.py
import mysql.connector
from mysql.connector import Error
from database.password_utils import encrypt_password
import sys

def create_database_if_not_exists(host='localhost', user='root', password='Ncy18225889352', database='RAG'):
    """创建数据库（如果不存在）"""
    try:
        # 首先连接到MySQL服务器（不指定数据库）
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # 检查数据库是否存在
            cursor.execute(f"SHOW DATABASES LIKE '{database}'")
            result = cursor.fetchone()

            if not result:
                # 数据库不存在，创建它
                print(f"数据库 '{database}' 不存在，正在创建...")
                cursor.execute(f"CREATE DATABASE {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                connection.commit()
                print(f"✅ 数据库 '{database}' 创建成功")
            else:
                print(f"✅ 数据库 '{database}' 已存在")

            cursor.close()
            connection.close()
            return True
    except Error as e:
        print(f"❌ 创建数据库失败: {e}")
        return False

def init_database_tables():
    """初始化数据库表结构"""
    try:
        # 使用DatabaseConnector连接到指定的数据库
        from db_utils import DatabaseConnector

        db = DatabaseConnector(host='localhost', database='RAG', user='root', password='Ncy18225889352')

        if not db.connect():
            print("数据库连接失败")
            return False

        cursor = db.connection.cursor()

        print("正在创建数据库表...")

        # 1. 创建用户表（users）
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS users (
                                                            id INT AUTO_INCREMENT PRIMARY KEY,
                                                            username VARCHAR(255) UNIQUE NOT NULL,
                                                            password VARCHAR(255) NOT NULL,
                                                            is_admin TINYINT DEFAULT 0,
                                                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                                            INDEX idx_username (username),
                                                            INDEX idx_created_at (created_at)
                       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                       ''')
        print("✅ 用户表 (users) 创建/检查完成")

        # 2. 创建会话表（chat_sessions）
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS chat_sessions (
                                                                    session_id INT AUTO_INCREMENT PRIMARY KEY,
                                                                    username VARCHAR(255) NOT NULL,
                                                                    session_title VARCHAR(255) DEFAULT '新对话',
                                                                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                                                    INDEX idx_username (username),
                                                                    INDEX idx_last_updated (last_updated),
                                                                    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE
                       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                       ''')
        print("✅ 会话表 (chat_sessions) 创建/检查完成")

        # 3. 创建对话消息表（user_conversations）
        cursor.execute('''
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
                                                                         INDEX idx_timestamp (timestamp),
                                                                         INDEX idx_session_time (session_id, timestamp),
                                                                         FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE ON UPDATE CASCADE,
                                                                         FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE
                       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                       ''')
        print("✅ 对话消息表 (user_conversations) 创建/检查完成")

        # 4. 创建系统日志表（可选）
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS system_logs (
                                                                  id INT AUTO_INCREMENT PRIMARY KEY,
                                                                  level ENUM('INFO', 'WARNING', 'ERROR') DEFAULT 'INFO',
                                                                  module VARCHAR(100),
                                                                  message TEXT,
                                                                  details JSON,
                                                                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                                  INDEX idx_level (level),
                                                                  INDEX idx_created_at (created_at),
                                                                  INDEX idx_module (module)
                       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                       ''')
        print("✅ 系统日志表 (system_logs) 创建/检查完成")

        # 5. 创建API访问日志表（可选）
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS api_access_logs (
                                                                      id INT AUTO_INCREMENT PRIMARY KEY,
                                                                      username VARCHAR(255),
                                                                      endpoint VARCHAR(255),
                                                                      method VARCHAR(10),
                                                                      status_code INT,
                                                                      duration_ms INT,
                                                                      user_agent TEXT,
                                                                      ip_address VARCHAR(45),
                                                                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                                      INDEX idx_username (username),
                                                                      INDEX idx_endpoint (endpoint),
                                                                      INDEX idx_status_code (status_code),
                                                                      INDEX idx_created_at (created_at)
                       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                       ''')
        print("✅ API访问日志表 (api_access_logs) 创建/检查完成")

        db.connection.commit()
        print("\n" + "="*50)
        print("✅ 所有数据库表创建/检查完成")
        print("="*50)

        # 创建默认管理员账户
        create_admin_account(db)

        return True

    except Error as e:
        print(f"❌ 数据库初始化错误: {e}")
        if 'db' in locals() and db.connection:
            db.connection.rollback()
        return False
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

def create_admin_account(db):
    """创建默认管理员账户"""
    try:
        cursor = db.connection.cursor()

        # 检查管理员账户是否已存在
        cursor.execute("SELECT * FROM users WHERE username = 'admin' AND is_admin = 1")

        if not cursor.fetchone():
            # 管理员账户不存在，创建它
            admin_pwd = encrypt_password('123456')
            try:
                cursor.execute(
                    "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, 1)",
                    ('admin', admin_pwd)
                )
                db.connection.commit()
                print("✅ 管理员账户创建成功")
                print("   用户名: admin")
                print("   密码: 123456")
            except mysql.connector.Error as e:
                if e.errno == 1062:  # Duplicate entry
                    print("⚠️ 管理员账户已存在")
                else:
                    raise e
        else:
            print("✅ 管理员账户已存在")

    except Exception as e:
        print(f"❌ 创建管理员账户错误: {e}")
        db.connection.rollback()
    finally:
        if 'cursor' in locals():
            cursor.close()

def test_database_connection():
    """测试数据库连接"""
    try:
        from db_utils import DatabaseConnector

        print("正在测试数据库连接...")
        db = DatabaseConnector(host='localhost', database='RAG', user='root', password='Ncy18225889352')

        if db.connect():
            print("✅ 数据库连接测试成功")

            # 测试表结构
            cursor = db.connection.cursor()

            # 检查用户表
            cursor.execute("SHOW TABLES LIKE 'users'")
            if cursor.fetchone():
                print("✅ 用户表存在")
            else:
                print("❌ 用户表不存在")

            # 检查会话表
            cursor.execute("SHOW TABLES LIKE 'chat_sessions'")
            if cursor.fetchone():
                print("✅ 会话表存在")
            else:
                print("❌ 会话表不存在")

            # 检查消息表
            cursor.execute("SHOW TABLES LIKE 'user_conversations'")
            if cursor.fetchone():
                print("✅ 消息表存在")
            else:
                print("❌ 消息表不存在")

            cursor.close()
            db.close()
            return True
        else:
            print("❌ 数据库连接测试失败")
            return False

    except Exception as e:
        print(f"❌ 数据库连接测试异常: {e}")
        return False

def init_database():
    """主初始化函数"""
    print("="*60)
    print("术后管理系统 - 数据库初始化")
    print("="*60)

    # 获取MySQL连接参数
    print("\n请确认MySQL连接参数:")
    print(f"主机: localhost")
    print(f"用户名: root")
    print(f"密码: {'*' * len('Ncy18225889352')}")
    print(f"数据库: RAG")

    # 检查MySQL服务是否运行
    try:
        # 尝试连接到MySQL服务器
        test_conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Ncy18225889352'
        )
        test_conn.close()
        print("✅ MySQL服务器连接成功")
    except Error as e:
        print(f"❌ 无法连接到MySQL服务器: {e}")
        print("\n请确保:")
        print("1. MySQL服务正在运行")
        print("2. MySQL用户名和密码正确")
        print("3. 已安装 mysql-connector-python 包")
        return False

    # 步骤1：创建数据库（如果不存在）
    print("\n" + "-"*40)
    print("步骤1: 检查/创建数据库")
    print("-"*40)
    if not create_database_if_not_exists():
        print("❌ 数据库创建失败，请检查MySQL配置")
        return False

    # 步骤2：初始化表结构
    print("\n" + "-"*40)
    print("步骤2: 初始化数据库表")
    print("-"*40)
    if not init_database_tables():
        print("❌ 数据库表初始化失败")
        return False

    # 步骤3：测试连接
    print("\n" + "-"*40)
    print("步骤3: 测试数据库连接")
    print("-"*40)
    if not test_database_connection():
        print("❌ 数据库连接测试失败")
        return False

    print("\n" + "="*60)
    print("✅ 数据库初始化完成！")
    print("="*60)
    print("\n系统已就绪，您可以:")
    print("1. 启动后端服务: python main.py")
    print("2. 访问管理界面: http://localhost:8000/docs")
    print("3. 使用管理员账户登录:")
    print("   - 用户名: admin")
    print("   - 密码: 123456")

    return True

def drop_database():
    """删除数据库（危险操作，仅用于开发）"""
    confirm = input("\n⚠️  警告：这将删除整个RAG数据库！\n是否继续？(yes/no): ")

    if confirm.lower() != 'yes':
        print("操作已取消")
        return False

    try:
        # 连接到MySQL服务器
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Ncy18225889352'
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # 删除数据库
            cursor.execute(f"DROP DATABASE IF EXISTS RAG")
            connection.commit()

            print("✅ 数据库已删除")

            cursor.close()
            connection.close()
            return True
    except Error as e:
        print(f"❌ 删除数据库失败: {e}")
        return False

def reset_database():
    """重置数据库（删除并重新创建）"""
    print("正在重置数据库...")

    if drop_database():
        print("等待2秒...")
        import time
        time.sleep(2)
        return init_database()

    return False

if __name__ == "__main__":
    # 解析命令行参数
    import argparse

    parser = argparse.ArgumentParser(description='术后管理系统数据库管理工具')
    parser.add_argument('action', choices=['init', 'test', 'drop', 'reset', 'create-admin'],
                        nargs='?', default='init', help='执行的操作')

    args = parser.parse_args()

    if args.action == 'init':
        init_database()
    elif args.action == 'test':
        test_database_connection()
    elif args.action == 'drop':
        drop_database()
    elif args.action == 'reset':
        reset_database()
    elif args.action == 'create-admin':
        # 仅创建管理员账户
        try:
            from local_db_utils import DatabaseConnector
            db = DatabaseConnector(host='localhost', database='RAG', user='root', password='Ncy18225889352')
            if db.connect():
                create_admin_account(db)
                db.close()
        except Exception as e:
            print(f"❌ 创建管理员账户失败: {e}")