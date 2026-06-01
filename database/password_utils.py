import hashlib
import secrets
import re


def _generate_salt() -> str:
    return secrets.token_hex(16)


def encrypt_password(password: str) -> str:
    salt = _generate_salt()
    combined = (password + salt).encode('utf-8')
    hashed = hashlib.sha256(combined).hexdigest()
    return f"1${salt}${hashed}"


def verify_password(input_password: str, stored_value: str) -> bool:
    if not stored_value:
        return False
    if "$" not in stored_value:
        salt = "medical_qa_system_salt_2024"
        combined = (input_password + salt).encode('utf-8')
        return hashlib.sha256(combined).hexdigest() == stored_value
    parts = stored_value.split("$")
    if len(parts) != 3:
        return False
    _, salt, old_hash = parts
    combined = (input_password + salt).encode('utf-8')
    return hashlib.sha256(combined).hexdigest() == old_hash


def verify_password_strength(password: str):
    """验证密码强度：至少6位，必须包含小写字母和数字"""
    if len(password) < 6:
        return False, "密码长度至少6位"
    if not re.search(r'[a-z]', password):
        return False, "密码需包含小写字母"
    if not re.search(r'[0-9]', password):
        return False, "密码需包含数字"
    return True, "密码强度符合要求"
