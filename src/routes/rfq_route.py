"""
RFQ routes — FastAPI router for RFQ endpoints.

Endpoints:
- POST   /rfqs              — #1 Create RFQ
- GET    /rfqs              — #2 List RFQs (paginated, with search/filter/sort)
- GET    /rfqs/stats        — #5 Dashboard KPIs
- GET    /rfqs/analytics    — #6 Business analytics
- GET    /rfqs/{rfqId}      — #3 Get RFQ detail
- PATCH  /rfqs/{rfqId}      — #4 Update RFQ
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from typing import Optional

from src.translators.rfq_translator import (
    RfqCreateRequest,
    RfqUpdateRequest,
    RfqDetail,
    RfqListResponse,
    RfqStats,
    RfqAnalytics,
)

from src.app_context import get_rfq_controller
from src.controllers.rfq_controller import RfqController


router = APIRouter(prefix="/rfqs", tags=["RFQ"])


# ── #1 — Create RFQ ──────────────────────────────────
@router.post("", status_code=201, response_model=RfqDetail)
def create_rfq(
    body: RfqCreateRequest,
    ctrl: RfqController = Depends(get_rfq_controller),
):
    """Create a new RFQ with auto-generated stages."""
    return ctrl.create(body)


# ── #2 — List RFQs ───────────────────────────────────
@router.get("", response_model=RfqListResponse)
def list_rfqs(
    search: Optional[str] = Query(None, description="Search in name and client"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    sort: Optional[str] = Query(None, description="Sort field, prefix - for desc"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    ctrl: RfqController = Depends(get_rfq_controller),
):
    """Paginated list with search, filters, and sort."""
    return ctrl.list(search=search, status=status, priority=priority, sort=sort, page=page, size=size)


# ── #5 — RFQ Stats ───────────────────────────────────
# IMPORTANT: /stats and /analytics must be BEFORE /{rfq_id}
@router.get("/stats", response_model=RfqStats)
def rfq_stats(
    ctrl: RfqController = Depends(get_rfq_controller),
):
    """Dashboard KPIs: total, open, critical, avg cycle."""
    return ctrl.get_stats()


# ── #6 — RFQ Analytics ───────────────────────────────
@router.get("/analytics", response_model=RfqAnalytics)
def rfq_analytics(
    ctrl: RfqController = Depends(get_rfq_controller),
):
    """Business analytics: win rate, margins, by-client breakdown."""
    return ctrl.get_analytics()


# ── #3 — Get RFQ Detail ──────────────────────────────
@router.get("/{rfq_id}", response_model=RfqDetail)
def get_rfq(
    rfq_id: UUID,
    ctrl: RfqController = Depends(get_rfq_controller),
):
    """Full RFQ detail by ID."""
    return ctrl.get(rfq_id)


# ── #4 — Update RFQ ──────────────────────────────────
@router.patch("/{rfq_id}", response_model=RfqDetail)
def update_rfq(
    rfq_id: UUID,
    body: RfqUpdateRequest,
    ctrl: RfqController = Depends(get_rfq_controller),
):
    """Partial update — only send fields you want to change."""
    return ctrl.update(rfq_id, body)
