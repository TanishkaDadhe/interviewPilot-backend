"""
PROMPT 2 — Question Generator Agent

Takes the profile_agent output + session configuration
and generates ALL interview questions in one Gemini call.

Runs ONCE per interview session.

Output:
[
    "Question 1",
    "Question 2",
    ...
]

Questions are stored in MongoDB and served one by one.
"""

import json
from utils.gemini_helper import generate_gemini


def generate_questions(
    profile_summary: dict,
    interview_type: str,
    difficulty: str,
    num_questions: int,
    focus_area: str | None = None,
    target_role: str = "Software Engineer",
) -> list[str]:
    """
    Generates all interview questions in a single prompt.

    Inputs:
    - profile_summary (from profile_agent)
    - interview configuration

    Returns:
    List[str]
    """

    strengths = "\n".join(
        f"  - {s}"
        for s in profile_summary.get("strengths", [])
    ) or "Not identified"

    weak_areas = "\n".join(
        f"  - {w}"
        for w in profile_summary.get("weak_areas", [])
    ) or "Not identified"

    missing_skills = "\n".join(
        f"  - {s}"
        for s in profile_summary.get("missing_skills", [])
    ) or "None identified"

    key_topics = "\n".join(
        f"  - {t}"
        for t in profile_summary.get("key_topics_to_cover", [])
    ) or "General role topics"

    seniority = profile_summary.get(
        "seniority_level",
        "mid"
    )

    interviewer_focus = profile_summary.get(
        "interviewer_focus",
        ""
    )

    job_fit_score = profile_summary.get(
        "job_fit_score",
        50
    )

    recommended_difficulty = profile_summary.get(
        "difficulty_recommendation",
        "medium"
    )

    focus_line = (
        f"\nSpecific focus area requested: {focus_area}"
        if focus_area else ""
    )

    type_instructions = {
        "technical":
            "Focus on technical knowledge, coding concepts, architecture decisions, APIs, databases, debugging, and problem-solving.",

        "behavioral":
            "Focus on real experiences using STAR format (Situation, Task, Action, Result).",

        "hr":
            "Focus on motivation, communication, teamwork, culture fit, career goals, strengths, weaknesses, and professionalism.",

        "mixed":
            "Create a balanced mix of technical, behavioral, HR, and situational questions.",
    }.get(
        interview_type,
        "Create a balanced mix of technical and behavioral questions."
    )

    difficulty_guidance = {
        "easy":
            "Foundational questions suitable for beginners and junior candidates.",

        "medium":
            "Industry-standard interview questions requiring practical knowledge and experience.",

        "hard":
            "Senior-level questions requiring deep expertise, trade-offs, architecture thinking, and leadership experience.",
    }.get(
        difficulty,
        "Industry-standard interview difficulty."
    )

    prompt = f"""
You are a friendly but thorough interviewer at a technology company.

Generate realistic interview questions for a:

ROLE: {target_role}

========================
PROFILE ANALYSIS
========================

Seniority:
{seniority}

Job Fit Score:
{job_fit_score}/100

Strengths:
{strengths}

Weak Areas:
{weak_areas}

Missing Skills:
{missing_skills}

Key Topics:
{key_topics}

Interviewer Focus:
{interviewer_focus}

========================
INTERVIEW CONFIGURATION
========================

Interview Type:
{interview_type}

Instructions:
{type_instructions}

Requested Difficulty:
{difficulty}

Recommended Difficulty:
{recommended_difficulty}

Difficulty Guidance:
{difficulty_guidance}

Number of Questions:
{num_questions}

{focus_line}

========================
QUESTION RULES
========================

Generate exactly {num_questions} questions.

Requirements:

1. Write questions in plain, simple English — like a real person talking, not a textbook.
2. Keep each question short and clear. One idea per question. No jargon unless necessary.
3. Validate candidate strengths with natural follow-up style questions.
4. Probe weak areas and missing skills.
5. Match the candidate's seniority level.
6. Cover important role-specific topics.
7. Mix conceptual, practical, situational, and experience-based questions.
8. No filler questions.
9. No multi-part questions.
10. Order questions from easier to harder.
11. Include at least one question targeting the strongest claimed skill.
12. Include at least {max(1, num_questions // 3)} questions targeting weak areas or skill gaps.

LANGUAGE STYLE:
- Use everyday words. Avoid corporate buzzwords.
- Questions should feel like a friendly but serious conversation.
- Bad example: "Articulate the architectural trade-offs you navigated when designing distributed systems."
- Good example: "Can you walk me through a time you had to choose between two different system designs? What made you go with one over the other?"

Return ONLY a JSON array.

Example:
[
  "Tell me about a challenging API you designed.",
  "How does dependency injection work in FastAPI?"
]

No markdown.
No explanations.
No numbering.
No extra text.
""".strip()
    
    print("=== QUESTION START ===")
    text = generate_gemini(prompt)
    print("=== QUESTION DONE ===")

    text = (
        text.strip()
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        questions = json.loads(text)

        if not isinstance(questions, list):
            raise ValueError("Response is not a list")

        questions = [str(q).strip() for q in questions]

        return questions[:num_questions]

    except Exception:
        return [
            f"Tell me about your experience related to {target_role}."
            for _ in range(num_questions)
        ]