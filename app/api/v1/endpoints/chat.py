from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from app.models.schemas import ChatRequest
from app.core.security import get_current_user, validate_token
from app.services.llm_service import llm_service
from app.services.ner_service import ner_service
from app.services.intent_service import intent_service
from app.services.kg_service import kg_service
from app.db.session import db_instance
from app.agents.orchestrator import orchestrator
from datetime import datetime
import json
import re

router = APIRouter()

class ConnectionManager:
    """WebSocket 连接管理"""
    def __init__(self):
        self.active_connections = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

manager = ConnectionManager()

async def _get_chat_response(query: str, model_choice: str = None) -> dict:
    """内部处理聊天消息逻辑"""
    entities = ner_service.recognize(query)
    intent_res = await intent_service.recognize(query, model_choice)
    prompt, yitu, entities, _ = kg_service.generate_enhanced_prompt(intent_res, query, entities)
    
    full_response = ""
    async for chunk in llm_service.chat(prompt, model_choice, stream=True):
        full_response += chunk
        
    knowledge = "\n".join([f"提示{i+1}: {k}" for i, k in enumerate(re.findall(r'<提示>(.*?)</提示>', prompt)) if len(k) >= 3])

    return {
        "content": full_response, "entities": str(entities),
        "intents": yitu, "knowledge": knowledge, "prompt": prompt
    }

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
            async for line in orchestrator.process_stream(request.message, username):
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

    result = await orchestrator.process(request.message, username)
    db_instance.save_message(
        session_id, username, "assistant",
        result["content"],
        str(result.get("metadata", {}).get("entities", "")),
        str(result.get("metadata", {}).get("intents", "")),
        str(result.get("metadata", {}).get("knowledge", ""))
    )
    return {"success": True, **result, "session_id": session_id}

@router.post("/agent")
async def agent_chat_endpoint(request: ChatRequest, user: dict = Depends(get_current_user)):
    """多智能体聊天（非流式）"""
    username = user["username"]
    session_id = request.session_id or db_instance.create_session(username, request.message[:30] + "...")
    if not session_id:
        raise HTTPException(status_code=500, detail="会话初始化失败")

    db_instance.save_message(session_id, username, "user", request.message)

    if request.stream:
        async def generate():
            yield json.dumps({"type": "start", "session_id": session_id}) + "\n"
            full_res = ""
            async for line in orchestrator.process_stream(request.message, username):
                yield line
                try:
                    data = json.loads(line)
                    if data.get("type") == "chunk":
                        full_res += data.get("content", "")
                except json.JSONDecodeError:
                    pass
            yield json.dumps({"type": "done"}) + "\n"
            db_instance.save_message(session_id, username, "assistant", full_res)
        return StreamingResponse(generate(), media_type="text/event-stream")

    result = await orchestrator.process(request.message, username)
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
    await manager.connect(websocket)
    try:
        user = validate_token(token) if token else None
        if not user:
            await websocket.send_text(json.dumps({"type": "error", "message": "未授权"})); await websocket.close(); return

        print(f"[INFO] ℹ️ 多智能体 WebSocket 用户 {user['username']} 已连接")
        while True:
            data = json.loads(await websocket.receive_text())
            if data.get("type") == "chat":
                query = data.get("message", "")
                if not query: continue
                async for line in orchestrator.process_stream(query, user["username"]):
                    await websocket.send_text(line.strip())
                await websocket.send_text(json.dumps({"type": "done"}))
    except WebSocketDisconnect: manager.disconnect(websocket)
    except Exception as e:
        print(f"[ERROR] ❌ 多智能体 WebSocket 异常: {e}")
        manager.disconnect(websocket)

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket, token: str = None):
    """WebSocket 实时聊天"""
    await manager.connect(websocket)
    try:
        user = validate_token(token) if token else None
        if not user:
            await websocket.send_text(json.dumps({"type": "error", "message": "未授权"})); await websocket.close(); return
        
        print(f"[INFO] ℹ️ WebSocket 用户 {user['username']} 已连接")
        while True:
            data = json.loads(await websocket.receive_text())
            if data.get("type") == "chat":
                query = data.get("message", "")
                if not query: continue
                res = await _get_chat_response(query, data.get("model_choice"))
                await websocket.send_text(json.dumps({"type": "response", **res}))
    except WebSocketDisconnect: manager.disconnect(websocket)
    except Exception as e:
        print(f"[ERROR] ❌ WebSocket 异常: {e}")
        manager.disconnect(websocket)
