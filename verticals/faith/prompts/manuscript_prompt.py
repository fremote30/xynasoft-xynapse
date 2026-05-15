from __future__ import annotations

import json

from verticals.faith.schemas.sermon_input import SermonInput
from verticals.faith.schemas.sermon_output import SermonOutput


def _denomination_guardrails(denom: str) -> str:
    """
    Same soft-guardrails approach as sermon_prompt,
    applied to manuscript expansion so the manuscript doesn't drift.
    """
    denom = (denom or "broad_evangelical").strip().lower()

    base = """
DENOMINATION GUARDRAILS (SOFT):
- Be respectful and non-argumentative across Christian traditions.
- Avoid framing that attacks or "debunks" other denominations.
- If a doctrine is debated, acknowledge diversity briefly and return to scripture/application.
- Do not promote prosperity theology or transactional "seed" language.
- Keep language pastoral, clear, and usable in Ghana contexts.
""".strip()

    extra_map = {
        "broad_evangelical": """
- Default: classic evangelical wording (grace, repentance, faith, discipleship).
- Avoid niche denominational slogans.
""",
        "pentecostal_charismatic": """
- Permit spiritual warmth: prayer emphasis, encouragement, and (optional) altar-call language.
- Avoid sensational claims; do not guarantee healing/outcomes.
- Avoid attacking cessationist views; keep unity.
""",
        "reformed": """
- Emphasize God’s sovereignty, grace, scripture authority, and Christ-centered exposition.
- Avoid anti-charismatic jabs.
""",
        "baptist": """
- Avoid baptism disputes; if baptism appears in the text, present it plainly and pastorally.
""",
        "methodist_wesleyan": """
- Use discipleship/holiness/sanctification language where appropriate.
- Avoid polemics; keep scripture-forward.
""",
        "catholic": """
- Maintain respectful tone; avoid anti-Catholic rhetoric.
- If mentioning sacraments, keep it gentle/non-controversial; scripture first.
""",
        "anglican": """
- Balanced, reverent tone; scripture-first with historic-church sensitivity.
""",
        "seventh_day_adventist": """
- Avoid sensational end-times speculation; keep Christ-centered hope and discipleship.
""",
        "non_denom": """
- Simple, widely accessible wording; avoid denominational labels.
""",
    }

    extra = (extra_map.get(denom) or "").strip()
    return base + ("\n\n" + extra if extra else "")


def build_manuscript_prompt(inp: SermonInput, outline: SermonOutput) -> str:
    """
    Generates a structured sermon manuscript + timings.
    Uses inp.resolved_passages() to treat multi-passages as one unified sermon.
    """

    # Keep prompts compact (Ghana low-data + speed)
    inp_dict = inp.model_dump()
    out_dict = outline.model_dump()

    passages = inp.resolved_passages()
    passages_str = "; ".join(passages) if passages else inp.passage_reference

    denom_rules = _denomination_guardrails(inp.denomination)

    return f"""
You are Xynapse Faith, a sermon-writing assistant for Ghana pastors.

TASK:
Using the SERMON OUTLINE below, write a full sermon MANUSCRIPT suitable for preaching.

MULTI-PASSAGE RULE:
- Treat these passages as ONE unified set: {passages_str}
- Do NOT produce separate mini-sermons.

IMPORTANT:
- Maintain scripture-first clarity and pastoral tone.
- Avoid prosperity-gospel framing.
- Avoid political endorsements.
- If uncertain about historical details, explicitly state uncertainty.
- Keep language clear, pastoral, and practical for Ghana context.
- Keep output concise enough for low-data environments.

{denom_rules}

OUTPUT FORMAT:
Return ONLY valid JSON matching this schema:

{{
  "manuscript": {{
    "introduction": "string",
    "body_sections": [
      {{
        "section_title": "string",
        "content": "string",
        "estimated_minutes": 8
      }}
    ],
    "application": "string",
    "closing_prayer": "string",
    "estimated_total_minutes": 30,
    "notes_for_pastor": "optional string"
  }}
}}

TIMING RULES:
- estimated_total_minutes must match inp.duration_minutes as closely as possible.
- body_sections should be 2–5 sections.
- Provide estimated_minutes for each section.

SERMON INPUT (JSON):
{json.dumps(inp_dict, ensure_ascii=False)}

SERMON OUTLINE (JSON):
{json.dumps(out_dict, ensure_ascii=False)}
""".strip()