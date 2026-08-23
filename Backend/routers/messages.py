"""Company–candidate messaging (conversations and messages)"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database.postgres import get_db
from database.models import User, Candidate, Job, Conversation, Message
from schemas.api import (
    ConversationResponse,
    ConversationCreate,
    MessageResponse,
    MessageCreate,
)
from auth.dependencies import get_current_active_user

router = APIRouter(prefix="/api/v1", tags=["Messages"])


def _can_access_conversation(conv: Conversation, user: User, candidate: Optional[Candidate]) -> bool:
    """Check if user is participant (recruiter or candidate)."""
    if conv.company_user_id == user.id:
        return True
    if candidate and conv.candidate_id == candidate.id:
        return True
    return False


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List conversations for current user (as recruiter or student)."""
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if candidate:
        convs = db.query(Conversation).filter(Conversation.candidate_id == candidate.id).order_by(Conversation.created_at.desc()).all()
    else:
        convs = db.query(Conversation).filter(Conversation.company_user_id == current_user.id).order_by(Conversation.created_at.desc()).all()
    result = []
    for c in convs:
        job_title = None
        if c.job_id:
            job = db.query(Job).filter(Job.id == c.job_id).first()
            job_title = job.title if job else None
        candidate_name = c.candidate.name if c.candidate else None
        last_msg = c.messages[-1] if c.messages else None
        last_preview = (last_msg.body[:80] + "…") if last_msg and len(last_msg.body) > 80 else (last_msg.body if last_msg else None)
        result.append(ConversationResponse(
            id=c.id,
            job_id=c.job_id,
            company_user_id=c.company_user_id,
            candidate_id=c.candidate_id,
            created_at=c.created_at,
            job_title=job_title,
            candidate_name=candidate_name,
            last_message_preview=last_preview,
        ))
    return result


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def list_messages(
    conversation_id: int,
    limit: int = Query(100, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get paginated messages for a conversation."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not _can_access_conversation(conv, current_user, candidate):
        raise HTTPException(status_code=403, detail="Not a participant")
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return messages


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    body: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a conversation. Student: pass job_id (and optional initial_message). Recruiter: pass candidate_id (and optional initial_message)."""
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if candidate:
        if body.candidate_id:
            raise HTTPException(status_code=400, detail="Students cannot set candidate_id")
        if not body.job_id:
            raise HTTPException(status_code=400, detail="Students must provide job_id")
        job = db.query(Job).filter(Job.id == body.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        company_user_id = job.created_by
        existing = (
            db.query(Conversation)
            .filter(Conversation.job_id == body.job_id, Conversation.candidate_id == candidate.id)
            .first()
        )
        if existing:
            if body.initial_message:
                msg = Message(conversation_id=existing.id, sender_id=current_user.id, body=body.initial_message)
                db.add(msg)
                db.commit()
            return ConversationResponse(
                id=existing.id,
                job_id=existing.job_id,
                company_user_id=existing.company_user_id,
                candidate_id=existing.candidate_id,
                created_at=existing.created_at,
                job_title=job.title,
                candidate_name=candidate.name,
                last_message_preview=body.initial_message[:80] + "…" if body.initial_message and len(body.initial_message) > 80 else body.initial_message,
            )
        conv = Conversation(job_id=body.job_id, company_user_id=company_user_id, candidate_id=candidate.id)
        db.add(conv)
        db.commit()
        db.refresh(conv)
        if body.initial_message:
            msg = Message(conversation_id=conv.id, sender_id=current_user.id, body=body.initial_message)
            db.add(msg)
            db.commit()
        return ConversationResponse(
            id=conv.id,
            job_id=conv.job_id,
            company_user_id=conv.company_user_id,
            candidate_id=conv.candidate_id,
            created_at=conv.created_at,
            job_title=job.title,
            candidate_name=candidate.name,
            last_message_preview=body.initial_message[:80] + "…" if body.initial_message and len(body.initial_message) > 80 else body.initial_message if body.initial_message else None,
        )
    else:
        if body.job_id and not body.candidate_id:
            raise HTTPException(status_code=400, detail="Recruiters must provide candidate_id to start a conversation")
        if not body.candidate_id:
            raise HTTPException(status_code=400, detail="Provide candidate_id")
        cand = db.query(Candidate).filter(Candidate.id == body.candidate_id).first()
        if not cand:
            raise HTTPException(status_code=404, detail="Candidate not found")
        existing = (
            db.query(Conversation)
            .filter(Conversation.company_user_id == current_user.id, Conversation.candidate_id == body.candidate_id)
            .filter(Conversation.job_id == body.job_id if body.job_id is not None else Conversation.job_id.is_(None))
            .first()
        )
        if existing:
            if body.initial_message:
                msg = Message(conversation_id=existing.id, sender_id=current_user.id, body=body.initial_message)
                db.add(msg)
                db.commit()
            job = db.query(Job).filter(Job.id == existing.job_id).first() if existing.job_id else None
            return ConversationResponse(
                id=existing.id,
                job_id=existing.job_id,
                company_user_id=existing.company_user_id,
                candidate_id=existing.candidate_id,
                created_at=existing.created_at,
                job_title=job.title if job else None,
                candidate_name=existing.candidate.name if existing.candidate else None,
                last_message_preview=body.initial_message[:80] + "…" if body.initial_message and len(body.initial_message) > 80 else body.initial_message if body.initial_message else None,
            )
        conv = Conversation(job_id=body.job_id, company_user_id=current_user.id, candidate_id=body.candidate_id)
        db.add(conv)
        db.commit()
        db.refresh(conv)
        if body.initial_message:
            msg = Message(conversation_id=conv.id, sender_id=current_user.id, body=body.initial_message)
            db.add(msg)
            db.commit()
        job = db.query(Job).filter(Job.id == conv.job_id).first() if conv.job_id else None
        return ConversationResponse(
            id=conv.id,
            job_id=conv.job_id,
            company_user_id=conv.company_user_id,
            candidate_id=conv.candidate_id,
            created_at=conv.created_at,
            job_title=job.title if job else None,
            candidate_name=cand.name,
            last_message_preview=body.initial_message[:80] + "…" if body.initial_message and len(body.initial_message) > 80 else body.initial_message if body.initial_message else None,
        )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    conversation_id: int,
    body: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Send a message in a conversation."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not _can_access_conversation(conv, current_user, candidate):
        raise HTTPException(status_code=403, detail="Not a participant")
    msg = Message(conversation_id=conversation_id, sender_id=current_user.id, body=body.body)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg
