from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict
from app.models.schemas import SessionCreateRequest, SessionUpdateRequest
from app.core.security import get_current_user
from app.db.session import db_instance

router = APIRouter()

@router.post("/create")
async def create_session(request: SessionCreateRequest, user: Dict = Depends(get_current_user)):
    """创建新的聊天会话"""
    try:
        if user["username"] != request.username:
            raise HTTPException(status_code=403, detail="无权为该用户创建会话")

        session_id = db_instance.create_session(request.username, request.session_title)
        if not session_id:
            raise HTTPException(status_code=500, detail="创建会话失败")

        return {
            "success": True,
            "session_id": session_id,
            "session_title": request.session_title,
            "message": "会话创建成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")

@router.get("/user/{username}")
async def get_user_sessions(username: str, user: Dict = Depends(get_current_user)):
    """获取用户的所有会话"""
    try:
        if user["username"] != username:
            raise HTTPException(status_code=403, detail="无权查看该用户的会话")

        sessions = db_instance.get_user_sessions(username)
        return {
            "success": True,
            "sessions": sessions,
            "count": len(sessions)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")

@router.get("/{session_id}/messages")
async def get_session_messages(session_id: int, username: Optional[str] = None,
                               user: Dict = Depends(get_current_user)):
    """获取会话的所有消息"""
    try:
        if username and user["username"] != username:
            raise HTTPException(status_code=403, detail="无权查看该会话")

        messages = db_instance.get_session_messages(session_id, username)
        return {
            "success": True,
            "messages": messages,
            "count": len(messages)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取消息失败: {str(e)}")

@router.put("/rename")
async def rename_session(request: SessionUpdateRequest, user: Dict = Depends(get_current_user)):
    """重命名会话"""
    try:
        # 验证用户对会话的权限
        session_info = db_instance.get_session_info(request.session_id)
        if not session_info or session_info['username'] != user["username"]:
            raise HTTPException(status_code=403, detail="无权修改此会话")

        success = db_instance.update_session_title(request.session_id, request.new_title)
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在或重命名失败")

        return {
            "success": True,
            "message": "会话重命名成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重命名失败: {str(e)}")

@router.delete("/{session_id}")
async def delete_session(session_id: int, username: Optional[str] = None,
                         user: Dict = Depends(get_current_user)):
    """删除会话"""
    try:
        if username and user["username"] != username:
            raise HTTPException(status_code=403, detail="无权删除该会话")

        success = db_instance.delete_session(session_id, username)
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在或删除失败")

        return {
            "success": True,
            "message": "会话删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
