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
