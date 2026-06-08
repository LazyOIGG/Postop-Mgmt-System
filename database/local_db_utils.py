import mysql.connector
from mysql.connector import Error, pooling
import time
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import os
from dotenv import load_dotenv

from app.core.logging import get_logger

# 加载环境变量
load_dotenv()

logger = get_logger(__name__)

class DatabaseConnector:
    def __init__(self, host=None, database=None, user=None, password=None,
                 pool_size=5, pool_name='medical_qa_pool'):
        # 从环境变量中读取配置，如果参数未提供
        self.host = host or os.getenv('MYSQL_HOST', 'localhost')
        self.database = database or os.getenv('MYSQL_DATABASE', 'RAG')
        self.user = user or os.getenv('MYSQL_USER', 'root')
        self.password = password or os.getenv('MYSQL_PASSWORD', '')
        self.pool_size = pool_size
        self.pool_name = pool_name
        self.connection_pool = None
        self.connection = None

        self._create_connection_pool()

    def _create_connection_pool(self):
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
        try:
            # 如果已有有效连接，直接复用，避免从连接池重复取连接导致池耗尽
            if self.connection and self.connection.is_connected():
                return True

            if self.connection_pool:
                self.connection = self.connection_pool.get_connection()
            else:
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
        if self.connection and self.connection.is_connected():
            if self.connection_pool:
                self.connection.close()
            else:
                self.connection.close()
            self.connection = None
            logger.info("数据库连接已关闭")

    def _ensure_connection(self) -> bool:
        if not self.connection or not self.connection.is_connected():
            return self.connect()
        return True

    def _execute_with_retry(self, query: str, params: tuple = None, retries: int = 3) -> Any:
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
                    time.sleep(1)
                    self.close()
                    continue
                else:
                    raise

    def check_user_exists(self, username: str) -> bool:
        try:
            query = "SELECT username FROM users WHERE username = %s"
            result = self._execute_with_retry(query, (username,))
            return len(result) > 0
        except Error as e:
            logger.error(f"检查用户存在性错误: {e}")
            return False

    def create_session(self, username: str, session_title: str = "新对话") -> Optional[int]:
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

            self.update_session_last_updated(session_id)

            return True
        except Error as e:
            logger.error(f"保存消息失败: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def update_session_last_updated(self, session_id: int) -> bool:
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

            for session in sessions:
                if not session['session_title'] or session['session_title'] == '新对话':
                    if session['first_message']:
                        title = session['first_message'][:20] + ('...' if len(session['first_message']) > 20 else '')
                        session['session_title'] = title

            return sessions
        except Error as e:
            logger.error(f"获取会话列表失败: {e}")
            return []

    def get_session_messages(self, session_id: int, username: str = None) -> List[Dict]:
        try:
            if username:
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
        try:
            if not self._ensure_connection():
                return False

            cursor = self.connection.cursor()

            if username:
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
        try:
            stats = {}

            query = "SELECT COUNT(*) as session_count FROM chat_sessions WHERE username = %s"
            result = self._execute_with_retry(query, (username,))
            if result:
                stats['session_count'] = result[0]['session_count']

            query = "SELECT COUNT(*) as total_messages FROM user_conversations WHERE username = %s"
            result = self._execute_with_retry(query, (username,))
            if result:
                stats['total_messages'] = result[0]['total_messages']

            query = """
                    SELECT MAX(last_updated) as last_active
                    FROM chat_sessions
                    WHERE username = %s \
                    """
            result = self._execute_with_retry(query, (username,))
            if result:
                stats['last_active'] = result[0]['last_active']

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

    def log_system_event(self, level: str, module: str, message: str, details: Dict = None):
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

    def get_database_stats(self) -> Dict:
        try:
            stats = {}

            tables = ['users', 'chat_sessions', 'user_conversations', 'system_logs', 'api_access_logs']

            for table in tables:
                try:
                    query = f"SELECT COUNT(*) as count FROM {table}"
                    result = self._execute_with_retry(query)
                    if result:
                        stats[f'{table}_count'] = result[0]['count']
                except:
                    stats[f'{table}_count'] = 0

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
            logger.error("save_patient_report_failed", error=str(e))
            if self.connection:
                self.connection.rollback()
            return False

    def save_health_assessment(self, username: str, session_id: int, source_type: str,
                            input_text: str, risk_level: str, risk_reasons: str,
                            advice: str, need_hospital: int) -> bool:
        try:
            if not self._ensure_connection():
                return False

            cursor = self.connection.cursor()
            query = """
                INSERT INTO health_assessments
                (username, session_id, source_type, input_text, risk_level, risk_reasons, advice, need_hospital)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                username, session_id, source_type, input_text,
                risk_level, risk_reasons, advice, need_hospital
            ))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error("save_health_assessment_failed", error=str(e))
            if self.connection:
                self.connection.rollback()
            return False

    def get_health_assessment_history(self, username: str):
        try:
            if not self._ensure_connection():
                return []

            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT id, session_id, source_type, input_text, risk_level,
                       risk_reasons, advice, need_hospital, created_at
                FROM health_assessments
                WHERE username = %s
                ORDER BY created_at DESC
            """
            cursor.execute(query, (username,))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error("get_health_assessment_history_failed", error=str(e))
            return []

    def save_patient_profile(
        self,
        username: str,
        real_name: str = "",
        gender: str = "",
        age: int = None,
        phone: str = "",
        height: float = None,
        weight: float = None,
        blood_type: str = "",
        medical_history: str = "",
        allergy_history: str = "",
        current_medications: str = "",
        emergency_contact: str = "",
        emergency_phone: str = "",
        health_stage: str = "长期管理"
    ) -> bool:
        try:
            if not self._ensure_connection():
                return False

            cursor = self.connection.cursor()

            query = """
            INSERT INTO patient_profiles (
                username, real_name, gender, age, phone, height, weight, blood_type,
                medical_history, allergy_history, current_medications,
                emergency_contact, emergency_phone, health_stage
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                real_name = VALUES(real_name),
                gender = VALUES(gender),
                age = VALUES(age),
                phone = VALUES(phone),
                height = VALUES(height),
                weight = VALUES(weight),
                blood_type = VALUES(blood_type),
                medical_history = VALUES(medical_history),
                allergy_history = VALUES(allergy_history),
                current_medications = VALUES(current_medications),
                emergency_contact = VALUES(emergency_contact),
                emergency_phone = VALUES(emergency_phone),
                health_stage = VALUES(health_stage)
            """
            cursor.execute(query, (
                username, real_name, gender, age, phone, height, weight, blood_type,
                medical_history, allergy_history, current_medications,
                emergency_contact, emergency_phone, health_stage
            ))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error("save_patient_profile_failed", error=str(e))
            if self.connection:
                self.connection.rollback()
            return False

    def get_patient_profile(self, username: str):
        try:
            if not self._ensure_connection():
                return None

            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT id, username, real_name, gender, age, phone, height, weight,
                       blood_type, medical_history, allergy_history, current_medications,
                       emergency_contact, emergency_phone, health_stage,
                       created_at, updated_at
                FROM patient_profiles
                WHERE username = %s
                LIMIT 1
            """
            cursor.execute(query, (username,))
            result = cursor.fetchone()
            cursor.close()
            return result
        except Exception as e:
            logger.error("get_patient_profile_failed", error=str(e))
            return None

    def get_latest_health_assessment(self, username: str):
        try:
            if not self._ensure_connection():
                return None

            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT id, source_type, input_text, risk_level, risk_reasons,
                       advice, need_hospital, created_at
                FROM health_assessments
                WHERE username = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            cursor.execute(query, (username,))
            result = cursor.fetchone()
            cursor.close()
            return result
        except Exception as e:
            logger.error("get_latest_health_assessment_failed", error=str(e))
            return None

    def save_daily_checkin(
        self,
        username: str,
        checkin_date: str,
        symptoms: str = "",
        temperature: float = None,
        blood_pressure: str = "",
        blood_sugar: float = None,
        heart_rate: int = None,
        sleep_status: str = "",
        diet_status: str = "",
        exercise_status: str = "",
        medication_taken: int = 0,
        note: str = "",
        abnormal_flag: int = 0,
        abnormal_reason: str = ""
    ) -> bool:
        try:
            if not self._ensure_connection():
                return False

            cursor = self.connection.cursor()
            query = """
            INSERT INTO daily_checkins (
                username, checkin_date, symptoms, temperature, blood_pressure,
                blood_sugar, heart_rate, sleep_status, diet_status, exercise_status,
                medication_taken, note, abnormal_flag, abnormal_reason
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                symptoms = VALUES(symptoms),
                temperature = VALUES(temperature),
                blood_pressure = VALUES(blood_pressure),
                blood_sugar = VALUES(blood_sugar),
                heart_rate = VALUES(heart_rate),
                sleep_status = VALUES(sleep_status),
                diet_status = VALUES(diet_status),
                exercise_status = VALUES(exercise_status),
                medication_taken = VALUES(medication_taken),
                note = VALUES(note),
                abnormal_flag = VALUES(abnormal_flag),
                abnormal_reason = VALUES(abnormal_reason)
            """
            cursor.execute(query, (
                username, checkin_date, symptoms, temperature, blood_pressure,
                blood_sugar, heart_rate, sleep_status, diet_status, exercise_status,
                medication_taken, note, abnormal_flag, abnormal_reason
            ))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error("save_daily_checkin_failed", error=str(e))
            if self.connection:
                self.connection.rollback()
            return False


    def get_daily_checkins(self, username: str, limit: int = 30):
        try:
            if not self._ensure_connection():
                return []

            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT id, checkin_date, symptoms, temperature, blood_pressure,
                       blood_sugar, heart_rate, sleep_status, diet_status,
                       exercise_status, medication_taken, note,
                       abnormal_flag, abnormal_reason, created_at, updated_at
                FROM daily_checkins
                WHERE username = %s
                ORDER BY checkin_date DESC
                LIMIT %s
            """
            cursor.execute(query, (username, limit))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error("get_daily_checkins_failed", error=str(e))
            return []


    def get_today_checkin(self, username: str, checkin_date: str):
        try:
            if not self._ensure_connection():
                return None

            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT id, checkin_date, symptoms, temperature, blood_pressure,
                       blood_sugar, heart_rate, sleep_status, diet_status,
                       exercise_status, medication_taken, note,
                       abnormal_flag, abnormal_reason
                FROM daily_checkins
                WHERE username = %s AND checkin_date = %s
                LIMIT 1
            """
            cursor.execute(query, (username, checkin_date))
            result = cursor.fetchone()
            cursor.close()
            return result
        except Exception as e:
            logger.error("get_today_checkin_failed", error=str(e))
            return None

    def get_recent_checkins_for_overview(self, username: str, days: int = 7):
        try:
            if not self._ensure_connection():
                return []

            cursor = self.connection.cursor(dictionary=True)
            query = f"""
                SELECT checkin_date, temperature, blood_pressure, blood_sugar,
                       heart_rate, symptoms, medication_taken,
                       abnormal_flag, abnormal_reason
                FROM daily_checkins
                WHERE username = %s
                ORDER BY checkin_date DESC
                LIMIT %s
            """
            cursor.execute(query, (username, days))
            results = cursor.fetchall()
            cursor.close()
            return list(reversed(results))  # 反转成时间正序，方便前端画图
        except Exception as e:
            logger.error("get_recent_checkins_for_overview_failed", error=str(e))
            return []

    def get_checkin_summary_stats(self, username: str, days: int = 7):
        try:
            if not self._ensure_connection():
                return None

            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT
                    COUNT(*) AS total_checkins,
                    SUM(CASE WHEN abnormal_flag = 1 THEN 1 ELSE 0 END) AS abnormal_count,
                    AVG(temperature) AS avg_temperature,
                    AVG(heart_rate) AS avg_heart_rate,
                    AVG(blood_sugar) AS avg_blood_sugar
                FROM (
                    SELECT *
                    FROM daily_checkins
                    WHERE username = %s
                    ORDER BY checkin_date DESC
                    LIMIT %s
                ) t
            """
            cursor.execute(query, (username, days))
            result = cursor.fetchone()
            cursor.close()
            return result
        except Exception as e:
            logger.error("get_checkin_summary_stats_failed", error=str(e))
            return None

    def save_reminder(
        self,
        username: str,
        reminder_type: str,
        title: str,
        description: str,
        reminder_date: str,
        reminder_time: str = None
    ):
        try:
            if not self._ensure_connection():
                return None

            cursor = self.connection.cursor()
            query = """
                INSERT INTO reminders
                (username, reminder_type, title, description, reminder_date, reminder_time, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending')
            """
            cursor.execute(query, (
                username, reminder_type, title, description,
                reminder_date, reminder_time
            ))
            self.connection.commit()
            new_id = cursor.lastrowid
            cursor.close()
            return new_id
        except Exception as e:
            logger.error("save_reminder_failed", error=str(e))
            if self.connection:
                self.connection.rollback()
            return None

    def get_reminders(self, username: str, limit: int = 50):
        try:
            if not self._ensure_connection():
                return []

            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT id, reminder_type, title, description,
                       reminder_date, reminder_time, status,
                       created_at, updated_at
                FROM reminders
                WHERE username = %s
                ORDER BY reminder_date ASC, reminder_time ASC
                LIMIT %s
            """
            cursor.execute(query, (username, limit))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error("get_reminders_failed", error=str(e))
            return []

    def update_reminder_status(self, username: str, reminder_id: int, status: str) -> bool:
        try:
            if not self._ensure_connection():
                return False

            cursor = self.connection.cursor()
            query = """
                UPDATE reminders
                SET status = %s
                WHERE id = %s AND username = %s
            """
            cursor.execute(query, (status, reminder_id, username))
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception as e:
            logger.error("update_reminder_status_failed", error=str(e))
            if self.connection:
                self.connection.rollback()
            return False

    def delete_reminder(self, username: str, reminder_id: int) -> bool:
        try:
            if not self._ensure_connection():
                return False

            cursor = self.connection.cursor()
            query = """
                DELETE FROM reminders
                WHERE id = %s AND username = %s
            """
            cursor.execute(query, (reminder_id, username))
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception as e:
            logger.error("delete_reminder_failed", error=str(e))
            if self.connection:
                self.connection.rollback()
            return False

    def get_today_reminder_stats(self, username: str):
        try:
            if not self._ensure_connection():
                return {"pending_count": 0, "completed_count": 0}

            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending_count,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_count
                FROM reminders
                WHERE username = %s AND reminder_date = CURDATE()
            """
            cursor.execute(query, (username,))
            result = cursor.fetchone()
            cursor.close()
            return {
                "pending_count": int(result.get("pending_count") or 0),
                "completed_count": int(result.get("completed_count") or 0)
            }
        except Exception as e:
            logger.error("get_today_reminder_stats_failed", error=str(e))
            return {"pending_count": 0, "completed_count": 0}

    def get_doctor_patient_list(self, limit: int = 100):
        try:
            if not self._ensure_connection():
                return []

            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT
                    u.username,
                    p.real_name,
                    p.gender,
                    p.age,
                    p.health_stage,
                    ha.risk_level AS latest_risk_level,
                    ha.created_at AS latest_assessment_time
                FROM users u
                LEFT JOIN patient_profiles p
                    ON u.username = p.username
                LEFT JOIN (
                    SELECT h1.username, h1.risk_level, h1.created_at
                    FROM health_assessments h1
                    INNER JOIN (
                        SELECT username, MAX(created_at) AS max_created_at
                        FROM health_assessments
                        GROUP BY username
                    ) h2
                    ON h1.username = h2.username AND h1.created_at = h2.max_created_at
                ) ha
                    ON u.username = ha.username
                ORDER BY ha.created_at DESC, u.username ASC
                LIMIT %s
            """
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error("get_doctor_patient_list_failed", error=str(e))
            return []

    def get_high_risk_assessments(self, limit: int = 50):
        try:
            if not self._ensure_connection():
                return []

            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT
                    h.id, h.username, p.real_name, h.source_type, h.input_text,
                    h.risk_level, h.risk_reasons, h.advice, h.need_hospital, h.created_at
                FROM health_assessments h
                LEFT JOIN patient_profiles p
                    ON h.username = p.username
                WHERE h.risk_level = '高风险'
                ORDER BY h.created_at DESC
                LIMIT %s
            """
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error("get_high_risk_assessments_failed", error=str(e))
            return []

    def get_abnormal_checkins_for_doctor(self, limit: int = 50):
        try:
            if not self._ensure_connection():
                return []

            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT
                    d.id, d.username, p.real_name, d.checkin_date, d.symptoms,
                    d.temperature, d.blood_pressure, d.blood_sugar, d.heart_rate,
                    d.abnormal_flag, d.abnormal_reason, d.created_at
                FROM daily_checkins d
                LEFT JOIN patient_profiles p
                    ON d.username = p.username
                WHERE d.abnormal_flag = 1
                ORDER BY d.checkin_date DESC, d.created_at DESC
                LIMIT %s
            """
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error("get_abnormal_checkins_for_doctor_failed", error=str(e))
            return []

    def get_patient_detail_for_doctor(self, username: str):
        try:
            if not self._ensure_connection():
                return None

            profile = self.get_patient_profile(username)
            latest_assessment = self.get_latest_health_assessment(username)
            checkins = self.get_daily_checkins(username, limit=7)
            reminders = self.get_reminders(username, limit=10)

            return {
                "profile": profile,
                "latest_assessment": latest_assessment,
                "recent_checkins": checkins,
                "recent_reminders": reminders
            }
        except Exception as e:
            logger.error("get_patient_detail_for_doctor_failed", error=str(e))
            return None

    def get_system_basic_stats(self):
        try:
            if not self._ensure_connection():
                return {}

            cursor = self.connection.cursor(dictionary=True)

            stats = {}

            # 1. 用户总数
            cursor.execute("SELECT COUNT(*) AS total_users FROM users")
            stats["total_users"] = int(cursor.fetchone()["total_users"])

            # 2. 健康评估总数
            cursor.execute("SELECT COUNT(*) AS total_assessments FROM health_assessments")
            stats["total_assessments"] = int(cursor.fetchone()["total_assessments"])

            # 3. 高风险评估数
            cursor.execute("SELECT COUNT(*) AS high_risk_assessments FROM health_assessments WHERE risk_level = '高风险'")
            stats["high_risk_assessments"] = int(cursor.fetchone()["high_risk_assessments"])

            # 4. 打卡总数
            cursor.execute("SELECT COUNT(*) AS total_checkins FROM daily_checkins")
            stats["total_checkins"] = int(cursor.fetchone()["total_checkins"])

            # 5. 异常打卡数
            cursor.execute("SELECT COUNT(*) AS abnormal_checkins FROM daily_checkins WHERE abnormal_flag = 1")
            stats["abnormal_checkins"] = int(cursor.fetchone()["abnormal_checkins"])

            # 6. 提醒总数
            cursor.execute("SELECT COUNT(*) AS total_reminders FROM reminders")
            stats["total_reminders"] = int(cursor.fetchone()["total_reminders"])

            # 7. 今日待完成提醒数
            cursor.execute("""
                SELECT COUNT(*) AS today_pending_reminders
                FROM reminders
                WHERE reminder_date = CURDATE() AND status = 'pending'
            """)
            stats["today_pending_reminders"] = int(cursor.fetchone()["today_pending_reminders"])

            cursor.close()
            return stats
        except Exception as e:
            logger.error("get_system_basic_stats_failed", error=str(e))
            return {}

    def get_system_ratio_stats(self):
        try:
            if not self._ensure_connection():
                return {}

            cursor = self.connection.cursor(dictionary=True)

            ratios = {}

            cursor.execute("""
                SELECT
                    COUNT(*) AS total_assessments,
                    SUM(CASE WHEN risk_level = '高风险' THEN 1 ELSE 0 END) AS high_risk_assessments
                FROM health_assessments
            """)
            assessment_result = cursor.fetchone()
            total_assessments = int(assessment_result["total_assessments"] or 0)
            high_risk_assessments = int(assessment_result["high_risk_assessments"] or 0)

            cursor.execute("""
                SELECT
                    COUNT(*) AS total_checkins,
                    SUM(CASE WHEN abnormal_flag = 1 THEN 1 ELSE 0 END) AS abnormal_checkins
                FROM daily_checkins
            """)
            checkin_result = cursor.fetchone()
            total_checkins = int(checkin_result["total_checkins"] or 0)
            abnormal_checkins = int(checkin_result["abnormal_checkins"] or 0)

            ratios["high_risk_ratio"] = round(high_risk_assessments / total_assessments * 100, 2) if total_assessments > 0 else 0.0
            ratios["abnormal_checkin_ratio"] = round(abnormal_checkins / total_checkins * 100, 2) if total_checkins > 0 else 0.0

            cursor.close()
            return ratios
        except Exception as e:
            logger.error("get_system_ratio_stats_failed", error=str(e))
            return {}

    def get_recent_high_risk_records(self, limit: int = 10):
        try:
            if not self._ensure_connection():
                return []

            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT
                    h.username,
                    p.real_name,
                    h.source_type,
                    h.risk_level,
                    h.created_at
                FROM health_assessments h
                LEFT JOIN patient_profiles p ON h.username = p.username
                WHERE h.risk_level = '高风险'
                ORDER BY h.created_at DESC
                LIMIT %s
            """
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error("get_recent_high_risk_records_failed", error=str(e))
            return []

    def get_recent_abnormal_checkins(self, limit: int = 10):
        try:
            if not self._ensure_connection():
                return []

            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT
                    d.username,
                    p.real_name,
                    d.checkin_date,
                    d.abnormal_reason,
                    d.created_at
                FROM daily_checkins d
                LEFT JOIN patient_profiles p ON d.username = p.username
                WHERE d.abnormal_flag = 1
                ORDER BY d.checkin_date DESC, d.created_at DESC
                LIMIT %s
            """
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error("get_recent_abnormal_checkins_failed", error=str(e))
            return []

    def create_alert_notification(
        self, username: str, real_name: str, risk_level: str,
        risk_reasons: str, advice: str, source_type: str = "text"
    ) -> bool:
        try:
            if not self._ensure_connection():
                return False
            cursor = self.connection.cursor()
            query = """
                INSERT INTO alert_notifications
                (username, real_name, risk_level, risk_reasons, advice, source_type)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (username, real_name, risk_level, risk_reasons, advice, source_type))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error("create_alert_notification_failed", error=str(e))
            if self.connection:
                self.connection.rollback()
            return False

    def get_alert_notifications(self, status: str = None, limit: int = 50):
        try:
            if not self._ensure_connection():
                return []
            cursor = self.connection.cursor(dictionary=True)
            if status:
                query = """
                    SELECT id, username, real_name, risk_level, risk_reasons,
                           advice, source_type, status, processed_at, created_at
                    FROM alert_notifications
                    WHERE status = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                cursor.execute(query, (status, limit))
            else:
                query = """
                    SELECT id, username, real_name, risk_level, risk_reasons,
                           advice, source_type, status, processed_at, created_at
                    FROM alert_notifications
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                cursor.execute(query, (limit,))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error("get_alert_notifications_failed", error=str(e))
            return []

    def process_alert_notification(self, alert_id: int) -> bool:
        try:
            if not self._ensure_connection():
                return False
            cursor = self.connection.cursor()
            query = """
                UPDATE alert_notifications
                SET status = 'processed', processed_at = NOW()
                WHERE id = %s
            """
            cursor.execute(query, (alert_id,))
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception as e:
            logger.error("process_alert_notification_failed", error=str(e))
            if self.connection:
                self.connection.rollback()
            return False

    def save_doctor_message(
        self, doctor_username: str, patient_username: str, content: str,
        message_type: str = 'text', media_url: str = None,
    ) -> Optional[int]:
        try:
            if not self._ensure_connection():
                return None
            cursor = self.connection.cursor()
            query = """
                INSERT INTO doctor_messages (doctor_username, patient_username, content, message_type, media_url)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (doctor_username, patient_username, content, message_type, media_url))
            self.connection.commit()
            msg_id = cursor.lastrowid
            cursor.close()
            return msg_id
        except Exception as e:
            logger.error("save_doctor_message_failed", error=str(e))
            if self.connection:
                self.connection.rollback()
            return None

    def get_doctor_messages(self, patient_username: str, limit: int = 30):
        try:
            if not self._ensure_connection():
                return []
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT id, doctor_username, patient_username, content, message_type, media_url, created_at
                FROM doctor_messages
                WHERE patient_username = %s
                ORDER BY created_at DESC
                LIMIT %s
            """
            cursor.execute(query, (patient_username, limit))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error("get_doctor_messages_failed", error=str(e))
            return []

    # ── P3.15 推送通知 DB 方法 ──

    def create_notification(
        self, username: str, notif_type: str, title: str,
        content: str = "", related_id: int = None
    ) -> Optional[int]:
        try:
            if not self._ensure_connection():
                return None
            cursor = self.connection.cursor()
            query = """
                INSERT INTO notifications (username, type, title, content, related_id)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (username, notif_type, title, content, related_id))
            self.connection.commit()
            nid = cursor.lastrowid
            cursor.close()
            return nid
        except Exception as e:
            logger.error("create_notification_failed", error=str(e))
            if self.connection:
                self.connection.rollback()
            return None

    def get_notifications(self, username: str, unread_only: bool = False, limit: int = 50):
        try:
            if not self._ensure_connection():
                return []
            cursor = self.connection.cursor(dictionary=True)
            if unread_only:
                query = """
                    SELECT id, username, type, title, content, related_id, is_read, created_at
                    FROM notifications
                    WHERE username = %s AND is_read = FALSE
                    ORDER BY created_at DESC LIMIT %s
                """
            else:
                query = """
                    SELECT id, username, type, title, content, related_id, is_read, created_at
                    FROM notifications
                    WHERE username = %s
                    ORDER BY created_at DESC LIMIT %s
                """
            cursor.execute(query, (username, limit))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error("get_notifications_failed", error=str(e))
            return []

    def get_unread_notification_count(self, username: str) -> int:
        try:
            if not self._ensure_connection():
                return 0
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT COUNT(*) AS cnt FROM notifications
                WHERE username = %s AND is_read = FALSE
            """
            cursor.execute(query, (username,))
            result = cursor.fetchone()
            cursor.close()
            return int(result['cnt']) if result else 0
        except Exception as e:
            logger.error("get_unread_notification_count_failed", error=str(e))
            return 0

    def mark_notification_read(self, notification_id: int, username: str) -> bool:
        try:
            if not self._ensure_connection():
                return False
            cursor = self.connection.cursor()
            query = """
                UPDATE notifications SET is_read = TRUE
                WHERE id = %s AND username = %s
            """
            cursor.execute(query, (notification_id, username))
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception as e:
            logger.error("mark_notification_read_failed", error=str(e))
            if self.connection:
                self.connection.rollback()
            return False

    def mark_all_notifications_read(self, username: str) -> bool:
        try:
            if not self._ensure_connection():
                return False
            cursor = self.connection.cursor()
            query = """
                UPDATE notifications SET is_read = TRUE
                WHERE username = %s AND is_read = FALSE
            """
            cursor.execute(query, (username,))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error("mark_all_notifications_read_failed", error=str(e))
            if self.connection:
                self.connection.rollback()
            return False

    def get_notifications_paginated(
        self, username: str, unread_only: bool = False, limit: int = 20, offset: int = 0
    ):
        """分页获取通知列表"""
        try:
            if not self._ensure_connection():
                return []
            cursor = self.connection.cursor(dictionary=True)
            if unread_only:
                query = """
                    SELECT id, username, type, title, content, related_id, is_read, created_at
                    FROM notifications
                    WHERE username = %s AND is_read = FALSE
                    ORDER BY created_at DESC LIMIT %s OFFSET %s
                """
            else:
                query = """
                    SELECT id, username, type, title, content, related_id, is_read, created_at
                    FROM notifications
                    WHERE username = %s
                    ORDER BY created_at DESC LIMIT %s OFFSET %s
                """
            cursor.execute(query, (username, limit, offset))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"分页获取通知失败: {e}")
            return []

    def get_notification_count(self, username: str, unread_only: bool = False) -> int:
        """获取通知总数"""
        try:
            if not self._ensure_connection():
                return 0
            cursor = self.connection.cursor(dictionary=True)
            if unread_only:
                query = """
                    SELECT COUNT(*) AS cnt FROM notifications
                    WHERE username = %s AND is_read = FALSE
                """
            else:
                query = """
                    SELECT COUNT(*) AS cnt FROM notifications
                    WHERE username = %s
                """
            cursor.execute(query, (username,))
            result = cursor.fetchone()
            cursor.close()
            return int(result['cnt']) if result else 0
        except Exception as e:
            logger.error(f"获取通知总数失败: {e}")
            return 0

    def delete_notification(self, notification_id: int, username: str) -> bool:
        """删除通知（仅所有者可删除）"""
        try:
            if not self._ensure_connection():
                return False
            cursor = self.connection.cursor()
            query = "DELETE FROM notifications WHERE id = %s AND username = %s"
            cursor.execute(query, (notification_id, username))
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception as e:
            logger.error(f"删除通知失败: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def get_admin_usernames(self) -> List[str]:
        try:
            if not self._ensure_connection():
                return []
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT username FROM users WHERE is_admin = 1")
            result = [row['username'] for row in cursor.fetchall()]
            cursor.close()
            return result
        except Exception as e:
            logger.error(f"获取管理员列表失败: {e}")
            return []

    # ── 原有方法 ──

    def save_admin_message_to_patient(
        self, doctor_username: str, patient_username: str, content: str
    ) -> bool:
        try:
            if not self._ensure_connection():
                return False
            cursor = self.connection.cursor()
            query = """
                INSERT INTO user_conversations (session_id, username, role, content)
                VALUES (
                    COALESCE(
                        (SELECT session_id FROM chat_sessions
                         WHERE username = %s ORDER BY last_updated DESC LIMIT 1),
                        (SELECT MAX(session_id) FROM chat_sessions WHERE username = %s)
                    ),
                    %s, 'assistant', %s
                )
            """
            cursor.execute(query, (patient_username, patient_username, patient_username, content))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"保存医生回复到患者对话失败: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    # ── 康复计划相关方法 ────────────────────────────────────────────

    def save_rehab_plan(
        self, username: str, surgery_type: str, plan_title: str, generated_plan: str = None
    ):
        try:
            if not self._ensure_connection():
                return None
            cursor = self.connection.cursor()
            query = """
                INSERT INTO rehab_plans (username, surgery_type, plan_title, generated_plan)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (username, surgery_type, plan_title, generated_plan))
            self.connection.commit()
            new_id = cursor.lastrowid
            cursor.close()
            return new_id
        except Exception as e:
            logger.error(f"保存康复计划失败: {e}")
            if self.connection:
                self.connection.rollback()
            return None

    def get_rehab_plans(self, username: str, status: str = None):
        try:
            if not self._ensure_connection():
                return []
            cursor = self.connection.cursor(dictionary=True)
            if status:
                query = """
                    SELECT id, username, surgery_type, plan_title, current_phase,
                           status, generated_plan, created_at, updated_at
                    FROM rehab_plans WHERE username = %s AND status = %s
                    ORDER BY created_at DESC
                """
                cursor.execute(query, (username, status))
            else:
                query = """
                    SELECT id, username, surgery_type, plan_title, current_phase,
                           status, generated_plan, created_at, updated_at
                    FROM rehab_plans WHERE username = %s
                    ORDER BY created_at DESC
                """
                cursor.execute(query, (username,))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"获取康复计划列表失败: {e}")
            return []

    def get_rehab_plan(self, plan_id: int):
        try:
            if not self._ensure_connection():
                return None
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT id, username, surgery_type, plan_title, current_phase,
                       status, generated_plan, created_at, updated_at
                FROM rehab_plans WHERE id = %s
            """
            cursor.execute(query, (plan_id,))
            result = cursor.fetchone()
            cursor.close()
            return result
        except Exception as e:
            logger.error(f"获取康复计划失败: {e}")
            return None

    def update_rehab_plan_phase(self, plan_id: int, current_phase: str) -> bool:
        try:
            if not self._ensure_connection():
                return False
            cursor = self.connection.cursor()
            query = "UPDATE rehab_plans SET current_phase = %s WHERE id = %s"
            cursor.execute(query, (current_phase, plan_id))
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception as e:
            logger.error(f"更新康复计划阶段失败: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def update_rehab_plan_status(self, plan_id: int, status: str) -> bool:
        try:
            if not self._ensure_connection():
                return False
            cursor = self.connection.cursor()
            query = "UPDATE rehab_plans SET status = %s WHERE id = %s"
            cursor.execute(query, (status, plan_id))
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception as e:
            logger.error(f"更新康复计划状态失败: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def save_rehab_plan_task(
        self, plan_id: int, username: str, phase: str, task_day: int,
        task_date: str, task_type: str, task_content: str, reminder_id: int = None
    ) -> bool:
        try:
            if not self._ensure_connection():
                return False
            cursor = self.connection.cursor()
            query = """
                INSERT INTO rehab_plan_tasks
                (plan_id, username, phase, task_day, task_date, task_type, task_content, reminder_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                plan_id, username, phase, task_day, task_date, task_type, task_content, reminder_id
            ))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"保存康复计划任务失败: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def get_rehab_plan_tasks(self, plan_id: int, phase: str = None, task_date: str = None):
        try:
            if not self._ensure_connection():
                return []
            cursor = self.connection.cursor(dictionary=True)
            conditions = ["plan_id = %s"]
            params = [plan_id]
            if phase:
                conditions.append("phase = %s")
                params.append(phase)
            if task_date:
                conditions.append("task_date = %s")
                params.append(task_date)
            where = " AND ".join(conditions)
            query = f"""
                SELECT id, plan_id, username, phase, task_day, task_date,
                       task_type, task_content, reminder_id, status, created_at, updated_at
                FROM rehab_plan_tasks WHERE {where}
                ORDER BY task_day ASC, task_type ASC
            """
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"获取康复计划任务失败: {e}")
            return []

    def get_today_rehab_tasks(self, username: str, task_date: str):
        try:
            if not self._ensure_connection():
                return []
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT t.id, t.plan_id, t.username, t.phase, t.task_day, t.task_date,
                       t.task_type, t.task_content, t.reminder_id, t.status,
                       p.plan_title, p.surgery_type
                FROM rehab_plan_tasks t
                JOIN rehab_plans p ON t.plan_id = p.id
                WHERE t.username = %s AND t.task_date = %s AND p.status = 'active'
                ORDER BY t.task_type ASC
            """
            cursor.execute(query, (username, task_date))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"获取今日康复任务失败: {e}")
            return []

    def update_rehab_task_status(self, task_id: int, status: str) -> bool:
        try:
            if not self._ensure_connection():
                return False
            cursor = self.connection.cursor()
            query = "UPDATE rehab_plan_tasks SET status = %s WHERE id = %s"
            cursor.execute(query, (status, task_id))
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception as e:
            logger.error(f"更新康复任务状态失败: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def get_rehab_plan_task(self, task_id: int):
        try:
            if not self._ensure_connection():
                return None
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT id, plan_id, username, phase, task_day, task_date,
                       task_type, task_content, reminder_id, status, created_at, updated_at
                FROM rehab_plan_tasks WHERE id = %s
            """
            cursor.execute(query, (task_id,))
            result = cursor.fetchone()
            cursor.close()
            return result
        except Exception as e:
            logger.error(f"获取康复任务失败: {e}")
            return None

    def get_rehab_plan_phase_task_stats(self, plan_id: int, phase: str):
        try:
            if not self._ensure_connection():
                return {"total": 0, "completed": 0}
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                FROM rehab_plan_tasks WHERE plan_id = %s AND phase = %s
            """
            cursor.execute(query, (plan_id, phase))
            result = cursor.fetchone()
            cursor.close()
            return result or {"total": 0, "completed": 0}
        except Exception as e:
            logger.error(f"获取康复阶段任务统计失败: {e}")
            return {"total": 0, "completed": 0}

    def delete_rehab_plan(self, plan_id: int) -> bool:
        try:
            if not self._ensure_connection():
                return False
            cursor = self.connection.cursor()
            # ON DELETE CASCADE will handle rehab_plan_tasks
            cursor.execute("DELETE FROM rehab_plans WHERE id = %s", (plan_id,))
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception as e:
            logger.error(f"删除康复计划失败: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    # ── rehab_metrics ──
    def save_rehab_metric(
        self, plan_id: int, username: str, metric_date: str,
        metric_type: str, metric_value: float, metric_unit: str = "", note: str = ""
    ):
        try:
            if not self._ensure_connection():
                return None
            cursor = self.connection.cursor()
            query = """
                INSERT INTO rehab_metrics (plan_id, username, metric_date, metric_type, metric_value, metric_unit, note)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE metric_value = VALUES(metric_value), metric_unit = VALUES(metric_unit), note = VALUES(note)
            """
            cursor.execute(query, (plan_id, username, metric_date, metric_type, metric_value, metric_unit, note))
            self.connection.commit()
            new_id = cursor.lastrowid
            cursor.close()
            return new_id
        except Exception as e:
            print(f"保存康复指标失败: {e}")
            if self.connection:
                self.connection.rollback()
            return None

    def get_rehab_metrics(
        self, plan_id: int, metric_type: str = None,
        date_from: str = None, date_to: str = None
    ):
        try:
            if not self._ensure_connection():
                return []
            cursor = self.connection.cursor(dictionary=True)
            conditions = ["plan_id = %s"]
            params = [plan_id]
            if metric_type:
                conditions.append("metric_type = %s")
                params.append(metric_type)
            if date_from:
                conditions.append("metric_date >= %s")
                params.append(date_from)
            if date_to:
                conditions.append("metric_date <= %s")
                params.append(date_to)
            where = " AND ".join(conditions)
            query = f"""
                SELECT id, plan_id, username, metric_date, metric_type,
                       metric_value, metric_unit, note, created_at
                FROM rehab_metrics WHERE {where}
                ORDER BY metric_date ASC, metric_type ASC
            """
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            print(f"获取康复指标失败: {e}")
            return []

    def get_latest_metrics(self, plan_id: int):
        try:
            if not self._ensure_connection():
                return {}
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT m.metric_type, m.metric_value, m.metric_unit, m.metric_date
                FROM rehab_metrics m
                INNER JOIN (
                    SELECT metric_type, MAX(metric_date) as max_date
                    FROM rehab_metrics WHERE plan_id = %s GROUP BY metric_type
                ) latest ON m.metric_type = latest.metric_type AND m.metric_date = latest.max_date
                WHERE m.plan_id = %s
            """
            cursor.execute(query, (plan_id, plan_id))
            results = cursor.fetchall()
            cursor.close()
            metrics = {}
            for r in results:
                metrics[r["metric_type"]] = {
                    "value": r["metric_value"],
                    "unit": r["metric_unit"],
                    "date": str(r["metric_date"])
                }
            return metrics
        except Exception as e:
            print(f"获取最新指标失败: {e}")
            return {}

    # ── rehab_exercises ──
    def get_rehab_exercises(
        self, phase: str = None, category: str = None,
        surgery_type: str = None, difficulty: str = None,
        search: str = None, limit: int = 50
    ):
        try:
            if not self._ensure_connection():
                return []
            cursor = self.connection.cursor(dictionary=True)
            conditions = []
            params = []
            if phase:
                conditions.append("phase_suitable = %s")
                params.append(phase)
            if category:
                conditions.append("category = %s")
                params.append(category)
            if difficulty:
                conditions.append("difficulty = %s")
                params.append(difficulty)
            if surgery_type:
                conditions.append("(surgery_type_tag = %s OR surgery_type_tag = '通用')")
                params.append(surgery_type)
            if search:
                conditions.append("(title LIKE %s OR description LIKE %s)")
                params.extend([f"%{search}%", f"%{search}%"])
            where = " AND ".join(conditions) if conditions else "1=1"
            query = f"""
                SELECT id, title, category, difficulty, target_body_part,
                       surgery_type_tag, video_url, thumbnail_url, image_urls,
                       description, steps, duration_minutes, repetitions,
                       precautions, phase_suitable
                FROM rehab_exercises WHERE {where}
                ORDER BY FIELD(phase_suitable, '急性期','恢复期','巩固期'), difficulty
                LIMIT %s
            """
            params.append(limit)
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            for r in results:
                if r.get("steps") and isinstance(r["steps"], str):
                    r["steps"] = __import__("json").loads(r["steps"])
                if r.get("image_urls") and isinstance(r["image_urls"], str):
                    r["image_urls"] = __import__("json").loads(r["image_urls"])
            return results
        except Exception as e:
            print(f"获取运动库失败: {e}")
            return []

    def get_rehab_exercise(self, exercise_id: int):
        try:
            if not self._ensure_connection():
                return None
            cursor = self.connection.cursor(dictionary=True)
            query = "SELECT * FROM rehab_exercises WHERE id = %s"
            cursor.execute(query, (exercise_id,))
            result = cursor.fetchone()
            cursor.close()
            if result:
                if result.get("steps") and isinstance(result["steps"], str):
                    result["steps"] = __import__("json").loads(result["steps"])
                if result.get("image_urls") and isinstance(result["image_urls"], str):
                    result["image_urls"] = __import__("json").loads(result["image_urls"])
            return result
        except Exception as e:
            print(f"获取运动详情失败: {e}")
            return None

    # ── rehab_journals ──
    def save_rehab_journal(self, plan_id: int, username: str, data: dict):
        try:
            if not self._ensure_connection():
                return None
            cursor = self.connection.cursor()
            photo_urls_json = __import__("json").dumps(data.get("photo_urls", []), ensure_ascii=False)
            query = """
                INSERT INTO rehab_journals
                (plan_id, username, journal_date, mood, pain_level, content,
                 photo_urls, voice_url, sleep_quality, appetite, energy_level, questions_for_doctor)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    mood = VALUES(mood), pain_level = VALUES(pain_level),
                    content = VALUES(content), photo_urls = VALUES(photo_urls),
                    voice_url = VALUES(voice_url), sleep_quality = VALUES(sleep_quality),
                    appetite = VALUES(appetite), energy_level = VALUES(energy_level),
                    questions_for_doctor = VALUES(questions_for_doctor)
            """
            cursor.execute(query, (
                plan_id, username, data.get("journal_date"),
                data.get("mood", "okay"), data.get("pain_level", 0),
                data.get("content", ""), photo_urls_json,
                data.get("voice_url", ""), data.get("sleep_quality", 3),
                data.get("appetite", 3), data.get("energy_level", 3),
                data.get("questions_for_doctor", "")
            ))
            self.connection.commit()
            new_id = cursor.lastrowid
            cursor.close()
            return new_id
        except Exception as e:
            print(f"保存康复日志失败: {e}")
            if self.connection:
                self.connection.rollback()
            return None

    def get_rehab_journals(self, plan_id: int, date_from: str = None, date_to: str = None):
        try:
            if not self._ensure_connection():
                return []
            cursor = self.connection.cursor(dictionary=True)
            conditions = ["plan_id = %s"]
            params = [plan_id]
            if date_from:
                conditions.append("journal_date >= %s")
                params.append(date_from)
            if date_to:
                conditions.append("journal_date <= %s")
                params.append(date_to)
            where = " AND ".join(conditions)
            query = f"SELECT * FROM rehab_journals WHERE {where} ORDER BY journal_date DESC"
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            for r in results:
                if r.get("photo_urls") and isinstance(r["photo_urls"], str):
                    r["photo_urls"] = __import__("json").loads(r["photo_urls"])
            return results
        except Exception as e:
            print(f"获取康复日志失败: {e}")
            return []

    def get_rehab_journal(self, journal_id: int):
        try:
            if not self._ensure_connection():
                return None
            cursor = self.connection.cursor(dictionary=True)
            query = "SELECT * FROM rehab_journals WHERE id = %s"
            cursor.execute(query, (journal_id,))
            result = cursor.fetchone()
            cursor.close()
            if result and result.get("photo_urls") and isinstance(result["photo_urls"], str):
                result["photo_urls"] = __import__("json").loads(result["photo_urls"])
            return result
        except Exception as e:
            print(f"获取日志详情失败: {e}")
            return None

    # ── achievements ──
    def get_all_achievement_defs(self):
        try:
            if not self._ensure_connection():
                return []
            cursor = self.connection.cursor(dictionary=True)
            query = "SELECT * FROM achievement_defs ORDER BY category, points"
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            for r in results:
                if r.get("condition_json") and isinstance(r["condition_json"], str):
                    r["condition_json"] = __import__("json").loads(r["condition_json"])
            return results
        except Exception as e:
            print(f"获取成就定义失败: {e}")
            return []

    def get_user_achievements(self, username: str, plan_id: int):
        try:
            if not self._ensure_connection():
                return []
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT ua.id as user_achievement_id, ua.earned_at,
                       ad.id, ad.code, ad.name, ad.description, ad.icon_url,
                       ad.category, ad.condition_json, ad.points
                FROM user_achievements ua
                JOIN achievement_defs ad ON ua.achievement_id = ad.id
                WHERE ua.username = %s AND ua.plan_id = %s
                ORDER BY ua.earned_at DESC
            """
            cursor.execute(query, (username, plan_id))
            results = cursor.fetchall()
            cursor.close()
            for r in results:
                if r.get("condition_json") and isinstance(r["condition_json"], str):
                    r["condition_json"] = __import__("json").loads(r["condition_json"])
            return results
        except Exception as e:
            print(f"获取用户成就失败: {e}")
            return []

    def award_achievement(self, username: str, plan_id: int, achievement_id: int):
        try:
            if not self._ensure_connection():
                return False
            cursor = self.connection.cursor()
            query = """
                INSERT IGNORE INTO user_achievements (username, plan_id, achievement_id)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (username, plan_id, achievement_id))
            self.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected > 0
        except Exception as e:
            print(f"授予成就失败: {e}")
            return False

    # ── 日历聚合 ──
    def get_rehab_calendar_data(self, plan_id: int, year: int, month: int):
        try:
            if not self._ensure_connection():
                return {}
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT task_date,
                       COUNT(*) as total,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                       SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped
                FROM rehab_plan_tasks
                WHERE plan_id = %s
                  AND YEAR(task_date) = %s AND MONTH(task_date) = %s
                GROUP BY task_date
                ORDER BY task_date
            """
            cursor.execute(query, (plan_id, year, month))
            results = cursor.fetchall()
            cursor.close()
            calendar = {}
            for r in results:
                calendar[str(r["task_date"])] = {
                    "total": r["total"],
                    "completed": r["completed"],
                    "skipped": r["skipped"]
                }
            return calendar
        except Exception as e:
            print(f"获取日历数据失败: {e}")
            return {}

    # ── 仪表盘聚合 ──
    def get_rehab_dashboard_stats(self, plan_id: int):
        try:
            if not self._ensure_connection():
                return {}
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_tasks
                FROM rehab_plan_tasks WHERE plan_id = %s
            """
            cursor.execute(query, (plan_id,))
            stats = cursor.fetchone()
            cursor.close()
            return stats or {"total_tasks": 0, "completed_tasks": 0, "pending_tasks": 0}
        except Exception as e:
            print(f"获取仪表盘统计失败: {e}")
            return {}

    # ── 更新计划统计（完成率、连续打卡） ──
    def update_rehab_plan_stats(self, plan_id: int):
        try:
            if not self._ensure_connection():
                return
            cursor = self.connection.cursor()
            query = """
                UPDATE rehab_plans p
                SET
                    total_completion_rate = (
                        SELECT ROUND(SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) * 100.0 / GREATEST(COUNT(*), 1), 2)
                        FROM rehab_plan_tasks WHERE plan_id = p.id
                    ),
                    last_checkin_date = (
                        SELECT MAX(task_date) FROM rehab_plan_tasks
                        WHERE plan_id = p.id AND status = 'completed'
                    )
                WHERE p.id = %s
            """
            cursor.execute(query, (plan_id,))
            self.connection.commit()
            cursor.close()
        except Exception as e:
            print(f"更新计划统计失败: {e}")

    # ── 临床指南检索 (RAG) ──
    def get_rehab_guidelines(
        self, surgery_type: str, phase: str = None, category: str = None
    ):
        """根据手术类型和阶段检索循证康复指南"""
        try:
            if not self._ensure_connection():
                return []
            cursor = self.connection.cursor(dictionary=True)
            conditions = ["(surgery_type = %s OR surgery_type = '通用')"]
            params = [surgery_type]
            if phase:
                conditions.append("(phase = %s OR phase = '通用')")
                params.append(phase)
            if category:
                conditions.append("category = %s")
                params.append(category)
            where = " AND ".join(conditions)
            query = f"""
                SELECT id, surgery_type, phase, category, title, content,
                       evidence_level, source
                FROM rehab_guidelines
                WHERE {where}
                ORDER BY FIELD(phase, %s, '通用') DESC, FIELD(surgery_type, %s, '通用') DESC
                LIMIT 15
            """
            params.extend([phase or '', surgery_type])
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            print(f"检索临床指南失败: {e}")
            return []