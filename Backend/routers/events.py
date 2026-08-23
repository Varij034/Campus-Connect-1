"""Hackathon, startup, workshop events and registrations"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from database.postgres import get_db
from database.models import User, Candidate, Event, EventRegistration, UserRole
from schemas.api import EventResponse, EventCreate, EventRegistrationResponse
from auth.dependencies import get_current_active_user

router = APIRouter(prefix="/api/v1/events", tags=["Events"])


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(
    body: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create an event (TPO or admin only)."""
    if current_user.role not in (UserRole.TPO, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only TPO or admin can create events")
    event = Event(
        title=body.title,
        description=body.description,
        type=body.type,
        start_date=body.start_date,
        end_date=body.end_date,
        location=body.location,
        registration_deadline=body.registration_deadline,
        max_participants=body.max_participants,
        is_active=body.is_active,
        created_by=current_user.id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return _event_to_response(event, registration_count=0)


def _event_to_response(e: Event, registration_count: Optional[int] = None) -> EventResponse:
    if registration_count is None and e.registrations is not None:
        registration_count = len(e.registrations)
    return EventResponse(
        id=e.id,
        title=e.title,
        description=e.description,
        type=e.type,
        start_date=e.start_date,
        end_date=e.end_date,
        location=e.location,
        registration_deadline=e.registration_deadline,
        max_participants=e.max_participants,
        is_active=e.is_active,
        created_by=e.created_by,
        created_at=e.created_at,
        registration_count=registration_count or 0,
    )


@router.get("", response_model=List[EventResponse])
async def list_events(
    type_filter: Optional[str] = Query(None, alias="type"),
    is_active: Optional[bool] = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List events with optional filters."""
    query = db.query(Event)
    if is_active is not None:
        query = query.filter(Event.is_active == is_active)
    if type_filter:
        query = query.filter(Event.type == type_filter)
    events = query.order_by(Event.start_date.desc()).all()
    result = []
    for e in events:
        count = db.query(func.count(EventRegistration.id)).filter(EventRegistration.event_id == e.id).scalar() or 0
        result.append(_event_to_response(e, registration_count=count))
    return result


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a single event with registration count."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    count = db.query(func.count(EventRegistration.id)).filter(EventRegistration.event_id == event_id).scalar() or 0
    return _event_to_response(event, registration_count=count)


@router.post("/{event_id}/register", response_model=EventRegistrationResponse, status_code=201)
async def register_for_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Register current user (student) for an event."""
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=400, detail="Candidate profile required to register for events")
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not event.is_active:
        raise HTTPException(status_code=400, detail="Event is not open for registration")
    existing = (
        db.query(EventRegistration)
        .filter(EventRegistration.event_id == event_id, EventRegistration.candidate_id == candidate.id)
        .first()
    )
    if existing:
        if existing.status == "cancelled":
            existing.status = "registered"
            db.commit()
            db.refresh(existing)
            return existing
        raise HTTPException(status_code=400, detail="Already registered for this event")
    reg_count = db.query(func.count(EventRegistration.id)).filter(EventRegistration.event_id == event_id).scalar() or 0
    status = "registered"
    if event.max_participants and reg_count >= event.max_participants:
        status = "waitlist"
    reg = EventRegistration(event_id=event_id, candidate_id=candidate.id, status=status)
    db.add(reg)
    db.commit()
    db.refresh(reg)
    return reg


@router.get("/registrations/me", response_model=List[EventRegistrationResponse])
async def list_my_registrations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List current user's event registrations."""
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        return []
    regs = (
        db.query(EventRegistration)
        .filter(EventRegistration.candidate_id == candidate.id)
        .order_by(EventRegistration.created_at.desc())
        .all()
    )
    return regs
