from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from railcheck.api.deps import get_review_service
from railcheck.api.schemas_reviews import ResolveReviewRequest, ReviewItemOut, ReviewListOut
from railcheck.application.review_service import (
    ReviewConflictError,
    ReviewNotFoundError,
    ReviewService,
)
from railcheck.domain.enums import ReviewStatus
from railcheck.domain.models import ReviewItem

router = APIRouter(prefix="/v1/reviews", tags=["reviews"])


def _to_out(item: ReviewItem) -> ReviewItemOut:
    return ReviewItemOut(
        id=str(item.id),
        status=item.status,
        action=item.result.action,
        reason=item.result.reason,
        triggered_by=item.result.triggered_by,
        pack=item.result.pack_name,
        backend=item.result.backend,
        candidate_output=item.context.candidate_output,
        user_prompt=item.context.user_prompt,
        tool_name=item.context.tool_name,
        answers=[
            {
                "key": a.key,
                "type": a.type.value,
                "value": a.value,
                "confidence": a.confidence,
                "probabilities": a.probabilities,
            }
            for a in item.result.answers
        ],
        created_at=item.created_at,
        resolved_at=item.resolved_at,
        resolver=item.resolver,
        resolution=item.resolution,
        note=item.note,
        rewritten_output=item.rewritten_output,
    )


@router.get("", response_model=ReviewListOut)
def list_reviews(
    service: Annotated[ReviewService, Depends(get_review_service)],
    status_filter: Annotated[
        ReviewStatus | None,
        Query(alias="status", description="Filter by pending or resolved"),
    ] = ReviewStatus.PENDING,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ReviewListOut:
    items = service.list_all(status=status_filter, limit=limit)
    return ReviewListOut(items=[_to_out(i) for i in items], count=len(items))


@router.get("/{review_id}", response_model=ReviewItemOut)
def get_review(
    review_id: UUID,
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> ReviewItemOut:
    try:
        return _to_out(service.get(review_id))
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{review_id}/resolve", response_model=ReviewItemOut)
def resolve_review(
    review_id: UUID,
    body: ResolveReviewRequest,
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> ReviewItemOut:
    try:
        resolved = service.resolve(
            review_id,
            resolution=body.resolution,
            resolver=body.resolver,
            note=body.note,
            rewritten_output=body.rewritten_output,
        )
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ReviewConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _to_out(resolved)
