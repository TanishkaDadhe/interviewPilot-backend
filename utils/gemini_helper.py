from fastapi import HTTPException
import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")


def generate_gemini(prompt: str):
    try:
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        error = str(e)

        print("Gemini Error:", error)

        if (
            "429" in error
            or "RESOURCE_EXHAUSTED" in error
            or "quota" in error.lower()
        ):
            raise HTTPException(
                status_code=429,
                detail="AI service daily quota is exhausted. Please try again in 24 hours."
            )

        raise HTTPException(
            status_code=500,
            detail="AI generation failed."
        )