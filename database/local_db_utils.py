import mysql.connector
from mysql.connector import Error, pooling
import time
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import json

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
            print(f"保存病例OCR失败: {e}")
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
            print(f"保存健康评估记录失败: {e}")
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
            print(f"查询健康评估历史失败: {e}")
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
            print(f"保存健康档案失败: {e}")
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
            print(f"查询健康档案失败: {e}")
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
            print(f"查询最近一次健康评估失败: {e}")
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
            print(f"保存每日打卡失败: {e}")
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
            print(f"获取每日打卡记录失败: {e}")
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
            print(f"获取今日打卡失败: {e}")
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
            print(f"获取趋势分析打卡数据失败: {e}")
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
            print(f"获取打卡汇总统计失败: {e}")
            return None
