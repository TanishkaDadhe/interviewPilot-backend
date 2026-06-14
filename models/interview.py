from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Any, Dict
from datetime import datetime


class AnswerRecord(BaseModel):
    question: str
    answer: str
    score: Optional[float] = None
    verdict: Optional[str] = None
    what_was_good: Optional[str] = None      # ← new
    what_was_missing: Optional[str] = None   # ← new
    answered_at: datetime = Field(default_factory=datetime.utcnow)
    # Remove: evaluation, coaching (these were blobs)


class StartSessionRequest(BaseModel):
    interview_type: Literal["technical", "behavioral", "hr", "mixed"] = "mixed"
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    num_questions: int = Field(default=5, ge=1, le=15)
    focus_area: Optional[str] = None 


class StartSessionResponse(BaseModel):
    session_id: str
    first_question: str
    interview_type: str
    total_questions: int


class SubmitAnswerRequest(BaseModel):
    session_id: str
    answer: str


class SubmitAnswerResponse(BaseModel):
    score: Optional[int] = None          # None until /complete is called
    evaluation: Optional[str] = None
    coaching: Optional[str] = None
    next_question: Optional[str] = None
    questions_remaining: int
    session_complete: bool


class CompleteSessionRequest(BaseModel):
    session_id: str


class CompleteSessionResponse(BaseModel):
    session_id: str

    average_score: float

    overall_feedback: str

    hire_confidence: Optional[int] = None

    overall_verdict: Optional[str] = None

    top_strength: Optional[str] = None

    critical_improvement: Optional[str] = None

    job_fit_score: Optional[int] = None

    roadmap: List[str] = []

    per_question: List[dict] = []

    answers: List[AnswerRecord]


class SessionSummaryResponse(BaseModel):
    session_id: str

    interview_type: str

    total_questions: int

    average_score: float

    answers: List[AnswerRecord]

    overall_feedback: Optional[str] = None

    completed_at: Optional[datetime] = None

    hire_confidence: Optional[int] = None

    overall_verdict: Optional[str] = None

    top_strength: Optional[str] = None

    critical_improvement: Optional[str] = None

    job_fit_score: Optional[int] = None

    roadmap: List[str] = []

    per_question: List[dict] = []

    

class SessionDetailResponse(BaseModel):
    session_id: str
    interview_type: str
    difficulty: str
    focus_area: str | None = None

    questions: list[str]

    current_index: int

    status: str



class QuestionAnalysis(BaseModel):
    question: str

    score: int

    what_you_did_well: Optional[str] = None

    missing_points: Optional[str] = None

    ideal_answer: Optional[str] = None

    coaching_tip: Optional[str] = None


class InterviewSessionDocument(BaseModel):
    user_id: str
    interview_type: str
    difficulty: str
    focus_area: Optional[str] = None

    questions: List[str] = Field(default_factory=list)
    current_index: int = 0
    answers: List[AnswerRecord] = Field(default_factory=list)
    profile_summary: Optional[Dict[str, Any]] = None

    status: Literal["active", "answers_complete", "completed"] = "active"
    overall_feedback: Optional[str] = None
    average_score: Optional[float] = None
    hire_confidence: Optional[int] = None
    overall_verdict: Optional[str] = None

    top_strength: Optional[str] = None

    critical_improvement: Optional[str] = None

    job_fit_score: Optional[int] = None

    roadmap: List[str] = Field(default_factory=list)

    question_analysis: List[QuestionAnalysis] = Field(
        default_factory=list
    )

    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        populate_by_name = True