from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from typing import Dict, Optional
import json

from app.core.security import get_current_user
from app.services.health_assessment_service import health_assessment_service
from app.services.speech_service import speech_service
from app.services.image_service import image_service
from app.db.session import db_instance

router = APIRouter()


@router.post("/assess/text")
async def assess_text(
    input_text: str = Form(...),
    session_id: Optional[str] = Form(None),
    user: Dict = Depends(get_current_user)
):
    username = user["username"]
    try:
        sid = int(session_id) if session_id and session_id.strip() else db_instance.create_session(username, "健康评估")
    except (ValueError, TypeError):
        sid = db_instance.create_session(username, "健康评估")

    if not sid:
        raise HTTPException(status_code=500, detail="创建会话失败")

    result = await health_assessment_service.assess(input_text, source_type="text")

    db_instance.save_message(sid, username, "user", input_text)
    db_instance.save_message(
        sid,
        username,
        "assistant",
        result["advice"],
        None,
        result["risk_level"],
        "\n".join(result["risk_reasons"])
    )

    db_instance.save_health_assessment(
        username=username,
        session_id=sid,
        source_type="text",
        input_text=input_text,
        risk_level=result["risk_level"],
        risk_reasons=json.dumps(result["risk_reasons"], ensure_ascii=False),
        advice=result["advice"],
        need_hospital=1 if result["need_hospital"] else 0
    )

    return {
        "success": True,
        **result,
        "session_id": sid
    }


@router.post("/assess/speech")
async def assess_speech(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    user: Dict = Depends(get_current_user)
):
    content = await file.read()
    recognized_text = await speech_service.transcribe(content)

    if not recognized_text or recognized_text.startswith("语音识别失败"):
        raise HTTPException(status_code=400, detail=f"语音识别失败：{recognized_text}")

    username = user["username"]
    try:
        sid = int(session_id) if session_id and session_id.strip() else db_instance.create_session(username, "健康评估")
    except (ValueError, TypeError):
        sid = db_instance.create_session(username, "健康评估")

    result = await health_assessment_service.assess(recognized_text, source_type="speech")

    db_instance.save_message(sid, username, "user", recognized_text)
    db_instance.save_message(
        sid,
        username,
        "assistant",
        result["advice"],
        None,
        result["risk_level"],
        "\n".join(result["risk_reasons"])
    )

    db_instance.save_health_assessment(
        username=username,
        session_id=sid,
        source_type="speech",
        input_text=recognized_text,
        risk_level=result["risk_level"],
        risk_reasons=json.dumps(result["risk_reasons"], ensure_ascii=False),
        advice=result["advice"],
        need_hospital=1 if result["need_hospital"] else 0
    )

    return {
        "success": True,
        **result,
        "session_id": sid
    }


@router.post("/assess/image")
async def assess_image(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    user: Dict = Depends(get_current_user)
):
    content = await file.read()

    ocr_result = await image_service.extract_text_from_report(
        image_data=content,
        filename=file.filename,
        content_type=file.content_type
    )

    if not ocr_result or ocr_result.get("message"):
        raise HTTPException(status_code=400, detail=ocr_result.get("message", "OCR识别失败"))

    ocr_text = ocr_result.get("text", "").strip()
    if not ocr_text:
        raise HTTPException(status_code=400, detail="未识别到有效文本")

    username = user["username"]
    try:
        sid = int(session_id) if session_id and session_id.strip() else db_instance.create_session(username, "健康评估")
    except (ValueError, TypeError):
        sid = db_instance.create_session(username, "健康评估")

    result = await health_assessment_service.assess(ocr_text, source_type="image")

    db_instance.save_message(sid, username, "user", f"[上传报告] {file.filename}")
    db_instance.save_message(
        sid,
        username,
        "assistant",
        result["advice"],
        None,
        result["risk_level"],
        "\n".join(result["risk_reasons"])
    )

    db_instance.save_patient_report(
        username=username,
        file_name=file.filename or "unknown",
        file_type=file.content_type or "image",
        raw_ocr_text=ocr_text,
        structured_json=json.dumps(ocr_result.get("structured", {}), ensure_ascii=False),
        ocr_score=ocr_result.get("avg_score", 0.0)
    )

    db_instance.save_health_assessment(
        username=username,
        session_id=sid,
        source_type="image",
        input_text=ocr_text,
        risk_level=result["risk_level"],
        risk_reasons=json.dumps(result["risk_reasons"], ensure_ascii=False),
        advice=result["advice"],
        need_hospital=1 if result["need_hospital"] else 0
    )

    return {
        "success": True,
        **result,
        "session_id": sid,
        "ocr_structured": ocr_result.get("structured", {}),
        "ocr_score": ocr_result.get("avg_score", 0.0)
    }


@router.get("/assess/history")
async def assess_history(user: Dict = Depends(get_current_user)):
    records = db_instance.get_health_assessment_history(user["username"])
    return {"success": True, "records": records}
