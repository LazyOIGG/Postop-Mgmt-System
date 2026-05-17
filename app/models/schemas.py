from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ChatRequest(BaseModel):
    message: str
    model_choice: Optional[str] = None
    session_id: Optional[int] = None
    stream: bool = False

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    confirm_password: str
    is_admin: bool = False

class SessionCreateRequest(BaseModel):
    username: str
    session_title: Optional[str] = "新对话"

class SessionUpdateRequest(BaseModel):
    session_id: int
    new_title: str

class MessageRequest(BaseModel):
    session_id: int
    username: str
    role: str
    content: str
    entities: Optional[str] = None
    intents: Optional[str] = None
    knowledge: Optional[str] = None

class KnowledgeGraphQuery(BaseModel):
    cypher_query: str
    limit: int = 100

class UserStatsResponse(BaseModel):
    username: str
    session_count: int
    total_messages: int
    last_active: Optional[datetime] = None

class PatientProfileUpdateRequest(BaseModel):
    real_name: Optional[str] = ""
    gender: Optional[str] = ""
    age: Optional[int] = None
    phone: Optional[str] = ""
    height: Optional[float] = None
    weight: Optional[float] = None
    blood_type: Optional[str] = ""
    medical_history: Optional[str] = ""
    allergy_history: Optional[str] = ""
    current_medications: Optional[str] = ""
    emergency_contact: Optional[str] = ""
    emergency_phone: Optional[str] = ""
    health_stage: Optional[str] = "长期管理"


class PatientProfileResponse(BaseModel):
    success: bool
    profile: Optional[dict] = None
    latest_assessment: Optional[dict] = None


class DailyCheckinRequest(BaseModel):
    checkin_date: str
    symptoms: Optional[str] = ""
    temperature: Optional[float] = None
    blood_pressure: Optional[str] = ""
    blood_sugar: Optional[float] = None
    heart_rate: Optional[int] = None
    sleep_status: Optional[str] = ""
    diet_status: Optional[str] = ""
    exercise_status: Optional[str] = ""
    medication_taken: Optional[bool] = False
    note: Optional[str] = ""


class ReminderCreateRequest(BaseModel):
    reminder_type: str
    title: str
    description: Optional[str] = ""
    reminder_date: str
    reminder_time: Optional[str] = None


class ReminderStatusUpdateRequest(BaseModel):
    reminder_id: int
    status: str


class DoctorMessageRequest(BaseModel):
    patient_username: str
    content: str


class AlertProcessRequest(BaseModel):
    alert_id: int


# ── P3.13 知识图谱增强 ──
class VisualizeRequest(BaseModel):
    entity_name: str
    max_hops: int = 3
    max_nodes: int = 50


class SchemaResponse(BaseModel):
    node_types: List[Dict[str, Any]] = []
    relationship_types: List[str] = []


# ── P3.15 推送通知系统 ──
class NotificationResponse(BaseModel):
    id: int
    username: str
    type: str
    title: str
    content: Optional[str] = ""
    related_id: Optional[int] = None
    is_read: bool = False
    created_at: Optional[datetime] = None


class UnreadCountResponse(BaseModel):
    count: int


# ── P3.16 语音交互 ──
class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
