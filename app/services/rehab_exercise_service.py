from typing import Dict, Optional
from app.db.session import db_instance


class RehabExerciseService:

    def get_exercises(
        self, phase: str = None, category: str = None,
        surgery_type: str = None, difficulty: str = None,
        search: str = None, limit: int = 50
    ) -> Dict:
        exercises = db_instance.get_rehab_exercises(
            phase=phase, category=category, surgery_type=surgery_type,
            difficulty=difficulty, search=search, limit=limit
        )
        return {"success": True, "exercises": exercises, "count": len(exercises)}

    def get_exercise_detail(self, exercise_id: int) -> Dict:
        exercise = db_instance.get_rehab_exercise(exercise_id)
        if not exercise:
            return {"success": False, "error": "运动不存在"}
        return {"success": True, "exercise": exercise}

    def get_recommended(self, surgery_type: str, current_phase: str) -> Dict:
        exercises = db_instance.get_rehab_exercises(
            phase=current_phase, surgery_type=surgery_type, limit=6
        )
        if len(exercises) < 3:
            fallback = db_instance.get_rehab_exercises(
                phase=current_phase, surgery_type="通用", limit=6
            )
            seen_ids = {e["id"] for e in exercises}
            for e in fallback:
                if e["id"] not in seen_ids:
                    exercises.append(e)
        return {"success": True, "exercises": exercises[:6], "count": min(len(exercises), 6)}


rehab_exercise_service = RehabExerciseService()
