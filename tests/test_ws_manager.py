"""WebSocket ConnectionManager 单元测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.ws_manager import ConnectionManager, WSMessageType


class FakeWebSocket:
    """模拟 WebSocket 连接"""

    def __init__(self):
        self.accepted = False
        self.sent_messages = []
        self.closed = False
        self.accept = AsyncMock(side_effect=self._accept)
        self.send_text = AsyncMock(side_effect=self._send_text)
        self.close = AsyncMock()

    async def _accept(self):
        self.accepted = True

    async def _send_text(self, data: str):
        self.sent_messages.append(data)

    async def receive_text(self):
        return '{"type": "pong"}'


class TestConnectionManager:
    """WebSocket 管理器测试"""

    @pytest.mark.asyncio
    async def test_connect(self):
        mgr = ConnectionManager()
        ws = FakeWebSocket()
        await mgr.connect("user1", ws)
        assert ws.accepted is True
        assert "user1" in mgr._connections
        assert ws in mgr._connections["user1"]

    @pytest.mark.asyncio
    async def test_multiple_connections_per_user(self):
        mgr = ConnectionManager()
        ws1 = FakeWebSocket()
        ws2 = FakeWebSocket()
        await mgr.connect("user1", ws1)
        await mgr.connect("user1", ws2)
        assert len(mgr._connections["user1"]) == 2

    @pytest.mark.asyncio
    async def test_disconnect(self):
        mgr = ConnectionManager()
        ws1 = FakeWebSocket()
        ws2 = FakeWebSocket()
        await mgr.connect("user1", ws1)
        await mgr.connect("user1", ws2)
        mgr.disconnect("user1", ws1)
        assert "user1" in mgr._connections
        assert ws1 not in mgr._connections["user1"]
        assert ws2 in mgr._connections["user1"]

    @pytest.mark.asyncio
    async def test_disconnect_last_removes_user(self):
        mgr = ConnectionManager()
        ws = FakeWebSocket()
        await mgr.connect("user1", ws)
        mgr.disconnect("user1", ws)
        assert "user1" not in mgr._connections

    @pytest.mark.asyncio
    async def test_send_to_user(self):
        mgr = ConnectionManager()
        ws1 = FakeWebSocket()
        ws2 = FakeWebSocket()
        await mgr.connect("user1", ws1)
        await mgr.connect("user1", ws2)
        await mgr.send_to_user("user1", {"type": "test", "msg": "hello"})
        assert len(ws1.sent_messages) == 1
        assert len(ws2.sent_messages) == 1
        assert '"type"' in ws1.sent_messages[0]

    @pytest.mark.asyncio
    async def test_send_to_user_cleans_dead_connections(self):
        mgr = ConnectionManager()
        ws_good = FakeWebSocket()
        ws_bad = FakeWebSocket()
        ws_bad.send_text = AsyncMock(side_effect=Exception("connection lost"))
        await mgr.connect("user1", ws_good)
        await mgr.connect("user1", ws_bad)
        await mgr.send_to_user("user1", {"type": "test"})
        # 死连接应被清理
        assert ws_bad not in mgr._connections.get("user1", [])
        assert ws_good in mgr._connections.get("user1", [])
        # 正常连接仍收到消息
        assert len(ws_good.sent_messages) == 1

    @pytest.mark.asyncio
    async def test_send_notification_alias(self):
        mgr = ConnectionManager()
        ws = FakeWebSocket()
        await mgr.connect("user1", ws)
        await mgr.send_notification("user1", {"type": "alert", "data": "test"})
        assert len(ws.sent_messages) == 1

    @pytest.mark.asyncio
    async def test_active_counts(self):
        mgr = ConnectionManager()
        ws1 = FakeWebSocket()
        ws2 = FakeWebSocket()
        ws3 = FakeWebSocket()
        await mgr.connect("user1", ws1)
        await mgr.connect("user1", ws2)
        await mgr.connect("user2", ws3)
        assert mgr.active_connection_count == 3
        assert mgr.active_user_count == 2

    @pytest.mark.asyncio
    async def test_shutdown(self):
        mgr = ConnectionManager()
        ws = FakeWebSocket()
        await mgr.connect("user1", ws)
        await mgr.shutdown()
        assert len(mgr._connections) == 0
