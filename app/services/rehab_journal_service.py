from typing import Dict, Optional
from app.db.session import db_instance


class RehabJournalService:

    def save_journal(self, username: str, plan_id: int, data: dict) -> Dict:
        journal_id = db_instance.save_rehab_journal(plan_id, username, data)
        if journal_id is None:
            return {"success": False, "error": "保存日志失败"}
        return {"success": True, "journal_id": journal_id}

    def get_journals(
        self, plan_id: int, date_from: str = None, date_to: str = None
    ) -> Dict:
        journals = db_instance.get_rehab_journals(plan_id, date_from, date_to)
        return {"success": True, "journals": journals}

    def get_journal(self, journal_id: int) -> Dict:
        journal = db_instance.get_rehab_journal(journal_id)
        if not journal:
            return {"success": False, "error": "日志不存在"}
        return {"success": True, "journal": journal}


rehab_journal_service = RehabJournalService()
