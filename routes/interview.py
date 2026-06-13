"""
Interview routes — redesigned for minimal Gemini API calls:

  POST /interview/start          → Prompt 1 (profile) + Prompt 2 (questions) = 2 calls
  POST /interview/answer         → Collects answers, NO AI call until session complete
  POST /interview/complete       → Prompt 3 (bulk evaluate) + Prompt 4 (bulk coach) = 2 calls
  GET  /interview/{id}/summary   → Read from DB, no AI call
  GET  /interview/history        → Read from DB, no AI call

Total AI calls per full interview: 4 (regardless of number of questions)
"""

from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from datetime import datetime

from database.connection import get_db
from models.interview import (
    StartSessionRequest, StartSessionResponse,
    SubmitAnswerRequest, SubmitAnswerResponse,
    CompleteSessionRequest, CompleteSessionResponse,
    SessionSummaryResponse, AnswerRecord,
    InterviewSessionDocument, SessionDetailResponse,
)
from agents.profile_agent import build_profile_summary
from agents.question_agent import generate_questions
from agents.evaluator_agent import evaluate_all_answers
from agents.coach_agent import coach_all_answers
from routes.auth import get_current_user

router = APIRouter()


# ── 1. Start session — generates profile + all questions (2 AI calls) ─────────

@router.post("/start", response_model=StartSessionResponse, status_code=201)
async def start_session(
    body: StartSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    target_role = current_user.get("target_role", "Software Engineer")

    # --- AI Call 1: Analyze candidate profile ---
    try:
        profile_summary = build_profile_summary(current_user)

        # Save extracted profile data into user document
        db.users.update_one(
            {"_id": current_user["_id"]},
            {
                "$set": {
                    "target_role":
                        profile_summary.get(
                            "target_role"
                        ),

                    "skills":
                        profile_summary.get(
                            "skills",
                            []
                        ),

                    "education":
                        profile_summary.get(
                            "education"
                        ),

                    "experience":
                        profile_summary.get(
                            "experience",
                            []
                        ),
                }
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Profile analysis failed: {str(e)}"
        )

    # --- AI Call 2: Generate all questions at once ---
    questions = generate_questions(
        profile_summary=profile_summary,
        interview_type=body.interview_type,
        difficulty=body.difficulty,
        num_questions=body.num_questions,
        focus_area=body.focus_area,
        target_role=target_role,
    )
    if not questions:
        raise HTTPException(status_code=500, detail="Could not generate questions")

    session = InterviewSessionDocument(
        user_id=str(current_user["_id"]),
        interview_type=body.interview_type,
        difficulty=body.difficulty,
        focus_area=body.focus_area,
        questions=questions,
        profile_summary=profile_summary,
    )
    result = db.sessions.insert_one(session.model_dump())
    session_id = str(result.inserted_id)

    return StartSessionResponse(
        session_id=session_id,
        first_question=questions[0],
        interview_type=body.interview_type,
        total_questions=len(questions),
    )


# ── 2. Submit answer — NO AI call, just stores the answer ─────────────────────

@router.post("/answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    body: SubmitAnswerRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(body.session_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    db = get_db()
    session = db.sessions.find_one({
        "_id": oid,
        "user_id": str(current_user["_id"]),
    })
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["status"] == "answers_complete":
        raise HTTPException(
            status_code=400,
            detail="Interview already finished. Call /complete."
        )
    if session["status"] == "completed":
        raise HTTPException(status_code=400, detail="Session already completed")

    idx = session["current_index"]
    question = session["questions"][idx]
    next_index = idx + 1
    total = len(session["questions"])
    session_complete = next_index >= total
    next_question = None if session_complete else session["questions"][next_index]

    # Store answer with no AI evaluation yet
    raw_answer = AnswerRecord(
        question=question,
        answer=body.answer,
    )

    update = {
        "$push": {"answers": raw_answer.model_dump()},
        "$set": {"current_index": next_index},
    }
    if session_complete:
        update["$set"]["status"] = "answers_complete"

    db.sessions.update_one({"_id": oid}, update)

    return SubmitAnswerResponse(
        score=None,
        evaluation=None,
        coaching=None,
        next_question=next_question,
        questions_remaining=max(0, total - next_index),
        session_complete=session_complete,
    )


# ── 3. Complete session — bulk evaluate + bulk coach (2 AI calls) ─────────────

@router.post("/complete", response_model=CompleteSessionResponse)
async def complete_session(
    body: CompleteSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(body.session_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    db = get_db()
    session = db.sessions.find_one({
        "_id": oid,
        "user_id": str(current_user["_id"]),
    })
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["status"] == "completed":
        raise HTTPException(status_code=400, detail="Session already completed")
    if session["status"] != "answers_complete":
        raise HTTPException(status_code=400, detail="Answer all questions before completing")

    answers = session.get("answers", [])
    profile_summary = session.get("profile_summary", {})
    target_role = current_user.get("target_role", "Software Engineer")

    qa_pairs = [{"question": a["question"], "answer": a["answer"]} for a in answers]

    # --- AI Call 3: Evaluate all answers in one prompt ---
    print("Calling evaluator")
    evaluations = evaluate_all_answers(
        qa_pairs=qa_pairs,
        target_role=target_role,
        profile_summary=profile_summary,
    )

    # Merge evaluations into answers
    qa_evaluations = []
    for i, (ans, ev) in enumerate(zip(answers, evaluations)):
        qa_evaluations.append({
            "question": ans["question"],
            "answer": ans["answer"],
            "score": ev["score"],
            "verdict": ev["verdict"],
            "what_was_good": ev["what_was_good"],
            "what_was_missing": ev["what_was_missing"],
            "ideal_answer_summary": ev["ideal_answer_summary"],
            "feedback": ev["feedback"],
        })

    # --- AI Call 4: Coach on all answers in one prompt ---
    print("Calling coach")
    coaching = coach_all_answers(
        qa_evaluations=qa_evaluations,
        target_role=target_role,
        profile_summary=profile_summary,
    )

    # Build final answer records with evaluations + per-question coaching
    per_q_coaching = {item["question_index"] - 1: item for item in coaching.get("per_question", [])}
    final_answers = []
    for i, (ans, ev) in enumerate(zip(answers, evaluations)):
        pq = per_q_coaching.get(i, {})
        evaluation_text = (
            f"Score: {ev['score']}/10 ({ev['verdict']})\n\n"
            f"What was good: {ev['what_was_good']}\n\n"
            f"What was missing: {ev['what_was_missing']}\n\n"
            f"Ideal answer: {ev['ideal_answer_summary']}\n\n"
            f"Feedback: {ev['feedback']}"
        )
        coaching_text = (
            f"{pq.get('encouragement', '')}\n\n"
            f"Top tip: {pq.get('top_tip', '')}\n\n"
            f"Better answer structure: {pq.get('better_answer_structure', '')}\n\n"
            f"Key talking point you missed: {pq.get('example_talking_point', '')}"
        )
        final_answers.append(AnswerRecord(
            question=ans["question"],
            answer=ans["answer"],
            score=ev["score"],
            evaluation=evaluation_text,
            coaching=coaching_text,
            answered_at=ans.get("answered_at", datetime.utcnow()),
        ))

    avg_score = (
        round(
            sum(a.score for a in final_answers) / len(final_answers),
            1
        )
        if final_answers
        else 0.0
    )
    overall_feedback = (
        f"{coaching.get('overall_feedback', '')}\n\n"
        f"Hire confidence: {coaching.get('hire_confidence', '?')}% | "
        f"Verdict: {coaching.get('overall_verdict', '?')}\n\n"
        f"Top strength: {coaching.get('top_strength', '')}\n\n"
        f"Critical improvement: {coaching.get('critical_improvement', '')}\n\n"
        f"Growth roadmap:\n" + "\n".join(
            f"- {s}"
            for s in coaching.get(
                "roadmap",
                []
            )
        ) +
        f"\n\nNext steps: {coaching.get('next_steps', '')}"
    )

    db.sessions.update_one(
        {"_id": oid},
        {"$set": {
            "answers": [a.model_dump() for a in final_answers],

            "overall_feedback": overall_feedback,

            "average_score": avg_score,

            "hire_confidence":
                coaching.get("hire_confidence"),

            "overall_verdict":
                coaching.get("overall_verdict"),

            "top_strength":
                coaching.get("top_strength"),

            "critical_improvement":
                coaching.get(
                    "critical_improvement"
                ),

            "job_fit_score":
                coaching.get(
                    "job_fit_score"
                ),

            "roadmap":
                coaching.get(
                    "roadmap",
                    []
                ),

            "per_question":
                coaching.get(
                    "per_question",
                    []
                ),

            "status": "completed",

            "completed_at":
                datetime.utcnow(),
        }}
    )

    return CompleteSessionResponse(
        session_id=body.session_id,

        average_score=avg_score,

        overall_feedback=overall_feedback,

        hire_confidence=
            coaching.get(
                "hire_confidence"
            ),

        overall_verdict=
            coaching.get(
                "overall_verdict"
            ),

        top_strength=
            coaching.get(
                "top_strength"
            ),

        critical_improvement=
            coaching.get(
                "critical_improvement"
            ),

        job_fit_score=
            coaching.get(
                "job_fit_score"
            ),

        roadmap=
            coaching.get(
                "roadmap",
                []
            ),

        per_question=
            coaching.get(
                "per_question",
                []
            ),

        answers=final_answers,
    )

# ── 6. History — pure DB read ──────────────────────────────────────────────────

@router.get("/history")
async def get_history(current_user: dict = Depends(get_current_user)):
    db = get_db()
    cursor = db.sessions.find(
        {
            "user_id": str(current_user["_id"]),
            "status": "completed"
        },
        {
            "questions": 0,
            "answers": 0,
            "profile_summary": 0,
        },
    ).sort("completed_at", -1).limit(20)

    sessions = []
    for s in cursor:
        sessions.append({
            "session_id": str(s["_id"]),
            "interview_type": s["interview_type"],
            "difficulty": s["difficulty"],
            "status": s["status"],
            "average_score": s.get("average_score"),
            "hire_confidence": s.get("hire_confidence"),
            "overall_verdict": s.get("overall_verdict"),
            "started_at": s.get("started_at"),
            "completed_at": s.get("completed_at"),
        })
    return sessions    



# ── 4. get session id Qs ──────────────────────────────────────────────────
@router.get(
    "/{session_id}",
    response_model=SessionDetailResponse,
)
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(session_id)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid session_id",
        )

    db = get_db()

    session = db.sessions.find_one({
        "_id": oid,
        "user_id": str(current_user["_id"]),
    })

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    return SessionDetailResponse(
        session_id=str(session["_id"]),
        interview_type=session["interview_type"],
        difficulty=session["difficulty"],
        focus_area=session.get("focus_area"),

        questions=session["questions"],

        current_index=session["current_index"],

        status=session["status"],
    )


# ── 5. Summary — pure DB read ──────────────────────────────────────────────────

@router.get("/{session_id}/summary", response_model=SessionSummaryResponse)
async def get_summary(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(session_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    db = get_db()
    session = db.sessions.find_one({
        "_id": oid,
        "user_id": str(current_user["_id"]),
    })
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    answers = session.get("answers", [])
    scores = [a["score"] for a in answers if a.get("score") is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    return SessionSummaryResponse(
        session_id=session_id,
        interview_type=session["interview_type"],
        total_questions=len(session["questions"]),
        average_score=avg_score,
        answers=[AnswerRecord(**a) for a in answers],
        overall_feedback=session.get("overall_feedback"),
        completed_at=session.get("completed_at"),
        hire_confidence=session.get(
            "hire_confidence"
        ),

        overall_verdict=session.get(
            "overall_verdict"
        ),

        top_strength=session.get(
            "top_strength"
        ),

        critical_improvement=session.get(
            "critical_improvement"
        ),

        job_fit_score=session.get(
            "job_fit_score"
        ),

        roadmap=session.get(
            "roadmap",
            []
        ),

        per_question=session.get(
            "per_question",
            []
        ),
            )


