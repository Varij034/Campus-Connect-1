"""HR-specific endpoints (stats, etc.)"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.postgres import get_db
from database.models import User, Job, Application, Evaluation
from auth.dependencies import get_current_active_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/hr", tags=["HR"])

class HRProfile(BaseModel):
    name: str
    company: str
    position: str
    email: str
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    
class HRProfileUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None

# Mock in-memory storage for HR profiles
_hr_profiles = {}


@router.get("/stats")
async def get_hr_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Return stats for the logged-in recruiter: jobs, applications, shortlisted (passed), avg score."""
    if current_user.role.value not in ["recruiter", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only recruiters and admins can access HR stats",
        )
    # Jobs created by this user
    job_ids = [row[0] for row in db.query(Job.id).filter(Job.created_by == current_user.id).all()]
    if not job_ids:
        return {
            "total_jobs": 0,
            "total_applications": 0,
            "shortlisted": 0,
            "avg_ats_score": 0.0,
        }
    total_jobs = len(job_ids)
    applications = db.query(Application).filter(Application.job_id.in_(job_ids)).all()
    application_ids = [a.id for a in applications]
    total_applications = len(application_ids)
    if not application_ids:
        return {
            "total_jobs": total_jobs,
            "total_applications": 0,
            "shortlisted": 0,
            "avg_ats_score": 0.0,
        }
    shortlisted = (
        db.query(Application.id)
        .filter(Application.id.in_(application_ids))
        .join(Evaluation, Evaluation.application_id == Application.id)
        .filter(Evaluation.passed == True)
        .distinct()
        .count()
    )
    # For avg score we need one evaluation per application (e.g. latest or any)
    evals = db.query(func.avg(Evaluation.ats_score)).filter(
        Evaluation.application_id.in_(application_ids)
    ).scalar()
    avg_ats_score = round(float(evals or 0), 2)
    return {
        "total_jobs": total_jobs,
        "total_applications": total_applications,
        "shortlisted": shortlisted,
        "avg_ats_score": avg_ats_score,
    }


@router.get("/profile", response_model=HRProfile)
async def get_hr_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get HR/Company profile (Mock)"""
    if current_user.role.value not in ["recruiter", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if current_user.id not in _hr_profiles:
        # Return mock data
        _hr_profiles[current_user.id] = {
            "name": current_user.email.split("@")[0].title(),
            "company": "Tech Corp (Mock)",
            "position": "Technical Recruiter",
            "email": current_user.email,
            "phone": "555-0123",
            "linkedin_url": "https://linkedin.com/in/mock-hr"
        }
        
    return HRProfile(**_hr_profiles[current_user.id])


@router.put("/profile", response_model=HRProfile)
async def update_hr_profile(
    profile_update: HRProfileUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update HR/Company profile (Mock)"""
    if current_user.role.value not in ["recruiter", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if current_user.id not in _hr_profiles:
        _hr_profiles[current_user.id] = {
            "name": current_user.email.split("@")[0].title(),
            "company": "Tech Corp (Mock)",
            "position": "Technical Recruiter",
            "email": current_user.email,
            "phone": "555-0123",
            "linkedin_url": "https://linkedin.com/in/mock-hr"
        }
        
    profile = _hr_profiles[current_user.id]
    
    update_data = profile_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        profile[key] = value
        
    _hr_profiles[current_user.id] = profile
    return HRProfile(**profile)
