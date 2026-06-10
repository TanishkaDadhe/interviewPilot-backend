"""
PROMPT 1 — Profile Agent

Analyzes:
- Resume
- Job Description
- Skills
- Experience
- Education

Runs ONCE when interview starts.

Output is stored in the interview session and reused by:
- Question Agent
- Evaluator Agent
- Coach Agent

This prevents repeated profile analysis API calls.
"""

import json
import google.generativeai as genai

from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")


def build_profile_summary(user_data: dict) -> dict:
    """
    Creates a structured candidate profile.

    Inputs:
    - resume_text
    - job_description
    - skills
    - experience
    - education

    Returns:
    Structured JSON profile used throughout the interview.
    """

    resume_section = ""
    if user_data.get("resume_text"):
        resume_section = f"""
RESUME:
{user_data["resume_text"][:5000]}
"""

    job_section = ""
    if user_data.get("job_description"):
        job_section = f"""
TARGET JOB DESCRIPTION:
{user_data["job_description"][:5000]}
"""

    experience_text = ""

    if user_data.get("experience"):
        exp = user_data["experience"]

        if isinstance(exp, list):
            experience_text = "\n".join(
                f"- {e.get('role', '?')} at {e.get('company', '?')} "
                f"({e.get('duration', '?')}): "
                f"{e.get('description', '')}"
                for e in exp
            )
        else:
            experience_text = str(exp)

    prompt = f"""
You are a senior technical recruiter, hiring manager, and interview coach.

Analyze BOTH:

1. Candidate Resume
2. Target Job Description

Think like a real recruiter preparing an interview panel.

If manually entered profile data conflicts with resume evidence,
prefer the resume.

Determine:

- Candidate strengths
- Candidate weaknesses
- Missing skills relative to the job description
- Realistic seniority level
- Job fit score (0-100)
- Interview topics that should be prioritized
- What interviewers will focus on
- Appropriate interview difficulty

========================
CANDIDATE INFORMATION
========================

Name:
{user_data.get("name", "Unknown")}

Target Role:
{user_data.get("target_role", "Software Engineer")}

Skills:
{", ".join(user_data.get("skills", [])) or "Not specified"}

Education:
{user_data.get("education", "Not specified")}

Experience:
{experience_text or "Not provided"}

{resume_section}

{job_section}

========================
RETURN FORMAT
========================

Return ONLY valid JSON.

{{
  "summary": "3 sentence professional summary",

  "seniority_level": "junior|mid|senior|lead",

  "job_fit_score": 0,

  "role_match_explanation":
    "Short explanation of why this fit score was assigned",

  "strengths": [
    "strength 1",
    "strength 2",
    "strength 3"
  ],

  "weak_areas": [
    "weakness 1",
    "weakness 2"
  ],

  "missing_skills": [
    "skill missing from job description",
    "another missing skill"
  ],

  "priority_topics": [
    {{
      "topic": "FastAPI",
      "importance": 10
    }},
    {{
      "topic": "MongoDB",
      "importance": 9
    }}
  ],

  "key_topics_to_cover": [
    "FastAPI",
    "MongoDB",
    "REST APIs"
  ],

  "recommended_question_types": [
    "technical",
    "behavioral",
    "system_design",
    "situational"
  ],

  "question_distribution": {{
    "technical": 60,
    "behavioral": 20,
    "system_design": 20
  }},

  "difficulty_recommendation": "easy|medium|hard",

  "interviewer_focus":
    "1-2 sentence explanation of what interviewers should focus on"
}}

Return ONLY JSON.
No markdown.
No explanation.
No code block.
""".strip()
    
    print("=== PROFILE START ===")
    response = model.generate_content(prompt)
    print("=== PROFILE DONE ===")

    text = (
        response.text.strip()
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        return json.loads(text)

    except Exception:
        return {
            "summary": "",
            "seniority_level": "mid",
            "job_fit_score": 50,
            "role_match_explanation": "",

            "strengths": [],
            "weak_areas": [],
            "missing_skills": [],

            "priority_topics": [],
            "key_topics_to_cover": [],

            "recommended_question_types": [
                "technical"
            ],

            "question_distribution": {
                "technical": 100
            },

            "difficulty_recommendation": "medium",

            "interviewer_focus": ""
        }