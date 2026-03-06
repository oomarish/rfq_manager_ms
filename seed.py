"""
Seed script — creates tables and inserts default workflow + stage templates.

Usage:
  python seed.py

Idempotent: skips insert if workflow already exists.
Requires a running PostgreSQL instance and valid DATABASE_URL (env var).
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base  # Base is shared across models

# Import ALL models so Base.metadata registers every table
from src.models.rfq import RFQ                                   # noqa: F401
from src.models.workflow import Workflow, StageTemplate           # noqa: F401
from src.models.rfq_stage import RFQStage                         # noqa: F401
from src.models.subtask import Subtask                            # noqa: F401
from src.models.rfq_note import RFQNote                           # noqa: F401
from src.models.rfq_file import RFQFile                           # noqa: F401
from src.models.rfq_stage_field_value import RFQStageFieldValue   # noqa: F401
from src.models.rfq_history import RFQHistory                     # noqa: F401
from src.models.reminder import Reminder, ReminderRule            # noqa: F401


WORKFLOW_CODE = "GHI-STD"


def _make_engine_and_session():
    """
    Create engine/session from DATABASE_URL env var.
    This avoids any config/.env overrides inside src.database.
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Example:\n"
            "  $env:DATABASE_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:5433/rfq_manager_db'"
        )

    engine = create_engine(db_url, future=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal


def seed():
    engine, SessionLocal = _make_engine_and_session()

    # ── 1. Create all tables ──────────────────────────
    print("Creating tables...")
    Base.metadata.create_all(engine)
    print(f"  ✓ {len(Base.metadata.tables)} tables created/verified")

    # ── 2. Seed default workflow ──────────────────────
    session = SessionLocal()
    try:
        existing = session.query(Workflow).filter_by(code=WORKFLOW_CODE).first()
        if existing:
            print(f"  ✓ Workflow '{WORKFLOW_CODE}' already exists (id={existing.id}) — skipping")
            return

        workflow = Workflow(
            name="GHI Standard Workflow",
            code=WORKFLOW_CODE,
            description="Standard 5-stage RFQ lifecycle for GHI equipment proposals.",
            is_active=True,
            is_default=True,
        )
        session.add(workflow)
        session.flush()  # generate workflow.id

        stages = [
            {
                "name": "Inquiry Review & Scope Definition",
                "order": 1,
                "default_team": "Sales Engineering",
                "planned_duration_days": 3,
                "mandatory_fields": None,
            },
            {
                "name": "BOQ / BOM Preparation",
                "order": 2,
                "default_team": "Engineering",
                "planned_duration_days": 7,
                "mandatory_fields": "boq_completed",
            },
            {
                "name": "Technical Design & Estimation",
                "order": 3,
                "default_team": "Engineering",
                "planned_duration_days": 10,
                "mandatory_fields": "design_approved,estimation_completed",
            },
            {
                "name": "Commercial Review & Pricing",
                "order": 4,
                "default_team": "Commercial",
                "planned_duration_days": 5,
                "mandatory_fields": "margin,final_price",
            },
            {
                "name": "Final Review & Submission",
                "order": 5,
                "default_team": "Management",
                "planned_duration_days": 3,
                "mandatory_fields": "approval_signature",
            },
        ]

        for stage_data in stages:
            template = StageTemplate(
                workflow_id=workflow.id,
                **stage_data,
            )
            session.add(template)

        session.commit()
        print(f"  ✓ Workflow '{WORKFLOW_CODE}' created (id={workflow.id}) with {len(stages)} stages")

    except Exception as e:
        session.rollback()
        print(f"  ✗ Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed()
    print("\nDone! You can now start the app and test POST /rfqs.")