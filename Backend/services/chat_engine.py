"""
Chat Engine for HR AI Assistant and Student AI Assistant
Handles intent classification, data retrieval, and response generation
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from database.models import Job, Candidate, Application, Evaluation, ApplicationStatus
from schemas.api import JobResponse, CandidateResponse, EvaluationResponse
from services.student_engine import CampusConnectStudentEngine
from config import USE_LLM_FEEDBACK, USE_LLM_CHAT
from llm.student_feedback import (
    generate_resume_feedback_llm,
    interpret_rejection_llm,
)
from llm.intent_router import classify_hr_intent, classify_student_intent


class IntentClassifier:
    """Classifies user queries into specific intents"""
    
    # Intent patterns
    JOB_PATTERNS = [
        r'\b(jobs?|postings?|openings?|positions?|vacancies?|roles?)\b',
        r'\bshow.*jobs?\b',
        r'\blist.*jobs?\b',
        r'\bget.*jobs?\b',
        r'\bfind.*jobs?\b',
    ]
    
    CANDIDATE_PATTERNS = [
        r'\b(candidates?|applicants?|people|profiles?)\b',
        r'\bshow.*candidates?\b',
        r'\blist.*candidates?\b',
        r'\bget.*candidates?\b',
        r'\bfind.*candidates?\b',
    ]
    
    EVALUATION_PATTERNS = [
        r'\b(ats.*score|evaluation|score|rating|assessment)\b',
        r'\bhow.*score\b',
        r'\bwhat.*score\b',
        r'\bget.*score\b',
        r'\bshow.*score\b',
    ]
    
    STATISTICS_PATTERNS = [
        r'\b(statistics?|stats?|summary|overview|dashboard|count|total|how many)\b',
        r'\bshow.*statistics?\b',
        r'\bget.*statistics?\b',
    ]
    
    JOB_DETAIL_PATTERNS = [
        r'\bjob\s+(\d+)\b',
        r'\bjob\s+#(\d+)\b',
        r'\bposition\s+(\d+)\b',
        r'\bdetails?\s+for\s+job\s+(\d+)\b',
    ]
    
    CANDIDATE_DETAIL_PATTERNS = [
        r'\bcandidate\s+(\d+)\b',
        r'\bcandidate\s+#(\d+)\b',
        r'\bapplicant\s+(\d+)\b',
        r'\bdetails?\s+for\s+candidate\s+(\d+)\b',
    ]
    
    SKILL_SEARCH_PATTERNS = [
        r'\bwith\s+(\w+(?:\s+\w+)*)\s+skills?\b',
        r'\b(\w+(?:\s+\w+)*)\s+skills?\b',
        r'\bwho\s+knows?\s+(\w+(?:\s+\w+)*)\b',
    ]
    
    APPLICATION_COUNT_PATTERNS = [
        r'\bhow\s+many\s+(applications?|candidates?|applicants?)\b',
        r'\bcount\s+of\s+(applications?|candidates?)\b',
        r'\bnumber\s+of\s+(applications?|candidates?)\b',
    ]
    
    # Pattern to extract candidate name (after "candidate" or "of candidate")
    CANDIDATE_NAME_PATTERNS = [
        r'\b(?:of|for|show|get|evaluations?\s+of|evaluations?\s+for)\s+(?:candidate|applicant)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)',
        r'\bcandidate\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)',
        r'\bapplicant\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)',
        # Pattern for "show evaluations of varij" or "evaluations of varij"
        r'\b(?:evaluations?\s+of|evaluation\s+of|show\s+evaluations?\s+of)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)',
    ]
    
    def extract_candidate_name(self, message: str) -> Optional[str]:
        """Extract candidate name from message"""
        message_lower = message.lower()
        
        # First, try patterns that explicitly mention "candidate" or "applicant"
        for pattern in self.CANDIDATE_NAME_PATTERNS[:3]:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Don't return if it's a number (ID)
                if not name.isdigit():
                    return name
        
        # Then try evaluation-specific patterns
        for pattern in self.CANDIDATE_NAME_PATTERNS[3:]:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if not name.isdigit():
                    return name
        
        return None
    
    def classify(self, message: str) -> Tuple[str, Dict[str, Any]]:
        """
        Classify user message into intent and extract parameters
        
        Returns:
            Tuple of (intent, parameters)
        """
        message_lower = message.lower().strip()
        
        # Check for specific ID queries first
        job_id_match = re.search(self.JOB_DETAIL_PATTERNS[0], message_lower)
        if job_id_match:
            return ("get_job", {"job_id": int(job_id_match.group(1))})
        
        # Check for candidate name before ID
        candidate_name = self.extract_candidate_name(message)
        if candidate_name and not any(re.search(pattern, message_lower) for pattern in self.EVALUATION_PATTERNS):
            return ("get_candidate_by_name", {"candidate_name": candidate_name})
        
        candidate_id_match = re.search(self.CANDIDATE_DETAIL_PATTERNS[0], message_lower)
        if candidate_id_match:
            return ("get_candidate", {"candidate_id": int(candidate_id_match.group(1))})
        
        # Check for skill-based searches
        skill_match = re.search(self.SKILL_SEARCH_PATTERNS[0], message_lower)
        if skill_match:
            skill = skill_match.group(1)
            if any(re.search(pattern, message_lower) for pattern in self.CANDIDATE_PATTERNS):
                return ("search_candidates_by_skill", {"skill": skill})
        
        # Check for application counts
        if any(re.search(pattern, message_lower) for pattern in self.APPLICATION_COUNT_PATTERNS):
            # Try to extract job ID
            job_id_match = re.search(r'\b(job|position)\s+(\d+)\b', message_lower)
            if job_id_match:
                return ("get_application_count", {"job_id": int(job_id_match.group(2))})
            return ("get_statistics", {})
        
        # Check for evaluation queries
        if any(re.search(pattern, message_lower) for pattern in self.EVALUATION_PATTERNS):
            # Try to extract candidate name first
            candidate_name = self.extract_candidate_name(message)
            if candidate_name:
                return ("get_candidate_evaluations_by_name", {"candidate_name": candidate_name})
            # Try to extract candidate ID
            candidate_id_match = re.search(r'\bcandidate\s+(\d+)\b', message_lower)
            if candidate_id_match:
                return ("get_candidate_evaluations", {"candidate_id": int(candidate_id_match.group(1))})
            job_id_match = re.search(r'\bjob\s+(\d+)\b', message_lower)
            if job_id_match:
                return ("get_job_evaluations", {"job_id": int(job_id_match.group(1))})
            return ("get_evaluations", {})
        
        # Check for statistics
        if any(re.search(pattern, message_lower) for pattern in self.STATISTICS_PATTERNS):
            return ("get_statistics", {})
        
        # Check for job queries
        if any(re.search(pattern, message_lower) for pattern in self.JOB_PATTERNS):
            # Check for company filter
            company_match = re.search(r'\b(?:at|from|company)\s+([A-Za-z][A-Za-z0-9\s]+?)(?:\s|$)', message_lower)
            if company_match:
                return ("list_jobs", {"company": company_match.group(1).strip()})
            return ("list_jobs", {})
        
        # Check for candidate queries
        if any(re.search(pattern, message_lower) for pattern in self.CANDIDATE_PATTERNS):
            return ("list_candidates", {})
        
        # Default to general help
        return ("help", {})


class StudentIntentClassifier:
    """Classifies student queries into specific intents"""
    
    # Job search patterns
    JOB_SEARCH_PATTERNS = [
        r'\b(find|search|show|get|list|recommend).*jobs?\b',
        r'\bjobs?\s+(?:for|with|in|using)\s+(\w+(?:\s+\w+)*)',
        r'\b(backend|frontend|full.?stack|python|java|javascript|react|node).*jobs?\b',
        r'\bpositions?\s+(?:for|in)\s+(\w+(?:\s+\w+)*)',
    ]
    
    # Skill gap patterns
    SKILL_GAP_PATTERNS = [
        r'\b(what|which|what are).*skills?\s+(?:do I|I need|required|missing)',
        r'\bskill\s+gap',
        r'\bmissing\s+skills?',
        r'\banalyze\s+(?:my\s+)?skills?',
        r'\bwhat\s+skills?\s+for\s+job',
    ]
    
    # Application status patterns
    APPLICATION_STATUS_PATTERNS = [
        r'\bmy\s+applications?',
        r'\bwhere\s+(?:did|have)\s+I\s+applied',
        r'\bapplication\s+status',
        r'\bshow\s+my\s+applications?',
        r'\bstatus\s+of\s+my\s+applications?',
    ]
    
    # Resume feedback patterns
    RESUME_FEEDBACK_PATTERNS = [
        r'\bresume\s+feedback',
        r'\bimprove\s+(?:my\s+)?resume',
        r'\bresume\s+tips?',
        r'\bhow\s+to\s+improve\s+resume',
        r'\bresume\s+for\s+job',
    ]
    
    # Rejection interpretation patterns
    REJECTION_PATTERNS = [
        r'\bwhy\s+(?:was I|am I|did I get)\s+rejected',
        r'\brejection\s+reason',
        r'\bexplain\s+(?:this\s+)?rejection',
        r'\bwhy\s+rejected',
    ]
    
    # Job detail patterns
    JOB_DETAIL_PATTERNS = [
        r'\bjob\s+(\d+)\b',
        r'\bdetails?\s+(?:for|of)\s+job\s+(\d+)\b',
        r'\bshow\s+job\s+(\d+)\b',
    ]
    
    def classify(self, message: str) -> Tuple[str, Dict[str, Any]]:
        """Classify student message into intent"""
        message_lower = message.lower().strip()
        
        # Check for job detail queries
        job_id_match = re.search(self.JOB_DETAIL_PATTERNS[0], message_lower)
        if job_id_match:
            # Check if it's asking for skill gap
            if any(re.search(pattern, message_lower) for pattern in self.SKILL_GAP_PATTERNS):
                return ("analyze_skill_gap_for_job", {"job_id": int(job_id_match.group(1))})
            return ("get_job_details", {"job_id": int(job_id_match.group(1))})
        
        # Check for skill gap queries
        if any(re.search(pattern, message_lower) for pattern in self.SKILL_GAP_PATTERNS):
            # Try to extract job ID
            job_id_match = re.search(r'\bjob\s+(\d+)\b', message_lower)
            if job_id_match:
                return ("analyze_skill_gap_for_job", {"job_id": int(job_id_match.group(1))})
            return ("analyze_skill_gap", {})
        
        # Check for application status
        if any(re.search(pattern, message_lower) for pattern in self.APPLICATION_STATUS_PATTERNS):
            return ("get_my_applications", {})
        
        # Check for resume feedback
        if any(re.search(pattern, message_lower) for pattern in self.RESUME_FEEDBACK_PATTERNS):
            # Try to extract job ID
            job_id_match = re.search(r'\bjob\s+(\d+)\b', message_lower)
            if job_id_match:
                return ("get_resume_feedback", {"job_id": int(job_id_match.group(1))})
            return ("get_resume_feedback", {})
        
        # Check for rejection interpretation
        if any(re.search(pattern, message_lower) for pattern in self.REJECTION_PATTERNS):
            # Try to extract job ID
            job_id_match = re.search(r'\bjob\s+(\d+)\b', message_lower)
            if job_id_match:
                return ("interpret_rejection", {"job_id": int(job_id_match.group(1))})
            return ("interpret_rejection", {})
        
        # Check for job search
        if any(re.search(pattern, message_lower) for pattern in self.JOB_SEARCH_PATTERNS):
            # Extract technology/skill from query
            tech_match = re.search(r'\b(backend|frontend|full.?stack|python|java|javascript|react|node|angular|vue|django|flask|spring)\b', message_lower)
            tech = tech_match.group(1) if tech_match else None
            return ("search_jobs", {"query": message, "technology": tech})
        
        # Default to job search if it contains job-related keywords
        if re.search(r'\b(jobs?|positions?|roles?|opportunities?)\b', message_lower):
            return ("search_jobs", {"query": message})
        
        # Default to help
        return ("help", {})


class DataRetriever:
    """Retrieves data from database based on intent"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def list_jobs(self, company: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """List all jobs with optional company filter"""
        query = self.db.query(Job)
        
        if company:
            query = query.filter(Job.company.ilike(f"%{company}%"))
        
        jobs = query.order_by(Job.created_at.desc()).limit(limit).all()
        
        result = []
        for job in jobs:
            application_count = self.db.query(Application).filter(
                Application.job_id == job.id
            ).count()
            
            result.append({
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "salary": job.salary,
                "application_count": application_count,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            })
        
        return result
    
    def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get specific job details"""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        
        if not job:
            return None
        
        application_count = self.db.query(Application).filter(
            Application.job_id == job.id
        ).count()
        
        applications = self.db.query(Application).filter(
            Application.job_id == job.id
        ).all()
        
        status_counts = {}
        for app in applications:
            status_counts[app.status.value] = status_counts.get(app.status.value, 0) + 1
        
        return {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "description": job.description,
            "location": job.location,
            "salary": job.salary,
            "requirements": job.requirements_json,
            "application_count": application_count,
            "status_counts": status_counts,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }
    
    def list_candidates(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List all candidates"""
        candidates = self.db.query(Candidate).order_by(
            Candidate.created_at.desc()
        ).limit(limit).all()
        
        result = []
        for candidate in candidates:
            application_count = self.db.query(Application).filter(
                Application.candidate_id == candidate.id
            ).count()
            
            result.append({
                "id": candidate.id,
                "name": candidate.name,
                "email": candidate.email,
                "phone": candidate.phone,
                "skills": candidate.skills_json or [],
                "application_count": application_count,
                "has_resume": candidate.resume_id is not None,
                "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
            })
        
        return result
    
    def get_candidate_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get candidate by name (case-insensitive partial match)"""
        # Try exact match first
        candidate = self.db.query(Candidate).filter(
            Candidate.name.ilike(name)
        ).first()
        
        # If not found, try partial match
        if not candidate:
            candidate = self.db.query(Candidate).filter(
                Candidate.name.ilike(f"%{name}%")
            ).first()
        
        if not candidate:
            return None
        
        applications = self.db.query(Application).filter(
            Application.candidate_id == candidate.id
        ).all()
        
        application_list = []
        for app in applications:
            job = self.db.query(Job).filter(Job.id == app.job_id).first()
            application_list.append({
                "id": app.id,
                "job_id": app.job_id,
                "job_title": job.title if job else "Unknown",
                "status": app.status.value,
                "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            })
        
        return {
            "id": candidate.id,
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
            "skills": candidate.skills_json or [],
            "resume_id": candidate.resume_id,
            "applications": application_list,
            "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
        }
    
    def get_candidate(self, candidate_id: int) -> Optional[Dict[str, Any]]:
        """Get specific candidate details"""
        candidate = self.db.query(Candidate).filter(Candidate.id == candidate_id).first()
        
        if not candidate:
            return None
        
        applications = self.db.query(Application).filter(
            Application.candidate_id == candidate.id
        ).all()
        
        application_list = []
        for app in applications:
            job = self.db.query(Job).filter(Job.id == app.job_id).first()
            application_list.append({
                "id": app.id,
                "job_id": app.job_id,
                "job_title": job.title if job else "Unknown",
                "status": app.status.value,
                "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            })
        
        return {
            "id": candidate.id,
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
            "skills": candidate.skills_json or [],
            "resume_id": candidate.resume_id,
            "applications": application_list,
            "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
        }
    
    def search_candidates_by_skill(self, skill: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search candidates by skill"""
        candidates = self.db.query(Candidate).filter(
            Candidate.skills_json.contains([skill])
        ).limit(limit).all()
        
        result = []
        for candidate in candidates:
            result.append({
                "id": candidate.id,
                "name": candidate.name,
                "email": candidate.email,
                "skills": candidate.skills_json or [],
            })
        
        return result
    
    def get_candidate_evaluations_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Get evaluations for a candidate by name"""
        # Find candidate by name
        candidate = self.db.query(Candidate).filter(
            Candidate.name.ilike(f"%{name}%")
        ).first()
        
        if not candidate:
            return []
        
        return self.get_candidate_evaluations(candidate.id)
    
    def get_candidate_evaluations(self, candidate_id: int) -> List[Dict[str, Any]]:
        """Get evaluations for a candidate"""
        applications = self.db.query(Application).filter(
            Application.candidate_id == candidate_id
        ).all()
        
        application_ids = [app.id for app in applications]
        
        if not application_ids:
            return []
        
        evaluations = self.db.query(Evaluation).filter(
            Evaluation.application_id.in_(application_ids)
        ).all()
        
        result = []
        for eval in evaluations:
            app = self.db.query(Application).filter(Application.id == eval.application_id).first()
            job = self.db.query(Job).filter(Job.id == app.job_id).first() if app else None
            
            result.append({
                "id": eval.id,
                "application_id": eval.application_id,
                "job_title": job.title if job else "Unknown",
                "ats_score": eval.ats_score,
                "passed": eval.passed,
                "skill_match_score": eval.skill_match_score,
                "education_score": eval.education_score,
                "experience_score": eval.experience_score,
                "matched_skills": eval.matched_skills_json or [],
                "missing_skills": eval.missing_skills_json or [],
                "created_at": eval.created_at.isoformat() if eval.created_at else None,
            })
        
        return result
    
    def get_job_evaluations(self, job_id: int) -> List[Dict[str, Any]]:
        """Get evaluations for a job"""
        applications = self.db.query(Application).filter(
            Application.job_id == job_id
        ).all()
        
        application_ids = [app.id for app in applications]
        
        if not application_ids:
            return []
        
        evaluations = self.db.query(Evaluation).filter(
            Evaluation.application_id.in_(application_ids)
        ).all()
        
        result = []
        for eval in evaluations:
            app = self.db.query(Application).filter(Application.id == eval.application_id).first()
            candidate = self.db.query(Candidate).filter(
                Candidate.id == app.candidate_id
            ).first() if app else None
            
            result.append({
                "id": eval.id,
                "application_id": eval.application_id,
                "candidate_name": candidate.name if candidate else "Unknown",
                "ats_score": eval.ats_score,
                "passed": eval.passed,
                "skill_match_score": eval.skill_match_score,
                "matched_skills": eval.matched_skills_json or [],
                "missing_skills": eval.missing_skills_json or [],
            })
        
        return result
    
    def get_application_count(self, job_id: int) -> Dict[str, Any]:
        """Get application count for a job"""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        
        total = self.db.query(Application).filter(Application.job_id == job_id).count()
        
        status_counts = {}
        for status in ApplicationStatus:
            count = self.db.query(Application).filter(
                and_(Application.job_id == job_id, Application.status == status)
            ).count()
            if count > 0:
                status_counts[status.value] = count
        
        return {
            "job_id": job_id,
            "job_title": job.title,
            "total_applications": total,
            "status_counts": status_counts,
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics"""
        total_jobs = self.db.query(Job).count()
        total_candidates = self.db.query(Candidate).count()
        total_applications = self.db.query(Application).count()
        total_evaluations = self.db.query(Evaluation).count()
        
        # Status breakdown
        status_counts = {}
        for status in ApplicationStatus:
            count = self.db.query(Application).filter(Application.status == status).count()
            status_counts[status.value] = count
        
        # Evaluation stats
        passed_count = self.db.query(Evaluation).filter(Evaluation.passed == True).count()
        failed_count = self.db.query(Evaluation).filter(Evaluation.passed == False).count()
        
        avg_score = self.db.query(func.avg(Evaluation.ats_score)).scalar()
        avg_score = float(avg_score) if avg_score else 0.0
        
        return {
            "total_jobs": total_jobs,
            "total_candidates": total_candidates,
            "total_applications": total_applications,
            "total_evaluations": total_evaluations,
            "application_status_counts": status_counts,
            "evaluation_stats": {
                "passed": passed_count,
                "failed": failed_count,
                "average_score": round(avg_score, 2),
            },
        }
    
    # Student-specific methods
    def get_student_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get student's candidate profile"""
        candidate = self.db.query(Candidate).filter(Candidate.user_id == user_id).first()
        
        if not candidate:
            return None
        
        return {
            "id": candidate.id,
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
            "skills": candidate.skills_json or [],
            "resume_id": candidate.resume_id,
            "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
        }
    
    def get_student_applications(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all applications for a student"""
        candidate = self.db.query(Candidate).filter(Candidate.user_id == user_id).first()
        
        if not candidate:
            return []
        
        applications = self.db.query(Application).filter(
            Application.candidate_id == candidate.id
        ).order_by(Application.applied_at.desc()).all()
        
        result = []
        for app in applications:
            job = self.db.query(Job).filter(Job.id == app.job_id).first()
            
            # Get evaluation if exists
            evaluation = self.db.query(Evaluation).filter(
                Evaluation.application_id == app.id
            ).first()
            
            result.append({
                "id": app.id,
                "job_id": app.job_id,
                "job_title": job.title if job else "Unknown",
                "company": job.company if job else "Unknown",
                "status": app.status.value,
                "applied_at": app.applied_at.isoformat() if app.applied_at else None,
                "ats_score": evaluation.ats_score if evaluation else None,
                "passed": evaluation.passed if evaluation else None,
            })
        
        return result
    
    def get_student_evaluations(self, user_id: int) -> List[Dict[str, Any]]:
        """Get evaluations for student's applications"""
        candidate = self.db.query(Candidate).filter(Candidate.user_id == user_id).first()
        
        if not candidate:
            return []
        
        return self.get_candidate_evaluations(candidate.id)
    
    def search_jobs_for_student(self, query: str, student_skills: List[str], top_k: int = 10) -> List[Dict[str, Any]]:
        """Search jobs using student engine"""
        from services.student_engine import CampusConnectStudentEngine
        
        # Get all jobs
        jobs = self.db.query(Job).all()
        
        # Convert to list of dicts
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
        
        # Use student engine
        student_engine = CampusConnectStudentEngine()
        results = student_engine.search_jobs(
            student_query=query,
            jobs=jobs_list,
            student_skills=student_skills,
            top_k=top_k
        )
        
        return results
    
    def analyze_skill_gap_for_job(self, job_id: int, student_skills: List[str]) -> Optional[Dict[str, Any]]:
        """Analyze skill gap for a specific job"""
        from services.student_engine import CampusConnectStudentEngine
        
        job = self.db.query(Job).filter(Job.id == job_id).first()
        
        if not job:
            return None
        
        requirements = job.requirements_json or {}
        job_skills = requirements.get("required_skills", [])
        
        student_engine = CampusConnectStudentEngine()
        result = student_engine.analyze_skill_gap(
            student_skills=student_skills,
            job_skills=job_skills,
            job_role=job.title
        )
        
        return {
            "job_id": job_id,
            "job_title": job.title,
            "company": job.company,
            **result
        }
    
    def get_job_details_for_student(self, job_id: int, student_skills: List[str]) -> Optional[Dict[str, Any]]:
        """Get job details with match analysis for student"""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        
        if not job:
            return None
        
        # Get basic job info
        job_data = {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "description": job.description,
            "location": job.location,
            "salary": job.salary,
            "requirements": job.requirements_json or {},
        }
        
        # Add skill gap analysis if student has skills
        if student_skills:
            skill_gap = self.analyze_skill_gap_for_job(job_id, student_skills)
            if skill_gap:
                job_data["skill_gap"] = {
                    "missing_skills": skill_gap.get("missing_skills", []),
                    "matched_skills": skill_gap.get("matched_skills", []),
                    "match_percentage": skill_gap.get("match_percentage", 0.0),
                }
        
        return job_data


class ResponseGenerator:
    """Generates natural language responses from data"""
    
    def generate(self, intent: str, data: Any, params: Dict[str, Any] = None) -> str:
        """Generate response based on intent and data"""
        params = params or {}
        
        if intent == "list_jobs":
            if not data:
                return "I couldn't find any job postings in the system."
            
            if len(data) == 1:
                job = data[0]
                return f"I found 1 job posting:\n\n**{job['title']}** at {job['company']}\n" \
                       f"Location: {job.get('location', 'Not specified')}\n" \
                       f"Applications: {job.get('application_count', 0)}"
            
            response = f"I found {len(data)} job postings:\n\n"
            for job in data[:10]:  # Limit to 10 for readability
                response += f"• **{job['title']}** at {job['company']} " \
                           f"(ID: {job['id']}, {job.get('application_count', 0)} applications)\n"
            
            if len(data) > 10:
                response += f"\n... and {len(data) - 10} more jobs."
            
            return response
        
        elif intent == "get_job":
            if not data:
                return f"I couldn't find job {params.get('job_id', '')} in the system."
            
            job = data
            response = f"**Job Details (ID: {job['id']}):**\n\n"
            response += f"Title: {job['title']}\n"
            response += f"Company: {job['company']}\n"
            if job.get('location'):
                response += f"Location: {job['location']}\n"
            if job.get('salary'):
                response += f"Salary: {job['salary']}\n"
            response += f"\nTotal Applications: {job.get('application_count', 0)}\n"
            
            if job.get('status_counts'):
                response += "\nApplication Status Breakdown:\n"
                for status, count in job['status_counts'].items():
                    response += f"  • {status.capitalize()}: {count}\n"
            
            return response
        
        elif intent == "list_candidates":
            if not data:
                return "I couldn't find any candidates in the system."
            
            if len(data) == 1:
                candidate = data[0]
                return f"I found 1 candidate:\n\n**{candidate['name']}** ({candidate['email']})\n" \
                       f"Skills: {', '.join(candidate.get('skills', [])[:5]) or 'None'}\n" \
                       f"Applications: {candidate.get('application_count', 0)}"
            
            response = f"I found {len(data)} candidates:\n\n"
            for candidate in data[:10]:
                skills = ', '.join(candidate.get('skills', [])[:3]) or 'No skills listed'
                response += f"• **{candidate['name']}** (ID: {candidate['id']}, {candidate.get('application_count', 0)} applications)\n"
                response += f"  Skills: {skills}\n"
            
            if len(data) > 10:
                response += f"\n... and {len(data) - 10} more candidates."
            
            return response
        
        elif intent == "get_candidate" or intent == "get_candidate_by_name":
            if not data:
                candidate_ref = params.get('candidate_name') or params.get('candidate_id', '')
                return f"I couldn't find candidate {candidate_ref} in the system."
            
            candidate = data
            response = f"**Candidate Details (ID: {candidate['id']}):**\n\n"
            response += f"Name: **{candidate['name']}**\n"
            response += f"Email: {candidate['email']}\n"
            if candidate.get('phone'):
                response += f"Phone: {candidate['phone']}\n"
            
            skills = candidate.get('skills', [])
            if skills:
                response += f"\nSkills: {', '.join(skills)}\n"
            
            response += f"\nTotal Applications: {len(candidate.get('applications', []))}\n"
            
            if candidate.get('applications'):
                response += "\nApplications:\n"
                for app in candidate['applications'][:5]:
                    response += f"  • {app['job_title']} (Status: {app['status']})\n"
            
            return response
        
        elif intent == "search_candidates_by_skill":
            if not data:
                return f"I couldn't find any candidates with the skill '{params.get('skill', '')}'."
            
            response = f"I found {len(data)} candidate(s) with '{params.get('skill', '')}' skill:\n\n"
            for candidate in data:
                response += f"• **{candidate['name']}** (ID: {candidate['id']})\n"
            
            return response
        
        elif intent == "get_candidate_evaluations" or intent == "get_candidate_evaluations_by_name":
            if not data:
                candidate_ref = params.get('candidate_name') or params.get('candidate_id', '')
                return f"I couldn't find any evaluations for candidate {candidate_ref}."
            
            candidate_name = params.get('candidate_name', 'this candidate')
            response = f"I found {len(data)} evaluation(s) for **{candidate_name}**:\n\n"
            for eval in data:
                status = "✅ Passed" if eval['passed'] else "❌ Failed"
                response += f"• **{eval['job_title']}** - {status}\n"
                response += f"  ATS Score: {eval['ats_score']:.1f}%\n"
                if eval.get('matched_skills'):
                    response += f"  Matched Skills: {', '.join(eval['matched_skills'][:5])}\n"
                if eval.get('missing_skills'):
                    response += f"  Missing Skills: {', '.join(eval['missing_skills'][:5])}\n"
            
            return response
        
        elif intent == "get_job_evaluations":
            if not data:
                return f"I couldn't find any evaluations for job {params.get('job_id', '')}."
            
            response = f"I found {len(data)} evaluation(s) for this job:\n\n"
            for eval in data:
                status = "✅ Passed" if eval['passed'] else "❌ Failed"
                response += f"• **{eval['candidate_name']}** - {status}\n"
                response += f"  ATS Score: {eval['ats_score']:.1f}%\n"
            
            return response
        
        elif intent == "get_application_count":
            if not data:
                return f"I couldn't find job {params.get('job_id', '')} in the system."
            
            response = f"**Application Statistics for {data['job_title']} (Job ID: {data['job_id']}):**\n\n"
            response += f"Total Applications: {data['total_applications']}\n\n"
            
            if data.get('status_counts'):
                response += "Status Breakdown:\n"
                for status, count in data['status_counts'].items():
                    response += f"  • {status.capitalize()}: {count}\n"
            
            return response
        
        elif intent == "get_statistics":
            if not data:
                return "I couldn't retrieve statistics at this time."
            
            stats = data
            response = "**Recruitment Dashboard Statistics:**\n\n"
            response += f"📊 **Overview:**\n"
            response += f"  • Total Jobs: {stats['total_jobs']}\n"
            response += f"  • Total Candidates: {stats['total_candidates']}\n"
            response += f"  • Total Applications: {stats['total_applications']}\n"
            response += f"  • Total Evaluations: {stats['total_evaluations']}\n\n"
            
            if stats.get('application_status_counts'):
                response += f"📋 **Application Status:**\n"
                for status, count in stats['application_status_counts'].items():
                    response += f"  • {status.capitalize()}: {count}\n"
                response += "\n"
            
            if stats.get('evaluation_stats'):
                eval_stats = stats['evaluation_stats']
                response += f"🎯 **Evaluation Results:**\n"
                response += f"  • Passed: {eval_stats['passed']}\n"
                response += f"  • Failed: {eval_stats['failed']}\n"
                response += f"  • Average ATS Score: {eval_stats['average_score']}%\n"
            
            return response
        
        elif intent == "help":
            return """I'm your AI recruitment assistant! I can help you with:

• **Jobs**: "Show me all jobs", "List jobs from Google", "Get details for job 5"
• **Candidates**: "List all candidates", "Show candidate 3", "Show candidate John", "Find candidates with Python skills"
• **Evaluations**: "Show evaluations for candidate 2", "Show evaluations of candidate varij", "What's the ATS score for job 1?"
• **Statistics**: "Show statistics", "How many applications for job 5?"

You can use candidate names or IDs. Just ask me in natural language and I'll help you find the information you need!"""
        
        else:
            return "I'm not sure how to help with that. Try asking about jobs, candidates, evaluations, or statistics."


class StudentResponseGenerator:
    """Generates natural language responses for student queries"""
    
    def generate(self, intent: str, data: Any, params: Dict[str, Any] = None, student_skills: List[str] = None) -> str:
        """Generate response based on intent and data"""
        params = params or {}
        student_skills = student_skills or []
        
        if intent == "search_jobs":
            if not data:
                return "I couldn't find any jobs matching your search. Try different keywords or skills."
            
            if len(data) == 1:
                job = data[0]
                status_emoji = "✅" if job.get("application_status") == "Direct Apply Eligible" else "💡"
                response = f"{status_emoji} I found 1 job matching your search:\n\n"
                response += f"**{job.get('title', 'Unknown')}** at {job.get('company', 'Unknown')}\n"
                response += f"Match Score: {job.get('match_score', 0):.1f}%\n"
                response += f"Status: {job.get('application_status', 'Recommended')}\n"
                if job.get('matched_skills'):
                    response += f"\nMatched Skills: {', '.join(job['matched_skills'][:5])}\n"
                if job.get('missing_skills'):
                    response += f"Missing Skills: {', '.join(job['missing_skills'][:5])}\n"
                return response
            
            response = f"I found {len(data)} jobs matching your search:\n\n"
            for job in data[:10]:
                status_emoji = "✅" if job.get("application_status") == "Direct Apply Eligible" else "💡"
                response += f"{status_emoji} **{job.get('title', 'Unknown')}** at {job.get('company', 'Unknown')}\n"
                response += f"   Match: {job.get('match_score', 0):.1f}% | {job.get('application_status', 'Recommended')}\n"
                if job.get('matched_skills'):
                    response += f"   Skills: {', '.join(job['matched_skills'][:3])}\n"
                response += "\n"
            
            if len(data) > 10:
                response += f"... and {len(data) - 10} more jobs."
            
            return response
        
        elif intent == "get_job_details":
            if not data:
                return f"I couldn't find job {params.get('job_id', '')} in the system."
            
            job = data
            response = f"**Job Details (ID: {job['id']}):**\n\n"
            response += f"Title: **{job['title']}**\n"
            response += f"Company: {job['company']}\n"
            if job.get('location'):
                response += f"Location: {job['location']}\n"
            if job.get('salary'):
                response += f"Salary: {job['salary']}\n"
            
            if job.get('skill_gap'):
                skill_gap = job['skill_gap']
                response += f"\n**Skill Match Analysis:**\n"
                response += f"Match: {skill_gap.get('match_percentage', 0):.1f}%\n"
                if skill_gap.get('matched_skills'):
                    response += f"✅ Matched: {', '.join(skill_gap['matched_skills'][:5])}\n"
                if skill_gap.get('missing_skills'):
                    response += f"❌ Missing: {', '.join(skill_gap['missing_skills'][:5])}\n"
            
            return response
        
        elif intent == "analyze_skill_gap" or intent == "analyze_skill_gap_for_job":
            if not data:
                return "I couldn't analyze the skill gap. Please make sure you have skills in your profile."
            
            analysis = data
            response = f"**Skill Gap Analysis for {analysis.get('job_title', 'this job')}:**\n\n"
            response += f"Match Percentage: **{analysis.get('match_percentage', 0):.1f}%**\n\n"
            
            if analysis.get('matched_skills'):
                response += f"✅ **Skills You Have:**\n"
                for skill in analysis['matched_skills'][:10]:
                    response += f"  • {skill}\n"
                response += "\n"
            
            if analysis.get('missing_skills'):
                response += f"❌ **Skills You Need:**\n"
                for skill in analysis['missing_skills'][:10]:
                    response += f"  • {skill}\n"
                response += "\n"
            
            if analysis.get('recommendations'):
                response += f"💡 **Recommendations:**\n"
                for rec in analysis['recommendations'][:5]:
                    if isinstance(rec, dict):
                        response += f"  • {rec.get('skill', '')}: {rec.get('reason', '')}\n"
                    else:
                        response += f"  • {rec}\n"
            
            return response
        
        elif intent == "get_my_applications":
            if not data:
                return "You haven't applied to any jobs yet. Start by searching for jobs that match your skills!"
            
            response = f"**Your Applications ({len(data)}):**\n\n"
            for app in data:
                status_emoji = {
                    "pending": "⏳",
                    "reviewing": "👀",
                    "shortlisted": "✅",
                    "rejected": "❌",
                    "accepted": "🎉"
                }.get(app['status'], "📋")
                
                response += f"{status_emoji} **{app['job_title']}** at {app['company']}\n"
                response += f"   Status: {app['status'].capitalize()}\n"
                if app.get('ats_score') is not None:
                    passed_emoji = "✅" if app.get('passed') else "❌"
                    response += f"   ATS Score: {app['ats_score']:.1f}% {passed_emoji}\n"
                response += "\n"
            
            return response
        
        elif intent == "get_resume_feedback":
            if not data:
                return "I couldn't generate resume feedback. Please provide a job ID or make sure you have a resume uploaded."
            
            feedback = data
            response = "**Resume Feedback & Optimization Tips:**\n\n"
            
            if feedback.get('feedback'):
                response += f"{feedback['feedback']}\n\n"
            
            if feedback.get('keyword_suggestions'):
                response += "**Keywords to Add:**\n"
                for keyword in feedback['keyword_suggestions'][:10]:
                    response += f"  • {keyword}\n"
                response += "\n"
            
            if feedback.get('improvements'):
                response += "**Improvements:**\n"
                for improvement in feedback['improvements'][:10]:
                    response += f"  • {improvement}\n"
            
            return response
        
        elif intent == "interpret_rejection":
            if not data:
                return "I couldn't interpret the rejection. Please provide more details about the job and rejection feedback."
            
            interpretation = data
            response = "**Rejection Explanation:**\n\n"
            response += f"{interpretation.get('student_friendly_explanation', 'No explanation available')}\n\n"
            
            if interpretation.get('improvement_suggestions'):
                response += "**How to Improve:**\n"
                for suggestion in interpretation['improvement_suggestions'][:5]:
                    response += f"  • {suggestion}\n"
                response += "\n"
            
            if interpretation.get('motivational_message'):
                response += f"💪 **{interpretation['motivational_message']}**\n"
            
            return response
        
        elif intent == "help":
            return """I'm your AI career assistant! I can help you with:

• **Job Search**: "Find backend developer jobs", "Show me Python positions", "Search for remote jobs"
• **Skill Analysis**: "What skills do I need for job 5?", "Analyze my skills for this job"
• **Applications**: "Show my applications", "Where did I apply?", "Application status"
• **Resume Help**: "How can I improve my resume?", "Resume feedback for job 3"
• **Rejections**: "Why was I rejected from job 2?", "Explain this rejection"

Just ask me in natural language and I'll help you find opportunities and improve your profile!"""
        
        else:
            return "I'm not sure how to help with that. Try asking about job search, skill gaps, applications, or resume feedback."


class ChatOrchestrator:
    """Main orchestrator that coordinates intent classification, data retrieval, and response generation"""
    
    def __init__(self, db: Session):
        self.intent_classifier = IntentClassifier()
        self.data_retriever = DataRetriever(db)
        self.response_generator = ResponseGenerator()
    
    def process_message(self, message: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Process a user message and return response with optional data
        
        Returns:
            Tuple of (response_text, data_dict)
        """
        # Classify intent (LLM-first, regex fallback)
        if USE_LLM_CHAT:
            intent, params = classify_hr_intent(message)
            # Basic safety: if LLM falls back to help with empty params, try regex
            if intent == "help" and not params:
                intent, params = self.intent_classifier.classify(message)
        else:
            intent, params = self.intent_classifier.classify(message)
        
        # Retrieve data based on intent
        data = None
        if intent == "list_jobs":
            data = self.data_retriever.list_jobs(company=params.get("company"))
        elif intent == "get_job":
            data = self.data_retriever.get_job(params.get("job_id"))
        elif intent == "list_candidates":
            data = self.data_retriever.list_candidates()
        elif intent == "get_candidate":
            data = self.data_retriever.get_candidate(params.get("candidate_id"))
        elif intent == "get_candidate_by_name":
            data = self.data_retriever.get_candidate_by_name(params.get("candidate_name"))
        elif intent == "search_candidates_by_skill":
            data = self.data_retriever.search_candidates_by_skill(params.get("skill"))
        elif intent == "get_candidate_evaluations":
            data = self.data_retriever.get_candidate_evaluations(params.get("candidate_id"))
        elif intent == "get_candidate_evaluations_by_name":
            data = self.data_retriever.get_candidate_evaluations_by_name(params.get("candidate_name"))
        elif intent == "get_job_evaluations":
            data = self.data_retriever.get_job_evaluations(params.get("job_id"))
        elif intent == "get_application_count":
            data = self.data_retriever.get_application_count(params.get("job_id"))
        elif intent == "get_statistics":
            data = self.data_retriever.get_statistics()
        
        # Generate response
        response = self.response_generator.generate(intent, data, params)
        
        # Return response and data (for frontend to render structured views if needed)
        return response, data


class StudentChatOrchestrator:
    """Main orchestrator for student chat that coordinates intent classification, data retrieval, and response generation"""
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.intent_classifier = StudentIntentClassifier()
        self.data_retriever = DataRetriever(db)
        self.response_generator = StudentResponseGenerator()
        self.user_id = user_id
        self.student_engine = CampusConnectStudentEngine()
    
    def get_student_skills(self) -> List[str]:
        """Get student's skills from their profile"""
        profile = self.data_retriever.get_student_profile(self.user_id)
        return profile.get('skills', []) if profile else []
    
    def process_message(self, message: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Process a student message and return response with optional data
        
        Returns:
            Tuple of (response_text, data_dict)
        """
        # Get student skills
        student_skills = self.get_student_skills()
        
        # Classify intent (LLM-first, regex fallback)
        if USE_LLM_CHAT:
            intent, params = classify_student_intent(message)
            if intent == "help" and not params:
                intent, params = self.intent_classifier.classify(message)
        else:
            intent, params = self.intent_classifier.classify(message)
        
        # Retrieve data based on intent
        data = None
        if intent == "search_jobs":
            query = params.get("query", message)
            data = self.data_retriever.search_jobs_for_student(query, student_skills, top_k=10)
        elif intent == "get_job_details":
            data = self.data_retriever.get_job_details_for_student(
                params.get("job_id"), student_skills
            )
        elif intent == "analyze_skill_gap_for_job":
            data = self.data_retriever.analyze_skill_gap_for_job(
                params.get("job_id"), student_skills
            )
        elif intent == "analyze_skill_gap":
            # Need job_id from params or ask user
            if params.get("job_id"):
                data = self.data_retriever.analyze_skill_gap_for_job(
                    params.get("job_id"), student_skills
                )
            else:
                return "Please specify which job you'd like me to analyze. For example: 'What skills do I need for job 5?'", None
        elif intent == "get_my_applications":
            data = self.data_retriever.get_student_applications(self.user_id)
        elif intent == "get_resume_feedback":
            job_id = params.get("job_id")
            if job_id:
                # Get job details
                job = self.db.query(Job).filter(Job.id == job_id).first()
                if job:
                    # Get student resume
                    profile = self.data_retriever.get_student_profile(self.user_id)
                    resume_id = profile.get('resume_id') if profile else None
                    
                    if resume_id:
                        from database.mongodb import get_mongo_db
                        mongo_db = get_mongo_db()
                        resume_doc = mongo_db.resumes.find_one({"resume_id": resume_id})
                        
                        if resume_doc:
                            resume_text = resume_doc.get("raw_text", "")
                            requirements = job.requirements_json or {}
                            
                            # Analyze skill gap first
                            skill_gap = self.data_retriever.analyze_skill_gap_for_job(job_id, student_skills)
                            
                            # Prefer LLM-based resume feedback when enabled
                            if USE_LLM_FEEDBACK:
                                feedback = generate_resume_feedback_llm(
                                    resume_text=resume_text,
                                    job_description=job.description or "",
                                    job_requirements=str(requirements),
                                    skill_gap_output=skill_gap or {},
                                )
                                if feedback:
                                    data = feedback
                                else:
                                    data = self.student_engine.get_resume_feedback(
                                        resume_text=resume_text,
                                        job_description=job.description or "",
                                        job_requirements=str(requirements),
                                        skill_gap_output=skill_gap or {},
                                    )
                            else:
                                data = self.student_engine.get_resume_feedback(
                                    resume_text=resume_text,
                                    job_description=job.description or "",
                                    job_requirements=str(requirements),
                                    skill_gap_output=skill_gap or {},
                                )
                    else:
                        return "You need to upload a resume first to get feedback. Please upload your resume in your profile.", None
                else:
                    return f"Job {job_id} not found.", None
            else:
                return "Please specify which job you'd like resume feedback for. For example: 'Resume feedback for job 5'", None
        elif intent == "interpret_rejection":
            job_id = params.get("job_id")
            if job_id:
                # Get application for this job
                candidate = self.db.query(Candidate).filter(Candidate.user_id == self.user_id).first()
                if candidate:
                    application = self.db.query(Application).filter(
                        and_(
                            Application.candidate_id == candidate.id,
                            Application.job_id == job_id
                        )
                    ).first()
                    
                    if application and application.status == ApplicationStatus.REJECTED:
                        # Get evaluation feedback
                        evaluation = self.db.query(Evaluation).filter(
                            Evaluation.application_id == application.id
                        ).first()
                        
                        if evaluation and evaluation.feedback_id:
                            from database.mongodb import get_mongo_db
                            mongo_db = get_mongo_db()
                            feedback_doc = mongo_db.feedback.find_one({"feedback_id": evaluation.feedback_id})
                            
                            if feedback_doc:
                                rejection_reasons = feedback_doc.get("rejection_reasons", [])
                                rejection_text = ". ".join(rejection_reasons) if rejection_reasons else "No specific feedback available."
                                
                                job = self.db.query(Job).filter(Job.id == job_id).first()
                                
                                # Prefer LLM-based interpretation when enabled
                                if USE_LLM_FEEDBACK:
                                    interpretation = interpret_rejection_llm(
                                        rejection_feedback=rejection_text,
                                        job_title=job.title if job else "Unknown",
                                        student_skills=student_skills,
                                    )
                                    if interpretation:
                                        data = interpretation
                                    else:
                                        data = self.student_engine.interpret_rejection(
                                            rejection_feedback=rejection_text,
                                            job_title=job.title if job else "Unknown",
                                            student_skills=student_skills,
                                        )
                                else:
                                    data = self.student_engine.interpret_rejection(
                                        rejection_feedback=rejection_text,
                                        job_title=job.title if job else "Unknown",
                                        student_skills=student_skills,
                                    )
                        else:
                            return "I couldn't find detailed rejection feedback for this application. The rejection may not have been processed yet.", None
                    else:
                        return f"You haven't been rejected from job {job_id}, or the application doesn't exist.", None
                else:
                    return "Could not find your candidate profile.", None
            else:
                return "Please specify which job rejection you'd like me to explain. For example: 'Why was I rejected from job 3?'", None
        
        # Generate response
        response = self.response_generator.generate(intent, data, params, student_skills)
        
        # Return response and data
        return response, data
