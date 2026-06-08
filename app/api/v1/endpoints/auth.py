from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from app.core.logging import get_logger
from app.core.response import ApiResponse
from app.core.security import (
    generate_token,
    get_current_user,
    invalidate_refresh_token,
    invalidate_token,
    validate_refresh_token,
)
from app.db.session import db_instance
from app.models.schemas import LoginRequest, LogoutRequest, RefreshRequest, RegisterRequest
from database.password_utils import encrypt_password, verify_password, verify_password_strength

logger = get_logger(__name__)

router = APIRouter()


@router.post("/login")
async def login(request: LoginRequest):
    """用户登录"""
    try:
        if not db_instance.connect():
            logger.error("login_failed reason=%s", "数据库连接失败")
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = db_instance.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT username, password, is_admin FROM users WHERE username = %s",
                (request.username,),
            )
            user = cursor.fetchone()
        finally:
            cursor.close()

        if not user or not verify_password(request.password, user["password"]):
            logger.warning("login_failed username=%s reason=%s", request.username, "凭据无效")
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        access_token, refresh_token = generate_token(
            user["username"], user.get("is_admin", 0) == 1
        )
        logger.info("login_success username=%s", request.username)
        return ApiResponse.ok(
            data={
                "username": user["username"],
                "is_admin": user["is_admin"] == 1,
                "token": access_token,
                "refresh_token": refresh_token,
            },
            message="登录成功",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("login_exception error=%s", str(e))
        raise HTTPException(status_code=500, detail="登录失败")


@router.post("/register")
async def register(request: RegisterRequest):
    """用户注册"""
    try:
        if request.password != request.confirm_password:
            raise HTTPException(status_code=400, detail="两次输入密码不一致")

        strength_ok, strength_msg = verify_password_strength(request.password)
        if not strength_ok:
            logger.warning("register_failed reason=%s", f"密码强度不足 - {strength_msg}")
            raise HTTPException(status_code=400, detail=f"密码强度不足: {strength_msg}")

        if not db_instance.connect():
            raise HTTPException(status_code=500, detail="数据库连接失败")

        if db_instance.check_user_exists(request.username):
            logger.warning("register_failed username=%s reason=%s", request.username, "用户名已存在")
            raise HTTPException(status_code=400, detail="用户名已存在")

        encrypted_pwd = encrypt_password(request.password)
        cursor = db_instance.connection.cursor()
        try:
            is_admin_val = 1 if request.is_admin else 0
            cursor.execute(
                "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)",
                (request.username, encrypted_pwd, is_admin_val),
            )
            db_instance.connection.commit()
        finally:
            cursor.close()

        # Auto-login after registration
        access_token, refresh_token = generate_token(request.username, request.is_admin)
        logger.info("register_success username=%s", request.username)
        return ApiResponse.ok(
            data={
                "username": request.username,
                "is_admin": request.is_admin,
                "token": access_token,
                "refresh_token": refresh_token,
            },
            message="注册成功",
        )
    except HTTPException:
        raise
    except Exception as e:
        if db_instance.connection:
            db_instance.connection.rollback()
        logger.error("register_exception error=%s", str(e))
        raise HTTPException(status_code=500, detail="注册失败")


@router.post("/refresh")
async def refresh_token(request: RefreshRequest):
    """刷新 access_token"""
    username = validate_refresh_token(request.refresh_token)
    if not username:
        raise HTTPException(status_code=401, detail="刷新令牌无效或已过期")

    # Rotate: invalidate old refresh token
    invalidate_refresh_token(request.refresh_token)

    # Query is_admin from DB
    is_admin = False
    if db_instance.connect():
        cursor = db_instance.connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT is_admin FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            if user:
                is_admin = user.get("is_admin", 0) == 1
        finally:
            cursor.close()

    access_token, refresh_token = generate_token(username, is_admin)
    return ApiResponse.ok(
        data={"token": access_token, "refresh_token": refresh_token},
        message="令牌刷新成功",
    )


@router.post("/logout")
async def logout(
    request: LogoutRequest,
    user: dict = Depends(get_current_user),
    authorization: Optional[str] = Header(None),
):
    """用户登出"""
    # Invalidate access token
    if authorization and authorization.startswith("Bearer "):
        invalidate_token(authorization.replace("Bearer ", ""))

    # Invalidate refresh token if provided
    if request.refresh_token:
        invalidate_refresh_token(request.refresh_token)

    logger.info("user_logout username=%s", user['username'])
    return ApiResponse.ok(message="已退出登录")


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return ApiResponse.ok(data={"username": user["username"], "is_admin": user["is_admin"]})
