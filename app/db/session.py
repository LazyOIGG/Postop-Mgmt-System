from database.local_db_utils import DatabaseConnector
from app.core.config import settings

def get_db():
    """获取数据库连接 (用于依赖注入)"""
    db = DatabaseConnector(
        host=settings.MYSQL_HOST,
        database=settings.MYSQL_DATABASE,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD
    )
    try:
        if db.connect():
            yield db
    finally:
        db.close()

# 全局数据库单例
db_instance = DatabaseConnector(
    host=settings.MYSQL_HOST,
    database=settings.MYSQL_DATABASE,
    user=settings.MYSQL_USER,
    password=settings.MYSQL_PASSWORD
)
