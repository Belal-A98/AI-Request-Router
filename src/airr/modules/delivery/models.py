"""Durable outbound delivery state (internal-only implementation)."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ...core.identifiers import new_id
from ...db import Base


class Delivery(Base):
    __tablename__ = 'deliveries'
    __table_args__ = (UniqueConstraint('request_id', name='uq_delivery_request'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey('requests.id'), nullable=False, index=True)
    destination: Mapped[str] = mapped_column(String(60), nullable=False, default='internal')
    status: Mapped[str] = mapped_column(String(25), nullable=False, default='PENDING')
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
