from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/sermons", tags=["Sermons"])


# -------------------------
# Request Models
# -------------------------

class OutlineRequest(BaseModel):
    topic: str
    scripture: str
    audience: str


class ManuscriptRequest(BaseModel):
    title: str
    scripture: str
    outline: str


# -------------------------
# Generate Sermon Outline
# -------------------------

@router.post("/generate-outline")
def generate_outline(data: OutlineRequest):

    outline = f"""
Sermon Topic: {data.topic}

Scripture: {data.scripture}

Audience: {data.audience}

Outline:

1. Introduction
   - Introduce the theme of {data.topic}

2. Biblical Context
   - Explain the meaning of {data.scripture}

3. Key Lesson
   - What this passage teaches believers today

4. Illustration
   - Story showing how faith works in real life

5. Application
   - How the audience can apply this message

6. Closing Prayer
"""

    return {"outline": outline}


# -------------------------
# Generate Sermon Manuscript
# -------------------------

@router.post("/generate-manuscript")
def generate_manuscript(data: ManuscriptRequest):

    manuscript = f"""
Title: {data.title}

Scripture: {data.scripture}

{data.outline}

Full Sermon Manuscript:

Today we reflect on the message found in {data.scripture}. 
This passage reminds us that God works in every situation 
to shape our faith and strengthen our character.

As believers, we are called to trust God even when life 
is difficult. Faith grows through challenges, and God 
uses those moments to teach us perseverance.

Let us reflect on this message and ask ourselves how we 
can apply this truth in our daily lives.

Amen.
"""

    return {"manuscript": manuscript}