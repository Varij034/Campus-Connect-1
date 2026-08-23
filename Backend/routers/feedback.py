"""Feedback generator router"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from database.postgres import get_db
from database.mongodb import get_mongo_db
from database.models import User, Evaluation
from schemas.api import FeedbackResponse
from schemas.domain import JobRequirement, ResumeData
from services.feedback_generator import FeedbackGenerator
from services.ats_engine import ATSEngine
from services.resume_parser import ResumeParser
from auth.dependencies import get_current_active_user

router = APIRouter(prefix="/api/v1/feedback", tags=["Feedback"])

# Initialize engines
feedback_generator = FeedbackGenerator()
ats_engine = ATSEngine()
resume_parser = ResumeParser()


@router.post("/generate", response_model=FeedbackResponse)
async def generate_feedback(
    evaluation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate feedback for rejected candidate"""
    # Get evaluation
    evaluation = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
    
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found"
        )
    
    # Check if candidate passed (no feedback needed)
    if evaluation.passed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback is only generated for rejected candidates"
        )
    
    # Get detailed ATS result from MongoDB
    mongo_db = get_mongo_db()
    ats_result_doc = mongo_db.ats_results.find_one({"evaluation_id": evaluation_id})
    
    if not ats_result_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ATS result not found"
        )
    
    ats_result = ats_result_doc.get("ats_result", {})
    resume_data_dict = ats_result_doc.get("resume_data", {})
    job_requirement_dict = ats_result_doc.get("job_requirement", {})
    
    # Generate feedback
    try:
        resume_data = ResumeData(**resume_data_dict)
        job_requirement = JobRequirement(**job_requirement_dict)
        
        feedback_dict = feedback_generator.generate_feedback(
            ats_result, resume_data_dict, job_requirement
        )
        
        if not feedback_dict:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate feedback"
            )
        
        # Store feedback in MongoDB
        feedback_id = str(uuid.uuid4())
        feedback_doc = {
            "feedback_id": feedback_id,
            "evaluation_id": evaluation_id,
            "feedback": feedback_dict,
            "created_at": str(uuid.uuid4())  # Use timestamp in production
        }
        mongo_db.feedback_details.insert_one(feedback_doc)
        
        # Update evaluation with feedback_id
        evaluation.feedback_id = feedback_id
        db.commit()
        
        return FeedbackResponse(
            feedback_id=feedback_id,
            evaluation_id=evaluation_id,
            rejection_reasons=feedback_dict.get("rejection_reasons", []),
            missing_critical_skills=feedback_dict.get("missing_critical_skills", []),
            resume_strengths=feedback_dict.get("resume_strengths", []),
            resume_weaknesses=feedback_dict.get("resume_weaknesses", []),
            improvement_recommendations=feedback_dict.get("improvement_recommendations", []),
            format_issues=feedback_dict.get("format_issues", []),
            mistake_highlights=feedback_dict.get("mistake_highlights", [])
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating feedback: {str(e)}"
        )


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    feedback_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get feedback details"""
    mongo_db = get_mongo_db()
    feedback_doc = mongo_db.feedback_details.find_one({"feedback_id": feedback_id})
    
    if not feedback_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    evaluation_id = feedback_doc.get("evaluation_id")
    evaluation = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
    
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found"
        )
    
    # Check access
    application = evaluation.application
    if (application.candidate.user_id != current_user.id and 
        application.job.created_by != current_user.id and 
        current_user.role.value != "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this feedback"
        )
    
    feedback_dict = feedback_doc.get("feedback", {})
    
    return FeedbackResponse(
        feedback_id=feedback_id,
        evaluation_id=evaluation_id,
        rejection_reasons=feedback_dict.get("rejection_reasons", []),
        missing_critical_skills=feedback_dict.get("missing_critical_skills", []),
        resume_strengths=feedback_dict.get("resume_strengths", []),
        resume_weaknesses=feedback_dict.get("resume_weaknesses", []),
        improvement_recommendations=feedback_dict.get("improvement_recommendations", []),
        format_issues=feedback_dict.get("format_issues", []),
        mistake_highlights=feedback_dict.get("mistake_highlights", [])
    )


@router.get("/candidate/{candidate_id}")
async def get_candidate_feedback(
    candidate_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all feedback for a candidate"""
    from database.models import Candidate, Application
    
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Check access
    if candidate.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this candidate's feedback"
        )
    
    # Get all applications for candidate
    applications = db.query(Application).filter(Application.candidate_id == candidate_id).all()
    evaluation_ids = []
    
    for app in applications:
        evaluations = db.query(Evaluation).filter(Evaluation.application_id == app.id).all()
        evaluation_ids.extend([e.id for e in evaluations])
    
    # Get all feedback from MongoDB
    mongo_db = get_mongo_db()
    feedback_docs = list(mongo_db.feedback_details.find({"evaluation_id": {"$in": evaluation_ids}}))
    
    feedbacks = []
    for doc in feedback_docs:
        feedback_dict = doc.get("feedback", {})
        feedbacks.append({
            "feedback_id": doc.get("feedback_id"),
            "evaluation_id": doc.get("evaluation_id"),
            "rejection_reasons": feedback_dict.get("rejection_reasons", []),
            "missing_critical_skills": feedback_dict.get("missing_critical_skills", []),
            "improvement_recommendations": feedback_dict.get("improvement_recommendations", [])
        })
    
    return {"feedbacks": feedbacks, "total": len(feedbacks)}
