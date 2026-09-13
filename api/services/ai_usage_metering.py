"""
Concurrency-safe XynaFaith V2 AI usage metering.

Lifecycle:

    reserve_usage()
        -> AI work
        -> complete_usage() on success
        -> release_usage() on failure

The UsageBucket row is the serialized quota authority.

These functions intentionally flush but do not commit. Transaction
ownership belongs to the caller.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.models.ai_usage_event import AIUsageEvent
from api.models.ai_usage_reservation import AIUsageReservation
from api.models.usage_bucket import UsageBucket


RESERVATION_RESERVED = "reserved"
RESERVATION_CONSUMED = "consumed"
RESERVATION_RELEASED = "released"


class UsageMeteringError(Exception):
    """Base metering exception."""


class UsageLimitExceeded(UsageMeteringError):
    """The requested metered work would exceed the allowance."""


class UsageReservationConflict(UsageMeteringError):
    """A request_id was reused for incompatible metered work."""


class UsageReservationStateError(UsageMeteringError):
    """The reservation is in an invalid lifecycle state."""


@dataclass(frozen=True)
class UsagePeriod:
    start: datetime
    end: datetime


def resolve_usage_period(
    usage_period: str,
    *,
    now: Optional[datetime] = None,
) -> UsagePeriod:
    """
    Resolve baseline calendar usage periods in UTC-style naive datetimes.

    Existing XynaFaith models currently use naive UTC datetimes, so this
    preserves that convention until the wider datetime migration occurs.
    """

    now = now or datetime.utcnow()
    normalized = (usage_period or "").strip().lower()

    if normalized == "daily":
        start = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return UsagePeriod(
            start=start,
            end=start + timedelta(days=1),
        )

    if normalized == "monthly":
        start = now.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        if start.month == 12:
            end = start.replace(
                year=start.year + 1,
                month=1,
            )
        else:
            end = start.replace(
                month=start.month + 1,
            )

        return UsagePeriod(
            start=start,
            end=end,
        )

    raise ValueError(
        f"Unsupported usage period: {usage_period!r}"
    )


def _reservation_matches(
    reservation: AIUsageReservation,
    *,
    user_id: int,
    church_id: Optional[int],
    subscription_id: Optional[int],
    entitlement_key: str,
    metric: str,
    units: int,
) -> bool:
    return (
        reservation.user_id == user_id
        and reservation.church_id == church_id
        and reservation.subscription_id == subscription_id
        and reservation.entitlement_key == entitlement_key
        and reservation.metric == metric
        and reservation.units == units
    )


def _acquire_request_lock(
    db: Session,
    request_id: str,
) -> None:
    """
    Serialize identical request IDs on PostgreSQL.

    The lock is transaction-scoped and automatically releases on
    commit or rollback. Other databases, including SQLite unit tests,
    do not need this PostgreSQL-specific concurrency primitive.
    """

    bind = db.get_bind()

    if bind.dialect.name != "postgresql":
        return

    db.execute(
        text(
            """
            SELECT pg_advisory_xact_lock(
                hashtextextended(:lock_key, 0)
            )
            """
        ),
        {
            "lock_key": (
                "xynafaith:ai-usage-request:"
                + request_id
            )
        },
    )


def _get_existing_reservation(
    db: Session,
    request_id: str,
) -> Optional[AIUsageReservation]:
    return (
        db.query(AIUsageReservation)
        .filter(
            AIUsageReservation.request_id == request_id
        )
        .first()
    )


def _acquire_bucket_lock(
    db: Session,
    *,
    user_id: Optional[int],
    church_id: Optional[int],
    entitlement_key: str,
    metric: str,
    period_start: datetime,
) -> None:
    """
    Serialize access to one logical usage bucket on PostgreSQL.

    This closes the first-use race where two transactions both observe
    that no bucket exists and then attempt to create the same bucket.
    The lock is transaction-scoped and automatically releases on
    commit or rollback.
    """

    if (user_id is None) == (church_id is None):
        raise ValueError(
            "Exactly one quota owner is required"
        )

    bind = db.get_bind()

    if bind.dialect.name != "postgresql":
        return

    if user_id is not None:
        owner = f"user:{user_id}"
    else:
        owner = f"church:{church_id}"

    lock_key = (
        "xynafaith:ai-usage-bucket:"
        f"{owner}:"
        f"{entitlement_key}:"
        f"{metric}:"
        f"{period_start.isoformat()}"
    )

    db.execute(
        text(
            """
            SELECT pg_advisory_xact_lock(
                hashtextextended(:lock_key, 0)
            )
            """
        ),
        {"lock_key": lock_key},
    )


def _get_or_create_bucket(
    db: Session,
    *,
    user_id: Optional[int],
    church_id: Optional[int],
    entitlement_key: str,
    metric: str,
    period: UsagePeriod,
    allowance_units: int,
) -> UsageBucket:
    """
    Load the quota bucket with a row lock, creating it when necessary.

    PostgreSQL serializes access to the logical bucket before lookup or
    creation. Partial unique indexes remain the final database invariant.
    """

    if (user_id is None) == (church_id is None):
        raise ValueError(
            "Exactly one quota owner is required"
        )

    _acquire_bucket_lock(
        db,
        user_id=user_id,
        church_id=church_id,
        entitlement_key=entitlement_key,
        metric=metric,
        period_start=period.start,
    )

    query = db.query(UsageBucket).filter(
        UsageBucket.entitlement_key == entitlement_key,
        UsageBucket.metric == metric,
        UsageBucket.period_start == period.start,
    )

    if user_id is not None:
        query = query.filter(
            UsageBucket.user_id == user_id,
            UsageBucket.church_id.is_(None),
        )
    else:
        query = query.filter(
            UsageBucket.church_id == church_id,
            UsageBucket.user_id.is_(None),
        )

    bucket = query.with_for_update().first()

    if bucket is not None:
        # Raising an allowance is safe. We deliberately do not lower an
        # existing bucket mid-period because doing so could make already
        # consumed/reserved work retroactively invalid.
        if allowance_units > bucket.allowance_units:
            bucket.allowance_units = allowance_units

        return bucket

    bucket = UsageBucket(
        user_id=user_id,
        church_id=church_id,
        entitlement_key=entitlement_key,
        metric=metric,
        period_start=period.start,
        period_end=period.end,
        allowance_units=allowance_units,
        consumed_units=0,
        reserved_units=0,
    )

    db.add(bucket)
    db.flush()

    # Lock the newly created row for the rest of this transaction.
    return (
        db.query(UsageBucket)
        .filter(UsageBucket.id == bucket.id)
        .with_for_update()
        .one()
    )


def reserve_usage(
    db: Session,
    *,
    request_id: str,
    actor_user_id: int,
    quota_user_id: Optional[int],
    quota_church_id: Optional[int],
    subscription_id: Optional[int],
    entitlement_key: str,
    metric: str,
    units: int,
    allowance_units: int,
    usage_period: str,
    now: Optional[datetime] = None,
) -> AIUsageReservation:
    """
    Reserve quota before performing expensive AI work.

    Reusing the same request_id with identical parameters is idempotent.
    Reusing it for different work fails closed.
    """

    request_id = (request_id or "").strip()

    if not request_id:
        raise ValueError("request_id is required")

    if units <= 0:
        raise ValueError("units must be positive")

    if allowance_units < 0:
        raise ValueError(
            "allowance_units cannot be negative"
        )

    if (quota_user_id is None) == (
        quota_church_id is None
    ):
        raise ValueError(
            "Exactly one quota owner is required"
        )

    now = now or datetime.utcnow()

    _acquire_request_lock(
        db,
        request_id,
    )

    existing = _get_existing_reservation(
        db,
        request_id,
    )

    expected_church_id = quota_church_id

    if existing is not None:
        if not _reservation_matches(
            existing,
            user_id=actor_user_id,
            church_id=expected_church_id,
            subscription_id=subscription_id,
            entitlement_key=entitlement_key,
            metric=metric,
            units=units,
        ):
            raise UsageReservationConflict(
                "request_id already belongs to different metered work"
            )

        return existing

    period = resolve_usage_period(
        usage_period,
        now=now,
    )

    bucket = _get_or_create_bucket(
        db,
        user_id=quota_user_id,
        church_id=quota_church_id,
        entitlement_key=entitlement_key,
        metric=metric,
        period=period,
        allowance_units=allowance_units,
    )

    available = (
        bucket.allowance_units
        - bucket.consumed_units
        - bucket.reserved_units
    )

    if units > available:
        raise UsageLimitExceeded(
            f"Usage limit exhausted for {entitlement_key}"
        )

    bucket.reserved_units += units

    reservation = AIUsageReservation(
        request_id=request_id,
        bucket_id=bucket.id,
        user_id=actor_user_id,
        church_id=quota_church_id,
        subscription_id=subscription_id,
        entitlement_key=entitlement_key,
        metric=metric,
        units=units,
        status=RESERVATION_RESERVED,
    )

    db.add(reservation)

    try:
        db.flush()
    except IntegrityError:
        # Do not rollback here. Transaction ownership belongs to caller.
        # A true concurrent duplicate request_id must be retried by the
        # transaction boundary after rollback.
        raise

    return reservation


def complete_usage(
    db: Session,
    *,
    request_id: str,
    now: Optional[datetime] = None,
) -> AIUsageReservation:
    """
    Convert a reservation into consumed usage and write the immutable event.
    """

    now = now or datetime.utcnow()

    reservation = (
        db.query(AIUsageReservation)
        .filter(
            AIUsageReservation.request_id == request_id
        )
        .with_for_update()
        .one_or_none()
    )

    if reservation is None:
        raise UsageReservationStateError(
            "Usage reservation does not exist"
        )

    if reservation.status == RESERVATION_CONSUMED:
        return reservation

    if reservation.status == RESERVATION_RELEASED:
        raise UsageReservationStateError(
            "Released usage cannot be completed"
        )

    if reservation.status != RESERVATION_RESERVED:
        raise UsageReservationStateError(
            f"Unknown reservation status: {reservation.status}"
        )

    bucket = (
        db.query(UsageBucket)
        .filter(
            UsageBucket.id == reservation.bucket_id
        )
        .with_for_update()
        .one()
    )

    if bucket.reserved_units < reservation.units:
        raise UsageReservationStateError(
            "Bucket reserved units are inconsistent"
        )

    bucket.reserved_units -= reservation.units
    bucket.consumed_units += reservation.units

    reservation.status = RESERVATION_CONSUMED
    reservation.completed_at = now

    event = AIUsageEvent(
        request_id=reservation.request_id,
        user_id=reservation.user_id,
        church_id=reservation.church_id,
        subscription_id=reservation.subscription_id,
        entitlement_key=reservation.entitlement_key,
        metric=reservation.metric,
        units=reservation.units,
    )

    db.add(event)
    db.flush()

    return reservation


def release_usage(
    db: Session,
    *,
    request_id: str,
    now: Optional[datetime] = None,
) -> AIUsageReservation:
    """
    Release reserved quota after AI work fails before successful completion.
    """

    now = now or datetime.utcnow()

    reservation = (
        db.query(AIUsageReservation)
        .filter(
            AIUsageReservation.request_id == request_id
        )
        .with_for_update()
        .one_or_none()
    )

    if reservation is None:
        raise UsageReservationStateError(
            "Usage reservation does not exist"
        )

    if reservation.status == RESERVATION_RELEASED:
        return reservation

    if reservation.status == RESERVATION_CONSUMED:
        raise UsageReservationStateError(
            "Consumed usage cannot be released"
        )

    if reservation.status != RESERVATION_RESERVED:
        raise UsageReservationStateError(
            f"Unknown reservation status: {reservation.status}"
        )

    bucket = (
        db.query(UsageBucket)
        .filter(
            UsageBucket.id == reservation.bucket_id
        )
        .with_for_update()
        .one()
    )

    if bucket.reserved_units < reservation.units:
        raise UsageReservationStateError(
            "Bucket reserved units are inconsistent"
        )

    bucket.reserved_units -= reservation.units

    reservation.status = RESERVATION_RELEASED
    reservation.released_at = now

    db.flush()

    return reservation
