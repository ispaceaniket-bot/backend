from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .models import UserRole, CaseStatus

# --- USER SCHEMAS ---
class UserCreate(BaseModel):
    email: str
    username: str
    password: str
    role: UserRole

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: UserRole
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

# --- CASE SCHEMAS ---
class CaseCreate(BaseModel):
    description: str
    date_of_birth: str

class CaseResponse(BaseModel):
    id: int
    status: CaseStatus
    description: str
    created_at: datetime
    claimant_id: int
    assigned_gp_id: Optional[int] = None
    specialty: Optional[str] = None
    sla_deadline: Optional[datetime] = None
    gp_decision_comment: Optional[str] = None
    assigned_qa_id: Optional[int] = None
    qa_feedback: Optional[str] = None
    date_of_birth: Optional[str] = None
    class Config:
        from_attributes = True

# --- MESSAGE SCHEMAS ---
class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    sender_id: int
    content: str
    timestamp: datetime
    sender_username: Optional[str] = None
    sender_role: Optional[str] = None
    class Config:
        from_attributes = True

# --- DOCUMENT SCHEMAS ---
class DocumentResponse(BaseModel):
    id: int
    case_id: int
    filename: str
    file_path: str
    file_type: str
    uploaded_at: datetime
    class Config:
        from_attributes = True

class AssignGPRequest(BaseModel):
    gp_id: int
    specialty: str
    sla_deadline: datetime # Expects format: 2026-01-30T15:00:00

# Add this new class for the GP Dropdown
class SimpleUser(BaseModel):
    id: int
    email: str
    username: str
    
    class Config:
        from_attributes = True