import os
import json
import re
from openai import OpenAI

_client = None


# -----------------------------
# CLIENT INIT (SAFE)
# -----------------------------
def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY not set")
        _client = OpenAI(api_key=api_key)
    return _client


# -----------------------------
# MCQ EXTRACTION
# -----------------------------
def extract_mcqs(text: str) -> list[dict]:
    client = _get_client()

    # safer truncation (avoid breaking mid-context too badly)
    text = text[:10000]

    system_prompt = """
You are an expert exam parser.

Extract ALL MCQs from the text.

Return ONLY valid JSON array:
[
  {
    "question": "",
    "options": ["", "", "", ""],
    "answer": ""
  }
]

Rules:
- No markdown
- No explanations
- No extra text
- If unclear answer → empty string
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
    )

    raw = response.choices[0].message.content.strip()
    raw = _strip_code_fences(raw)

    parsed = _safe_json_parse(raw)

    if not isinstance(parsed, list):
        return []

    cleaned = []

    for item in parsed:
        if not isinstance(item, dict):
            continue

        if "question" not in item:
            continue

        cleaned.append({
            "question": str(item.get("question", "")).strip(),
            "options": list(item.get("options", []))[:4],
            "answer": str(item.get("answer", "")).strip()
        })

    return cleaned


# -----------------------------
# CHAPTER TAGGING (OPTIMIZED)
# -----------------------------
def tag_chapter_batch(questions: list[str]) -> list[str]:
    """
    MUCH BETTER: batch tagging instead of per-question API calls
    """
    client = _get_client()

    system_prompt = """
You are an NCERT expert.

Map each question to its chapter.

Return JSON array of chapter names only.
Example:
["Thermodynamics", "Matrices", "Organic Chemistry"]
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(questions[:20])},
        ],
    )

    raw = _strip_code_fences(response.choices[0].message.content.strip())

    parsed = _safe_json_parse(raw)

    if isinstance(parsed, list):
        return parsed

    return ["Unknown"] * len(questions)


# -----------------------------
# SAFE SINGLE TAG (fallback)
# -----------------------------
def tag_chapter(question: str) -> str:
    if not question or len(question.strip()) < 5:
        return "Unknown"

    client = _get_client()

    system_prompt = """
Return ONLY NCERT chapter name.
No explanation.
If unsure → General.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question[:300]},
        ],
    )

    chapter = response.choices[0].message.content.strip()
    return chapter.strip('"\'')[:80] if chapter else "Unknown"


# -----------------------------
# SAFE JSON PARSER (IMPORTANT)
# -----------------------------
def _safe_json_parse(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # attempt cleanup
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)
        try:
            return json.loads(text)
        except:
            return None


# -----------------------------
# STRIP CODE BLOCKS
# -----------------------------
def _strip_code_fences(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()
