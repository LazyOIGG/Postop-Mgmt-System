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


doctor_service = DoctorService()