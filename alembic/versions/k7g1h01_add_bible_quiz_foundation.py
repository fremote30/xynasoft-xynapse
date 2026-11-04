"""add Bible Quiz foundation

Revision ID: k7g1h01
Revises: j6f0g01
"""

from alembic import op
import sqlalchemy as sa

revision = "k7g1h01"
down_revision = "j6f0g01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("bible_quizzes",
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('church_id', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('creator_user_id', sa.Integer(), primary_key=False, nullable=True),
        sa.Column('title', sa.String(length=200), primary_key=False, nullable=False),
        sa.Column('description', sa.Text(), primary_key=False, nullable=True),
        sa.Column('scripture', sa.String(length=500), primary_key=False, nullable=True),
        sa.Column('difficulty', sa.String(length=32), primary_key=False, nullable=False),
        sa.Column('status', sa.String(length=32), primary_key=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), primary_key=False, nullable=False),
        sa.Column('updated_at', sa.DateTime(), primary_key=False, nullable=False),
        sa.Column('published_at', sa.DateTime(), primary_key=False, nullable=True),
        sa.ForeignKeyConstraint(['church_id'], ['churches.id'], ondelete='CASCADE'),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name='ck_bible_quiz_status'),
        sa.ForeignKeyConstraint(['creator_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.CheckConstraint("difficulty IN ('beginner', 'intermediate', 'advanced')", name='ck_bible_quiz_difficulty'),
    )
    op.create_index('ix_bible_quizzes_church_id', 'bible_quizzes', ['church_id'], unique=False)
    op.create_index('ix_bible_quizzes_church_status', 'bible_quizzes', ['church_id', 'status'], unique=False)
    op.create_table("bible_quiz_questions",
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('quiz_id', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('position', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('question_text', sa.Text(), primary_key=False, nullable=False),
        sa.Column('option_a', sa.Text(), primary_key=False, nullable=False),
        sa.Column('option_b', sa.Text(), primary_key=False, nullable=False),
        sa.Column('option_c', sa.Text(), primary_key=False, nullable=False),
        sa.Column('option_d', sa.Text(), primary_key=False, nullable=False),
        sa.Column('correct_option', sa.String(length=1), primary_key=False, nullable=False),
        sa.Column('explanation', sa.Text(), primary_key=False, nullable=True),
        sa.ForeignKeyConstraint(['quiz_id'], ['bible_quizzes.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('quiz_id', 'position', name='uq_bible_quiz_question_position'),
        sa.CheckConstraint('position > 0', name='ck_bible_quiz_question_position'),
        sa.CheckConstraint("correct_option IN ('A', 'B', 'C', 'D')", name='ck_bible_quiz_correct_option'),
    )
    op.create_table("bible_quiz_attempts",
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('quiz_id', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('user_id', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('status', sa.String(length=32), primary_key=False, nullable=False),
        sa.Column('score', sa.Integer(), primary_key=False, nullable=True),
        sa.Column('total_questions', sa.Integer(), primary_key=False, nullable=True),
        sa.Column('correct_answers', sa.Integer(), primary_key=False, nullable=True),
        sa.Column('started_at', sa.DateTime(), primary_key=False, nullable=False),
        sa.Column('submitted_at', sa.DateTime(), primary_key=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.CheckConstraint("status != 'submitted' OR (score IS NOT NULL AND total_questions IS NOT NULL AND correct_answers IS NOT NULL AND submitted_at IS NOT NULL)", name='ck_bible_quiz_submitted_complete'),
        sa.CheckConstraint('correct_answers IS NULL OR correct_answers >= 0', name='ck_bible_quiz_correct_answers'),
        sa.CheckConstraint("status IN ('in_progress', 'submitted')", name='ck_bible_quiz_attempt_status'),
        sa.CheckConstraint('total_questions IS NULL OR total_questions > 0', name='ck_bible_quiz_total_questions'),
        sa.CheckConstraint('correct_answers IS NULL OR total_questions IS NULL OR correct_answers <= total_questions', name='ck_bible_quiz_correct_count_limit'),
        sa.ForeignKeyConstraint(['quiz_id'], ['bible_quizzes.id'], ondelete='CASCADE'),
        sa.CheckConstraint('score IS NULL OR (score >= 0 AND score <= 100)', name='ck_bible_quiz_attempt_score'),
    )
    op.create_index('ix_bible_quiz_attempts_quiz_id', 'bible_quiz_attempts', ['quiz_id'], unique=False)
    op.create_index('ix_bible_quiz_attempts_user_id', 'bible_quiz_attempts', ['user_id'], unique=False)
    op.create_table("bible_quiz_answers",
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('attempt_id', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('question_id', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('selected_option', sa.String(length=1), primary_key=False, nullable=False),
        sa.Column('is_correct', sa.Integer(), primary_key=False, nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['bible_quiz_questions.id'], ondelete='CASCADE'),
        sa.CheckConstraint('is_correct IN (0, 1)', name='ck_bible_quiz_is_correct'),
        sa.UniqueConstraint('attempt_id', 'question_id', name='uq_bible_quiz_attempt_question'),
        sa.ForeignKeyConstraint(['attempt_id'], ['bible_quiz_attempts.id'], ondelete='CASCADE'),
        sa.CheckConstraint("selected_option IN ('A', 'B', 'C', 'D')", name='ck_bible_quiz_selected_option'),
    )


def downgrade():
    op.drop_table("bible_quiz_answers")
    op.drop_index('ix_bible_quiz_attempts_quiz_id', table_name='bible_quiz_attempts')
    op.drop_index('ix_bible_quiz_attempts_user_id', table_name='bible_quiz_attempts')
    op.drop_table("bible_quiz_attempts")
    op.drop_table("bible_quiz_questions")
    op.drop_index('ix_bible_quizzes_church_id', table_name='bible_quizzes')
    op.drop_index('ix_bible_quizzes_church_status', table_name='bible_quizzes')
    op.drop_table("bible_quizzes")
