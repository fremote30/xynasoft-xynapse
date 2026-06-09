from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from io import BytesIO
from docx import Document
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

import json

from sqlalchemy.orm import Session

from fastapi import (
    Depends,
    HTTPException
)

from api.db.database import get_db

from api.models.sermon import Sermon

from api.core.dependencies import get_current_user

from api.models.user import User
from api.models.shared_sermon import SharedSermon

# =========================================
# SCHEMAS
# =========================================
from api.schemas.faith import (
    SermonRequest,
    SermonResponse,
    SermonRefineRequest
)

# =========================================
# AI SERVICES
# =========================================
from api.services.ai_service import (
    generate_ai_response,
    refine_sermon,
    generate_multiverse_sermons
)
from api.models.sermon_comment import SermonComment

router = APIRouter()


# =========================================
# GENERATE SERMON
# =========================================
@router.post(
    "/sermon",
    response_model=SermonResponse
)
async def create_sermon(
    payload: SermonRequest,
    current_user: User = Depends(
        get_current_user
    )
):

    if (
        current_user.role != "admin"
        and current_user.pastor_status != "approved"
    ):
        raise HTTPException(
            status_code=403,
            detail="Pastor approval required to access Sermon Studio"
        )
    print("\n==========")
    print("SERMON REQUEST")
    print("Scripture:", payload.scripture)
    print("Input:", payload.input)
    print("==========\n")
    sermon = generate_ai_response(
    payload
    )

    # =====================================
    # FORCE REQUESTED BIBLE VERSE
    # =====================================

    if payload.scripture:

        sermon["scripture"] = payload.scripture
    # =====================================
    # COMPATIBILITY LAYER
    # =====================================

    if (
        "points" in sermon
        and "main_points" not in sermon
    ):

        sermon["main_points"] = sermon["points"]

    print(
        "REQUESTED BIBLE:",
        payload.scripture
    )

    print(
        "RETURNED SCRIPTURE:",
        sermon.get("scripture")
    )

    return sermon

# =========================================
# REFINE SERMON
# =========================================
@router.post("/sermon/refine")
async def refine_existing_sermon(
    payload: SermonRefineRequest
):

    refined = refine_sermon(
        payload.sermon,
        payload.refine_type
    )

    return {
        "success": True,
        "sermon": refined
    }


# =========================================
# MULTIVERSE SERMONS
# =========================================
@router.post("/sermon/multiverse")
async def multiverse_sermons(
    payload: SermonRequest
):

    universes = generate_multiverse_sermons(
        payload.topic
    )

    return universes


# =========================================
# HEALTH CHECK
# =========================================
@router.get("/sermon-health")
async def sermon_health():

    return {
        "status": "ok",
        "service": "XynaFaith Sermon AI"
    }


# =========================================
# EXPORT PDF
# =========================================
@router.post("/sermon/export-pdf")
async def export_sermon_pdf(
    payload: dict
):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=60,
        bottomMargin=60
    )

    styles = getSampleStyleSheet()

    # =====================================
    # PREMIUM STYLES
    # =====================================
    title_style = styles["Title"]
    title_style.fontSize = 28
    title_style.leading = 34

    heading_style = styles["Heading2"]
    heading_style.fontSize = 18
    heading_style.leading = 24

    body_style = styles["BodyText"]
    body_style.fontSize = 12
    body_style.leading = 22

    story = []

    # =========================
    # TITLE
    # =========================
    title = payload.get(
        "title",
        "Untitled Sermon"
    )

    story.append(
        Paragraph(
            f"<b>{title}</b>",
            title_style
        )
    )

    story.append(
        Spacer(1, 24)
    )

    # =========================
    # SCRIPTURE
    # =========================
    scripture = payload.get(
        "scripture"
    )

    if scripture:

        story.append(
            Paragraph(
                f"<i>📖 {scripture}</i>",
                heading_style
            )
        )

        story.append(
            Spacer(1, 24)
        )

    # =========================
    # INTRODUCTION
    # =========================
    intro = payload.get(
        "introduction",
        ""
    )

    story.append(
        Paragraph(
            "<b>Introduction</b>",
            heading_style
        )
    )

    story.append(
        Paragraph(
            intro,
            body_style
        )
    )

    story.append(
        Spacer(1, 24)
    )

    # =========================
    # MAIN POINTS
    # =========================
    points = payload.get(
        "main_points",
        []
    )

    for point in points:

        story.append(
            Paragraph(
                f"<b>{point.get('title', '')}</b>",
                heading_style
            )
        )

        story.append(
            Paragraph(
                point.get(
                    "content",
                    ""
                ),
                body_style
            )
        )

        story.append(
            Spacer(1, 24)
        )

    # =========================
    # APPLICATION
    # =========================
    application = payload.get(
        "application",
        ""
    )

    story.append(
        Paragraph(
            "<b>Application</b>",
            heading_style
        )
    )

    story.append(
        Paragraph(
            application,
            body_style
        )
    )

    story.append(
        Spacer(1, 24)
    )

    # =========================
    # CONCLUSION
    # =========================
    conclusion = payload.get(
        "conclusion",
        ""
    )

    story.append(
        Paragraph(
            "<b>Conclusion</b>",
            heading_style
        )
    )

    story.append(
        Paragraph(
            conclusion,
            body_style
        )
    )

    # =========================
    # FOOTER BRANDING
    # =========================
    story.append(
        Spacer(1, 40)
    )

    story.append(
        Paragraph(
            "Generated with XynaFaith",
            styles["Italic"]
        )
    )

    # =========================
    # BUILD PDF
    # =========================
    doc.build(story)

    buffer.seek(0)

    filename = (
        title
        .replace(" ", "_")
        + ".pdf"
    )

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
            f"attachment; filename={filename}"
        }
    )


# =========================================
# EXPORT DOCX
# =========================================
@router.post("/sermon/export-docx")
async def export_sermon_docx(
    payload: dict
):

    document = Document()

    # =========================
    # TITLE
    # =========================
    title = payload.get(
        "title",
        "Untitled Sermon"
    )

    document.add_heading(
        title,
        level=1
    )

    # =========================
    # SCRIPTURE
    # =========================
    scripture = payload.get(
        "scripture"
    )

    if scripture:

        document.add_heading(
            "Scripture",
            level=2
        )

        document.add_paragraph(
            scripture
        )

    # =========================
    # INTRODUCTION
    # =========================
    intro = payload.get(
        "introduction",
        ""
    )

    document.add_heading(
        "Introduction",
        level=2
    )

    document.add_paragraph(
        intro
    )

    # =========================
    # MAIN POINTS
    # =========================
    points = payload.get(
        "main_points",
        []
    )

    for point in points:

        document.add_heading(
            point.get(
                "title",
                "Point"
            ),
            level=2
        )

        document.add_paragraph(
            point.get(
                "content",
                ""
            )
        )

    # =========================
    # APPLICATION
    # =========================
    application = payload.get(
        "application",
        ""
    )

    document.add_heading(
        "Application",
        level=2
    )

    document.add_paragraph(
        application
    )

    # =========================
    # CONCLUSION
    # =========================
    conclusion = payload.get(
        "conclusion",
        ""
    )

    document.add_heading(
        "Conclusion",
        level=2
    )

    document.add_paragraph(
        conclusion
    )

    # =========================
    # FOOTER
    # =========================
    document.add_paragraph(
        "\nGenerated with XynaFaith"
    )

    # =========================
    # SAVE TO MEMORY
    # =========================
    buffer = BytesIO()

    document.save(
        buffer
    )

    buffer.seek(0)

    filename = (
        title
        .replace(" ", "_")
        + ".docx"
    )

    return StreamingResponse(

        buffer,

        media_type=
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",

        headers={
            "Content-Disposition":
            f"attachment; filename={filename}"
        }
    )

# =========================================
# SAVE SERMON
# =========================================
@router.post("/sermon/save")
async def save_sermon(

    payload: dict,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    )
):

    try:

        # =========================
        # TITLE
        # =========================
        title = payload.get(
            "title",
            "Untitled Sermon"
        )

        # =========================
        # SCRIPTURE
        # =========================
        scripture = payload.get(
            "scripture"
        )

        # =========================
        # CREATE SERMON
        # =========================
        sermon = Sermon(

            title=title,

            scripture=scripture,

            author_id=current_user.id,

            # LEGACY STORAGE
            content=json.dumps(
                payload
            ),

            # NEW STRUCTURED STORAGE
            sermon_data=payload,

            is_public=0
        )

        # =========================
        # SAVE
        # =========================
        db.add(sermon)

        db.commit()

        db.refresh(sermon)

        return {

            "success": True,

            "message":
                "Sermon saved",

            "sermon_id":
                sermon.id
        }

    except Exception as e:

        print(
            "SAVE SERMON ERROR:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to save sermon"
        )
    
# =========================================
# GET MY SERMONS
# =========================================
@router.get("/sermon/my")
async def get_my_sermons(

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    )
):

    try:

        # =========================
        # FETCH SERMONS
        # =========================
        sermons = (

            db.query(Sermon)

            .filter(
                Sermon.author_id
                == current_user.id
            )

            .order_by(
                Sermon.created_at.desc()
            )

            .all()
        )

        # =========================
        # FORMAT RESPONSE
        # =========================
        formatted = []

        for sermon in sermons:

            formatted.append({

                "id":
                    sermon.id,

                "title":
                    sermon.title,

                "scripture":
                    sermon.scripture,

                "created_at":
                    sermon.created_at,

                "views":
                    sermon.views,

                "shares":
                    sermon.shares,

                "is_public":
                    sermon.is_public
            })

        return {
            "success": True,
            "sermons": formatted
        }

    except Exception as e:

        print(
            "GET MY SERMONS ERROR:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=
              "Failed to load sermons"
        )
    
# =========================================
# GET SINGLE SERMON
# =========================================
@router.get("/sermon/{sermon_id}")
async def get_single_sermon(

    sermon_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    )
):

    try:

        # =========================
        # OWNED SERMON
        # =========================
        sermon = (

            db.query(Sermon)

            .filter(
                Sermon.id == sermon_id
            )

            .filter(
                Sermon.author_id
                == current_user.id
            )

            .first()
        )

        # =========================
        # SHARED ACCESS
        # =========================
        if not sermon:

            shared = (

                db.query(SharedSermon)

                .filter(
                    SharedSermon.sermon_id
                    == sermon_id
                )

                .filter(
                    SharedSermon.to_pastor_id
                    == current_user.id
                )

                .first()
            )

            if shared:

                sermon = shared.sermon

        # =========================
        # NOT FOUND
        # =========================
        if not sermon:

            raise HTTPException(
                status_code=404,
                detail="Sermon not found"
            )

        # =========================
        # STRUCTURED DATA
        # =========================
        if sermon.sermon_data:

            return {

                "success": True,

                "sermon":
                    sermon.sermon_data
            }

        # =========================
        # LEGACY FALLBACK
        # =========================
        parsed = json.loads(
            sermon.content
        )

        return {

            "success": True,

            "sermon": parsed
        }

    except Exception as e:

        print(
            "GET SERMON ERROR:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=
              "Failed to load sermon"
        )
    
# =========================================
# UPDATE SERMON
# =========================================
@router.put("/sermon/update/{sermon_id}")
async def update_sermon(

    sermon_id: int,

    payload: dict,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    )
):

    try:

        sermon = (

            db.query(Sermon)

            .filter(
                Sermon.id == sermon_id
            )

            .filter(
                Sermon.author_id
                == current_user.id
            )

            .first()
        )

        if not sermon:

            raise HTTPException(
                status_code=404,
                detail="Sermon not found"
            )

        # =========================
        # UPDATE FIELDS
        # =========================
        sermon.title = payload.get(
            "title",
            sermon.title
        )

        sermon.scripture = payload.get(
            "scripture",
            sermon.scripture
        )

        # LEGACY
        sermon.content = json.dumps(
            payload
        )

        # STRUCTURED
        sermon.sermon_data = payload

        db.commit()

        db.refresh(sermon)

        return {

            "success": True,

            "message":
                "Sermon updated"
        }

    except Exception as e:

        print(
            "UPDATE SERMON ERROR:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=
              "Failed to update sermon"
        )
    
# =========================================
# SHARE SERMON
# =========================================
@router.post("/sermon/share")
async def share_sermon(

    payload: dict,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    )
):

    try:

        # =========================
        # INPUTS
        # =========================
        sermon_id = payload.get(
            "sermon_id"
        )

        to_pastor_id = payload.get(
            "to_pastor_id"
        )

        comment = payload.get(
            "comment",
            ""
        )

        # =========================
        # VALIDATE SERMON
        # =========================
        sermon = (

            db.query(Sermon)

            .filter(
                Sermon.id == sermon_id
            )

            .filter(
                Sermon.author_id
                == current_user.id
            )

            .first()
        )

        if not sermon:

            raise HTTPException(
                status_code=404,
                detail="Sermon not found"
            )

        # =========================
        # CREATE SHARE
        # =========================
        shared = SharedSermon(

            sermon_id=sermon.id,

            from_pastor_id=
                current_user.id,

            to_pastor_id=
                to_pastor_id,

            comment=comment
        )

        # =========================
        # ANALYTICS
        # =========================
        sermon.shares += 1

        # =========================
        # SAVE
        # =========================
        db.add(shared)

        db.commit()

        return {

            "success": True,

            "message":
                "Sermon shared"
        }

    except Exception as e:

        print(
            "SHARE SERMON ERROR:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=
              "Failed to share sermon"
        )
    
# =========================================
# SEARCH PASTORS
# =========================================
@router.get("/pastors/search")
async def search_pastors(

    query: str,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    )
):

    try:

        # =========================
        # SEARCH USERS
        # =========================
        pastors = (

            db.query(User)

            .filter(
                User.role == "pastor"
            )

            .filter(
                User.name.ilike(
                    f"%{query}%"
                )
            )

            .limit(10)

            .all()
        )

        # =========================
        # FORMAT
        # =========================
        results = []

        for pastor in pastors:

            results.append({

                "id":
                    pastor.id,

                "name":
                    pastor.name,

                "email":
                    pastor.email
            })

        return {

            "success": True,

            "pastors": results
        }

    except Exception as e:

        print(
            "SEARCH PASTORS ERROR:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=
              "Failed to search pastors"
        )
    
# =========================================
# SHARED SERMONS INBOX
# =========================================
@router.get("/sermon/shared-with-me")
async def shared_with_me(

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    )
):

    try:

        # =========================
        # FETCH SHARED SERMONS
        # =========================
        shared = (

            db.query(SharedSermon)

            .filter(
                SharedSermon.to_pastor_id
                == current_user.id
            )

            .order_by(
                SharedSermon.created_at.desc()
            )

            .all()
        )

        # =========================
        # FORMAT
        # =========================
        results = []

        for item in shared:

            sermon = item.sermon

            sender = item.from_pastor

            results.append({

                "share_id":
                    item.id,

                "sermon_id":
                    sermon.id,

                "title":
                    sermon.title,

                "scripture":
                    sermon.scripture,

                "comment":
                    item.comment,

                "shared_at":
                    item.created_at,

                "sender_name":
                    sender.name,

                "sender_email":
                    sender.email
            })

        return {

            "success": True,

            "shared_sermons":
                results
        }

    except Exception as e:

        print(
            "SHARED INBOX ERROR:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=
              "Failed to load shared sermons"
        )
    
# =========================================
# ADD SERMON COMMENT
# =========================================
@router.post("/sermon/comment")
async def add_sermon_comment(

    payload: dict,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    )
):

    try:

        sermon_id = payload.get(
            "sermon_id"
        )

        comment_text = payload.get(
            "comment"
        )

        if not comment_text:

            raise HTTPException(
                status_code=400,
                detail="Comment required"
            )

        # =========================
        # VALIDATE ACCESS
        # =========================
        sermon = (

            db.query(Sermon)

            .filter(
                Sermon.id == sermon_id
            )

            .first()
        )

        if not sermon:

            raise HTTPException(
                status_code=404,
                detail="Sermon not found"
            )

        # =========================
        # CREATE COMMENT
        # =========================
        comment = SermonComment(

            sermon_id=sermon.id,

            pastor_id=current_user.id,

            comment=comment_text
        )

        db.add(comment)

        db.commit()

        return {

            "success": True,

            "message":
                "Comment added"
        }

    except Exception as e:

        print(
            "ADD COMMENT ERROR:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=
              "Failed to add comment"
        )
    
# =========================================
# GET SERMON COMMENTS
# =========================================
@router.get("/sermon/comments/{sermon_id}")
async def get_sermon_comments(

    sermon_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    )
):

    try:

        comments = (

            db.query(SermonComment)

            .filter(
                SermonComment.sermon_id
                == sermon_id
            )

            .order_by(
                SermonComment.created_at.asc()
            )

            .all()
        )

        results = []

        for item in comments:

            results.append({

                "id":
                    item.id,

                "comment":
                    item.comment,

                "created_at":
                    item.created_at,

                "pastor_name":
                    item.pastor.name
            })

        return {

            "success": True,

            "comments": results
        }

    except Exception as e:

        print(
            "GET COMMENTS ERROR:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=
              "Failed to load comments"
        )