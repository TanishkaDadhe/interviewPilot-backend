from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form
import pdfplumber
import io

from database.connection import get_db
from models.user import ProfileUpdateRequest
from routes.auth import get_current_user

router = APIRouter()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Return full profile for the logged-in user."""
    return {
        "user_id": str(current_user["_id"]),
        "name": current_user["name"],
        "email": current_user["email"],
        "target_role": current_user.get("target_role"),
        "skills": current_user.get("skills", []),
        "experience": current_user.get("experience", []),
        "education": current_user.get("education"),
        "resume_text": current_user.get("resume_text"),
        "job_description": current_user.get("job_description"),
    }


@router.put("/")
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update profile fields only. No AI calls."""

    update_fields = body.model_dump(exclude_none=True)

    # Convert ExperienceEntry objects → plain dicts for Mongo
    if "experience" in update_fields:
        update_fields["experience"] = [
            e if isinstance(e, dict) else e.model_dump()
            for e in update_fields["experience"]
        ]

    db = get_db()

    db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": update_fields},
    )

    return {
        "message": "Profile updated",
        "fields_updated": list(update_fields.keys())
    }


@router.post("/setup")
async def setup_profile(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload resume PDF + job description together.
    Stores both in MongoDB.
    No AI calls.
    """

    if not resume.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    contents = await resume.read()

    try:
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            resume_text = "\n".join(
                page.extract_text() or ""
                for page in pdf.pages
            ).strip()

    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Could not parse PDF: {e}"
        )

    if not resume_text:
        raise HTTPException(
            status_code=422,
            detail="PDF appears to be empty or scanned"
        )

    db = get_db()

    db.users.update_one(
        {"_id": current_user["_id"]},
        {
            "$set": {
                "resume_text": resume_text,
                "job_description": job_description,
            }
        }
    )

    return {
        "message": "Resume and job description saved",
        "resume_characters": len(resume_text),
        "job_description_characters": len(job_description),
    }
   