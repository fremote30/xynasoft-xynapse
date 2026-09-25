from logging.config import fileConfig
import os

from sqlalchemy import create_engine, pool
from alembic import context
from dotenv import load_dotenv


from api.db.database import Base

from api.models.user import User
from api.models.sermon import Sermon
from api.models.prayer import Prayer
from api.models.shared_sermon import SharedSermon
from api.models.sermon_comment import SermonComment
from api.models.follow import PastorFollower
from api.models.pastor import Pastor
from api.models.pastor_profile import PastorProfile
from api.models.pastor_member import PastorMember
from api.models.sermon_collaborator import SermonCollaborator
from api.models.refresh_token import RefreshToken
from api.models.church import Church
from api.models.church_membership import ChurchMembership
from api.models.church_announcement import ChurchAnnouncement
from api.models.church_event import ChurchEvent
from api.models.member_profile import MemberProfile
from api.models.conversation_action_execution import (
    ConversationActionExecution,
)
from api.models.conversation_pending_memory_action import (
    ConversationPendingMemoryAction,
)

target_metadata = Base.metadata
# -------------------------------------------------
# Load environment variables
# -------------------------------------------------

# Preserve an explicitly supplied DATABASE_URL before loading .env.
# This lets CI, Render, and isolated development environments select
# their database without being overridden by DATABASE_URL_LOCAL.
EXPLICIT_DATABASE_URL = os.getenv("DATABASE_URL")

load_dotenv(".env")

DATABASE_URL = (
    EXPLICIT_DATABASE_URL
    or os.getenv("DATABASE_URL_LOCAL")
    or os.getenv("DATABASE_URL")
)

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL not set. "
        "Provide DATABASE_URL explicitly or define "
        "DATABASE_URL_LOCAL / DATABASE_URL in .env"
    )

# -------------------------------------------------
# Alembic Config
# -------------------------------------------------
config = context.config

# Override sqlalchemy.url from env (ignore alembic.ini value)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No ORM metadata yet (DDL-only migrations)


# -------------------------------------------------
# Offline migrations
# -------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# -------------------------------------------------
# Online migrations
# -------------------------------------------------
def run_migrations_online() -> None:
    """Run migrations in online mode."""
    engine = create_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
        future=True,
    )

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# -------------------------------------------------
# Entrypoint
# -------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


# XynaFaith V2 monetization models
from api.models.plan import Plan
from api.models.plan_entitlement import PlanEntitlement
from api.models.subscription import Subscription
from api.models.ai_usage_event import AIUsageEvent

# XynaFaith V2 AI usage metering
from api.models.usage_bucket import UsageBucket
from api.models.ai_usage_reservation import AIUsageReservation
