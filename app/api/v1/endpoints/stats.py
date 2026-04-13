from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from app.core.security import get_current_user
from app.db.session import db_instance
from datetime import datetime

router = APIRouter()

@router.get("/user/{username}")
async def get_user_stats(username: str, user: Dict = Depends(get_current_user)):
    """获取用户统计信息"""
    try:
        if user["username"] != username:
            raise HTTPException(status_code=403, detail="无权查看该用户的统计信息")

        sessions = db_instance.get_user_sessions(username)
        total_messages = 0

        for session in sessions:
            messages = db_instance.get_session_messages(session['session_id'], username)
            total_messages += len(messages)

        return {
            "success": True,
            "username": username,
            "session_count": len(sessions),
            "total_messages": total_messages,
            "last_active": sessions[0]['last_updated'] if sessions else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")

@router.get("/system")
async def get_system_stats(user: Dict = Depends(get_current_user)):
    """获取系统统计信息（仅管理员）"""
    try:
        # 检查是否为管理员
        cursor = db_instance.connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT is_admin FROM users WHERE username = %s",
            (user["username"],)
        )
        user_info = cursor.fetchone()
        cursor.close()

        if not user_info or user_info['is_admin'] != 1:
            raise HTTPException(status_code=403, detail="需要管理员权限")

        stats = {
            "total_users": 0,
            "total_sessions": 0,
            "total_messages": 0,
            "active_today": 0
        }

        try:
            cursor = db_instance.connection.cursor(dictionary=True)
            cursor.execute("SELECT COUNT(*) as count FROM users")
            stats["total_users"] = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM chat_sessions")
            stats["total_sessions"] = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM user_conversations")
            stats["total_messages"] = cursor.fetchone()['count']
            cursor.execute("""
                           SELECT COUNT(DISTINCT username) as count
                           FROM chat_sessions
                           WHERE DATE(last_updated) = CURDATE()
                           """)
            stats["active_today"] = cursor.fetchone()['count']
            cursor.close()
        except Exception as e:
            print(f"获取数据库统计失败: {e}")

        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统统计失败: {str(e)}")
