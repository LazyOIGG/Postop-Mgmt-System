from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from typing import Dict, Optional
import json
import logging

from app.models.schemas import ChatRequest
from app.core.security import get_current_user, validate_token
from app.core.ws_manager import ws_manager, WSMessageType
from app.db.session import db_instance
from app.agents.orchestrator import orchestrator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("")
async def chat_endpoint(request: ChatRequest, user: dict = Depends(get_current_user)):
    """处理聊天问答 — 多智能体编排"""
    username = user["username"]
    session_id = request.session_id or db_instance.create_session(username, request.message[:30] + "...")
    if not session_id:
        raise HTTPException(status_code=500, detail="会话初始化失败")
    db_instance.save_message(session_id, username, "user", request.message)

    if request.stream:
        async def generate():
            yield json.dumps({"type": "start", "session_id": session_id}) + "\n"
            full_res = ""
            async for line in orchestrator.process_stream(request.message, username, session_id=session_id):
                yield line
                try:
                    data = json.loads(line)
                    if data.get("type") == "chunk":
                        full_res += data.get("content", "")
                except json.JSONDecodeError:
                    pass
            yield json.dumps({"type": "complete"}) + "\n"
            db_instance.save_message(session_id, username, "assistant", full_res)
        return StreamingResponse(generate(), media_type="text/event-stream")

    result = await orchestrator.process(request.message, username, session_id=session_id)
    db_instance.save_message(
        session_id, username, "assistant",
        result["content"],
        str(result.get("metadata", {}).get("entities", "")),
        str(result.get("metadata", {}).get("intents", "")),
        str(result.get("metadata", {}).get("knowledge", ""))
    )
    return {"success": True, **result, "session_id": session_id}


@router.websocket("/agent/ws")
async def agent_websocket_chat(websocket: WebSocket, token: str = None):
    """多智能体 WebSocket 实时聊天"""
    if not token:
        await websocket.close(code=4001)
        return
    user = validate_token(token)
    if not user:
        await websocket.close(code=4001)
        return

    username = user["username"]
    await ws_manager.connect(username, websocket)
    logger.info("agent_websocket_connected", username=username)

    session_id = None
    try:
        while True:
            data = json.loads(await websocket.receive_text())

            # 处理心跳响应
            if data.get("type") == WSMessageType.PONG:
                continue

            if data.get("type") == "chat":
                query = data.get("message", "")
                if not query:
                    continue
                ws_session_id = data.get("session_id") or session_id
                if not ws_session_id:
                    ws_session_id = db_instance.create_session(username, query[:30] + "...")
                session_id = ws_session_id
                db_instance.save_message(session_id, username, "user", query)
                full_res = ""
                async for line in orchestrator.process_stream(query, username, session_id=session_id):
                    await websocket.send_text(line.strip())
                    try:
                        d = json.loads(line)
                        if d.get("type") == "chunk":
                            full_res += d.get("content", "")
                    except json.JSONDecodeError:
                        pass
                db_instance.save_message(session_id, username, "assistant", full_res)
                await websocket.send_text(json.dumps({"type": "done", "session_id": session_id}))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("agent_websocket_error", username=username, error=str(e))
    finally:
        ws_manager.disconnect(username, websocket)


@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket, token: str = None):
    """WebSocket 实时聊天 — 多智能体编排"""
    if not token:
        await websocket.close(code=4001)
        return
    user = validate_token(token)
    if not user:
        await websocket.close(code=4001)
        return

    username = user["username"]
    await ws_manager.connect(username, websocket)
    logger.info("websocket_chat_connected", username=username)

    session_id = None
    try:
        while True:
            data = json.loads(await websocket.receive_text())

            if data.get("type") == WSMessageType.PONG:
                continue

            if data.get("type") == "chat":
                query = data.get("message", "")
                if not query:
                    continue
                ws_session_id = data.get("session_id") or session_id
                if not ws_session_id:
                    ws_session_id = db_instance.create_session(username, query[:30] + "...")
                session_id = ws_session_id
                db_instance.save_message(session_id, username, "user", query)
                full_res = ""
                async for line in orchestrator.process_stream(query, username, session_id=session_id):
                    await websocket.send_text(line.strip())
                    try:
                        d = json.loads(line)
                        if d.get("type") == "chunk":
                            full_res += d.get("content", "")
                    except json.JSONDecodeError:
                        pass
                db_instance.save_message(session_id, username, "assistant", full_res)
                await websocket.send_text(json.dumps({"type": "done", "session_id": session_id}))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("websocket_chat_error", username=username, error=str(e))
    finally:
        ws_manager.disconnect(username, websocket)


@router.websocket("/notifications/ws")
async def notification_websocket(websocket: WebSocket, token: str = None):
    """WebSocket 通知推送"""
    if not token:
        await websocket.close(code=4001)
        return
    user = validate_token(token)
    if not user:
        await websocket.close(code=4001)
        return

    username = user["username"]
    await ws_manager.connect(username, websocket)
    logger.info("notification_websocket_connected", username=username)

    try:
        while True:
            data = await websocket.receive_text()
            if data and json.loads(data).get("type") == WSMessageType.PONG:
                continue
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("notification_websocket_error", username=username, error=str(e))
    finally:
        ws_manager.disconnect(username, websocket)
