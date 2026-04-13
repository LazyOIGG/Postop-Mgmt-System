from fastapi import APIRouter
from app.api.v1.endpoints import auth, chat, sessions, kg, stats, tools, multimodal

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["用户认证"])
api_router.include_router(chat.router, prefix="/chat", tags=["聊天问答"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["会话管理"])
api_router.include_router(kg.router, prefix="/kg", tags=["知识图谱"])
api_router.include_router(stats.router, prefix="/stats", tags=["统计信息"])
api_router.include_router(tools.router, prefix="/tools", tags=["辅助工具"])
api_router.include_router(multimodal.router, prefix="/multimodal", tags=["多模态功能"])
