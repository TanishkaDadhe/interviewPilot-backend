"""
PROMPT 3 — Bulk Evaluator Agent

Evaluates ALL answers in a single Gemini call.

Called ONCE after the final answer is submitted.
"""

import json
import google.generativeai as genai

from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")


def evaluate_all_answers(
    qa_pairs: list[dict],
    target_role: str = "Software Engineer",
    profile_summary: dict | None = None,
) -> list[dict]:
    """
    Evaluates ALL question-answer pairs in one Gemini call.

    Input:
        [
            {
                "question": "...",
                "answer": "..."
            }
        ]

    Output:
        [
            {
                "question_index": 1,
                "score": 8,
                ...
            }
        ]
    """

    profile_summary = profile_summary or {}

    seniority = profile_summary.get(
        "seniority_level",
        "mid"
    )

    strengths = ", ".join(
        profile_summary.get("strengths", [])
    ) or "None identified"

    weak_areas = ", ".join(
        profile_summary.get("weak_areas", [])
    ) or "None identified"

    missing_skills = ", ".join(
        profile_summary.get("missing_skills", [])
    ) or "None identified"

    qa_block = ""

    for i, qa in enumerate(qa_pairs, start=1):
        qa_block += f"""

Q{i}: {qa['question']}

A{i}: {qa['answer']}
"""

    prompt = f"""
You are a senior interviewer evaluating a completed interview.

========================
ROLE CONTEXT
========================

Target Role:
{target_role}

Candidate Seniority:
{seniority}

Known Strengths:
{strengths}

Known Weak Areas:
{weak_areas}

Known Missing Skills:
{missing_skills}

========================
INTERVIEW TRANSCRIPT
========================

{qa_block.strip()}

========================
EVALUATION INSTRUCTIONS
========================

Evaluate EACH answer independently.

Consider:

- Candidate seniority
- Target role expectations
- Claimed strengths
- Known weak areas
- Missing skills
- Accuracy
- Depth
- Communication quality
- Practical understanding

Scoring Guide:

9-10
Exceptional. Demonstrates mastery.

7-8
Strong. Good depth and accuracy.

5-6
Average. Basic understanding but lacks depth.

3-4
Weak. Significant gaps.

1-2
Poor. Incorrect or largely irrelevant.

========================
RETURN FORMAT
========================

Return ONLY a JSON array with exactly {len(qa_pairs)} objects.

[
  {{
    "question_index": 1,
    "score": 8,
    "verdict": "strong",
    "what_was_good": "...",
    "what_was_missing": "...",
    "ideal_answer_summary": "...",
    "feedback": "..."
  }}
]

No markdown.
No explanation.
Only JSON.
""".strip()
    
    print("=== EVALUATOR START ===")
    response = model.generate_content(prompt)
    print("=== EVALUATOR DONE ===")

    text = (
        response.text.strip()
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        evaluations = json.loads(text)

        if (
            not isinstance(evaluations, list)
            or len(evaluations) != len(qa_pairs)
        ):
            raise ValueError("Invalid evaluation format")

        return evaluations

    except Exception:

        return [
            {
                "question_index": i + 1,
                "score": 5,
                "verdict": "average",
                "what_was_good": "",
                "what_was_missing": "",
                "ideal_answer_summary": "",
                "feedback": "Evaluation unavailable."
            }
            for i in range(len(qa_pairs))
        ]


def evaluate_answer(
    question: str,
    answer: str,
    role: str = "Software Engineer"
) -> dict:
    """
    Backward-compatible wrapper.
    """

    results = evaluate_all_answers(
        qa_pairs=[
            {
                "question": question,
                "answer": answer
            }
        ],
        target_role=role,
    )

    result = results[0]

    return {
        "score": result["score"],
        "verdict": result["verdict"],
        "what_was_good": result["what_was_good"],
        "what_was_missing": result["what_was_missing"],
        "ideal_answer_summary": result["ideal_answer_summary"],
        "feedback": result["feedback"],
    }