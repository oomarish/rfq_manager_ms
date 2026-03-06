"""
SQLAlchemy model for the `rfq_history` table.

Audit log tracking all changes to RFQs, stages, subtasks, and reminders.

Columns:
- id              UUID PK
- rfq_id          UUID FK → rfq.id
- entity_type     VARCHAR  — rfq | rfq_stage | subtask | reminder | rfq_file | rfq_note
- entity_id       UUID     — PK of the changed entity
- action          VARCHAR  — created | updated | deleted | advanced | status_changed
- changed_by      VARCHAR  — user who made the change
- changes         JSONB    — diff of old vs new values
- created_at      TIMESTAMP WITH TZ
"""

import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from src.database import Base


class RFQHistory(Base):
    __tablename__ = "rfq_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Which RFQ this event belongs to ───────────────
    rfq_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rfq.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── What happened ─────────────────────────────────
    entity_type = Column(String(50), nullable=False)     # "rfq", "rfq_stage", "subtask", "file"
    entity_id = Column(UUID(as_uuid=True), nullable=False)  # ID of the specific entity
    action = Column(String(50), nullable=False)          # "CREATED", "UPDATED", "DELETED", "STAGE_ADVANCED"

    # ── What changed ──────────────────────────────────
    changes = Column(JSON, nullable=True)                # {"field": {"old": X, "new": Y}}

    # ── Who did it ────────────────────────────────────
    user_id = Column(String(200), nullable=True)         # from auth token — NULL in dev
    user_name = Column(String(200), nullable=True)

    # ── When (append-only — no updated_at) ────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
