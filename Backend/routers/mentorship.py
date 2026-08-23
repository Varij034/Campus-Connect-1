"""Alumni mentorship: mentors list, requests, accept/decline"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database.postgres import get_db
from database.models import User, Candidate, MentorProfile, MentorshipRequest, UserRole
from schemas.api import (
    MentorProfileResponse,
    MentorProfileCreate,
    MentorshipRequestCreate,
    MentorshipRequestUpdate,
    MentorshipRequestResponse,
)
from auth.dependencies import get_current_active_user

router = APIRouter(prefix="/api/v1", tags=["Mentorship"])


def _mentor_to_response(m: MentorProfile) -> MentorProfileResponse:
    return MentorProfileResponse(
        id=m.id,
        user_id=m.user_id,
        headline=m.headline,
        bio=m.bio,
        skills_json=m.skills_json if isinstance(m.skills_json, list) else list(m.skills_json) if m.skills_json else None,
        company=m.company,
        years_experience=m.years_experience,
        linkedin_url=m.linkedin_url,
        is_available=m.is_available,
        created_at=m.created_at,
    )


@router.get("/mentors", response_model=List[MentorProfileResponse])
async def list_mentors(
    skill: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    is_available: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List mentor profiles with optional filters."""
    query = db.query(MentorProfile)
    if is_available is not None:
        query = query.filter(MentorProfile.is_available == is_available)
    if company:
        query = query.filter(MentorProfile.company.ilike(f"%{company}%"))
    mentors = query.all()
    if skill:
        skill_lower = skill.lower()
        mentors = [m for m in mentors if m.skills_json and any(s and s.lower() == skill_lower for s in (m.skills_json or []))]
    return [_mentor_to_response(m) for m in mentors]


@router.post("/mentors", response_model=MentorProfileResponse, status_code=201)
async def create_my_mentor_profile(
    body: MentorProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create or update mentor profile (role MENTOR only)."""
    if current_user.role != UserRole.MENTOR:
        raise HTTPException(status_code=403, detail="Only mentors can create a mentor profile")
    existing = db.query(MentorProfile).filter(MentorProfile.user_id == current_user.id).first()
    if existing:
        if body.headline is not None:
            existing.headline = body.headline
        if body.bio is not None:
            existing.bio = body.bio
        if body.skills_json is not None:
            existing.skills_json = body.skills_json
        if body.company is not None:
            existing.company = body.company
        if body.years_experience is not None:
            existing.years_experience = body.years_experience
        if body.linkedin_url is not None:
            existing.linkedin_url = body.linkedin_url
        if body.is_available is not None:
            existing.is_available = body.is_available
        db.commit()
        db.refresh(existing)
        return _mentor_to_response(existing)
    mentor = MentorProfile(
        user_id=current_user.id,
        headline=body.headline,
        bio=body.bio,
        skills_json=body.skills_json,
        company=body.company,
        years_experience=body.years_experience,
        linkedin_url=body.linkedin_url,
        is_available=body.is_available if body.is_available is not None else True,
    )
    db.add(mentor)
    db.commit()
    db.refresh(mentor)
    return _mentor_to_response(mentor)


@router.get("/mentors/{mentor_id}", response_model=MentorProfileResponse)
async def get_mentor(
    mentor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a single mentor profile."""
    mentor = db.query(MentorProfile).filter(MentorProfile.id == mentor_id).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")
    return _mentor_to_response(mentor)


@router.post("/mentorship/requests", response_model=MentorshipRequestResponse)
async def create_mentorship_request(
    body: MentorshipRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Student creates a mentorship request (requires student/candidate profile)."""
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=400, detail="Candidate profile required to request mentorship")
    mentor = db.query(MentorProfile).filter(MentorProfile.id == body.mentor_id).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")
    existing = (
        db.query(MentorshipRequest)
        .filter(
            MentorshipRequest.mentor_id == body.mentor_id,
            MentorshipRequest.student_id == candidate.id,
            MentorshipRequest.status == "pending",
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="You already have a pending request for this mentor")
    req = MentorshipRequest(
        mentor_id=body.mentor_id,
        student_id=candidate.id,
        message=body.message,
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("/mentorship/requests/me", response_model=List[MentorshipRequestResponse])
async def list_my_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List mentorship requests for current user (as student or mentor)."""
    # As student: requests I sent
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    mentor_profile = db.query(MentorProfile).filter(MentorProfile.user_id == current_user.id).first()
    requests = []
    if candidate:
        requests = list(
            db.query(MentorshipRequest).filter(MentorshipRequest.student_id == candidate.id).all()
        )
    if mentor_profile:
        mentor_requests = (
            db.query(MentorshipRequest).filter(MentorshipRequest.mentor_id == mentor_profile.id).all()
        )
        for r in mentor_requests:
            if r not in requests:
                requests.append(r)
    return requests


@router.patch("/mentorship/requests/{request_id}", response_model=MentorshipRequestResponse)
async def update_mentorship_request(
    request_id: int,
    body: MentorshipRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mentor accepts or declines a request."""
    if body.status not in ("accepted", "declined"):
        raise HTTPException(status_code=400, detail="status must be 'accepted' or 'declined'")
    mentor_profile = db.query(MentorProfile).filter(MentorProfile.user_id == current_user.id).first()
    if not mentor_profile:
        raise HTTPException(status_code=403, detail="Only mentors can respond to requests")
    req = db.query(MentorshipRequest).filter(MentorshipRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.mentor_id != mentor_profile.id:
        raise HTTPException(status_code=403, detail="Not your request to respond to")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Request already responded to")
    req.status = body.status
    req.responded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(req)
    return req
