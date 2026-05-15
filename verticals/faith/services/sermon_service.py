from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

import httpx

from verticals.faith.prompts.manuscript_prompt import build_manuscript_prompt
from verticals.faith.prompts.sermon_prompt import build_sermon_prompt
from verticals.faith.rules.guardrails import contains_disallowed
from verticals.faith.schemas.sermon_input import SermonInput
from verticals.faith.schemas.sermon_manuscript import ManuscriptResponse
from verticals.faith.schemas.sermon_output import SermonOutput

OPENAI_MODEL = os.getenv("XYNASOFT_FAITH_MODEL", "gpt-4.1-mini")
VERSION = os.getenv("XYNASOFT_FAITH_VERSION", "v0.1 Ghana Beta")
PLATFORM = "Xynapse Faith"


# -------------------------
# LLM Call (Responses API)
# -------------------------
async def _call_openai(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "input": prompt,
            },
        )
        r.raise_for_status()
        data = r.json()

    # Extract output_text (Responses API format)
    out0 = (data.get("output") or [{}])[0]
    contents = out0.get("content") or []
    for c in contents:
        if c.get("type") == "output_text":
            return (c.get("text", "") or "").strip()

    raise RuntimeError("No output_text returned from model")


# -------------------------
# JSON Robust Parsing
# -------------------------
def _extract_json_object(text: str) -> str:
    """
    Try to extract the first valid JSON object from the model output.
    Handles cases where the model wraps JSON with extra text.
    """
    if not text:
        raise ValueError("Empty model response")

    s = text.strip()

    # Fast-path: already JSON
    if s.startswith("{") and s.endswith("}"):
        return s

    # Find first {...} block (simple brace matching)
    start = s.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model output")

    depth = 0
    in_str = False
    esc = False

    for i in range(start, len(s)):
        ch = s[i]

        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]

    raise ValueError("Could not extract a complete JSON object from model output")


def _parse_json_or_retry(raw_text: str, *, context_label: str) -> Dict[str, Any]:
    """
    Parse JSON robustly. If it fails, attempt extraction and re-parse.
    """
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        extracted = _extract_json_object(raw_text)
        try:
            return json.loads(extracted)
        except json.JSONDecodeError as e:
            preview = (raw_text or "")[:800]
            raise ValueError(f"{context_label}: Model did not return valid JSON. Raw preview: {preview}") from e


# -------------------------
# Sermon Outline
# -------------------------
async def generate_sermon(payload: SermonInput) -> SermonOutput:
    prompt = build_sermon_prompt(payload)
    raw_text = await _call_openai(prompt)

    parsed = _parse_json_or_retry(raw_text, context_label="Sermon outline")
    sermon = SermonOutput.model_validate(parsed)

    # Add metadata (trust + debugging)
    sermon.metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": OPENAI_MODEL,
        "platform": PLATFORM,
        "version": VERSION,
        "denomination": getattr(payload, "denomination", "Broad Christian (default)"),
        "passages": payload.resolved_passages(),
    }

    # Guardrail scan
    combined_text = json.dumps(sermon.model_dump(), ensure_ascii=False)
    hits = contains_disallowed(combined_text)
    if hits:
        raise ValueError(f"Guardrail triggered: {hits}")

    # Ensure 3–5 points (soft enforcement)
    pts = sermon.sermon_structure.main_points
    if len(pts) < 3:
        raise ValueError("Output has fewer than 3 sermon points. Please regenerate/refine prompt.")
    if len(pts) > 5:
        sermon.sermon_structure.main_points = pts[:5]

    return sermon


# -------------------------
# Manuscript Expansion
# -------------------------
async def generate_manuscript(
    sermon_input: SermonInput,
    sermon_outline: SermonOutput,
) -> ManuscriptResponse:
    """
    Expands an outline into a structured manuscript with timings.
    Uses multi-passage inputs via sermon_input.resolved_passages().
    """
    prompt = build_manuscript_prompt(sermon_input, sermon_outline)
    raw_text = await _call_openai(prompt)

    parsed = _parse_json_or_retry(raw_text, context_label="Manuscript")
    manuscript = ManuscriptResponse.model_validate(parsed)

    # Guardrail scan
    combined_text = json.dumps(manuscript.model_dump(), ensure_ascii=False)
    hits = contains_disallowed(combined_text)
    if hits:
        raise ValueError(f"Guardrail triggered: {hits}")

    # Add lightweight tracking into notes_for_pastor
    try:
        m = manuscript.manuscript
        stamp = (
            f"Generated: {datetime.now(timezone.utc).isoformat()} | "
            f"Model: {OPENAI_MODEL} | {PLATFORM} {VERSION} | "
            f"Denomination: {getattr(sermon_input, 'denomination', 'Broad Christian (default)')}"
        )
        m.notes_for_pastor = (getattr(m, "notes_for_pastor", "") or "").strip()
        m.notes_for_pastor = f"{m.notes_for_pastor}\n\n{stamp}".strip() if m.notes_for_pastor else stamp
    except Exception:
        pass

    return manuscript