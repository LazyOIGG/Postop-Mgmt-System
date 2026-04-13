from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.api import api_router
from app.core.config import settings
from app.db.session import db_instance
from app.services.ner_service import ner_service
from app.services.kg_service import kg_service
from datetime import datetime

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="模块化设计的术后管理系统，集成知识图谱与 DeepSeek 大模型",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含 API 路由
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "message": "术后管理系统 API 服务运行中 (Modular Version)",
        "version": settings.VERSION,
        "status": "healthy",
        "api_docs": "/docs"
    }

@app.get("/health")
async def health_check():
    db_status = "connected" if db_instance.connection and db_instance.connection.is_connected() else "disconnected"
    neo4j_status = "connected" if kg_service.client else "disconnected"
    
    return {
        "status": "healthy",
        "service": "postop-mgmt-api",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "neo4j": neo4j_status
    }

@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print(f"{settings.PROJECT_NAME} 启动中...")
    
    # 尝试连接数据库
    if db_instance.connect():
        print("✅ 数据库连接成功")
    else:
        print("⚠️ 数据库连接失败")

    print(f"API 文档地址: http://localhost:8000/docs")
    print("=" * 50)

@app.on_event("shutdown")
async def shutdown_event():
    db_instance.close()
    print("数据库连接已关闭")

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
