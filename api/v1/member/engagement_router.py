from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.models.member_reading_plan import (
    MemberReadingPlan,
    MemberReadingProgress,
)
from api.models.member_sermon_note import MemberSermonNote
from api.models.reading_plan import ReadingPlan, ReadingPlanDay
from api.models.sermon import Sermon
from api.models.user import User
from api.schemas.member_engagement import (
    MemberSermonNoteCreate,
    MemberSermonNoteUpdate,
    ReadingProgressUpdate,
)


router = APIRouter()


def _iso(value):
    return value.isoformat() if value else None


def _plan_summary(plan):
    return {
        "id": plan.id,
        "title": plan.title,
        "description": plan.description,
        "duration_days": plan.duration_days,
        "status": plan.status,
    }


def _progress_payload(progress):
    return {
        "day_id": progress.day_id,
        "completed": progress.completed_at is not None,
        "completed_at": _iso(progress.completed_at),
    }


def _enrollment_payload(enrollment):
    completed_day_ids = {
        progress.day_id
        for progress in enrollment.progress
        if progress.completed_at is not None
    }

    days = [
        {
            "id": day.id,
            "day_number": day.day_number,
            "title": day.title,
            "scripture": day.scripture,
            "reflection": day.reflection,
            "prompt": day.prompt,
            "completed": day.id in completed_day_ids,
        }
        for day in enrollment.plan.days
    ]

    return {
        "id": enrollment.id,
        "status": enrollment.status,
        "started_at": _iso(enrollment.started_at),
        "completed_at": _iso(enrollment.completed_at),
        "completed_days": len(completed_day_ids),
        "total_days": len(days),
        "plan": _plan_summary(enrollment.plan),
        "days": days,
    }


def _note_payload(note):
    return {
        "id": note.id,
        "sermon_id": note.sermon_id,
        "title": note.title,
        "body": note.body,
        "created_at": _iso(note.created_at),
        "updated_at": _iso(note.updated_at),
    }


def _get_owned_enrollment(db, enrollment_id, user_id):
    enrollment = (
        db.query(MemberReadingPlan)
        .options(
            selectinload(MemberReadingPlan.plan).selectinload(
                ReadingPlan.days
            ),
            selectinload(MemberReadingPlan.progress),
        )
        .filter(
            MemberReadingPlan.id == enrollment_id,
            MemberReadingPlan.user_id == user_id,
        )
        .first()
    )

    if not enrollment:
        raise HTTPException(
            status_code=404,
            detail="Reading plan enrollment not found",
        )

    return enrollment


def _get_owned_note(db, note_id, user_id):
    note = (
        db.query(MemberSermonNote)
        .filter(
            MemberSermonNote.id == note_id,
            MemberSermonNote.user_id == user_id,
        )
        .first()
    )

    if not note:
        raise HTTPException(
            status_code=404,
            detail="Sermon note not found",
        )

    return note


@router.get("/reading-plans")
def list_reading_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plans = (
        db.query(ReadingPlan)
        .filter(ReadingPlan.status == "published")
        .order_by(ReadingPlan.created_at.desc(), ReadingPlan.id.desc())
        .all()
    )

    return {
        "reading_plans": [
            _plan_summary(plan)
            for plan in plans
        ]
    }


@router.get("/reading-plans/mine")
def list_my_reading_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enrollments = (
        db.query(MemberReadingPlan)
        .options(
            selectinload(MemberReadingPlan.plan).selectinload(
                ReadingPlan.days
            ),
            selectinload(MemberReadingPlan.progress),
        )
        .filter(MemberReadingPlan.user_id == current_user.id)
        .order_by(MemberReadingPlan.updated_at.desc())
        .all()
    )

    return {
        "reading_plans": [
            _enrollment_payload(item)
            for item in enrollments
        ]
    }


@router.post("/reading-plans/{plan_id}/start")
def start_reading_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = (
        db.query(ReadingPlan)
        .options(selectinload(ReadingPlan.days))
        .filter(
            ReadingPlan.id == plan_id,
            ReadingPlan.status == "published",
        )
        .first()
    )

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Reading plan not found",
        )

    existing = (
        db.query(MemberReadingPlan)
        .filter(
            MemberReadingPlan.user_id == current_user.id,
            MemberReadingPlan.plan_id == plan.id,
        )
        .first()
    )

    if existing:
        return _enrollment_payload(
            _get_owned_enrollment(
                db,
                existing.id,
                current_user.id,
            )
        )

    enrollment = MemberReadingPlan(
        user_id=current_user.id,
        plan_id=plan.id,
        status="active",
    )
    db.add(enrollment)
    db.flush()

    for day in plan.days:
        db.add(
            MemberReadingProgress(
                enrollment_id=enrollment.id,
                day_id=day.id,
            )
        )

    db.commit()

    return _enrollment_payload(
        _get_owned_enrollment(
            db,
            enrollment.id,
            current_user.id,
        )
    )


@router.get("/reading-plans/mine/{enrollment_id}")
def get_my_reading_plan(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _enrollment_payload(
        _get_owned_enrollment(
            db,
            enrollment_id,
            current_user.id,
        )
    )


@router.patch(
    "/reading-plans/mine/{enrollment_id}/days/{day_id}"
)
def update_reading_progress(
    enrollment_id: int,
    day_id: int,
    request: ReadingProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enrollment = _get_owned_enrollment(
        db,
        enrollment_id,
        current_user.id,
    )

    valid_day_ids = {
        day.id
        for day in enrollment.plan.days
    }

    if day_id not in valid_day_ids:
        raise HTTPException(
            status_code=404,
            detail="Reading plan day not found",
        )

    progress = (
        db.query(MemberReadingProgress)
        .filter(
            MemberReadingProgress.enrollment_id == enrollment.id,
            MemberReadingProgress.day_id == day_id,
        )
        .first()
    )

    if not progress:
        raise HTTPException(
            status_code=404,
            detail="Reading progress not found",
        )

    progress.completed_at = (
        datetime.utcnow()
        if request.completed
        else None
    )

    all_progress = (
        db.query(MemberReadingProgress)
        .filter(
            MemberReadingProgress.enrollment_id == enrollment.id
        )
        .all()
    )

    all_complete = all(
        item.completed_at is not None
        for item in all_progress
    )

    if all_complete and all_progress:
        enrollment.status = "completed"
        enrollment.completed_at = datetime.utcnow()
    else:
        enrollment.status = "active"
        enrollment.completed_at = None

    enrollment.updated_at = datetime.utcnow()

    db.commit()

    return _enrollment_payload(
        _get_owned_enrollment(
            db,
            enrollment.id,
            current_user.id,
        )
    )


@router.get("/sermon-notes")
def list_sermon_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notes = (
        db.query(MemberSermonNote)
        .filter(MemberSermonNote.user_id == current_user.id)
        .order_by(
            MemberSermonNote.updated_at.desc(),
            MemberSermonNote.id.desc(),
        )
        .all()
    )

    return {
        "notes": [
            _note_payload(note)
            for note in notes
        ]
    }


@router.post("/sermon-notes")
def create_sermon_note(
    request: MemberSermonNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if request.sermon_id is not None:
        sermon = (
            db.query(Sermon)
            .filter(Sermon.id == request.sermon_id)
            .first()
        )

        if not sermon:
            raise HTTPException(
                status_code=404,
                detail="Sermon not found",
            )

    body = request.body.strip()
    if not body:
        raise HTTPException(
            status_code=422,
            detail="Note body is required",
        )

    title = (
        request.title.strip()
        if request.title
        else None
    ) or None

    note = MemberSermonNote(
        user_id=current_user.id,
        sermon_id=request.sermon_id,
        title=title,
        body=body,
    )

    db.add(note)
    db.commit()
    db.refresh(note)

    return _note_payload(note)


@router.get("/sermon-notes/{note_id}")
def get_sermon_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _note_payload(
        _get_owned_note(
            db,
            note_id,
            current_user.id,
        )
    )


@router.patch("/sermon-notes/{note_id}")
def update_sermon_note(
    note_id: int,
    request: MemberSermonNoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = _get_owned_note(
        db,
        note_id,
        current_user.id,
    )

    body = request.body.strip()
    if not body:
        raise HTTPException(
            status_code=422,
            detail="Note body is required",
        )

    note.title = (
        request.title.strip()
        if request.title
        else None
    ) or None
    note.body = body
    note.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(note)

    return _note_payload(note)


@router.delete("/sermon-notes/{note_id}")
def delete_sermon_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = _get_owned_note(
        db,
        note_id,
        current_user.id,
    )

    db.delete(note)
    db.commit()

    return {
        "deleted": True,
        "note_id": note_id,
    }
