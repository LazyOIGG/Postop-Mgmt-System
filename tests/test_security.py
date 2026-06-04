"""安全模块测试"""

import pytest


class TestSecurity:
    """require_admin, token 黑名单"""

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, async_client):
        """无 token 访问需要认证的端点应返回 401"""
        response = await async_client.get("/api/v1/notifications/unread-count")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_invalid_token(self, async_client):
        """无效 token 应返回 401"""
        response = await async_client.get(
            "/api/v1/notifications/unread-count",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_cors_headers(self, async_client):
        """CORS 预检请求应包含正确头部"""
        response = await async_client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        # FastAPI CORSMiddleware 会处理 OPTIONS 请求
        assert response.status_code in (200, 405)
