import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Set, Tuple

import jwt
from fastapi import Depends, Header, HTTPException

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── 内存回退存储 ──────────────────────────────────────────────────
# 当 REDIS_URL 未配置时使用；Redis 可用时优先 Redis

_token_blacklist: Set[Tuple[str, datetime]] = set()  # (jti, expiry)
_refresh_tokens: Set[Tuple[str, datetime]] = set()  # (jti, expiry)

ALGORITHM = "HS256"


def _generate_jti() -> str:
    return uuid.uuid4().hex


def _find_entry(entries: Set[Tuple[str, datetime]], jti: str) -> Optional[Tuple[str, datetime]]:
    """通过 jti 查找集合中的条目"""
    for entry in entries:
        if entry[0] == jti:
            return entry
    return None


# ── Redis helpers ─────────────────────────────────────────────────

async def _get_redis():
    """懒加载 Redis 客户端，返回 None 表示 Redis 不可用"""
    from app.db.session import get_redis
    return await get_redis()


def _ttl_seconds(exp: datetime) -> int:
    """计算从当前时间到过期时间的剩余秒数"""
    return max(1, int((exp - datetime.now(timezone.utc)).total_seconds()))


def _unix_to_datetime(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


# ── Token generation ──────────────────────────────────────────────

def generate_token(username: str, is_admin: bool = False) -> tuple:
    """生成 JWT access_token 和 refresh_token，返回 (access_token, refresh_token)"""
    now = datetime.now(timezone.utc)

    # Access token
    access_jti = _generate_jti()
    access_exp = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_payload = {
        "sub": username,
        "is_admin": is_admin,
        "type": "access",
        "exp": access_exp,
        "iat": now,
        "jti": access_jti,
    }
    access_token = jwt.encode(access_payload, settings.SECRET_KEY, algorithm=ALGORITHM)

    # Refresh token
    refresh_jti = _generate_jti()
    refresh_exp = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_payload = {
        "sub": username,
        "type": "refresh",
        "exp": refresh_exp,
        "iat": now,
        "jti": refresh_jti,
    }
    refresh_token = jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm=ALGORITHM)

    # Store refresh token — try Redis first, fall back to memory
    _refresh_tokens.add((refresh_jti, refresh_exp))

    # Fire-and-forget: also store in Redis if available
    async def _store_in_redis():
        redis = await _get_redis()
        if redis:
            await redis.setex(
                f"refresh:{refresh_jti}",
                settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
                username,
            )
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_store_in_redis())
        else:
            loop.run_until_complete(_store_in_redis())
    except RuntimeError:
        pass

    return access_token, refresh_token


# ── Token validation ──────────────────────────────────────────────

def validate_token(token: str) -> Optional[Dict]:
    """验证 JWT access_token，返回 {"username", "is_admin"} 或 None"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        jti = payload.get("jti")
        if jti and _find_entry(_token_blacklist, jti):
            return None
        return {"username": payload["sub"], "is_admin": payload.get("is_admin", False)}
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


async def validate_token_async(token: str) -> Optional[Dict]:
    """验证 access_token（检查 Redis 黑名单）"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None

        jti = payload.get("jti")
        if jti:
            # Check Redis blacklist first
            redis = await _get_redis()
            if redis and await redis.exists(f"blacklist:{jti}"):
                return None
            # Fallback: memory blacklist
            if _find_entry(_token_blacklist, jti):
                return None

        return {"username": payload["sub"], "is_admin": payload.get("is_admin", False)}
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def validate_refresh_token(token: str) -> Optional[str]:
    """验证 refresh_token，返回 username 或 None"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        jti = payload.get("jti")
        if not jti or not _find_entry(_refresh_tokens, jti):
            return None
        return payload["sub"]
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


async def validate_refresh_token_async(token: str) -> Optional[str]:
    """验证 refresh_token（检查 Redis）"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None

        jti = payload.get("jti")
        if not jti:
            return None

        # Check Redis first
        redis = await _get_redis()
        if redis:
            stored_username = await redis.get(f"refresh:{jti}")
            if stored_username:
                return stored_username

        # Fallback: memory
        if _find_entry(_refresh_tokens, jti):
            return payload["sub"]

        return None
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ── Token invalidation ────────────────────────────────────────────

def invalidate_token(token: str) -> None:
    """将 access_token 加入黑名单"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        if jti:
            _token_blacklist.add((jti, exp))

            # Fire-and-forget: also add to Redis
            async def _add_to_redis():
                redis = await _get_redis()
                if redis:
                    ttl = _ttl_seconds(exp)
                    await redis.setex(f"blacklist:{jti}", ttl, "1")
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(_add_to_redis())
                else:
                    loop.run_until_complete(_add_to_redis())
            except RuntimeError:
                pass
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        pass


def invalidate_refresh_token(token: str) -> None:
    """从 refresh token 集合中移除"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        if jti:
            entry = _find_entry(_refresh_tokens, jti)
            if entry:
                _refresh_tokens.discard(entry)

            # Fire-and-forget: also remove from Redis
            async def _remove_from_redis():
                redis = await _get_redis()
                if redis:
                    await redis.delete(f"refresh:{jti}")
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(_remove_from_redis())
                else:
                    loop.run_until_complete(_remove_from_redis())
            except RuntimeError:
                pass
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        pass


# ── FastAPI dependencies ──────────────────────────────────────────

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict:
    """FastAPI 依赖注入：获取当前用户"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权访问")
    token = authorization.replace("Bearer ", "")
    user_data = validate_token(token)
    if not user_data:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
    return user_data


def require_admin(user: Dict = Depends(get_current_user)) -> Dict:
    """FastAPI 依赖注入：要求管理员权限"""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


# ── Cleanup ───────────────────────────────────────────────────────

async def _cleanup_expired_data():
    """定期清理过期的黑名单和 refresh token（内存回退）"""
    while True:
        await asyncio.sleep(300)
        now = datetime.now(timezone.utc)
        expired_blacklist = {entry for entry in _token_blacklist if entry[1] < now}
        expired_refresh = {entry for entry in _refresh_tokens if entry[1] < now}
        _token_blacklist -= expired_blacklist
        _refresh_tokens -= expired_refresh

        # 同时清理 Redis 过期 key（Redis TTL 会自动过期，这里只是兜底）
        redis = await _get_redis()
        if redis:
            # Redis TTL 机制已自动处理，无需额外清理
            pass

        if expired_blacklist or expired_refresh:
            logger.info("cleanup_complete",
                        expired_blacklist=len(expired_blacklist),
                        expired_refresh=len(expired_refresh))
