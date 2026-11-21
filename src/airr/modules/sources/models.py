"""Operator-provisioned sources; raw API keys are never persisted."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from ...core.identifiers import now_utc
from ...db import Base


class Source(Base):
    __tablename__ = 'sources'

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    key_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc,
                                                 onupdate=now_utc, nullable=False)
