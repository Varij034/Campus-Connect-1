"""TPO (Training & Placement Officer) router - verification and stats"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from database.postgres import get_db
from database.models import User, Candidate, Application, Job, ApplicationStatus
from schemas.api import CandidateResponse
from auth.dependencies import get_current_active_user

router = APIRouter(prefix="/api/v1/tpo", tags=["TPO"])


def require_tpo_or_admin(current_user: User) -> None:
    if current_user.role.value not in ["tpo", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only TPO and admins can access this resource",
        )


@router.get("/candidates/pending-verification", response_model=List[CandidateResponse])
async def list_pending_verification(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List candidates with is_verified=False for TPO verification queue."""
    require_tpo_or_admin(current_user)
    candidates = (
        db.query(Candidate)
        .filter(Candidate.is_verified == False)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return candidates


@router.post("/candidates/{candidate_id}/verify", response_model=CandidateResponse)
async def verify_candidate(
    candidate_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mark a candidate as TPO-verified."""
    require_tpo_or_admin(current_user)
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )
    candidate.is_verified = True
    candidate.verified_at = datetime.now(timezone.utc)
    candidate.verified_by = current_user.id
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("/stats")
async def get_tpo_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Return stats for TPO dashboard: total candidates, verified count, placements, etc."""
    require_tpo_or_admin(current_user)
    total_candidates = db.query(Candidate).count()
    verified_count = db.query(Candidate).filter(Candidate.is_verified == True).count()
    total_applications = db.query(Application).count()
    placements = db.query(Application).filter(Application.status == ApplicationStatus.ACCEPTED).count()
    active_jobs = db.query(Job).count()
    return {
        "total_candidates": total_candidates,
        "verified_count": verified_count,
        "total_applications": total_applications,
        "placements": placements,
        "active_jobs": active_jobs,
    }
