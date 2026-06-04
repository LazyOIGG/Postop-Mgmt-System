"""测试公共 fixtures — mock DB, mock LLM, async test client"""

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def async_client():
    """创建异步 HTTP 测试客户端"""
    # 延迟导入 + 设置 Redis 回退（CI 无 .env 时也能跑）
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-min-32!")
    os.environ.setdefault("PROJECT_NAME", "Test")
    os.environ.setdefault("VERSION", "0.1.0")
    os.environ.setdefault("API_V1_STR", "/api/v1")
    os.environ.setdefault("DEEPSEEK_API_KEY", "placeholder")
    os.environ.setdefault("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    os.environ.setdefault("DEEPSEEK_MODEL", "deepseek-chat")
    os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
    os.environ.setdefault("NEO4J_USER", "neo4j")
    os.environ.setdefault("NEO4J_PASSWORD", "password")
    os.environ.setdefault("NEO4J_NAME", "neo4j")
    os.environ.setdefault("MYSQL_HOST", "localhost")
    os.environ.setdefault("MYSQL_PORT", "3306")
    os.environ.setdefault("MYSQL_USER", "root")
    os.environ.setdefault("MYSQL_PASSWORD", "")
    os.environ.setdefault("MYSQL_DATABASE", "RAG")
    os.environ.setdefault("BERT_MODEL_PATH", "./model")
    os.environ.setdefault("NER_MODEL_WEIGHTS", "./model")
    os.environ.setdefault("TAG2IDX_PATH", "./model")
    os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

    from app.core.config import settings
    settings.REDIS_URL = None

    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def auth_headers(async_client):
    """登录获取 Authorization header"""
    response = await async_client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "testpass123",
    })
    if response.status_code == 200:
        data = response.json()
        token = data.get("data", {}).get("token", "")
        return {"Authorization": f"Bearer {token}"}
    # 注册新用户
    await async_client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "password": "testpass123",
        "confirm_password": "testpass123",
    })
    response = await async_client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "testpass123",
    })
    data = response.json()
    token = data.get("data", {}).get("token", "")
    return {"Authorization": f"Bearer {token}"}
