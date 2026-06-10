from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str


# ── Profile ───────────────────────────────────────────────────────────────────

class ExperienceEntry(BaseModel):
    company: str
    role: str
    duration: str                        # e.g. "Jan 2022 – Mar 2024" 
    description: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    target_role: Optional[str] = None    # e.g. "Senior Backend Engineer"
    skills: Optional[List[str]] = None   # ["Python", "FastAPI", "MongoDB"]
    experience: Optional[List[ExperienceEntry]] = None
    education: Optional[str] = None
    resume_text: Optional[str] = None    # raw text extracted from uploaded PDF
    job_description: Optional[str] = None   # raw text extracted from uploaded job_description text


# ── DB document (what we actually store in Mongo) ────────────────────────────

class UserDocument(BaseModel):
    name: str
    email: EmailStr
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # profile fields (filled in later)
    target_role: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience: List[ExperienceEntry] = Field(default_factory=list)
    education: Optional[str] = None
    resume_text: Optional[str] = None
    job_description: Optional[str] = None   
      

    class Config:
        # allow _id from Mongo to pass through without error
        populate_by_name = True