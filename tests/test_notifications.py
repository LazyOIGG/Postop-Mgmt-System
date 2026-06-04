"""通知 API 测试"""

import pytest


class TestNotificationsAPI:
    """通知 CRUD + 分页"""

    @pytest.mark.asyncio
    async def test_get_notifications_requires_auth(self, async_client):
        response = await async_client.get("/api/v1/notifications")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_notifications_with_auth(self, async_client, auth_headers):
        response = await async_client.get("/api/v1/notifications", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_notifications_paginated(self, async_client, auth_headers):
        response = await async_client.get(
            "/api/v1/notifications?page=1&size=5", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "pagination" in data
        assert "page" in data["pagination"]
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 5

    @pytest.mark.asyncio
    async def test_get_notifications_legacy_limit(self, async_client, auth_headers):
        response = await async_client.get(
            "/api/v1/notifications?limit=10", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_unread_count(self, async_client, auth_headers):
        response = await async_client.get(
            "/api/v1/notifications/unread-count", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "count" in data["data"]

    @pytest.mark.asyncio
    async def test_delete_nonexistent_notification(self, async_client, auth_headers):
        response = await async_client.delete(
            "/api/v1/notifications/99999", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_read_nonexistent(self, async_client, auth_headers):
        response = await async_client.put(
            "/api/v1/notifications/99999/read", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_all_read(self, async_client, auth_headers):
        response = await async_client.put(
            "/api/v1/notifications/read-all", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_pagination_invalid_params(self, async_client, auth_headers):
        """非法分页参数应由 FastAPI 验证拦截"""
        response = await async_client.get(
            "/api/v1/notifications?page=0&size=200", headers=auth_headers
        )
        # page=0 和 size=200 超出约束范围
        assert response.status_code == 422
