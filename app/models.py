from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class UserRole(str, enum.Enum):
    CLAIMANT = "claimant"
    ADMIN = "admin"
    GP = "gp"
    QA = "qa"

class CaseStatus(str, enum.Enum):
    PENDING = "pending"
    REVIEW = "review"
    ASSIGNED = "assigned"
    CLARIFICATION = "clarification"
    
    # --- NEW STATUSES ---
    QA_PENDING = "qa_pending"   # Approved by GP, waiting for QA
    RETURNED = "returned"       # Denied/Sent back to Claimant
    COMPLETED = "completed"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(SQLEnum(UserRole))

class Case(Base):
    __tablename__ = "cases"
    
    id = Column(Integer, primary_key=True, index=True)
    claimant_id = Column(Integer, ForeignKey("users.id"))
    assigned_gp_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    specialty = Column(String, nullable=True)
    sla_deadline = Column(DateTime, nullable=True)
    
    gp_decision_comment = Column(Text, nullable=True)
    
    assigned_qa_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    qa_feedback = Column(Text, nullable=True)

    description = Column(Text)
    date_of_birth = Column(String)
    status = Column(SQLEnum(CaseStatus), default=CaseStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    filename = Column(String)
    file_path = Column(String)
    file_type = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)