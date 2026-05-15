import os
import json
from dotenv import load_dotenv

# OpenAI
from openai import OpenAI

# Claude (Anthropic)
import anthropic

load_dotenv()

# ================================
# ENV CONFIG
# ================================
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


# ================================
# SYSTEM PROMPT (UPGRADED)
# ================================
SYSTEM_PROMPT = """
You are a Spirit-led Christian sermon assistant helping pastors.

CORE PRINCIPLES:
- Do NOT replace spiritual inspiration
- Help organize what God has placed in their heart
- Respect denomination theology
- Maintain a natural pastoral tone (not robotic)
- Be clear, structured, and spiritually grounded

CRITICAL OUTPUT RULE:
- ALWAYS return valid JSON ONLY
- DO NOT include explanations, markdown, or extra text
"""


# ================================
# CLEAN JSON RESPONSE (🔥 CRITICAL)
# ================================
def clean_json_response(text: str):
    """
    Removes markdown wrappers like ```json and fixes common issues
    """

    if not text:
        return text

    text = text.strip()

    # Remove ```json blocks
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    # Try to extract JSON block if extra text exists
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        text = text[start:end + 1]

    return text


# ================================
# OPENAI
# ================================
def call_openai(prompt):
    if not openai_client:
        raise Exception("OpenAI not configured")

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        content = response.choices[0].message.content
        return clean_json_response(content)

    except Exception as e:
        print("OpenAI error:", e)
        raise e


# ================================
# CLAUDE
# ================================
def call_claude(prompt):
    if not claude_client:
        raise Exception("Claude not configured")

    try:
        response = claude_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            temperature=0.7,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        content = response.content[0].text
        return clean_json_response(content)

    except Exception as e:
        print("Claude error:", e)
        raise e


# ================================
# VALIDATE JSON (🔥 SAFETY)
# ================================
def validate_json_output(text: str):
    try:
        return json.loads(text)
    except Exception as e:
        print("JSON validation failed:", e)
        return None


# ================================
# MAIN ROUTER (SMART ENGINE)
# ================================
def generate_ai_response(prompt, mode=None):

    """
    Smart routing:
    - Expository → Claude
    - Default → ENV provider
    - Fallback → alternate provider
    """

    try:
        # SPECIAL MODE
        if mode == "expository" and claude_client:
            raw = call_claude(prompt)
        else:
            if AI_PROVIDER == "claude":
                raw = call_claude(prompt)
            else:
                raw = call_openai(prompt)

        # Validate JSON
        parsed = validate_json_output(raw)

        if parsed:
            return raw

        raise Exception("Invalid JSON from primary AI")

    except Exception as primary_error:
        print("Primary AI failed:", primary_error)

        # FALLBACK
        try:
            if AI_PROVIDER == "claude" and openai_client:
                raw = call_openai(prompt)
            elif claude_client:
                raw = call_claude(prompt)
            else:
                return '{"error": "No AI provider available"}'

            parsed = validate_json_output(raw)

            if parsed:
                return raw

            raise Exception("Fallback also failed JSON validation")

        except Exception as fallback_error:
            print("Fallback AI failed:", fallback_error)

            # FINAL SAFE RESPONSE
            return json.dumps({
                "title": "Sermon Generation Error",
                "main_message": "We encountered an issue generating your sermon. Please try again.",
                "scripture": [],
                "introduction": "",
                "outline": [],
                "closing": "",
                "prayer": ""
            })