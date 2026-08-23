"""ATS engine router"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from database.postgres import get_db
from database.mongodb import get_mongo_db
from database.models import User, Job, Application, Evaluation, Candidate, ApplicationStatus
from schemas.api import ATSScoreRequest, ATSScoreResponse, EvaluationResponse
from schemas.domain import JobRequirement, ResumeData
from pydantic import BaseModel
from services.ats_engine import ATSEngine
from services.resume_parser import ResumeParser
from auth.dependencies import get_current_active_user

router = APIRouter(prefix="/api/v1/ats", tags=["ATS"])

# Initialize engines
ats_engine = ATSEngine()
resume_parser = ResumeParser()


@router.post("/score", response_model=ATSScoreResponse)
async def score_resume(
    request: ATSScoreRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Score resume against job requirements"""
    try:
        # Get resume data
        resume_data = None
        if request.resume_id:
            mongo_db = get_mongo_db()
            # Try to find by resume_id field first (for API-uploaded resumes)
            resume_doc = mongo_db.resumes.find_one({"resume_id": request.resume_id})
            
            # If not found, try to find by _id (for seeded resumes)
            if not resume_doc:
                try:
                    from bson import ObjectId
                    resume_doc = mongo_db.resumes.find_one({"_id": ObjectId(request.resume_id)})
                except:
                    pass
            
            if not resume_doc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Resume not found"
                )
            parsed_data = resume_doc.get("parsed_data", {})
            resume_data = ResumeData(**parsed_data)
        elif request.resume_text:
            parsed_data = resume_parser.parse(resume_text=request.resume_text)
            resume_data = ResumeData(**parsed_data)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either resume_id or resume_text must be provided"
            )
        
        # Parse job requirement
        job_requirement = JobRequirement(**request.job_requirement)
        
        # Score resume
        ats_result = ats_engine.score_resume(resume_data, job_requirement)
        
        # Store detailed result in MongoDB
        mongo_db = get_mongo_db()
        result_id = str(uuid.uuid4())
        result_doc = {
            "result_id": result_id,
            "user_id": current_user.id,
            "ats_result": ats_result,
            "resume_data": resume_data.dict(),
            "job_requirement": job_requirement.dict()
        }
        mongo_db.ats_results.insert_one(result_doc)
        
        return ATSScoreResponse(
            evaluation_id=0,  # Will be set if linked to application
            ats_score=ats_result["ats_score"],
            passed=ats_result["passed"],
            skill_match_score=ats_result["skill_match_score"],
            education_score=ats_result["education_score"],
            experience_score=ats_result["experience_score"],
            keyword_match_score=ats_result["keyword_match_score"],
            format_score=ats_result["format_score"],
            matched_skills=ats_result["matched_skills"],
            missing_skills=ats_result["missing_skills"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error scoring resume: {str(e)}"
        )


@router.get("/evaluation/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(
    evaluation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get evaluation details"""
    evaluation = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
    
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found"
        )
    
    # Check access (user must be related to the application or be admin)
    application = evaluation.application
    if (application.candidate.user_id != current_user.id and 
        application.job.created_by != current_user.id and 
        current_user.role.value != "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this evaluation"
        )
    
    return evaluation


@router.post("/batch-score")
async def batch_score(
    requests: List[ATSScoreRequest],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Score multiple resumes"""
    results = []
    for request in requests:
        try:
            result = await score_resume(request, current_user, db)
            results.append(result.dict())
        except Exception as e:
            results.append({"error": str(e)})
    
    return {"results": results, "total": len(results)}


def create_evaluation_for_application(application: Application, db: Session) -> Optional[Evaluation]:
    """Helper function to create an evaluation for an application"""
    try:
        # Check if evaluation already exists
        existing_evaluation = db.query(Evaluation).filter(
            Evaluation.application_id == application.id
        ).first()
        if existing_evaluation:
            return existing_evaluation
        
        candidate = application.candidate
        job = application.job
        
        # Check if candidate has a resume
        if not candidate.resume_id:
            return None
        
        # Get resume data - handle both resume_id field and _id (ObjectId) cases
        mongo_db = get_mongo_db()
        
        # First, try to find by resume_id field (for API-uploaded resumes)
        resume_doc = mongo_db.resumes.find_one({"resume_id": candidate.resume_id})
        
        # If not found, try to find by _id (for seeded resumes where resume_id is the MongoDB _id)
        if not resume_doc:
            try:
                from bson import ObjectId
                resume_doc = mongo_db.resumes.find_one({"_id": ObjectId(candidate.resume_id)})
            except (ValueError, TypeError):
                pass
        
        # If still not found, try to find by user_id as a fallback
        if not resume_doc:
            resume_doc = mongo_db.resumes.find_one({"user_id": candidate.user_id})
        
        if not resume_doc:
            return None
        
        parsed_data = resume_doc.get("parsed_data", {})
        if not parsed_data:
            return None
        
        resume_data = ResumeData(**parsed_data)
        
        # Get job requirements
        if not job.requirements_json:
            return None
        
        job_requirement = JobRequirement(**job.requirements_json)
        
        # Score resume
        ats_result = ats_engine.score_resume(resume_data, job_requirement)
        
        # Create evaluation
        evaluation = Evaluation(
            application_id=application.id,
            ats_score=ats_result["ats_score"],
            passed=ats_result["passed"],
            skill_match_score=ats_result.get("skill_match_score"),
            education_score=ats_result.get("education_score"),
            experience_score=ats_result.get("experience_score"),
            keyword_match_score=ats_result.get("keyword_match_score"),
            format_score=ats_result.get("format_score"),
            matched_skills_json=ats_result.get("matched_skills", []),
            missing_skills_json=ats_result.get("missing_skills", [])
        )
        
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)
        # Persist ATS result to MongoDB so feedback/generate can use it
        try:
            result_doc = {
                "evaluation_id": evaluation.id,
                "ats_result": ats_result,
                "resume_data": getattr(resume_data, "model_dump", resume_data.dict)(),
                "job_requirement": getattr(job_requirement, "model_dump", job_requirement.dict)(),
            }
            mongo_db.ats_results.insert_one(result_doc)
        except Exception:
            pass  # Do not fail evaluation creation if MongoDB write fails
        if evaluation.passed:
            from routers.badges import try_award_badges_for_passed_evaluation
            try_award_badges_for_passed_evaluation(
                db,
                application.candidate_id,
                ats_result.get("matched_skills") or [],
                ats_result.get("skill_match_score") or 0,
            )
        from routers.notifications import notify_user
        candidate = application.candidate
        if candidate:
            notify_user(candidate.user_id, {"type": "evaluation_ready", "application_id": application.id})
        return evaluation
    except Exception as e:
        db.rollback()
        return None


class CreateEvaluationRequest(BaseModel):
    candidate_id: int
    job_id: int


@router.post("/create-evaluation", response_model=EvaluationResponse)
async def create_evaluation(
    request: CreateEvaluationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create an evaluation for a candidate against a job"""
    # Only recruiters and admins can create evaluations
    if current_user.role.value not in ["recruiter", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only recruiters and admins can create evaluations"
        )
    
    try:
        # Get candidate
        candidate = db.query(Candidate).filter(Candidate.id == request.candidate_id).first()
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        # Get job
        job = db.query(Job).filter(Job.id == request.job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Check if candidate has a resume
        if not candidate.resume_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Candidate does not have a resume uploaded"
            )
        
        # Get or create application
        application = db.query(Application).filter(
            Application.candidate_id == request.candidate_id,
            Application.job_id == request.job_id
        ).first()
        
        if not application:
            application = Application(
                candidate_id=request.candidate_id,
                job_id=request.job_id,
                status=ApplicationStatus.PENDING
            )
            db.add(application)
            db.flush()  # Flush to get the application ID
        
        # Get resume data - handle both resume_id field and _id (ObjectId) cases
        mongo_db = get_mongo_db()
        
        # First, try to find by resume_id field (for API-uploaded resumes)
        resume_doc = mongo_db.resumes.find_one({"resume_id": candidate.resume_id})
        
        # If not found, try to find by _id (for seeded resumes where resume_id is the MongoDB _id)
        if not resume_doc:
            try:
                from bson import ObjectId
                resume_doc = mongo_db.resumes.find_one({"_id": ObjectId(candidate.resume_id)})
            except (ValueError, TypeError):
                # candidate.resume_id is not a valid ObjectId, continue to next attempt
                pass
        
        # If still not found, try to find by user_id as a fallback
        if not resume_doc:
            resume_doc = mongo_db.resumes.find_one({"user_id": candidate.user_id})
        
        if not resume_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resume not found for candidate '{candidate.name}'. The candidate has resume_id '{candidate.resume_id}' but no matching resume document exists in the database."
            )
        
        parsed_data = resume_doc.get("parsed_data", {})
        if not parsed_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resume document found but parsed_data is missing or empty"
            )
        
        resume_data = ResumeData(**parsed_data)
        
        # Get job requirements
        if not job.requirements_json:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job does not have requirements defined"
            )
        
        job_requirement = JobRequirement(**job.requirements_json)
        
        # Score resume
        ats_result = ats_engine.score_resume(resume_data, job_requirement)
        
        # Create evaluation
        evaluation = Evaluation(
            application_id=application.id,
            ats_score=ats_result["ats_score"],
            passed=ats_result["passed"],
            skill_match_score=ats_result.get("skill_match_score"),
            education_score=ats_result.get("education_score"),
            experience_score=ats_result.get("experience_score"),
            keyword_match_score=ats_result.get("keyword_match_score"),
            format_score=ats_result.get("format_score"),
            matched_skills_json=ats_result.get("matched_skills", []),
            missing_skills_json=ats_result.get("missing_skills", [])
        )
        
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)
        # Persist ATS result to MongoDB so feedback/generate can use it
        try:
            result_doc = {
                "evaluation_id": evaluation.id,
                "ats_result": ats_result,
                "resume_data": getattr(resume_data, "model_dump", resume_data.dict)(),
                "job_requirement": getattr(job_requirement, "model_dump", job_requirement.dict)(),
            }
            mongo_db.ats_results.insert_one(result_doc)
        except Exception:
            pass  # Do not fail evaluation creation if MongoDB write fails
        if evaluation.passed:
            from routers.badges import try_award_badges_for_passed_evaluation
            try_award_badges_for_passed_evaluation(
                db,
                candidate.id,
                ats_result.get("matched_skills") or [],
                ats_result.get("skill_match_score") or 0,
            )
        from routers.notifications import notify_user
        notify_user(candidate.user_id, {"type": "evaluation_ready", "application_id": application.id})
        return evaluation
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating evaluation: {str(e)}"
        )
