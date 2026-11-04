"""
XynaFaith V2 Bible Quiz domain models.

Quiz authoring, member participation, and server-side scoring.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from api.db.database import Base


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BibleQuiz(Base):
    __tablename__ = "bible_quizzes"

    id = Column(Integer, primary_key=True)

    church_id = Column(
        Integer,
        ForeignKey("churches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    creator_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    generation_request_id = Column(
        String(128),
        nullable=True,
        unique=True,
        index=True,
    )

    generation_input_hash = Column(
        String(64),
        nullable=True,
    )

    title = Column(String(200), nullable=False)
    description = Column(Text)
    scripture = Column(String(500))
    difficulty = Column(
        String(32),
        nullable=False,
        default="beginner",
    )
    status = Column(
        String(32),
        nullable=False,
        default="draft",
    )

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    published_at = Column(DateTime)

    questions = relationship(
        "BibleQuizQuestion",
        back_populates="quiz",
        cascade="all, delete-orphan",
        order_by="BibleQuizQuestion.position",
    )

    attempts = relationship(
        "BibleQuizAttempt",
        back_populates="quiz",
    )

    __table_args__ = (
        Index("ix_bible_quizzes_church_status", "church_id", "status"),
        CheckConstraint(
            "difficulty IN ('beginner', 'intermediate', 'advanced')",
            name="ck_bible_quiz_difficulty",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_bible_quiz_status",
        ),
    )


class BibleQuizQuestion(Base):
    __tablename__ = "bible_quiz_questions"

    id = Column(Integer, primary_key=True)

    quiz_id = Column(
        Integer,
        ForeignKey("bible_quizzes.id", ondelete="CASCADE"),
        nullable=False,
    )

    position = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)

    option_a = Column(Text, nullable=False)
    option_b = Column(Text, nullable=False)
    option_c = Column(Text, nullable=False)
    option_d = Column(Text, nullable=False)

    correct_option = Column(String(1), nullable=False)
    explanation = Column(Text)

    quiz = relationship(
        "BibleQuiz",
        back_populates="questions",
    )

    __table_args__ = (
        UniqueConstraint(
            "quiz_id",
            "position",
            name="uq_bible_quiz_question_position",
        ),
        CheckConstraint(
            "position > 0",
            name="ck_bible_quiz_question_position",
        ),
        CheckConstraint(
            "correct_option IN ('A', 'B', 'C', 'D')",
            name="ck_bible_quiz_correct_option",
        ),
    )


class BibleQuizAttempt(Base):
    __tablename__ = "bible_quiz_attempts"

    id = Column(Integer, primary_key=True)

    quiz_id = Column(
        Integer,
        ForeignKey("bible_quizzes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(
        String(32),
        nullable=False,
        default="in_progress",
    )

    score = Column(Integer)
    total_questions = Column(Integer)
    correct_answers = Column(Integer)

    started_at = Column(DateTime, default=utc_now, nullable=False)
    submitted_at = Column(DateTime)

    quiz = relationship(
        "BibleQuiz",
        back_populates="attempts",
    )

    answers = relationship(
        "BibleQuizAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'submitted')",
            name="ck_bible_quiz_attempt_status",
        ),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name="ck_bible_quiz_attempt_score",
        ),
        CheckConstraint(
            "correct_answers IS NULL OR correct_answers >= 0",
            name="ck_bible_quiz_correct_answers",
        ),
        CheckConstraint(
            "total_questions IS NULL OR total_questions > 0",
            name="ck_bible_quiz_total_questions",
        ),
        CheckConstraint(
            "correct_answers IS NULL OR total_questions IS NULL OR correct_answers <= total_questions",
            name="ck_bible_quiz_correct_count_limit",
        ),
        CheckConstraint(
            "status != 'submitted' OR (score IS NOT NULL AND total_questions IS NOT NULL AND correct_answers IS NOT NULL AND submitted_at IS NOT NULL)",
            name="ck_bible_quiz_submitted_complete",
        ),
    )


class BibleQuizAnswer(Base):
    __tablename__ = "bible_quiz_answers"

    id = Column(Integer, primary_key=True)

    attempt_id = Column(
        Integer,
        ForeignKey("bible_quiz_attempts.id", ondelete="CASCADE"),
        nullable=False,
    )

    question_id = Column(
        Integer,
        ForeignKey("bible_quiz_questions.id", ondelete="CASCADE"),
        nullable=False,
    )

    selected_option = Column(String(1), nullable=False)
    is_correct = Column(Integer, nullable=False)

    attempt = relationship(
        "BibleQuizAttempt",
        back_populates="answers",
    )

    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "question_id",
            name="uq_bible_quiz_attempt_question",
        ),
        CheckConstraint(
            "selected_option IN ('A', 'B', 'C', 'D')",
            name="ck_bible_quiz_selected_option",
        ),
        CheckConstraint(
            "is_correct IN (0, 1)",
            name="ck_bible_quiz_is_correct",
        ),
    )
