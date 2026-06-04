from typing import Optional

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


# ── Redis 连接池 ──────────────────────────────────────────────────

_redis_pool = None
_redis_client: Optional["redis.asyncio.Redis"] = None  # type: ignore[name-defined]


async def get_redis() -> Optional["redis.asyncio.Redis"]:  # type: ignore[name-defined]
    """惰性初始化 Redis 连接（单例 + 连接池）。

    当 REDIS_URL 未配置时返回 None，调用方需回退到内存存储。
    """
    global _redis_pool, _redis_client
    if not settings.REDIS_URL:
        return None
    if _redis_client is None:
        try:
            import redis.asyncio as aioredis
            _redis_pool = aioredis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=10,
                decode_responses=True,
            )
            _redis_client = aioredis.Redis(connection_pool=_redis_pool)
        except Exception:
            return None
    return _redis_client


async def close_redis():
    """关闭 Redis 连接池"""
    global _redis_pool, _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        _redis_pool = None
