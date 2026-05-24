import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File
from typing import Dict
from app.core.security import get_current_user

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'static', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_IMAGE = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_VOICE = {'.webm', '.mp3', '.wav', '.ogg', '.m4a'}


@router.post("/image")
async def upload_image(file: UploadFile = File(...), user: Dict = Depends(get_current_user)):
    ext = os.path.splitext(file.filename or '.jpg')[1].lower()
    if ext not in ALLOWED_IMAGE:
        return {"success": False, "message": "不支持的图片格式"}
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    content = await file.read()
    with open(filepath, 'wb') as f:
        f.write(content)
    url = f"/static/uploads/{filename}"
    return {"success": True, "url": url}


@router.post("/voice")
async def upload_voice(file: UploadFile = File(...), user: Dict = Depends(get_current_user)):
    ext = os.path.splitext(file.filename or '.webm')[1].lower()
    if ext not in ALLOWED_VOICE:
        return {"success": False, "message": "不支持的音频格式"}
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    content = await file.read()
    with open(filepath, 'wb') as f:
        f.write(content)
    url = f"/static/uploads/{filename}"
    return {"success": True, "url": url}
