"""Recruiter productivity LLM endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth.dependencies import get_current_active_user
from config import GROQ_API_KEY
from database.models import User, Job, Candidate
from database.postgres import get_db
from schemas.api import CandidateResponse, JobResponse
from llm.groq_client import get_groq_client


router = APIRouter(prefix="/api/v1/llm/recruiter", tags=["LLM - Recruiter"])


def _require_recruiter_or_admin(user: User) -> None:
    if user.role.value not in ["recruiter", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only recruiters and admins can use these endpoints.",
        )
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GROQ_API_KEY is not configured; LLM recruiter tools are unavailable.",
        )


@router.post("/resume-summary")
async def summarize_resume(
    candidate_id: int,
    job_id: int | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Summarize a candidate's resume into a short recruiter-friendly card.

    Optionally conditioned on a target job.
    """
    _require_recruiter_or_admin(current_user)

    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    if not candidate.resume_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate does not have a resume uploaded.",
        )

    from database.mongodb import get_mongo_db

    mongo_db = get_mongo_db()
    resume_doc = mongo_db.resumes.find_one({"resume_id": candidate.resume_id})
    if not resume_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume document not found for candidate.",
        )

    resume_text = resume_doc.get("raw_text", "")
    job = db.query(Job).filter(Job.id == job_id).first() if job_id else None

    client = get_groq_client()
    system_prompt = (
        "You create very concise recruiter-facing summaries from resumes. "
        "Always return valid JSON only."
    )
    user_prompt = (
        "Summarize the following candidate for a recruiter.\n\n"
        f"Candidate name: {candidate.name}\n"
        f"Email: {candidate.email}\n"
        f"Skills (structured): {candidate.skills_json or []}\n"
    )
    if job:
        user_prompt += (
            f"\nTarget job title: {job.title} at {job.company}\n"
            f"Job description: {job.description or ''}\n"
        )
    user_prompt += (
        "\nResume text:\n"
        f"{resume_text[:8000]}\n\n"
        "Respond with JSON: {\n"
        '  "headline": string,\n'
        '  "summary_bullets": string[],\n'
        '  "risks": string[],\n'
        '  "overall_fit": one of ["strong", "medium", "weak"]\n'
        "}"
    )

    result = client.chat_json(system_prompt=system_prompt, user_prompt=user_prompt)

    return {
        "candidate_id": candidate.id,
        "job_id": job.id if job else None,
        "headline": result.get("headline", ""),
        "summary_bullets": result.get("summary_bullets", []),
        "risks": result.get("risks", []),
        "overall_fit": result.get("overall_fit", "medium"),
    }


@router.post("/outreach")
async def draft_outreach_email(
    candidate_id: int,
    job_id: int,
    tone: str = "friendly",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Generate a personalized outreach email from recruiter to candidate for a given job."""
    _require_recruiter_or_admin(current_user)

    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    client = get_groq_client()
    system_prompt = (
        "You write short, professional outreach emails from recruiters to students. "
        "Always return valid JSON only."
    )
    user_prompt = (
        f"Write a {tone} outreach email from a recruiter to the candidate below "
        "about the job opportunity. Do NOT invent nonsense; keep it factual and concise.\n\n"
        f"Candidate name: {candidate.name}\n"
        f"Candidate skills: {candidate.skills_json or []}\n\n"
        f"Job title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Job description: {job.description or ''}\n\n"
        "Respond with JSON: {\n"
        '  "subject": string,\n'
        '  "body": string\n'
        "}"
    )

    result = client.chat_json(system_prompt=system_prompt, user_prompt=user_prompt)

    return {
        "candidate_id": candidate.id,
        "job_id": job.id,
        "subject": result.get("subject", ""),
        "body": result.get("body", ""),
    }


@router.post("/interview-questions")
async def generate_interview_questions(
    job_id: int,
    count: int = 6,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Generate interview questions for a job, tagged by skill/topic."""
    _require_recruiter_or_admin(current_user)

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    requirements = job.requirements_json or {}
    required_skills = requirements.get("required_skills") or []

    client = get_groq_client()
    system_prompt = (
        "You generate concise technical and behavioral interview questions for campus hiring. "
        "Always return valid JSON only."
    )
    user_prompt = (
        f"Generate {count} interview questions for this job.\n\n"
        f"Job title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Job description: {job.description or ''}\n"
        f"Required skills: {required_skills}\n\n"
        "Respond with JSON: {\n"
        '  "questions": [\n'
        "     {\"question\": string, \"type\": \"technical\"|\"behavioral\", \"skill_tags\": string[]}\n"
        "  ]\n"
        "}"
    )

    result = client.chat_json(system_prompt=system_prompt, user_prompt=user_prompt)
    questions = result.get("questions", []) or []

    return {
        "job_id": job.id,
        "questions": questions[:count],
    }

