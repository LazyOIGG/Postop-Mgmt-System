from typing import Dict, List, Optional
from app.db.session import db_instance
from app.services.notification_service import notification_service


class DoctorService:
    def get_patient_list(self) -> List[Dict]:
        return db_instance.get_doctor_patient_list(limit=100)

    def get_high_risk_records(self) -> List[Dict]:
        return db_instance.get_high_risk_assessments(limit=50)

    def get_abnormal_checkins(self) -> List[Dict]:
        return db_instance.get_abnormal_checkins_for_doctor(limit=50)

    def get_patient_detail(self, username: str) -> Optional[Dict]:
        return db_instance.get_patient_detail_for_doctor(username)

    def get_alerts(self, status: str = None) -> List[Dict]:
        return db_instance.get_alert_notifications(status=status, limit=50)

    def process_alert(self, alert_id: int) -> bool:
        return db_instance.process_alert_notification(alert_id)

    async def send_message(self, doctor_username: str, patient_username: str, content: str) -> Dict:
        msg_id = db_instance.save_doctor_message(doctor_username, patient_username, content)
        db_instance.save_admin_message_to_patient(doctor_username, patient_username, content)
        await notification_service.notify_doctor_message(
            patient_username, doctor_username, content, msg_id
        )
        return {"content": content, "patient_username": patient_username}

    def get_messages(self, patient_username: str) -> List[Dict]:
        return db_instance.get_doctor_messages(patient_username=patient_username, limit=50)

    def get_unread_count(self, patient_username: str) -> int:
        messages = db_instance.get_doctor_messages(patient_username=patient_username, limit=50)
        return len(messages)

    async def send_message_from_patient(self, patient_username: str, content: str) -> Dict:
        db_instance.save_doctor_message(patient_username, patient_username, content)
        return {"content": content, "patient_username": patient_username}


doctor_service = DoctorService()
