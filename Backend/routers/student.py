"""Student engine router"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database.postgres import get_db
from database.models import User, Job, Candidate, Application, Evaluation, ApplicationStatus
from schemas.api import (
    JobSearchRequest, JobSearchResponse,
    SkillGapRequest, SkillGapResponse,
    ResumeFeedbackRequest,
    RejectionInterpretRequest, RejectionInterpretResponse,
    StudentApplicationResponse
)
from services.student_engine import CampusConnectStudentEngine
from auth.dependencies import get_current_active_user
from config import USE_QDRANT_MATCHING, QDRANT_COLLECTION_JOBS, USE_LLM_FEEDBACK
from vector.embedder import get_embedder
from vector.qdrant_client import search as qdrant_search, ensure_collections
from qdrant_client.http import models as qm
from llm.student_feedback import (
    generate_resume_feedback_llm,
    interpret_rejection_llm,
)

router = APIRouter(prefix="/api/v1/student", tags=["Student"])

# Initialize student engine
student_engine = CampusConnectStudentEngine()


@router.post("/jobs/search", response_model=List[JobSearchResponse])
async def search_jobs(
    request: JobSearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Natural language job search"""
    try:
        # If Qdrant matching is disabled, fall back to existing in-memory search
        if not USE_QDRANT_MATCHING:
            jobs = db.query(Job).all()

            jobs_list = []
            for job in jobs:
                requirements = job.requirements_json or {}
                jobs_list.append({
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "salary": job.salary,
                    "description": job.description or "",
                    "requirements": requirements.get("job_description", "") or
                                  f"{', '.join(requirements.get('required_skills', []))}"
                })

            results = student_engine.search_jobs(
                student_query=request.query,
                jobs=jobs_list,
                student_skills=request.student_skills,
                top_k=request.top_k
            )
        else:
            # Qdrant-backed semantic search
            embedder = get_embedder()
            ensure_collections(embedder.dimension)
            query_vec = embedder.embed_text(request.query)

            scored_points = qdrant_search(
                collection=QDRANT_COLLECTION_JOBS,
                query_vector=query_vec,
                top_k=request.top_k,
                filter_=None,
            )

            if not scored_points:
                return []

            # Fetch corresponding jobs from DB
            job_ids = [int(point.payload.get("job_id")) for point in scored_points if point.payload.get("job_id") is not None]
            if not job_ids:
                return []

            jobs = db.query(Job).filter(Job.id.in_(job_ids)).all()
            jobs_by_id = {job.id: job for job in jobs}

            # Rebuild job dicts in the order of Qdrant scores
            jobs_list = []
            for point in scored_points:
                job_id = point.payload.get("job_id")
                if job_id is None:
                    continue
                job = jobs_by_id.get(int(job_id))
                if not job:
                    continue

                requirements = job.requirements_json or {}
                jobs_list.append({
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "salary": job.salary,
                    "description": job.description or "",
                    "requirements": requirements.get("job_description", "") or
                                  f"{', '.join(requirements.get('required_skills', []))}"
                })

            if not jobs_list:
                return []

            # Reuse existing job matching logic to determine application status
            results = student_engine.search_jobs(
                student_query=request.query,
                jobs=jobs_list,
                student_skills=request.student_skills,
                top_k=request.top_k
            )
        
        # Convert to response format
        response_list = []
        for result in results:
            response_list.append(JobSearchResponse(
                job_id=result.get("job_id", 0),
                title=result.get("title", ""),
                company=result.get("company", ""),
                location=result.get("location"),
                salary=result.get("salary"),
                match_score=result.get("match_score", 0.0),
                application_status=result.get("application_status", "Recommended"),
                missing_skills=result.get("missing_skills", []),
                matched_skills=result.get("matched_skills", []),
                message=result.get("message", ""),
                required_skills=result.get("required_skills", [])
            ))
        
        return response_list
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching jobs: {str(e)}"
        )


@router.post("/skill-gap/analyze", response_model=SkillGapResponse)
async def analyze_skill_gap(
    request: SkillGapRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Analyze skill gap between student and job requirements"""
    try:
        result = student_engine.analyze_skill_gap(
            student_skills=request.student_skills,
            job_skills=request.job_skills,
            job_role=request.job_role
        )
        
        return SkillGapResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing skill gap: {str(e)}"
        )


@router.post("/resume/feedback")
async def get_resume_feedback(
    request: ResumeFeedbackRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get resume feedback for ATS optimization"""
    try:
        # Prefer LLM-based feedback when enabled and configured
        if USE_LLM_FEEDBACK:
            llm_result = generate_resume_feedback_llm(
                resume_text=request.resume_text,
                job_description=request.job_description,
                job_requirements=request.job_requirements,
                skill_gap_output=request.skill_gap_output,
            )
            if llm_result:
                return llm_result

        # Fallback to deterministic engine
        return student_engine.get_resume_feedback(
            resume_text=request.resume_text,
            job_description=request.job_description,
            job_requirements=request.job_requirements,
            skill_gap_output=request.skill_gap_output,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating resume feedback: {str(e)}"
        )


@router.post("/rejection/interpret", response_model=RejectionInterpretResponse)
async def interpret_rejection(
    request: RejectionInterpretRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Interpret rejection feedback"""
    try:
        # Prefer LLM-based interpretation when enabled
        if USE_LLM_FEEDBACK:
            llm_result = interpret_rejection_llm(
                rejection_feedback=request.rejection_feedback,
                job_title=request.job_title,
                student_skills=request.student_skills,
            )
            if llm_result:
                return RejectionInterpretResponse(**llm_result)

        # Fallback to deterministic interpreter
        result = student_engine.interpret_rejection(
            rejection_feedback=request.rejection_feedback,
            job_title=request.job_title,
            student_skills=request.student_skills,
        )
        return RejectionInterpretResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interpreting rejection: {str(e)}"
        )


@router.get("/applications", response_model=List[StudentApplicationResponse])
async def get_my_applications(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all applications for the current student"""
    try:
        # Get candidate profile for the user
        candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
        
        if not candidate:
            return []
        
        # Get all applications for this candidate
        applications = db.query(Application).filter(
            Application.candidate_id == candidate.id
        ).order_by(Application.applied_at.desc()).all()
        
        result = []
        for app in applications:
            job = db.query(Job).filter(Job.id == app.job_id).first()
            
            # Get evaluation if exists
            evaluation = db.query(Evaluation).filter(
                Evaluation.application_id == app.id
            ).first()
            
            result.append(StudentApplicationResponse(
                id=app.id,
                job_id=app.job_id,
                job_title=job.title if job else "Unknown",
                company=job.company if job else "Unknown",
                status=app.status.value,
                applied_at=app.applied_at.isoformat() if app.applied_at else None,
                ats_score=evaluation.ats_score if evaluation else None,
                passed=evaluation.passed if evaluation else None,
            ))
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching applications: {str(e)}"
        )


@router.post("/jobs/{job_id}/apply", response_model=StudentApplicationResponse)
async def apply_for_job(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Apply for a specific job"""
    try:
        candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
        if not candidate:
            raise HTTPException(status_code=400, detail="Candidate profile not found")
        
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
        existing_app = db.query(Application).filter(
            Application.candidate_id == candidate.id,
            Application.job_id == job_id
        ).first()
        
        if existing_app:
            raise HTTPException(status_code=400, detail="Application already exists")
            
        new_app = Application(
            job_id=job_id,
            candidate_id=candidate.id,
            status=ApplicationStatus.PENDING
        )
        db.add(new_app)
        db.commit()
        db.refresh(new_app)
        
        return StudentApplicationResponse(
            id=new_app.id,
            job_id=job.id,
            job_title=job.title,
            company=job.company,
            status=new_app.status.value,
            applied_at=new_app.applied_at.isoformat() if new_app.applied_at else None,
            ats_score=None,
            passed=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error applying for job: {str(e)}"
        )
