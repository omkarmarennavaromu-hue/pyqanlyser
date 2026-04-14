import os
import json
import re
from openai import OpenAI

_client = None

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Free + capable model available on OpenRouter; change to any model you have access to
MODEL = "openai/gpt-4o-mini"


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENROUTER_API_KEY environment variable not set")
        _client = OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
        )
    return _client


def extract_mcqs(text: str) -> list[dict]:
    """
    Use GPT to parse raw exam text into structured MCQ JSON.
    Returns list of dicts: [{question, options, answer}]
    """
    client = _get_client()

    system_prompt = (
        "You are an expert exam question parser. "
        "Extract ALL multiple choice questions from the provided exam text. "
        "Return ONLY a valid JSON array with no extra commentary. "
        "Each element must have exactly these keys: "
        "\"question\" (string), \"options\" (array of 4 strings), \"answer\" (string). "
        "If options are labeled A/B/C/D or 1/2/3/4, include the label in the option string. "
        "If answer is not clear, set answer to empty string. "
        "Do NOT include markdown, code fences, or any text outside the JSON array."
    )

    user_prompt = f"Extract all MCQs from the following exam text:\n\n{text[:12000]}"

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = response.choices[0].message.content.strip()
    raw = _strip_code_fences(raw)

    try:
        mcqs = json.loads(raw)
        if not isinstance(mcqs, list):
            return []
        # Normalize each entry
        result = []
        for item in mcqs:
            if isinstance(item, dict) and "question" in item:
                result.append({
                    "question": str(item.get("question", "")),
                    "options": list(item.get("options", [])),
                    "answer": str(item.get("answer", "")),
                })
        return result
    except json.JSONDecodeError:
        return []


def tag_chapter(question: str) -> str:
    """
    Use GPT to identify the NCERT chapter (Class 11/12) for a given question.
    Returns chapter name as string.
    """
    if not question or len(question.strip()) < 5:
        return "Unknown"

    client = _get_client()

    system_prompt = (
        "You are an expert in NCERT Class 11 and Class 12 Physics, Chemistry, and Mathematics. "
        "Given an exam question, identify which NCERT chapter it belongs to. "
        "Return ONLY the chapter name (e.g., 'Thermodynamics', 'Organic Chemistry', 'Matrices'). "
        "Do NOT include class number, subject, or any explanation. "
        "If uncertain, return 'General'."
    )

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Question: {question[:500]}"},
        ],
    )

    chapter = response.choices[0].message.content.strip()
    # Strip quotes if any
    chapter = chapter.strip('"\'')
    # Limit length
    return chapter[:100] if chapter else "Unknown"


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences if present."""
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()
