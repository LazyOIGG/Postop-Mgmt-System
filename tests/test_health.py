"""健康检查端点测试"""

import pytest


class TestHealthEndpoint:
    """健康检查"""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, async_client):
        response = await async_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_endpoint(self, async_client):
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_includes_db_status(self, async_client):
        response = await async_client.get("/health")
        data = response.json()
        # A4 重构后改为 checks.mysql 结构
        assert "checks" in data
        assert "mysql" in data["checks"]

    @pytest.mark.asyncio
    async def test_api_docs_accessible(self, async_client):
        response = await async_client.get("/docs")
        assert response.status_code == 200
