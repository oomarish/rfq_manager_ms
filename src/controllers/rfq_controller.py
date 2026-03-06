"""
RFQ controller — business logic for the RFQ resource.

Orchestrates:
- RFQ creation: validates workflow_id, auto-generates rfq_stage instances,
  back-calculates planned dates from deadline, sets initial status
- RFQ update: deadline change triggers recalculation of all stage planned dates
- Stats & analytics aggregation

Dependencies: RfqDatasource, RfqStageDatasource, WorkflowDatasource
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from src.datasources.rfq_datasource import RfqDatasource
from src.datasources.workflow_datasource import WorkflowDatasource
from src.datasources.rfq_stage_datasource import RfqStageDatasource
from src.translators import rfq_translator
from src.utils.errors import NotFoundError, BadRequestError
from src.utils.pagination import PaginationParams, paginate, paginated_response


class RfqController:

    def __init__(
        self,
        rfq_datasource: RfqDatasource,
        workflow_datasource: WorkflowDatasource,
        rfq_stage_datasource: RfqStageDatasource,
        session: Session,
    ):
        self.rfq_ds = rfq_datasource
        self.workflow_ds = workflow_datasource
        self.stage_ds = rfq_stage_datasource
        self.session = session

    # ══════════════════════════════════════════════════
    # CREATE — the most complex method
    # ══════════════════════════════════════════════════
    def create(self, request: rfq_translator.RfqCreateRequest) -> rfq_translator.RfqDetail:
        """Create an RFQ with auto-generated stages."""

        # ── 1. Validate workflow exists ───────────────
        workflow = self.workflow_ds.get_by_id(request.workflow_id)
        if not workflow:
            raise NotFoundError(f"Workflow '{request.workflow_id}' not found")

        if not workflow.stages:
            raise BadRequestError(f"Workflow '{workflow.name}' has no stage templates")

        # ── 2. Create the RFQ row ─────────────────────
        rfq_data = rfq_translator.from_create_request(request)
        rfq = self.rfq_ds.create(rfq_data)

        # ── 3. Calculate planned dates ────────────────
        stage_dates = self._calculate_stage_dates(
            deadline=request.deadline,
            stages=workflow.stages,
        )

        # ── 4. Create rfq_stage rows ─────────────────
        overrides = {}
        if request.stage_overrides:
            for override in request.stage_overrides:
                overrides[override.stage_template_id] = override.assigned_team

        first_stage = None
        for template in workflow.stages:
            dates = stage_dates[template.order]
            assigned_team = overrides.get(template.id, template.default_team)

            stage_data = {
                "rfq_id": rfq.id,
                "name": template.name,
                "order": template.order,
                "assigned_team": assigned_team,
                "status": "Not started",
                "progress": 0,
                "planned_start": dates["start"],
                "planned_end": dates["end"],
                "mandatory_fields": template.mandatory_fields,  # snapshot from template
            }

            if template.order == 1:
                stage_data["status"] = "In Progress"
                stage_data["actual_start"] = date.today()

            stage = self.stage_ds.create(stage_data)

            if template.order == 1:
                first_stage = stage

        # ── 5. Set current_stage_id ───────────────────
        if first_stage:
            rfq.current_stage_id = first_stage.id
            self.session.flush()

        # ── 6. Commit — everything or nothing ─────────
        self.session.commit()
        self.session.refresh(rfq)

        return rfq_translator.to_detail(rfq, current_stage_name=first_stage.name if first_stage else None)

    # ══════════════════════════════════════════════════
    # GET
    # ══════════════════════════════════════════════════
    def get(self, rfq_id) -> rfq_translator.RfqDetail:
        """Fetch one RFQ by ID. Raises 404 if not found."""
        rfq = self.rfq_ds.get_by_id(rfq_id)
        if not rfq:
            raise NotFoundError(f"RFQ '{rfq_id}' not found")

        current_stage_name = self._get_current_stage_name(rfq)
        return rfq_translator.to_detail(rfq, current_stage_name=current_stage_name)

    # ══════════════════════════════════════════════════
    # LIST
    # ══════════════════════════════════════════════════
    def list(
        self,
        search: str = None,
        status: str = None,
        priority: str = None,
        sort: str = None,
        page: int = 1,
        size: int = 20,
    ) -> dict:
        """List RFQs with filters, sort, and pagination."""
        query = self.rfq_ds.list(search=search, status=status, priority=priority, sort=sort)

        params = PaginationParams(page=page, size=size)
        items, total = paginate(query, params)

        summaries = [rfq_translator.to_summary(rfq) for rfq in items]
        return paginated_response(summaries, total, params)

    # ══════════════════════════════════════════════════
    # STATS (#5)
    # ══════════════════════════════════════════════════
    def get_stats(self) -> dict:
        """Dashboard KPIs: total, open, critical, avg cycle."""
        return self.rfq_ds.get_stats()

    # ══════════════════════════════════════════════════
    # ANALYTICS (#6)
    # ══════════════════════════════════════════════════
    def get_analytics(self) -> dict:
        """Business analytics: win rate, margins, by-client breakdown."""
        return self.rfq_ds.get_analytics()

    # ══════════════════════════════════════════════════
    # UPDATE
    # ══════════════════════════════════════════════════
    def update(self, rfq_id, request: rfq_translator.RfqUpdateRequest) -> rfq_translator.RfqDetail:
        """Partial update. Deadline change triggers stage date recalculation."""
        rfq = self.rfq_ds.get_by_id(rfq_id)
        if not rfq:
            raise NotFoundError(f"RFQ '{rfq_id}' not found")

        update_data = request.model_dump(exclude_unset=True)

        if "deadline" in update_data:
            self._recalculate_stage_dates(rfq, update_data["deadline"])

        rfq = self.rfq_ds.update(rfq, update_data)
        self.session.commit()
        self.session.refresh(rfq)

        current_stage_name = self._get_current_stage_name(rfq)
        return rfq_translator.to_detail(rfq, current_stage_name=current_stage_name)

    # ══════════════════════════════════════════════════
    # PRIVATE HELPERS
    # ══════════════════════════════════════════════════

    def _calculate_stage_dates(self, deadline: date, stages) -> dict:
        """Back-calculate planned_start/planned_end from the deadline."""
        result = {}
        sorted_stages = sorted(stages, key=lambda s: s.order, reverse=True)
        current_end = deadline

        for stage in sorted_stages:
            duration = stage.planned_duration_days
            stage_start = current_end - timedelta(days=duration)

            result[stage.order] = {
                "start": stage_start,
                "end": current_end,
            }
            current_end = stage_start

        return result

    def _recalculate_stage_dates(self, rfq, new_deadline: date):
        """When the deadline changes, recalculate all uncompleted stage planned dates."""
        workflow = self.workflow_ds.get_by_id(rfq.workflow_id)
        if not workflow:
            return

        new_dates = self._calculate_stage_dates(new_deadline, workflow.stages)

        from src.models.rfq_stage import RFQStage
        stages = (
            self.session.query(RFQStage)
            .filter_by(rfq_id=rfq.id)
            .all()
        )

        for stage in stages:
            if stage.status not in ("Completed", "Skipped"):
                dates = new_dates.get(stage.order)
                if dates:
                    stage.planned_start = dates["start"]
                    stage.planned_end = dates["end"]

        self.session.flush()

    def _get_current_stage_name(self, rfq) -> str | None:
        """Get the name of the current stage for response formatting."""
        if not rfq.current_stage_id:
            return None

        from src.models.rfq_stage import RFQStage
        stage = self.session.query(RFQStage).filter(RFQStage.id == rfq.current_stage_id).first()
        return stage.name if stage else None
