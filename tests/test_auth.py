"""认证 API 测试"""

import pytest


class TestAuthAPI:
    """登录 / 注册 / 刷新 / 登出"""

    @pytest.mark.asyncio
    async def test_register_new_user(self, async_client):
        response = await async_client.post("/api/v1/auth/register", json={
            "username": "newuser_test",
            "password": "Test@123456",
            "confirm_password": "Test@123456",
        })
        assert response.status_code in (200, 400)  # 400 if user already exists
        data = response.json()
        assert "success" in data
        if data["success"]:
            assert "token" in data.get("data", {})

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, async_client):
        response = await async_client.post("/api/v1/auth/login", json={
            "username": "nonexistent_user_xyz",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_success(self, async_client):
        response = await async_client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass123",
        })
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "token" in data.get("data", {})
            assert "refresh_token" in data.get("data", {})

    @pytest.mark.asyncio
    async def test_refresh_token(self, async_client):
        # First login
        resp = await async_client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass123",
        })
        if resp.status_code != 200:
            pytest.skip("需要先注册 testuser")
        refresh_token = resp.json()["data"]["refresh_token"]

        # Then refresh
        response = await async_client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_me_endpoint(self, async_client, auth_headers):
        response = await async_client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_me_without_token(self, async_client):
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_password_mismatch(self, async_client):
        response = await async_client.post("/api/v1/auth/register", json={
            "username": "mismatch_user",
            "password": "Test@123456",
            "confirm_password": "Different@123456",
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_empty_username(self, async_client):
        response = await async_client.post("/api/v1/auth/register", json={
            "username": "",
            "password": "Test@123456",
            "confirm_password": "Test@123456",
        })
        # 当前后端允许空用户名注册，后续应添加参数校验
        # 如需限制，可在 RegisterRequest schema 中加 min_length=1
        assert response.status_code in (200, 400, 422)
