"""
SQLAlchemy model for the `rfq_stage_field_value` table.

Stores individual captured field values for a stage. Alternative to
using the `captured_data` JSONB column on rfq_stage — allows
structured querying across stages.

Columns:
- id              UUID PK
- rfq_stage_id    UUID FK → rfq_stage.id
- field_name      VARCHAR  — key name (e.g. "vessel_count", "material_grade")
- field_value     TEXT     — serialized value
- created_at      TIMESTAMP WITH TZ
- updated_at      TIMESTAMP WITH TZ
"""

import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from src.database import Base


class RFQStageFieldValue(Base):
    __tablename__ = "rfq_stage_field_value"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Parent stage ──────────────────────────────────
    rfq_stage_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rfq_stage.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Key-value pair ────────────────────────────────
    field_name = Column(String(200), nullable=False)     # "margin", "final_price"
    value = Column(JSON, nullable=True)                  # any JSON-serializable value

    # ── Metadata ──────────────────────────────────────
    updated_by = Column(String(200), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
