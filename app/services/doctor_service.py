from app.db.session import db_instance


class DoctorService:
    def get_patient_list(self):
        return db_instance.get_doctor_patient_list(limit=100)

    def get_high_risk_records(self):
        return db_instance.get_high_risk_assessments(limit=50)

    def get_abnormal_checkins(self):
        return db_instance.get_abnormal_checkins_for_doctor(limit=50)

    def get_patient_detail(self, username: str):
        return db_instance.get_patient_detail_for_doctor(username)

    def get_alerts(self, status: str = None):
        return db_instance.get_alert_notifications(status=status, limit=50)

    def process_alert(self, alert_id: int):
        return db_instance.process_alert_notification(alert_id)

    def send_message(self, doctor_username: str, patient_username: str, content: str):
        db_instance.save_doctor_message(doctor_username, patient_username, content)
        db_instance.save_admin_message_to_patient(doctor_username, patient_username, content)
        return {"content": content, "patient_username": patient_username}


doctor_service = DoctorService()
