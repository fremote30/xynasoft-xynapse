import os
import json
from dotenv import load_dotenv

# =========================================
# OPENAI
# =========================================
from openai import OpenAI

# =========================================
# CLAUDE (ANTHROPIC)
# =========================================
import anthropic

load_dotenv()

# =========================================
# ENV CONFIG
# =========================================
AI_PROVIDER = os.getenv(
    "AI_PROVIDER",
    "openai"
)

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY"
)

ANTHROPIC_API_KEY = os.getenv(
    "ANTHROPIC_API_KEY"
)

# =========================================
# CLIENTS
# =========================================
openai_client = (
    OpenAI(api_key=OPENAI_API_KEY)
    if OPENAI_API_KEY
    else None
)

claude_client = (
    anthropic.Anthropic(
        api_key=ANTHROPIC_API_KEY
    )
    if ANTHROPIC_API_KEY
    else None
)

# =========================================
# XYNAFAITH SYSTEM PROMPT
# =========================================
SYSTEM_PROMPT = """
You are XynaFaith AI,
an advanced sermon co-pilot designed to help pastors create powerful, biblically grounded, spiritually mature, and highly preachable sermons.

CORE IDENTITY:
- Assist pastors without replacing spiritual inspiration
- Help organize and strengthen messages God has placed in their hearts
- Maintain authentic pastoral language and sermon cadence
- Sound spiritually grounded, warm, and human
- Create sermons that feel preached, not AI-generated

SERMON STYLE:
- Strong introductions
- Clear sermon flow
- Practical applications
- Scripture integration
- Emotional progression
- Powerful conclusions
- Natural transitions
- Evangelistic and pastoral warmth

AVOID:
- robotic AI phrasing
- repetitive wording
- generic devotional tone
- corporate language
- shallow motivational writing

STYLE EXAMPLES:
XynaFaith sermons should:
- sound pastoral and human
- include scripture naturally
- contain practical applications
- build emotional and spiritual momentum
- feel preachable
- use clear transitions
- maintain spiritual authority

OUTPUT REQUIREMENTS:
You MUST return ONLY valid JSON.

Use EXACTLY this structure:

{
  "title": "",
  "scripture": "",
  "introduction": "",
  "main_points": [
    {
      "title": "",
      "content": ""
    }
  ],
  "application": "",
  "conclusion": ""
}

DO NOT include markdown.
DO NOT include explanations.
DO NOT wrap JSON in code blocks.
"""

# =========================================
# CLEAN JSON RESPONSE
# =========================================
def clean_json_response(text: str):

    """
    Cleans malformed AI JSON responses
    """

    if not text:
        return text

    text = text.strip()

    # =====================================
    # REMOVE MARKDOWN BLOCKS
    # =====================================
    if text.startswith("```"):

        text = (
            text
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

    # =====================================
    # EXTRACT JSON OBJECT
    # =====================================
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:

        text = text[start:end + 1]

    return text


# =========================================
# VALIDATE JSON
# =========================================
def validate_json_output(text: str):

    try:

        cleaned = clean_json_response(text)

        return json.loads(cleaned)

    except Exception as e:

        print(
            "JSON validation failed:",
            e
        )

        return None


# =========================================
# OPENAI CALL
# =========================================
def call_openai(prompt):

    if not openai_client:
        raise Exception(
            "OpenAI not configured"
        )

    if not OPENAI_API_KEY:
        raise Exception(
            "Missing OPENAI_API_KEY"
        )

    try:

        response = (
            openai_client
            .chat
            .completions
            .create(
                model="gpt-4o-mini",

                messages=[
                    {
                        "role": "system",
                        "content":
                            SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content":
                            prompt
                    }
                ],

                temperature=0.7,

                response_format={
                    "type":
                        "json_object"
                }
            )
        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        return clean_json_response(
            content
        )

    except Exception as e:

        print(
            "OpenAI error:",
            e
        )

        raise e


# =========================================
# CLAUDE CALL
# =========================================
def call_claude(prompt):

    if not claude_client:

        raise Exception(
            "Claude not configured"
        )

    try:

        response = (
            claude_client
            .messages
            .create(
                model=
                    "claude-sonnet-4-6",

                max_tokens=4000,

                temperature=0.7,

                system=SYSTEM_PROMPT,

                messages=[
                    {
                        "role": "user",
                        "content":
                            prompt
                    }
                ]
            )
        )

        content = (
            response
            .content[0]
            .text
        )

        return clean_json_response(
            content
        )

    except Exception as e:

        print(
            "Claude error:",
            e
        )

        raise e


# =========================================
# BUILD SERMON PROMPT
# =========================================
def build_sermon_prompt(payload):

    return f"""

Generate a sermon using the following information.

SERMON TOPIC:
{payload.get("input", "")}

SCRIPTURE:
{payload.get("scripture", "")}

DENOMINATION:
{payload.get("denomination", "general")}

AUDIENCE:
{payload.get("audience", "")}

LOCAL CONTEXT:
{payload.get("context", "")}

TONE:
{payload.get("tone", "balanced")}

DURATION:
{payload.get("duration", "30")}

IMPORTANT:
- Create a deeply biblical and practical sermon
- Make the sermon emotionally engaging
- Include strong transitions
- Make it sound naturally preachable
- Include practical applications
- Make the conclusion powerful and spiritually uplifting

"""


# =========================================
# BUILD REFINE PROMPT
# =========================================
def build_refine_prompt(
    sermon,
    refine_type
):

    return f"""

You are refining an existing sermon.

IMPORTANT:
- Preserve the theology
- Preserve the sermon topic
- Preserve scripture focus
- Preserve pastoral tone
- Preserve the original sermon movement
- Preserve the overall sermon structure
- Do NOT rewrite the sermon unnecessarily
- Improve ONLY the requested refinement area
- Keep the sermon preachable
- Maintain strong transitions between sections
- Return the SAME JSON structure

REFINEMENT TYPE:
{refine_type}

CURRENT SERMON:

{json.dumps(sermon, indent=2)}

REFINEMENT TYPES:

deepen:
- deeper biblical insight
- richer exposition
- stronger theological depth
- more powerful applications
- improve preaching impact
- strengthen transitions

simplify:
- use clearer language
- make ideas easier to understand
- shorten overly complex sentences
- preserve biblical depth
- maintain preaching quality
- make sermon accessible to wider audiences
- improve clarity without sounding childish
- simplify theological wording where necessary
- preserve emotional impact

evangelistic:
- salvation emphasis
- repentance
- gospel invitation
- stronger altar call
- urgency for salvation

prophetic:
- spiritual urgency
- revival tone
- strong exhortation
- spiritual intensity
- bold faith language

scripture:
- intelligently add multiple supporting scriptures
- add scriptures throughout the sermon
- connect scriptures to each major point
- include Old and New Testament connections
- strengthen biblical authority
- add cross references where appropriate
- improve theological continuity
- avoid random verse dumping
- naturally weave scriptures into sermon flow
- support sermon transitions with scripture
- enhance applications with biblical references

illustration:
- add memorable stories
- add analogies
- add relatable examples
- add emotional connections
- improve audience engagement
- make the sermon more preachable
- include modern-day applications

shorten:
- make concise
- preserve core message
- simplify transitions
- reduce repetition

expand:
- add depth and detail
- enrich explanations
- add stronger applications
- increase sermon richness

youth:
- modern relatable language
- energetic tone
- practical applications
- conversational style
- culturally relatable examples

leadership:
- leadership applications
- vision casting
- spiritual leadership principles
- organizational wisdom
- ministry development

Return ONLY valid JSON.

"""


# =========================================
# NORMALIZE SERMON JSON
# =========================================
def normalize_sermon_json(data):

    if not isinstance(data, dict):

        return fallback_sermon_response()

    return {

        "title":
            data.get(
                "title",
                "Untitled Sermon"
            ),

        "scripture":
            data.get(
                "scripture",
                ""
            ),

        "introduction":
            data.get(
                "introduction",
                ""
            ),

        "main_points":

            data.get(
                "main_points",
                []
            )

            if isinstance(
                data.get(
                    "main_points",
                    []
                ),
                list
            )

            else [],

        "application":
            data.get(
                "application",
                ""
            ),

        "conclusion":
            data.get(
                "conclusion",
                ""
            )
    }


# =========================================
# SAFE FALLBACK RESPONSE
# =========================================
def fallback_sermon_response():

    return {

        "title":
            "Unable to Generate Sermon",

        "scripture":
            "",

        "introduction":
            (
                "An error occurred while "
                "generating the sermon."
            ),

        "main_points":
            [],

        "application":
            "",

        "conclusion":
            "Please try again."
    }


# =========================================
# MAIN AI ROUTER
# =========================================
def generate_ai_response(
    payload,
    mode="sermon"
):

    """
    XynaFaith AI Orchestration

    Claude:
    - Sermons
    - Long-form preaching
    - Refinement

    OpenAI:
    - JSON formatting
    - Validation
    - Fallback
    """

    try:

        # =====================================
        # PYDANTIC → DICT
        # =====================================
        if hasattr(payload, "dict"):

            payload = payload.dict()

        prompt = build_sermon_prompt(
            payload
        )

        # =====================================
        # PRIMARY MODEL
        # =====================================
        if mode in [
            "sermon",
            "expository",
            "topical",
            "prophetic",
            "evangelistic",
            "youth",
            "leadership"
        ] and claude_client:

            raw = call_claude(prompt)

        else:

            if (
                AI_PROVIDER
                == "claude"
            ):

                raw = call_claude(prompt)

            else:

                raw = call_openai(prompt)

        # =====================================
        # VALIDATE JSON
        # =====================================
        parsed = validate_json_output(
            raw
        )

        if parsed:

            normalized = (
                normalize_sermon_json(
                    parsed
                )
            )

            return normalized

        raise Exception(
            "Invalid JSON from primary AI"
        )

    except Exception as primary_error:

        print(
            "Primary AI failed:",
            primary_error
        )

        # =====================================
        # FALLBACK
        # =====================================
        try:

            prompt = build_sermon_prompt(
                payload
            )

            # =====================================
            # ALWAYS FALL BACK TO OPENAI
            # =====================================
            if openai_client:

                raw = call_openai(prompt)

            else:

                return (
                    fallback_sermon_response()
                )

            parsed = validate_json_output(
                raw
            )

            if parsed:

                normalized = (
                    normalize_sermon_json(
                        parsed
                    )
                )

                return normalized

            raise Exception(
                "Fallback JSON validation failed"
            )

        except Exception as fallback_error:

            print(
                "Fallback AI failed:",
                fallback_error
            )

            return fallback_sermon_response()


# =========================================
# REFINE SERMON
# =========================================
def refine_sermon(
    sermon,
    refine_type
):

    try:

        prompt = build_refine_prompt(
            sermon,
            refine_type
        )

        # =====================================
        # CLAUDE FIRST
        # =====================================
        if claude_client:

            raw = call_claude(prompt)

        else:

            raw = call_openai(prompt)

        parsed = validate_json_output(
            raw
        )

        if parsed:

            normalized = (
                normalize_sermon_json(
                    parsed
                )
            )

            return normalized

        raise Exception(
            "Invalid refine JSON"
        )

    except Exception as e:

        print(
            "Refine sermon error:",
            e
        )

        return normalize_sermon_json(
            sermon
        )


# =========================================
# MULTIVERSE SERMONS
# =========================================
def generate_multiverse_sermons(
    topic
):

    prompt = f"""

You are creating MULTIPLE sermon universes
from ONE sermon topic.

TOPIC:
{topic}

Generate 5 DISTINCT sermon approaches:

1. Evangelistic
2. Teaching
3. Prophetic
4. Youth
5. Leadership

Each sermon should include:

- title
- main scripture
- tone
- introduction
- key points
- application
- conclusion

IMPORTANT:
- Each version must feel unique
- Do NOT repeat the same sermon
- Use different emotional tones
- Use different preaching styles
- Make each version highly preachable
- Sound pastoral and human
- Return ONLY valid JSON

JSON FORMAT:

{{
  "universes": [
    {{
      "type": "Evangelistic",
      "title": "",
      "scripture": "",
      "tone": "",
      "introduction": "",
      "points": [],
      "application": "",
      "conclusion": ""
    }}
  ]
}}

"""

    response = call_ai(prompt)

    return safe_json_loads(response)

# =========================================
# BUILD UPLOADED SERMON PROMPT
# =========================================
def build_uploaded_sermon_prompt(
    sermon_text
):

    return f"""

You are an expert sermon editor
helping pastors improve existing sermons.

TASK:
Transform the uploaded sermon
into a polished structured sermon.

IMPORTANT:
- Preserve the pastor's original voice
- Preserve emotional moments
- Preserve spiritual tone
- Preserve the original theology
- Preserve the original core message
- Improve sermon flow naturally
- Improve transitions
- Improve clarity
- Add structure
- Add practical applications
- Add supporting scriptures where appropriate
- Modernize wording where appropriate
- Improve audience engagement
- Keep the sermon highly preachable
- Add smoother transitions
- Strengthen applications
- Avoid sounding AI-generated
- Maintain pastoral warmth
- Maintain sermon cadence
- Keep emotional and spiritual momentum

UPLOADED SERMON:

{sermon_text}

Return ONLY valid JSON.

Use EXACTLY this structure:

{{
  "title": "",
  "scripture": "",
  "introduction": "",
  "main_points": [
    {{
      "title": "",
      "content": ""
    }}
  ],
  "application": "",
  "conclusion": ""
}}

DO NOT include markdown.
DO NOT include explanations.
DO NOT wrap JSON in code blocks.

"""


# =========================================
# REWRITE UPLOADED SERMON
# =========================================
def rewrite_uploaded_sermon(
    sermon_text
):

    try:

        prompt = (
            build_uploaded_sermon_prompt(
                sermon_text
            )
        )

        # =====================================
        # CLAUDE FIRST
        # =====================================
        if claude_client:

            raw = call_claude(prompt)

        else:

            raw = call_openai(prompt)

        # =====================================
        # VALIDATE JSON
        # =====================================
        parsed = validate_json_output(
            raw
        )

        if parsed:

            normalized = (
                normalize_sermon_json(
                    parsed
                )
            )

            return normalized

        raise Exception(
            "Invalid upload rewrite JSON"
        )

    except Exception as e:

        print(
            "Rewrite upload error:",
            e
        )

        return fallback_sermon_response()