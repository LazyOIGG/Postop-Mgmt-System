import json
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Optional, List
from app.core.security import get_current_user
from app.services.rehab_exercise_service import rehab_exercise_service
from app.db.session import db_instance

router = APIRouter()


@router.get("/rehab-exercises")
async def get_exercises(
    phase: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    surgery_type: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50),
    user: Dict = Depends(get_current_user)
):
    return rehab_exercise_service.get_exercises(
        phase=phase, category=category, surgery_type=surgery_type,
        difficulty=difficulty, search=search, limit=limit)


@router.get("/rehab-exercises/recommended")
async def get_recommended(
    surgery_type: Optional[str] = Query(None),
    current_phase: Optional[str] = Query("恢复期"),
    user: Dict = Depends(get_current_user)
):
    return rehab_exercise_service.get_recommended(surgery_type, current_phase)


@router.get("/rehab-exercises/{exercise_id}")
async def get_exercise_detail(
    exercise_id: int, user: Dict = Depends(get_current_user)
):
    result = rehab_exercise_service.get_exercise_detail(exercise_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


# ===== AAOS 图文运动库 =====

SURGERY_KEYWORD_MAP = {
    "膝": "膝关节锻炼", "acl": "ACL重建术", "半月板": "半月板修复术",
    "髋": "髋关节锻炼", "股骨": "股骨颈骨折",
    "肩": "肩关节锻炼", "肩袖": "肩袖修复术", "锁骨": "锁骨骨折",
    "腰椎": "腰椎间盘手术", "颈椎": "颈椎管狭窄", "脊柱": "脊柱锻炼",
    "椎间盘": "腰椎间盘手术", "背": "脊柱锻炼", "腰": "脊柱锻炼",
    "踝": "足踝锻炼", "跟腱": "跟腱修复术", "足底筋膜炎": "足底筋膜炎",
    "足": "足踝锻炼", "拇囊": "拇囊炎术后", "脚": "足踝锻炼",
    "腕": "腕管松解术", "腕管": "腕管松解术", "肘": "网球肘",
    "网球肘": "网球肘", "肱骨": "肱骨骨折", "手": "手腕骨折",
    "骨折": "骨折内固定术",
}


def _normalize_surgery_type(raw: str) -> list:
    if not raw:
        return ["膝关节锻炼"]
    raw_lower = raw.lower().strip()
    matches = []
    for keyword, category in SURGERY_KEYWORD_MAP.items():
        if keyword in raw or keyword.lower() in raw_lower:
            matches.append(category)
    seen = set()
    result = []
    for m in matches:
        if m not in seen:
            result.append(m)
            seen.add(m)
    if not result:
        result = ["膝关节锻炼", "足踝锻炼", "肩关节锻炼"]
    return result


@router.get("/rehab-exercises/aaos/{surgery_type}")
async def get_aaos_exercises(
    surgery_type: str,
    user: Dict = Depends(get_current_user)
):
    try:
        if not db_instance._ensure_connection():
            return {"success": False, "error": "DB"}
        cursor = db_instance.connection.cursor(dictionary=True)
        categories = _normalize_surgery_type(surgery_type)
        conditions = " OR ".join(["surgery_type LIKE %s"] * len(categories))
        params = [f"%{c}%" for c in categories]
        cursor.execute(f"""
            SELECT id, surgery_type, chunk_index, section_title as name,
                   content, char_count, source_file as source_url, source_url as image_json
            FROM guideline_chunks
            WHERE ({conditions}) AND content != ''
            ORDER BY FIELD(surgery_type, {','.join(['%s'] * len(categories))}), chunk_index
            LIMIT 30
        """, params + categories)
        rows = cursor.fetchall()
        cursor.close()
        exercises = []
        for row in rows:
            image_urls = []; local_images = []
            try:
                if row.get("image_json"):
                    image_urls = json.loads(row["image_json"])
                    safe = row["surgery_type"].replace('/', '_')
                    ci = row.get("chunk_index", 1)
                    for i in range(len(image_urls)):
                        local_images.append(f"/aaos_images/{safe}_{ci:02d}_{i+1:02d}.jpg")
            except: pass
            exercises.append({
                "id": row["id"], "surgery_type": row["surgery_type"],
                "name": row["name"], "content": row["content"],
                "image_urls": image_urls, "local_images": local_images,
                "source_url": row.get("source_url", ""),
            })
        return {"success": True, "exercises": exercises, "count": len(exercises)}
    except Exception as e:
        return {"success": False, "error": str(e)}
