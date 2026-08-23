"""JD Analyzer router - resume vs job description skill gap analysis."""

import os
import sys
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from typing import Optional

from auth.dependencies import get_current_active_user
from database.models import User
from database.mongodb import get_mongo_db

from jd_analyzer.resume_parser import extract_text_from_resume
from jd_analyzer.skill_analyzer import analyze_missing_skills
from jd_analyzer.job_descriptions import get_job_description

router = APIRouter(prefix="/api/v1/jd-analyzer", tags=["JD Analyzer"])


class JDAnalyzeRequest(BaseModel):
    resume_text: Optional[str] = None
    resume_id: Optional[str] = None
    jd_name: Optional[str] = None
    jd_text: Optional[str] = None


def _get_resume_text_from_id(resume_id: str) -> str:
    """Fetch resume raw/parsed text from MongoDB by resume_id."""
    mongo_db = get_mongo_db()
    resume_doc = mongo_db.resumes.find_one({"resume_id": resume_id})
    if not resume_doc:
        try:
            from bson import ObjectId
            resume_doc = mongo_db.resumes.find_one({"_id": ObjectId(resume_id)})
        except Exception:
            pass
    if not resume_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    raw = resume_doc.get("raw_text") or ""
    if raw:
        return raw
    parsed = resume_doc.get("parsed_data", {})
    return parsed.get("raw_text", "") or ""


def _get_jd_text(jd_name: Optional[str], jd_text: Optional[str]) -> str:
    """Resolve JD text from jd_name (predefined) or jd_text (custom)."""
    if jd_name:
        jds = get_job_description(None)
        if jds is None or not isinstance(jds, dict):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job description '{jd_name}' not found"
            )
        jd_name_lower = jd_name.lower().replace(" ", "_")
        if jd_name_lower in jds:
            return jds[jd_name_lower]
        for key, value in jds.items():
            if jd_name_lower in key or key in jd_name_lower:
                return value
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job description '{jd_name}' not found. Available: {list(jds.keys())}"
        )
    if jd_text and jd_text.strip():
        return jd_text.strip()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Either jd_name or jd_text must be provided"
    )


def _ensure_resume_text(
    resume_text: Optional[str],
    resume_id: Optional[str],
    resume_file_path: Optional[str],
) -> str:
    """Get resume text from one of: resume_text, resume_id, or file path."""
    if resume_file_path and os.path.exists(resume_file_path):
        try:
            text = extract_text_from_resume(resume_file_path)
            if text and text.strip():
                return text.strip()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not extract text from resume file: {str(e)}"
            )
    if resume_text and resume_text.strip():
        return resume_text.strip()
    if resume_id:
        return _get_resume_text_from_id(resume_id)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide one of: resume_text, resume_id, or resume file upload"
    )


@router.get("/jds")
async def list_jds(
    current_user: User = Depends(get_current_active_user),
):
    """Return list of predefined job description names."""
    jds = get_job_description(None)
    if jds is None or not isinstance(jds, dict):
        return {"available_jds": [], "message": "No predefined JDs available"}
    return {
        "available_jds": list(jds.keys()),
        "message": "Use jd_name in POST /analyze to select a JD, or provide jd_text for custom JD"
    }


@router.post("/analyze")
async def analyze(
    request: JDAnalyzeRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Analyze resume against job description (resume_text or resume_id + jd_name or jd_text).
    Returns matching/missing skills and match percentage.
    """
    jd_text = _get_jd_text(request.jd_name, request.jd_text)
    resume_text = _ensure_resume_text(request.resume_text, request.resume_id, None)

    try:
        analysis_result = analyze_missing_skills(resume_text, jd_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing resume: {str(e)}"
        )

    return {
        "jd_name": request.jd_name or "Custom JD",
        "analysis": analysis_result
    }


@router.post("/analyze/upload")
async def analyze_upload(
    file: UploadFile = File(...),
    jd_name: Optional[str] = Form(None),
    jd_text: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
):
    """
    Analyze uploaded resume file against job description (jd_name or jd_text in form).
    """
    jd_text_resolved = _get_jd_text(jd_name, jd_text)

    suffix = Path(file.filename or "resume").suffix.lower()
    if suffix not in (".pdf", ".docx", ".doc", ".txt"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Use PDF, DOCX, DOC, or TXT."
        )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        resume_text = _ensure_resume_text(None, None, tmp_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing resume file: {str(e)}"
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    try:
        analysis_result = analyze_missing_skills(resume_text, jd_text_resolved)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing resume: {str(e)}"
        )

    return {
        "jd_name": jd_name or "Custom JD",
        "filename": file.filename,
        "analysis": analysis_result
    }
