from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


class JobRequirement(BaseModel):
    """Model for job requirements posted by recruiters"""
    job_title: str = Field(..., description="Title of the job position")
    required_skills: List[str] = Field(..., description="List of required skills")
    preferred_skills: List[str] = Field(default_factory=list, description="List of preferred skills")
    education_level: Optional[str] = Field(None, description="Required education level (e.g., Bachelor's, Master's)")
    years_of_experience: Optional[int] = Field(None, description="Required years of experience")
    job_description: Optional[str] = Field(None, description="Detailed job description")
    keywords: List[str] = Field(default_factory=list, description="Important keywords for the role")
    minimum_ats_score: float = Field(50.0, ge=0, le=100, description="Minimum ATS score required to pass")


class ResumeData(BaseModel):
    """Model for parsed resume data"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = []
    education: List[Dict] = []
    experience: List[Dict] = []
    certifications: List[str] = []
    projects: List[Dict] = []
    raw_text: str = ""


class ATSResult(BaseModel):
    """Model for ATS scoring result"""
    candidate_id: str
    ats_score: float = Field(..., ge=0, le=100, description="ATS score out of 100")
    passed: bool = Field(..., description="Whether candidate passed the minimum threshold")
    skill_match_score: float = Field(..., description="Score for skill matching")
    education_score: float = Field(..., description="Score for education match")
    experience_score: float = Field(..., description="Score for experience match")
    keyword_match_score: float = Field(..., description="Score for keyword matching")
    format_score: float = Field(..., description="Score for resume format and structure")
    matched_skills: List[str] = Field(default_factory=list, description="Skills that matched")
    missing_skills: List[str] = Field(default_factory=list, description="Required skills not found")
    recommendations: List[str] = Field(default_factory=list, description="General recommendations")


class RejectionFeedback(BaseModel):
    """Model for detailed feedback when candidate is rejected"""
    candidate_id: str
    ats_score: float
    minimum_required_score: float
    rejection_reasons: List[str] = Field(..., description="Specific reasons for rejection")
    missing_critical_skills: List[str] = Field(default_factory=list, description="Critical skills missing")
    resume_strengths: List[str] = Field(default_factory=list, description="What the resume does well")
    resume_weaknesses: List[str] = Field(default_factory=list, description="Areas of weakness")
    improvement_recommendations: List[str] = Field(..., description="Specific actionable recommendations")
    format_issues: List[str] = Field(default_factory=list, description="Resume format problems")
    mistake_highlights: List[str] = Field(default_factory=list, description="Mistakes found in resume")


class CandidateEvaluationRequest(BaseModel):
    """Request model for evaluating a candidate"""
    job_requirement: JobRequirement
    resume_file_path: Optional[str] = None
    resume_text: Optional[str] = None


class CandidateEvaluationResponse(BaseModel):
    """Response model for candidate evaluation"""
    candidate_id: str
    ats_result: ATSResult
    feedback: Optional[RejectionFeedback] = None
    message: str


