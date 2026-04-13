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
