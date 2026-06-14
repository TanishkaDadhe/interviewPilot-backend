"""
PROMPT 4 — Bulk Coach Agent

Takes ALL questions + answers + evaluations at once
and generates a complete coaching report.

Called ONCE after evaluation completes.
"""

import json
from utils.gemini_helper import generate_gemini


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
            roadmap
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
You are a friendly and honest interview coach helping a candidate improve.

You have just reviewed their mock interview. Now write a coaching report.

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
LANGUAGE STYLE — VERY IMPORTANT
========================

Write everything in simple, clear, everyday English.

Rules:
- Imagine you are talking to a friend who just finished a practice interview.
- Use short sentences. No long paragraphs.
- Avoid jargon, buzzwords, and complicated words.
- Be honest, but kind. Not harsh or robotic.
- Every piece of advice must be specific to what this candidate actually said — not generic.
- The roadmap steps must be simple, concrete actions anyone can understand and start tomorrow.

Bad roadmap example (too vague and complicated):
"Enhance your articulation of system design trade-offs by engaging with distributed systems literature."

Good roadmap example (simple and actionable):
"Practice explaining system design out loud. Pick one topic like caching or load balancing and explain it to yourself or a friend in 2 minutes."

========================
COACHING RULES
========================

- Be specific. Reference actual things the candidate said or missed.
- Every tip must help them do better in a real interview.
- Focus on: how they communicated, how deep their answers were, what concepts they missed, and what a real interviewer would think.

========================
RETURN FORMAT
========================

Return ONLY valid JSON.

{{
  "overall_feedback":
    "3-4 sentences. Plain summary of how the interview went. Talk about their communication style, answer quality, and main strengths and weaknesses. Keep it simple and direct. Do NOT include hire verdict, scores, or roadmap here.",

  "overall_verdict":
    "hire|lean_hire|lean_no_hire|no_hire",

  "hire_confidence":
    0,

  "job_fit_score": 0,

  "top_strength":
    "One short phrase — their single best skill shown in this interview.",

  "critical_improvement":
    "One short phrase — the single most important thing they need to work on.",

  "per_question": [
    {{
      "question_index": 1,

      "encouragement":
        "One or two sentences. Say something specific and genuine they did well.",

      "top_tip":
        "One clear, simple thing they should do differently next time for this type of question.",

      "better_answer_structure":
        "In plain English, explain how they should have structured their answer. Keep it short.",

      "example_talking_point":
        "One specific thing they forgot to mention that would have made their answer much stronger.",

      "ideal_answer_framework": "Show a short improved version of the answer — only the parts they missed or should have said better. Do NOT repeat what they already said correctly."
    }}
  ],

  "roadmap": [
    "5 steps. Each step is one simple, specific action they can take this week to improve before their next interview. Write like you are texting a friend advice. No bullet formatting inside the string — just plain text."
  ]

}}

The per_question array must contain exactly {len(qa_evaluations)} items.

Return ONLY JSON.
No markdown.
No explanation.
""".strip()
    
    print("=== COACH START ===")
    text = generate_gemini(prompt)
    print("=== COACH DONE ===")

    text = (
        text.strip()
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

            "job_fit_score": job_fit_score,

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
                        "",

                    "ideal_answer_framework": ""
                }
                for i in range(len(qa_evaluations))
            ],

            "roadmap": [],

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
                    "",

                "ideal_answer_framework":
                    ""
            }
        )

    coaching["per_question"] = coaching["per_question"][:len(qa_evaluations)]
    coaching.setdefault(
        "job_fit_score",
        job_fit_score
    )

    coaching.setdefault(
        "roadmap",
        []
    )

    coaching.setdefault(
        "top_strength",
        ""
    )

    coaching.setdefault(
        "critical_improvement",
        ""
    )

    coaching.setdefault(
        "hire_confidence",
        50
    )

    coaching.setdefault(
        "overall_verdict",
        "lean_no_hire"
    )

    coaching.setdefault(
        "overall_feedback",
        "No feedback available."
    )


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