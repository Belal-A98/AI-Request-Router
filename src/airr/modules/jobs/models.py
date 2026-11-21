"""Durable work queue entry for a request."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ...core.identifiers import new_id
from ...db import Base


class Job(Base):
    __tablename__ = 'jobs'
    __table_args__ = (UniqueConstraint('request_id', 'kind', name='uq_job_request_kind'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey('requests.id'), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False, default='classify')
    status: Mapped[str] = mapped_column(String(24), nullable=False, default='PENDING')
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(50))
