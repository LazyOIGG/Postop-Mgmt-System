import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Set, Tuple

import jwt
from fastapi import Header, HTTPException

from app.core.config import settings

# In-memory stores for token management
_token_blacklist: Set[Tuple[str, datetime]] = set()  # (jti, expiry)
_refresh_tokens: Set[Tuple[str, datetime]] = set()  # (jti, expiry)


def _find_entry(entries: Set[Tuple[str, datetime]], jti: str) -> Optional[Tuple[str, datetime]]:
    """通过 jti 查找集合中的条目"""
    for entry in entries:
        if entry[0] == jti:
            return entry
    return None

ALGORITHM = "HS256"


def _generate_jti() -> str:
    return uuid.uuid4().hex


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
    _refresh_tokens.add((refresh_jti, refresh_exp))

    return access_token, refresh_token


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


def invalidate_token(token: str) -> None:
    """将 access_token 加入黑名单"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        if jti:
            _token_blacklist.add((jti, exp))
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
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        pass


def get_current_user(authorization: Optional[str] = Header(None)) -> Dict:
    """FastAPI 依赖注入：获取当前用户"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权访问")
    token = authorization.replace("Bearer ", "")
    user_data = validate_token(token)
    if not user_data:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
    return user_data


async def _cleanup_expired_data():
    """定期清理过期的黑名单和 refresh token"""
    while True:
        await asyncio.sleep(300)
        now = datetime.now(timezone.utc)
        expired_blacklist = {entry for entry in _token_blacklist if entry[1] < now}
        expired_refresh = {entry for entry in _refresh_tokens if entry[1] < now}
        _token_blacklist -= expired_blacklist
        _refresh_tokens -= expired_refresh
        if expired_blacklist or expired_refresh:
            print(f"[INFO] 已清理 {len(expired_blacklist)} 个过期黑名单令牌, {len(expired_refresh)} 个过期刷新令牌")
