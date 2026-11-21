"""Lease-based acquisition of pending work (current implementation; PG fencing unverified)."""
from datetime import timedelta
from sqlalchemy import select, update
from ...core.identifiers import now_utc

LEASE_SECONDS = 60


def claim_next(session, model):
    current = now_utc()
    stale = current - timedelta(seconds=LEASE_SECONDS)
    eligible = (model.status == 'PENDING') | ((model.status == 'CLAIMED') & (model.claimed_at < stale))
    row = session.scalars(select(model).where(eligible).order_by(model.id).limit(1)).first()
    if row is None:
        return None
    changed = session.execute(update(model).where(
        model.id == row.id,
        ((model.status == 'PENDING') | ((model.status == 'CLAIMED') & (model.claimed_at < stale))),
    ).values(status='CLAIMED', claimed_at=current, attempts=model.attempts + 1)
     .execution_options(synchronize_session=False)).rowcount
    if changed != 1:
        return None
    return row.id, row.request_id
