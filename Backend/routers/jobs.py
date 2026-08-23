"""Job management router"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from database.postgres import get_db
from database.mongodb import get_mongo_db
from database.models import User, Job, Application
from schemas.api import JobCreate, JobUpdate, JobResponse
from auth.dependencies import get_current_active_user
from config import USE_QDRANT_MATCHING, QDRANT_COLLECTION_JOBS
from vector.embedder import get_embedder
from vector.qdrant_client import ensure_collections, upsert_points

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])


def _build_job_vector_text_and_payload(job: Job) -> tuple[str, dict]:
    """Construct the text representation and payload for a job for vector search."""
    requirements = job.requirements_json or {}
    required_skills = requirements.get("required_skills") or []
    job_description = requirements.get("job_description") or ""

    text_parts = [
        job.title or "",
        job.company or "",
        job.description or "",
        job_description or "",
        ", ".join(required_skills),
    ]
    full_text = " ".join(part for part in text_parts if part)

    payload = {
        "job_id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "salary": job.salary,
        "required_skills": required_skills,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }
    return full_text, payload


def _index_job_in_qdrant(job: Job) -> None:
    """Index or update a single job in the Qdrant collection."""
    if not USE_QDRANT_MATCHING:
        return

    try:
        embedder = get_embedder()
        text, payload = _build_job_vector_text_and_payload(job)
        if not text:
            return

        vector = embedder.embed_text(text)
        ensure_collections(embedder.dimension)
        upsert_points(
            collection=QDRANT_COLLECTION_JOBS,
            ids=[str(job.id)],
            vectors=[vector],
            payloads=[payload],
        )
    except Exception as e:
        # Indexing failures should not break core job flows
        print(f"[QDRANT] Failed to index job {job.id}: {e}")


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    skip: int = 0,
    limit: int = 100,
    company: Optional[str] = None,
    title: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all jobs with optional filters"""
    query = db.query(Job)
    
    if company:
        query = query.filter(Job.company.ilike(f"%{company}%"))
    if title:
        query = query.filter(Job.title.ilike(f"%{title}%"))
    
    jobs = query.offset(skip).limit(limit).all()
    
    # Add application count for each job
    result = []
    for job in jobs:
        application_count = db.query(Application).filter(Application.job_id == job.id).count()
        job_dict = {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "description": job.description,
            "location": job.location,
            "salary": job.salary,
            "requirements_json": job.requirements_json,
            "created_by": job.created_by,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "application_count": application_count
        }
        result.append(JobResponse(**job_dict))
    
    return result


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new job posting"""
    # Only recruiters and admins can create jobs
    if current_user.role.value not in ["recruiter", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only recruiters and admins can create jobs"
        )
    
    # Store full job description in MongoDB
    mongo_db = get_mongo_db()
    job_desc_id = str(uuid.uuid4())
    job_desc_doc = {
        "job_desc_id": job_desc_id,
        "description": job_data.description,
        "requirements": job_data.requirements_json,
        "created_by": current_user.id
    }
    mongo_db.job_descriptions.insert_one(job_desc_doc)
    
    # Create job in PostgreSQL
    new_job = Job(
        title=job_data.title,
        company=job_data.company,
        description=job_data.description,
        location=job_data.location,
        salary=job_data.salary,
        requirements_json=job_data.requirements_json,
        created_by=current_user.id
    )
    
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Best-effort index in Qdrant for semantic search
    _index_job_in_qdrant(new_job)

    return new_job


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get job details"""
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Add application count
    application_count = db.query(Application).filter(Application.job_id == job_id).count()
    job_dict = {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "description": job.description,
        "location": job.location,
        "salary": job.salary,
        "requirements_json": job.requirements_json,
        "created_by": job.created_by,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "application_count": application_count
    }
    
    return JobResponse(**job_dict)


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    job_data: JobUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update job posting"""
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Only creator or admin can update
    if job.created_by != current_user.id and current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this job"
        )
    
    # Update fields
    update_data = job_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)
    
    # Update MongoDB if description changed
    if job_data.description or job_data.requirements_json:
        mongo_db = get_mongo_db()
        job_desc_doc = {
            "job_desc_id": str(uuid.uuid4()),
            "description": job.description,
            "requirements": job.requirements_json,
            "updated_by": current_user.id
        }
        mongo_db.job_descriptions.insert_one(job_desc_doc)
    
    db.commit()
    db.refresh(job)

    # Best-effort re-index in Qdrant when job changes
    _index_job_in_qdrant(job)

    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete job posting"""
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Only creator or admin can delete
    if job.created_by != current_user.id and current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this job"
        )
    
    db.delete(job)
    db.commit()
    
    return None
