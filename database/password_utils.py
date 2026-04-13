import hashlib
import re

def encrypt_password(password: str) -> str:
    """密码加密（使用SHA-256加盐）"""
    salt = "medical_qa_system_salt_2024"
    combined = (password + salt).encode('utf-8')
    return hashlib.sha256(combined).hexdigest()

def verify_password(input_password: str, stored_hash: str) -> bool:
    """验证密码"""
    return encrypt_password(input_password) == stored_hash

def verify_password_strength(password: str):
    """验证密码强度：至少8位，包含大小写字母、数字和特殊字符"""
    if len(password) < 8:
        return False, "密码长度至少8位"
    if not re.search(r'[A-Z]', password):
        return False, "密码需包含大写字母"
    if not re.search(r'[a-z]', password):
        return False, "密码需包含小写字母"
    if not re.search(r'[0-9]', password):
        return False, "密码需包含数字"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "密码需包含特殊字符"
    return True, "密码强度符合要求"