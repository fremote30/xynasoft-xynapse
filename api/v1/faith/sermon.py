from fastapi import APIRouter
from pydantic import BaseModel
import json
import re

from api.services.ai_service import generate_ai_response

router = APIRouter()


# ================================
# REQUEST MODEL
# ================================
class SermonRequest(BaseModel):
    input: str
    bible: str = ""
    theme: str = ""
    denomination: str = "general"
    audience: str = ""
    context: str = ""
    service_type: str = ""
    tone: str = ""
    duration: str = ""
    mode: str = "default"


# ================================
# MODE HANDLING
# ================================
def get_mode_instruction(mode: str):
    return {
        "expand": "Expand deeply with detailed teaching.",
        "simplify": "Make it simple and clear.",
        "illustrate": "Add strong real-life illustrations.",
        "preach": "Make it powerful and preach-ready."
    }.get(mode, "Balanced sermon.")


# ================================
# STRICT PROMPT (IMPROVED)
# ================================
def build_prompt(data: SermonRequest):

    return f"""
You are a STRICT Christian sermon generator.

INPUTS:
- Theme: "{data.theme}"
- Scripture: "{data.bible}"
- Message: "{data.input}"

RULES:
1. Theme MUST dominate entire sermon
2. Scripture MUST be used clearly
3. Message MUST influence direction
4. DO NOT default to generic topics

STRUCTURE:
- Title
- Introduction
- 3–5 Points
- Conclusion

RETURN JSON ONLY:

{{
  "title": "...",
  "scripture": "...",
  "introduction": "...",
  "points": [
    {{
      "title": "...",
      "scriptures": ["..."],
      "message": "...",
      "application": "..."
    }}
  ],
  "conclusion": "..."
}}
"""


# ================================
# JSON EXTRACTION
# ================================
def extract_json(text: str):
    try:
        return json.loads(text)
    except:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())

    raise Exception("Invalid JSON")


# ================================
# NORMALIZE OUTPUT
# ================================
def normalize_output(data: dict):

    data.setdefault("title", "")
    data.setdefault("scripture", "")
    data.setdefault("introduction", "")
    data.setdefault("points", [])
    data.setdefault("conclusion", "")

    clean_points = []

    for p in data["points"]:
        if isinstance(p, str):
            clean_points.append({
                "title": "",
                "scriptures": [],
                "message": p,
                "application": ""
            })
        else:
            clean_points.append({
                "title": p.get("title", ""),
                "scriptures": p.get("scriptures", []),
                "message": p.get("message") or "",
                "application": p.get("application", "")
            })

    data["points"] = clean_points
    return data


# ================================
# VALIDATION (BALANCED + STRONG)
# ================================
def validate_sermon(sermon, data):

    text = json.dumps(sermon).lower()

    # Theme check
    if data.theme and data.theme.lower() not in text:
        return False, "Theme missing"

    # Scripture check
    if data.bible:
        keyword = data.bible.split()[0].lower()
        if keyword not in text:
            return False, "Scripture missing"

    # Message check (NEW 🔥)
    if data.input:
        words = data.input.lower().split()[:3]
        if not any(w in text for w in words):
            return False, "Message not used"

    # Structure check
    if len(sermon.get("points", [])) < 3:
        return False, "Too few points"

    return True, "OK"


# ================================
# FALLBACK
# ================================
def fallback_sermon(data: SermonRequest):
    return {
        "title": f"{data.theme or 'Sermon'} (Fallback)",
        "scripture": data.bible or "",
        "introduction": "Reflect on this topic.",
        "points": [
            {
                "title": "Core Idea",
                "scriptures": [],
                "message": "Stay grounded in God's word.",
                "application": "Apply this daily."
            }
        ],
        "conclusion": "God is faithful."
    }


# ================================
# MAIN API (FINAL STABLE VERSION)
# ================================
@router.post("/sermon")
@router.post("/faith/sermon")
@router.post("/api/faith/sermon")
async def generate_sermon(data: SermonRequest):

    try:
        MAX_RETRIES = 3
        base_prompt = build_prompt(data)
        prompt = base_prompt

        for attempt in range(MAX_RETRIES):

            print(f"\n🚀 ATTEMPT {attempt+1}")

            ai_response = generate_ai_response(prompt)
            print("🔥 RAW:", ai_response)

            try:
                parsed = extract_json(ai_response)
            except:
                continue

            parsed = normalize_output(parsed)

            is_valid, reason = validate_sermon(parsed, data)

            if is_valid:
                print("✅ VALID")
                return parsed

            print("❌ FAILED:", reason)

            # 🔥 IMPROVED RETRY (FIXED)
            prompt = base_prompt + f"""

CORRECTION:
Previous output failed: {reason}

STRICT:
- Focus ONLY on "{data.theme}"
- Use "{data.bible}"
- Use message "{data.input}"

Retry correctly.
"""

        print("🔥 FALLBACK USED")
        return fallback_sermon(data)

    except Exception as e:
        print("🔥 ERROR:", e)
        return fallback_sermon(data)