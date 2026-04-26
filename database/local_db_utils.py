import mysql.connector
from mysql.connector import Error, pooling
import time
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConnector:
    def __init__(self, host='localhost', database='RAG', user='root', password='GX3216379973.qq',
                 pool_size=5, pool_name='medical_qa_pool'):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.pool_size = pool_size
        self.pool_name = pool_name
        self.connection_pool = None
        self.connection = None

        # 尝试创建连接池
        self._create_connection_pool()

    def _create_connection_pool(self):
        """创建数据库连接池"""
        try:
            self.connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name=self.pool_name,
                pool_size=self.pool_size,
                pool_reset_session=True,
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                charset='utf8mb4',
                use_unicode=True,
                autocommit=False
            )
            logger.info(f"数据库连接池创建成功: {self.pool_name}")
        except Error as e:
            logger.error(f"创建连接池失败: {e}")
            self.connection_pool = None

    def connect(self) -> bool:
        """连接到数据库（从连接池获取连接）"""
        try:
            if self.connection_pool:
                self.connection = self.connection_pool.get_connection()
            else:
                # 如果没有连接池，直接创建连接
                self.connection = mysql.connector.connect(
                    host=self.host,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    charset='utf8mb4',
                    use_unicode=True,
                    autocommit=False
                )

            if self.connection.is_connected():
                logger.info(f"数据库连接成功: {self.database}")
                return True
            else:
                logger.error("数据库连接失败")
                return False

        except Error as e:
            logger.error(f"数据库连接错误: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self.connection and self.connection.is_connected():
            if self.connection_pool:
                # 如果是连接池的连接，归还到连接池
                self.connection.close()
            else:
                # 如果是普通连接，直接关闭
                self.connection.close()
            self.connection = None
            logger.info("数据库连接已关闭")

    def _ensure_connection(self) -> bool:
        """确保数据库连接正常"""
        if not self.connection or not self.connection.is_connected():
            return self.connect()
        return True

    def _execute_with_retry(self, query: str, params: tuple = None, retries: int = 3) -> Any:
        """执行SQL查询，支持重试"""
        for attempt in range(retries):
            try:
                if not self._ensure_connection():
                    raise Error("无法建立数据库连接")

                cursor = self.connection.cursor(dictionary=True)
                cursor.execute(query, params)
                result = cursor.fetchall()
                cursor.close()
                return result

            except Error as e:
                logger.error(f"SQL执行失败 (尝试 {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(1)  # 等待1秒后重试
                    self.close()   # 关闭旧连接
                    continue
                else:
                    raise

    def check_user_exists(self, username: str) -> bool:
        """检查用户是否存在"""
        try:
            query = "SELECT username FROM users WHERE username = %s"
            result = self._execute_with_retry(query, (username,))
            return len(result) > 0
        except Error as e:
            logger.error(f"检查用户存在性错误: {e}")
            return False

    def create_session(self, username: str, session_title: str = "新对话") -> Optional[int]:
        """创建新的对话会话"""
        try:
            if not self._ensure_connection():
                return None

            cursor = self.connection.cursor()
            query = """
                    INSERT INTO chat_sessions (username, session_title)
                    VALUES (%s, %s) \
                    """
            cursor.execute(query, (username, session_title))
            self.connection.commit()
            session_id = cursor.lastrowid
            cursor.close()

            logger.info(f"创建会话成功: session_id={session_id}, username={username}")

            # 记录API日志
            self.log_api_access(username, f"/api/sessions/create", "POST", 200, 0)

            return session_id
        except Error as e:
            logger.error(f"创建会话失败: {e}")
            if self.connection:
                self.connection.rollback()
            return None

    def save_message(self, session_id: int, username: str, role: str, content: str,
                     entities: Optional[str] = None, intents: Optional[str] = None,
                     knowledge: Optional[str] = None) -> bool:
        """保存对话消息"""
        try:
            if not self._ensure_connection():
                return False

            cursor = self.connection.cursor()
            query = """
                    INSERT INTO user_conversations
                        (session_id, username, role, content, entities, intents, knowledge)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) \
                    """
            cursor.execute(query, (session_id, username, role, content,
                                   entities, intents, knowledge))
            self.connection.commit()
            cursor.close()

            logger.info(f"消息保存成功: session_id={session_id}, role={role}, length={len(content)}")

            # 更新会话的last_updated时间
            self.update_session_last_updated(session_id)

            return True
        except Error as e:
            logger.error(f"保存消息失败: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def update_session_last_updated(self, session_id: int) -> bool:
        """更新会话的最后更新时间"""
        try:
            if not self._ensure_connection():
                return False

            cursor = self.connection.cursor()
            query = "UPDATE chat_sessions SET last_updated = CURRENT_TIMESTAMP WHERE session_id = %s"
            cursor.execute(query, (session_id,))
            self.connection.commit()
            cursor.close()
            return True
        except Error as e:
            logger.error(f"更新会话时间失败: {e}")
            return False

    def get_user_sessions(self, username: str) -> List[Dict]:
        """获取用户所有会话列表"""
        try:
            query = """
                    SELECT
                        session_id,
                        session_title,
                        start_time,
                        last_updated,
                        (SELECT COUNT(*) FROM user_conversations WHERE session_id = chat_sessions.session_id) as message_count,
                        (SELECT content FROM user_conversations
                         WHERE session_id = chat_sessions.session_id
                         ORDER BY timestamp ASC LIMIT 1) as first_message
                    FROM chat_sessions
                    WHERE username = %s
                    ORDER BY last_updated DESC \
                    """
            sessions = self._execute_with_retry(query, (username,))

            # 处理每个会话，确保有合适的标题
            for session in sessions:
                if not session['session_title'] or session['session_title'] == '新对话':
                    if session['first_message']:
                        # 使用第一条消息的前20个字符作为标题
                        title = session['first_message'][:20] + ('...' if len(session['first_message']) > 20 else '')
                        session['session_title'] = title

            return sessions
        except Error as e:
            logger.error(f"获取会话列表失败: {e}")
            return []

    def get_session_messages(self, session_id: int, username: str = None) -> List[Dict]:
        """获取指定会话的所有消息"""
        try:
            if username:
                # 验证会话属于该用户
                query = """
                        SELECT uc.id, uc.role, uc.content, uc.entities, uc.intents, uc.knowledge, uc.timestamp
                        FROM user_conversations uc
                                 INNER JOIN chat_sessions cs ON uc.session_id = cs.session_id
                        WHERE uc.session_id = %s AND cs.username = %s
                        ORDER BY uc.timestamp ASC \
                        """
                messages = self._execute_with_retry(query, (session_id, username))
            else:
                query = """
                        SELECT id, role, content, entities, intents, knowledge, timestamp
                        FROM user_conversations
                        WHERE session_id = %s
                        ORDER BY timestamp ASC \
                        """
                messages = self._execute_with_retry(query, (session_id,))

            return messages
        except Error as e:
            logger.error(f"获取会话消息失败: {e}")
            return []

    def update_session_title(self, session_id: int, new_title: str) -> bool:
        """更新会话标题"""
        try:
            if not self._ensure_connection():
                return False

            cursor = self.connection.cursor()
            query = "UPDATE chat_sessions SET session_title = %s WHERE session_id = %s"
            cursor.execute(query, (new_title, session_id))
            self.connection.commit()
            success = cursor.rowcount > 0
            cursor.close()

            if success:
                logger.info(f"更新会话标题成功: session_id={session_id}, new_title={new_title}")

            return success
        except Error as e:
            logger.error(f"更新会话标题失败: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def delete_session(self, session_id: int, username: str = None) -> bool:
        """删除会话及其所有消息"""
        try:
            if not self._ensure_connection():
                return False

            cursor = self.connection.cursor()

            if username:
                # 验证会话属于该用户
                query = "DELETE FROM chat_sessions WHERE session_id = %s AND username = %s"
                cursor.execute(query, (session_id, username))
            else:
                query = "DELETE FROM chat_sessions WHERE session_id = %s"
                cursor.execute(query, (session_id,))

            self.connection.commit()
            deleted = cursor.rowcount > 0
            cursor.close()

            if deleted:
                logger.info(f"删除会话成功: session_id={session_id}")

            return deleted
        except Error as e:
            logger.error(f"删除会话失败: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def get_session_info(self, session_id: int) -> Optional[Dict]:
        """获取会话详细信息"""
        try:
            query = """
                    SELECT cs.*, u.username, u.is_admin,
                           COUNT(uc.id) as total_messages
                    FROM chat_sessions cs
                             LEFT JOIN users u ON cs.username = u.username
                             LEFT JOIN user_conversations uc ON cs.session_id = uc.session_id
                    WHERE cs.session_id = %s
                    GROUP BY cs.session_id \
                    """
            result = self._execute_with_retry(query, (session_id,))
            return result[0] if result else None
        except Error as e:
            logger.error(f"获取会话信息失败: {e}")
            return None

    def get_user_statistics(self, username: str) -> Dict:
        """获取用户统计信息"""
        try:
            stats = {}

            # 获取会话数量
            query = "SELECT COUNT(*) as session_count FROM chat_sessions WHERE username = %s"
            result = self._execute_with_retry(query, (username,))
            if result:
                stats['session_count'] = result[0]['session_count']

            # 获取消息总数
            query = "SELECT COUNT(*) as total_messages FROM user_conversations WHERE username = %s"
            result = self._execute_with_retry(query, (username,))
            if result:
                stats['total_messages'] = result[0]['total_messages']

            # 获取最近活动时间
            query = """
                    SELECT MAX(last_updated) as last_active
                    FROM chat_sessions
                    WHERE username = %s \
                    """
            result = self._execute_with_retry(query, (username,))
            if result:
                stats['last_active'] = result[0]['last_active']

            # 获取今天发送的消息数
            query = """
                    SELECT COUNT(*) as today_messages
                    FROM user_conversations
                    WHERE username = %s AND DATE(timestamp) = CURDATE() \
                    """
            result = self._execute_with_retry(query, (username,))
            if result:
                stats['today_messages'] = result[0]['today_messages']

            return stats
        except Error as e:
            logger.error(f"获取用户统计信息失败: {e}")
            return {}

    # 日志记录功能
    def log_system_event(self, level: str, module: str, message: str, details: Dict = None):
        """记录系统事件到数据库"""
        try:
            if not self._ensure_connection():
                return

            cursor = self.connection.cursor()
            query = """
                    INSERT INTO system_logs (level, module, message, details)
                    VALUES (%s, %s, %s, %s) \
                    """
            details_json = json.dumps(details) if details else None
            cursor.execute(query, (level, module, message, details_json))
            self.connection.commit()
            cursor.close()
        except Error as e:
            logger.error(f"记录系统日志失败: {e}")

    def log_api_access(self, username: str, endpoint: str, method: str,
                       status_code: int, duration_ms: int,
                       user_agent: str = None, ip_address: str = None):
        """记录API访问日志"""
        try:
            if not self._ensure_connection():
                return

            cursor = self.connection.cursor()
            query = """
                    INSERT INTO api_access_logs
                    (username, endpoint, method, status_code, duration_ms, user_agent, ip_address)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) \
                    """
            cursor.execute(query, (username, endpoint, method, status_code,
                                   duration_ms, user_agent, ip_address))
            self.connection.commit()
            cursor.close()
        except Error as e:
            logger.error(f"记录API访问日志失败: {e}")

    # 管理功能
    def get_database_stats(self) -> Dict:
        """获取数据库统计信息"""
        try:
            stats = {}

            # 各表记录数
            tables = ['users', 'chat_sessions', 'user_conversations', 'system_logs', 'api_access_logs']

            for table in tables:
                try:
                    query = f"SELECT COUNT(*) as count FROM {table}"
                    result = self._execute_with_retry(query)
                    if result:
                        stats[f'{table}_count'] = result[0]['count']
                except:
                    stats[f'{table}_count'] = 0

            # 数据库大小
            query = """
                    SELECT
                        table_schema as database_name,
                        SUM(data_length + index_length) / 1024 / 1024 as size_mb
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    GROUP BY table_schema \
                    """
            result = self._execute_with_retry(query, (self.database,))
            if result:
                stats['database_size_mb'] = round(result[0]['size_mb'], 2)

            # 活跃用户数（最近7天）
            query = """
                    SELECT COUNT(DISTINCT username) as active_users
                    FROM chat_sessions
                    WHERE last_updated >= DATE_SUB(NOW(), INTERVAL 7 DAY) \
                    """
            result = self._execute_with_retry(query)
            if result:
                stats['active_users_7d'] = result[0]['active_users']

            return stats
        except Error as e:
            logger.error(f"获取数据库统计失败: {e}")
            return {}

    def save_patient_report(self, username: str, file_name: str, file_type: str, 
                           raw_ocr_text: str, structured_json: str, ocr_score: float) -> bool:
        """保存患者报告OCR结果"""
        try:
            if not self._ensure_connection():
                return False

            cursor = self.connection.cursor()
            query = """
                INSERT INTO patient_reports
                (username, file_name, file_type, raw_ocr_text, structured_json, ocr_score)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                username, file_name, file_type, raw_ocr_text, structured_json, ocr_score
            ))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"保存病例OCR失败: {e}")
            if self.connection:
                self.connection.rollback()
            return False
        
    