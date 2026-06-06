"""WebSocket 连接管理器 — 支持多连接、心跳、消息协议标准化"""

import asyncio
import json
import logging
from typing import Dict, List, Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WSMessageType:
    """WebSocket 消息协议标准化"""
    NOTIFICATION = "notification"
    CHAT_START = "chat_start"
    CHAT_CHUNK = "chat_chunk"
    CHAT_COMPLETE = "chat_complete"
    RISK_ALERT = "risk_alert"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"


class ConnectionManager:
    """WebSocket 连接管理器

    支持特性:
    - 单用户多连接 (多设备/多标签页)
    - 30s 心跳保活
    - 死连接自动清理
    - 标准化消息协议
    """

    def __init__(self):
        # username → List[WebSocket]
        self._connections: Dict[str, List[WebSocket]] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_interval: int = 30

    # ── Connection lifecycle ──────────────────────────────────────

    async def connect(self, username: str, websocket: WebSocket):
        """接受 WebSocket 连接并注册到用户连接池"""
        await websocket.accept()
        if username not in self._connections:
            self._connections[username] = []
        self._connections[username].append(websocket)
        logger.info("websocket_connected username=%s active_connections=%s",
                     username, len(self._connections[username]))

    def disconnect(self, username: str, websocket: WebSocket):
        """移除指定连接，如果用户无连接则清理用户条目"""
        if username in self._connections:
            self._connections[username] = [
                ws for ws in self._connections[username] if ws != websocket
            ]
            if not self._connections[username]:
                del self._connections[username]
            logger.info("websocket_disconnected username=%s remaining=%s",
                         username, len(self._connections.get(username, [])))

    # ── Sending ───────────────────────────────────────────────────

    async def send_to_user(self, username: str, message: dict):
        """向用户所有连接发送消息，自动清理死连接"""
        if username not in self._connections:
            return

        payload = json.dumps(message, ensure_ascii=False)
        dead: List[tuple] = []

        for ws in self._connections[username]:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append((username, ws))

        # 清理死连接
        for uname, ws in dead:
            self.disconnect(uname, ws)

    async def send_notification(self, username: str, data: dict):
        """向后兼容别名 — 发送通知到用户"""
        await self.send_to_user(username, data)

    async def broadcast(self, message: dict):
        """向所有已连接用户广播消息"""
        for username in list(self._connections.keys()):
            await self.send_to_user(username, message)

    async def send_to_all_doctors(self, data: dict):
        """向所有在线用户广播（医生端扩展用）"""
        await self.broadcast(data)

    # ── Heartbeat ─────────────────────────────────────────────────

    async def _heartbeat_loop(self):
        """定期发送 ping 保持连接活跃，清理无响应连接"""
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            ping_msg = json.dumps({"type": WSMessageType.PING})
            dead: List[tuple] = []

            for username, conns in list(self._connections.items()):
                for ws in list(conns):
                    try:
                        await ws.send_text(ping_msg)
                    except Exception:
                        dead.append((username, ws))

            for username, ws in dead:
                self.disconnect(username, ws)

            if dead:
                logger.info("heartbeat_cleanup dead_count=%s active_users=%s",
                            len(dead), len(self._connections))

    def start_heartbeat(self):
        """启动心跳任务（在 FastAPI startup 事件中调用）"""
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("heartbeat_started interval=%s", self._heartbeat_interval)

    async def shutdown(self):
        """优雅关闭：停止心跳并关闭所有连接"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        # 关闭所有连接
        for conns in list(self._connections.values()):
            for ws in conns:
                try:
                    await ws.close()
                except Exception:
                    pass
        self._connections.clear()
        logger.info("websocket_manager_shutdown")

    # ── Convenience builders ──────────────────────────────────────

    @staticmethod
    def build_payload(msg_type: str, **kwargs) -> dict:
        """构建标准化的消息体"""
        return {"type": msg_type, "data": kwargs, **kwargs}

    @property
    def active_connection_count(self) -> int:
        """当前活跃连接总数"""
        return sum(len(conns) for conns in self._connections.values())

    @property
    def active_user_count(self) -> int:
        """当前活跃用户数"""
        return len(self._connections)


# 全局单例
ws_manager = ConnectionManager()
