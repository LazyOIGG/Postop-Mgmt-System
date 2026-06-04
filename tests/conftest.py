"""测试公共 fixtures — mock DB, mock LLM, async test client"""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# 确保测试环境不使用 Redis（走内存回退）
from app.core.config import settings
settings.REDIS_URL = None


@pytest_asyncio.fixture
async def async_client():
    """创建异步 HTTP 测试客户端"""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def auth_headers(async_client):
    """登录获取 Authorization header（需要测试数据库中有 testuser/testpass）"""
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
