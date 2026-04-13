import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import Header, HTTPException
from app.core.config import settings

# 内存令牌存储 (生产环境建议使用 Redis)
user_tokens: Dict[str, Dict] = {}

def generate_token(username: str) -> str:
    """生成用户访问令牌"""
    token = secrets.token_urlsafe(32)
    user_tokens[token] = {
        "username": username,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return token

def validate_token(token: str) -> Optional[Dict]:
    """验证令牌有效性"""
    if token not in user_tokens:
        return None
    user_data = user_tokens[token]
    if datetime.now() > user_data["expires_at"]:
        del user_tokens[token]
        return None
    return user_data

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict:
    """FastAPI 依赖注入：获取当前用户"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权访问")
    token = authorization.replace("Bearer ", "")
    user_data = validate_token(token)
    if not user_data:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
    return user_data
