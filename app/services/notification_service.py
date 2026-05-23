import json


class NotificationService:
    async def notify_doctor_message(
        self, patient_username: str, doctor_username: str, content: str, msg_id: int
    ):
        from app.api.v1.endpoints.chat import ws_manager

        await ws_manager.send_notification(
            patient_username,
            {
                "type": "doctor_message",
                "from": doctor_username,
                "content": content,
                "msg_id": msg_id,
            },
        )

    async def notify_alert(self, username: str, alert_data: dict):
        from app.api.v1.endpoints.chat import ws_manager

        await ws_manager.send_notification(
            username,
            {"type": "alert", **alert_data},
        )


notification_service = NotificationService()
