from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import LoginRequest, RegisterRequest
from app.core.security import generate_token
from app.db.session import db_instance
from database.password_utils import encrypt_password, verify_password, verify_password_strength

router = APIRouter()

@router.post("/login")
async def login(request: LoginRequest):
    """用户登录"""
    try:
        if not db_instance.connect():
            print("[ERROR] 登录失败: 数据库连接失败")
            raise HTTPException(status_code=500, detail="数据库连接失败")

        cursor = db_instance.connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT username, password, is_admin FROM users WHERE username = %s", (request.username,))
            user = cursor.fetchone()
        finally:
            cursor.close()

        if not user or not verify_password(request.password, user['password']):
            print(f"[WARN] 登录失败: 用户 {request.username} 凭据无效")
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        token = generate_token(user['username'])
        print(f"[SUCCESS] 用户 {request.username} 登录成功")
        return {
            "success": True, "username": user['username'],
            "is_admin": user['is_admin'] == 1, "token": token, "message": "登录成功"
        }
    except HTTPException: raise
    except Exception as e:
        print(f"[ERROR] 登录异常: {str(e)}")
        raise HTTPException(status_code=500, detail="登录失败")

@router.post("/register")
async def register(request: RegisterRequest):
    """用户注册"""
    try:
        if request.password != request.confirm_password:
            raise HTTPException(status_code=400, detail="两次输入密码不一致")

        strength_ok, strength_msg = verify_password_strength(request.password)
        if not strength_ok:
            print(f"[WARN] 注册失败: 密码强度不足 - {strength_msg}")
            raise HTTPException(status_code=400, detail=f"密码强度不足: {strength_msg}")

        if not db_instance.connect():
            raise HTTPException(status_code=500, detail="数据库连接失败")

        if db_instance.check_user_exists(request.username):
            print(f"[WARN] 注册失败: 用户名 {request.username} 已存在")
            raise HTTPException(status_code=400, detail="用户名已存在")

        encrypted_pwd = encrypt_password(request.password)
        cursor = db_instance.connection.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, is_admin) VALUES (%s, %s, 0)", (request.username, encrypted_pwd))
            db_instance.connection.commit()
        finally:
            cursor.close()

        print(f"[SUCCESS] 用户 {request.username} 注册成功")
        return {"success": True, "message": "注册成功"}
    except HTTPException: raise
    except Exception as e:
        if db_instance.connection: db_instance.connection.rollback()
        print(f"[ERROR] 注册异常: {str(e)}")
        raise HTTPException(status_code=500, detail="注册失败")
