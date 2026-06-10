"""
PROMPT 4 — Bulk Coach Agent

Takes ALL questions + answers + evaluations at once
and generates a complete coaching report.

Called ONCE after evaluation completes.
"""

import json
import google.generativeai as genai

from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")


def coach_all_answers(
    qa_evaluations: list[dict],
    target_role: str = "Software Engineer",
    profile_summary: dict | None = None,
) -> dict:
    """
    Input:
        Full interview transcript with evaluations.

    Output:
        {
            overall_feedback,
            overall_verdict,
            hire_confidence,
            top_strength,
            critical_improvement,
            per_question,
            study_plan,
            next_steps
        }
    """

    profile_summary = profile_summary or {}

    seniority = profile_summary.get(
        "seniority_level",
        "mid"
    )

    strengths = profile_summary.get(
        "strengths",
        []
    )

    weak_areas = profile_summary.get(
        "weak_areas",
        []
    )

    missing_skills = profile_summary.get(
        "missing_skills",
        []
    )

    job_fit_score = profile_summary.get(
        "job_fit_score",
        50
    )

    avg_score = (
        round(
            sum(item["score"] for item in qa_evaluations)
            / len(qa_evaluations),
            1
        )
        if qa_evaluations
        else 0.0
    )

    transcript = ""

    for i, item in enumerate(qa_evaluations, start=1):
        transcript += f"""

--- Question {i} ---

Q: {item['question']}

A: {item['answer']}

Score: {item['score']}/10

Verdict: {item['verdict']}

What was good:
{item['what_was_good']}

What was missing:
{item['what_was_missing']}
"""

    prompt = f"""
You are a world-class interview coach.

You have reviewed a completed mock interview.

========================
ROLE CONTEXT
========================

Target Role:
{target_role}

Candidate Seniority:
{seniority}

Profile Job Fit Score:
{job_fit_score}/100

Known Strengths:
{", ".join(strengths) or "Not identified"}

Known Weak Areas:
{", ".join(weak_areas) or "Not identified"}

Known Missing Skills:
{", ".join(missing_skills) or "Not identified"}

Session Average Score:
{avg_score}/10

========================
FULL INTERVIEW TRANSCRIPT
========================

{transcript.strip()}

========================
COACHING RULES
========================

Provide coaching that is:

- Specific
- Actionable
- Personalized
- Honest

Do NOT give generic advice.

Every recommendation must reference actual weaknesses
observed in the candidate's answers.

Focus on:

- Communication
- Technical depth
- Missing concepts
- Interview strategy
- Seniority expectations

========================
RETURN FORMAT
========================

Return ONLY valid JSON.

{{
  "overall_feedback":
    "3-4 sentence summary",

  "overall_verdict":
    "hire|lean_hire|lean_no_hire|no_hire",

  "hire_confidence":
    0,

  "top_strength":
    "single strongest demonstrated skill",

  "critical_improvement":
    "single most important improvement",

  "per_question": [
    {{
      "question_index": 1,

      "encouragement":
        "specific compliment",

      "top_tip":
        "best improvement",

      "better_answer_structure":
        "specific structure advice",

      "example_talking_point":
        "something important they missed"
    }}
  ],

  "study_plan": [
    "topic 1",
    "topic 2",
    "topic 3"
  ],

  "next_steps":
    "exact next actions"
}}

The per_question array must contain exactly {len(qa_evaluations)} items.

Return ONLY JSON.
No markdown.
No explanation.
""".strip()
    
    print("=== COACH START ===")
    response = model.generate_content(prompt)
    print("=== COACH DONE ===")

    text = (
        response.text.strip()
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        coaching = json.loads(text)

    except Exception:

        coaching = {
            "overall_feedback":
                "Coaching unavailable.",

            "overall_verdict":
                "lean_no_hire",

            "hire_confidence":
                50,

            "top_strength":
                "",

            "critical_improvement":
                "",

            "per_question": [
                {
                    "question_index": i + 1,

                    "encouragement":
                        "",

                    "top_tip":
                        "Review this topic again.",

                    "better_answer_structure":
                        "",

                    "example_talking_point":
                        ""
                }
                for i in range(len(qa_evaluations))
            ],

            "study_plan": [],

            "next_steps":
                "Practice another mock interview."
        }

    coaching.setdefault("per_question", [])

    while len(coaching["per_question"]) < len(qa_evaluations):
        coaching["per_question"].append(
            {
                "question_index":
                    len(coaching["per_question"]) + 1,

                "encouragement":
                    "",

                "top_tip":
                    "Review this topic again.",

                "better_answer_structure":
                    "",

                "example_talking_point":
                    ""
            }
        )

    coaching["per_question"] = coaching["per_question"][:len(qa_evaluations)]

    return coaching


def get_coaching(
    question: str,
    answer: str,
    score: int,
    role: str = "Software Engineer"
) -> str:
    """
    Backward-compatible wrapper.
    """

    fake_eval = {
        "question": question,
        "answer": answer,
        "score": score,
        "verdict":
            "strong"
            if score >= 7
            else "average"
            if score >= 4
            else "weak",

        "what_was_good": "",
        "what_was_missing": "",
    }

    result = coach_all_answers(
        [fake_eval],
        target_role=role,
    )

    pq = result.get("per_question", [{}])[0]

    return pq.get(
        "top_tip",
        result.get(
            "critical_improvement",
            ""
        )
    )