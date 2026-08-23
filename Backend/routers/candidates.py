"""Candidate management router"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from database.postgres import get_db
from database.mongodb import get_mongo_db
from database.models import User, Candidate, Application, Evaluation, Job
from schemas.api import (
    CandidateResponse, CandidateCreate, CandidateUpdate,
    ApplicationResponse, EvaluationResponse
)
from schemas.domain import JobRequirement, ResumeData, CandidateEvaluationRequest, CandidateEvaluationResponse, ATSResult, RejectionFeedback
from services.resume_parser import ResumeParser
from services.ats_engine import ATSEngine
from services.feedback_generator import FeedbackGenerator
from auth.dependencies import get_current_active_user

router = APIRouter(prefix="/api/v1/candidates", tags=["Candidates"])

# Initialize engines
resume_parser = ResumeParser()
ats_engine = ATSEngine()
feedback_generator = FeedbackGenerator()


@router.post("/evaluate", response_model=CandidateEvaluationResponse)
async def evaluate_candidate(
    request: CandidateEvaluationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Evaluate a candidate against job requirements"""
    # Only recruiters and admins can evaluate
    if current_user.role.value not in ["recruiter", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only recruiters and admins can evaluate candidates"
        )
    
    import uuid as uuid_module
    
    try:
        # Parse resume
        if request.resume_file_path:
            parsed_resume = resume_parser.parse(file_path=request.resume_file_path)
        elif request.resume_text:
            parsed_resume = resume_parser.parse(resume_text=request.resume_text)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either resume_file_path or resume_text must be provided"
            )
        
        resume_data = ResumeData(**parsed_resume)
        
        # Score resume using ATS
        ats_result_dict = ats_engine.score_resume(resume_data, request.job_requirement)
        
        # Generate candidate ID
        candidate_id = str(uuid_module.uuid4())
        
        # Create ATSResult
        ats_result = ATSResult(
            candidate_id=candidate_id,
            ats_score=ats_result_dict['ats_score'],
            passed=ats_result_dict['passed'],
            skill_match_score=ats_result_dict['skill_match_score'],
            education_score=ats_result_dict['education_score'],
            experience_score=ats_result_dict['experience_score'],
            keyword_match_score=ats_result_dict['keyword_match_score'],
            format_score=ats_result_dict['format_score'],
            matched_skills=ats_result_dict['matched_skills'],
            missing_skills=ats_result_dict['missing_skills'],
            recommendations=[]
        )
        
        # Generate feedback if rejected
        feedback = None
        message = ""
        
        if not ats_result.passed:
            feedback_dict = feedback_generator.generate_feedback(
                ats_result_dict, parsed_resume, request.job_requirement
            )
            
            if feedback_dict:
                feedback = RejectionFeedback(
                    candidate_id=candidate_id,
                    ats_score=ats_result.ats_score,
                    minimum_required_score=request.job_requirement.minimum_ats_score,
                    rejection_reasons=feedback_dict['rejection_reasons'],
                    missing_critical_skills=feedback_dict['missing_critical_skills'],
                    resume_strengths=feedback_dict['resume_strengths'],
                    resume_weaknesses=feedback_dict['resume_weaknesses'],
                    improvement_recommendations=feedback_dict['improvement_recommendations'],
                    format_issues=feedback_dict['format_issues'],
                    mistake_highlights=feedback_dict['mistake_highlights']
                )
                
                message = (
                    f"Candidate rejected. ATS Score: {ats_result.ats_score:.2f}% "
                    f"(Minimum Required: {request.job_requirement.minimum_ats_score}%). "
                    f"Feedback provided."
                )
        else:
            message = (
                f"Candidate PASSED! ATS Score: {ats_result.ats_score:.2f}% "
                f"(Minimum Required: {request.job_requirement.minimum_ats_score}%)."
            )
        
        return CandidateEvaluationResponse(
            candidate_id=candidate_id,
            ats_result=ats_result,
            feedback=feedback,
            message=message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error evaluating candidate: {str(e)}"
        )


@router.get("/me", response_model=CandidateResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get the current logged in candidate's profile"""
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    
    if not candidate:
        # Create it with empty fields
        candidate = Candidate(
            user_id=current_user.id,
            name=current_user.email.split("@")[0],
            email=current_user.email,
            phone=None,
            skills_json=[],
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        
    return candidate


@router.put("/me", response_model=CandidateResponse)
async def update_my_profile(
    profile_update: CandidateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update the current logged in candidate's profile"""
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    
    if not candidate:
        candidate = Candidate(
            user_id=current_user.id,
            name=current_user.email.split("@")[0],
            email=current_user.email,
            phone=None,
            skills_json=[],
        )
        db.add(candidate)
        
    if profile_update.name is not None:
        candidate.name = profile_update.name
    if profile_update.phone is not None:
        candidate.phone = profile_update.phone
    if profile_update.skills is not None:
        candidate.skills_json = profile_update.skills
    if profile_update.linkedin_url is not None:
        candidate.linkedin_url = profile_update.linkedin_url
    if profile_update.location is not None:
        candidate.location = profile_update.location
    if profile_update.education is not None:
        candidate.education = profile_update.education
    if profile_update.college is not None:
        candidate.college = profile_update.college
    if profile_update.branch is not None:
        candidate.branch = profile_update.branch
    if profile_update.graduation_year is not None:
        candidate.graduation_year = profile_update.graduation_year
    if profile_update.cgpa is not None:
        candidate.cgpa = profile_update.cgpa
    if profile_update.bio is not None:
        candidate.bio = profile_update.bio
    if profile_update.experience is not None:
        candidate.experience = profile_update.experience
        
    db.commit()
    db.refresh(candidate)
    
    return candidate


@router.get("", response_model=List[CandidateResponse])
async def list_candidates(
    skip: int = 0,
    limit: int = 100,
    passed: Optional[bool] = None,
    job_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all candidates and automatically create evaluations for applications.
    Optional: passed=true to only return candidates with at least one passing evaluation;
    job_id to scope to applications for that job."""
    # Only recruiters and admins can list candidates
    if current_user.role.value not in ["recruiter", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only recruiters and admins can list candidates"
        )
    
    query = db.query(Candidate)
    
    if passed is True or job_id is not None:
        # Subquery: candidate_ids that have an application (optionally for job_id) with a passing evaluation
        subq = (
            db.query(Application.candidate_id)
            .join(Evaluation, Evaluation.application_id == Application.id)
        )
        if job_id is not None:
            subq = subq.filter(Application.job_id == job_id)
        if passed is True:
            subq = subq.filter(Evaluation.passed == True)
        subq = subq.distinct()
        candidate_ids = [row[0] for row in subq.all()]
        if not candidate_ids:
            return []
        query = query.filter(Candidate.id.in_(candidate_ids))
    
    candidates = query.offset(skip).limit(limit).all()
    
    # Automatically create evaluations for all applications that don't have evaluations
    from routers.ats import create_evaluation_for_application
    
    for candidate in candidates:
        if candidate.resume_id:
            applications = db.query(Application).filter(
                Application.candidate_id == candidate.id
            ).all()
            for application in applications:
                existing_eval = db.query(Evaluation).filter(
                    Evaluation.application_id == application.id
                ).first()
                if not existing_eval:
                    try:
                        create_evaluation_for_application(application, db)
                    except Exception:
                        pass
    
    return candidates


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get candidate details"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Check access
    if candidate.user_id != current_user.id and current_user.role.value not in ["recruiter", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this candidate"
        )
    
    return candidate


@router.get("/{candidate_id}/evaluations", response_model=List[EvaluationResponse])
async def get_candidate_evaluations(
    candidate_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all evaluations for a candidate"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Check access
    if candidate.user_id != current_user.id and current_user.role.value not in ["recruiter", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this candidate's evaluations"
        )
    
    # Get all applications for candidate
    applications = db.query(Application).filter(Application.candidate_id == candidate_id).all()
    application_ids = [app.id for app in applications]
    
    # Get all evaluations
    evaluations = db.query(Evaluation).filter(Evaluation.application_id.in_(application_ids)).all()
    
    return evaluations
