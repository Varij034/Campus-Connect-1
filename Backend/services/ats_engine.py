"""
ATS (Applicant Tracking System) Engine Module
Scores resumes based on job requirements and various criteria
"""

from typing import Dict, List, Tuple
from schemas.domain import ResumeData, JobRequirement
import re
from difflib import SequenceMatcher


class ATSEngine:
    """Core ATS scoring engine that evaluates resumes against job requirements"""
    
    def __init__(self):
        self.skill_similarity_threshold = 0.7
    
    def score_resume(self, resume_data: ResumeData, job_requirement: JobRequirement) -> Dict:
        """
        Main scoring function that evaluates resume against job requirements
        
        Args:
            resume_data: Parsed resume data
            job_requirement: Job requirements posted by recruiter
            
        Returns:
            Dictionary containing detailed scoring breakdown
        """
        # Calculate individual scores
        skill_score, matched_skills, missing_skills = self._calculate_skill_score(
            resume_data.skills, job_requirement.required_skills, job_requirement.preferred_skills
        )
        
        education_score = self._calculate_education_score(
            resume_data.education, job_requirement.education_level
        )
        
        experience_score = self._calculate_experience_score(
            resume_data.experience, resume_data.raw_text, job_requirement.years_of_experience
        )
        
        keyword_score, matched_keywords = self._calculate_keyword_score(
            resume_data.raw_text, job_requirement.keywords, job_requirement.job_description
        )
        
        format_score, format_issues = self._calculate_format_score(resume_data)
        
        # Calculate weighted total ATS score
        total_score = self._calculate_total_score(
            skill_score, education_score, experience_score, keyword_score, format_score,
            job_requirement
        )
        
        # Determine if passed
        passed = total_score >= job_requirement.minimum_ats_score
        
        return {
            'ats_score': round(total_score, 2),
            'passed': passed,
            'skill_match_score': round(skill_score, 2),
            'education_score': round(education_score, 2),
            'experience_score': round(experience_score, 2),
            'keyword_match_score': round(keyword_score, 2),
            'format_score': round(format_score, 2),
            'matched_skills': matched_skills,
            'missing_skills': missing_skills,
            'matched_keywords': matched_keywords,
            'format_issues': format_issues,
            'skill_score': skill_score,
            'education_score_raw': education_score,
            'experience_score_raw': experience_score,
            'keyword_score_raw': keyword_score,
            'format_score_raw': format_score
        }
    
    def _calculate_skill_score(self, resume_skills: List[str], required_skills: List[str], 
                               preferred_skills: List[str]) -> Tuple[float, List[str], List[str]]:
        """Calculate score based on skill matching"""
        if not required_skills and not preferred_skills:
            return 100.0, [], []
        
        resume_skills_lower = [skill.lower().strip() for skill in resume_skills]
        required_skills_lower = [skill.lower().strip() for skill in required_skills]
        preferred_skills_lower = [skill.lower().strip() for skill in preferred_skills]
        
        matched_skills = []
        missing_skills = []
        
        # Check required skills (critical - 70% weight)
        required_matches = 0
        for req_skill in required_skills_lower:
            matched = False
            for res_skill in resume_skills_lower:
                similarity = SequenceMatcher(None, req_skill, res_skill).ratio()
                if similarity >= self.skill_similarity_threshold or req_skill in res_skill or res_skill in req_skill:
                    matched_skills.append(req_skill.title())
                    matched = True
                    break
            if not matched:
                missing_skills.append(req_skill.title())
            else:
                required_matches += 1
        
        required_score = (required_matches / len(required_skills_lower) * 100) if required_skills_lower else 50
        
        # Check preferred skills (bonus - 30% weight)
        preferred_matches = 0
        for pref_skill in preferred_skills_lower:
            for res_skill in resume_skills_lower:
                similarity = SequenceMatcher(None, pref_skill, res_skill).ratio()
                if similarity >= self.skill_similarity_threshold or pref_skill in res_skill or res_skill in pref_skill:
                    if pref_skill.title() not in matched_skills:
                        matched_skills.append(pref_skill.title())
                    preferred_matches += 1
                    break
        
        preferred_score = (preferred_matches / len(preferred_skills_lower) * 100) if preferred_skills_lower else 50
        
        # Weighted combination: 70% required, 30% preferred
        if required_skills_lower and preferred_skills_lower:
            total_score = (required_score * 0.7) + (preferred_score * 0.3)
        elif required_skills_lower:
            total_score = required_score
        elif preferred_skills_lower:
            total_score = preferred_score * 0.5  # Preferred skills are bonus, not critical
        else:
            total_score = 100.0
        
        return total_score, matched_skills, missing_skills
    
    def _calculate_education_score(self, resume_education: List[Dict], required_education: str) -> float:
        """Calculate score based on education level matching"""
        if not required_education:
            return 100.0
        
        required_edu_lower = required_education.lower()
        resume_text = ' '.join([str(edu) for edu in resume_education]).lower()
        
        # Education hierarchy
        education_hierarchy = {
            'phd': 5, 'doctorate': 5,
            'master': 4, 'm.sc': 4, 'm.tech': 4, 'mba': 4, 'm.e': 4,
            'bachelor': 3, 'b.sc': 3, 'b.tech': 3, 'b.e': 3, 'b.a': 3,
            'diploma': 2, 'certificate': 1
        }
        
        required_level = 0
        for key, level in education_hierarchy.items():
            if key in required_edu_lower:
                required_level = level
                break
        
        if required_level == 0:
            return 100.0  # Can't determine, give benefit of doubt
        
        resume_level = 0
        for key, level in education_hierarchy.items():
            if key in resume_text:
                resume_level = max(resume_level, level)
        
        if resume_level >= required_level:
            return 100.0
        elif resume_level == required_level - 1:
            return 60.0  # One level below
        else:
            return 30.0  # Much below requirement
    
    def _calculate_experience_score(self, resume_experience: List[Dict], resume_text: str, 
                                    required_years: int) -> float:
        """Calculate score based on years of experience"""
        if not required_years or required_years == 0:
            return 100.0
        
        # Extract years from experience text
        year_pattern = r'(\d+\.?\d*)\s*(?:years?|yrs?|year)'
        matches = re.findall(year_pattern, resume_text, re.IGNORECASE)
        
        total_years = 0
        for match in matches:
            try:
                years = float(match)
                total_years = max(total_years, years)
            except:
                continue
        
        # Also check experience list
        for exp in resume_experience:
            if exp.get('duration'):
                duration_text = str(exp['duration'])
                matches = re.findall(year_pattern, duration_text, re.IGNORECASE)
                for match in matches:
                    try:
                        years = float(match)
                        total_years = max(total_years, years)
                    except:
                        continue
        
        if total_years >= required_years:
            return 100.0
        elif total_years >= required_years * 0.7:
            return 80.0
        elif total_years >= required_years * 0.5:
            return 60.0
        elif total_years > 0:
            return 40.0
        else:
            return 10.0  # No experience found
    
    def _calculate_keyword_score(self, resume_text: str, keywords: List[str], 
                                 job_description: str) -> Tuple[float, List[str]]:
        """Calculate score based on keyword matching"""
        resume_text_lower = resume_text.lower()
        matched_keywords = []
        
        # Check explicit keywords
        keyword_matches = 0
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in resume_text_lower:
                matched_keywords.append(keyword)
                keyword_matches += 1
        
        explicit_score = (keyword_matches / len(keywords) * 100) if keywords else 50
        
        # Extract keywords from job description if provided
        if job_description:
            # Simple keyword extraction (can be enhanced with NLP)
            job_keywords = re.findall(r'\b[a-z]{4,}\b', job_description.lower())
            common_words = {'the', 'and', 'or', 'but', 'with', 'from', 'this', 'that', 
                          'will', 'would', 'should', 'could', 'must', 'have', 'has', 
                          'been', 'were', 'was', 'they', 'their', 'them', 'these', 'those'}
            job_keywords = [kw for kw in job_keywords if kw not in common_words and len(kw) > 4]
            
            job_keyword_matches = 0
            unique_job_keywords = list(set(job_keywords))[:20]  # Top 20 unique keywords
            for keyword in unique_job_keywords:
                if keyword in resume_text_lower:
                    job_keyword_matches += 1
            
            job_desc_score = (job_keyword_matches / len(unique_job_keywords) * 100) if unique_job_keywords else 50
        else:
            job_desc_score = 50
        
        # Combine scores
        if keywords and job_description:
            total_score = (explicit_score * 0.6) + (job_desc_score * 0.4)
        elif keywords:
            total_score = explicit_score
        elif job_description:
            total_score = job_desc_score
        else:
            total_score = 100.0
        
        return total_score, matched_keywords
    
    def _calculate_format_score(self, resume_data: ResumeData) -> Tuple[float, List[str]]:
        """Calculate score based on resume format and structure"""
        score = 100.0
        issues = []
        
        # Check for essential sections
        if not resume_data.name:
            score -= 10
            issues.append("Missing name")
        
        if not resume_data.email:
            score -= 15
            issues.append("Missing email address")
        
        if not resume_data.phone:
            score -= 10
            issues.append("Missing phone number")
        
        if len(resume_data.skills) < 3:
            score -= 10
            issues.append("Insufficient skills listed (less than 3)")
        
        if not resume_data.education:
            score -= 15
            issues.append("Missing education information")
        
        if not resume_data.experience and len(resume_data.raw_text) < 500:
            score -= 10
            issues.append("Limited experience or content")
        
        # Check resume length (should be substantial but not too long)
        text_length = len(resume_data.raw_text)
        if text_length < 200:
            score -= 15
            issues.append("Resume too short (less than 200 characters)")
        elif text_length > 5000:
            score -= 5
            issues.append("Resume very long (may need trimming)")
        
        # Check for proper structure
        if not any(keyword in resume_data.raw_text.lower() for keyword in ['education', 'experience', 'skill']):
            score -= 10
            issues.append("Missing standard resume sections")
        
        return max(score, 0.0), issues
    
    def _calculate_total_score(self, skill_score: float, education_score: float, 
                               experience_score: float, keyword_score: float, 
                               format_score: float, job_requirement: JobRequirement) -> float:
        """Calculate weighted total ATS score"""
        # Weight distribution (can be adjusted based on job requirements)
        weights = {
            'skill': 0.40,      # Skills are most important
            'keyword': 0.25,    # Keyword matching is important for ATS
            'experience': 0.20, # Experience matters
            'education': 0.10,  # Education has some weight
            'format': 0.05      # Format is important but not critical
        }
        
        # Adjust weights if certain requirements are not specified
        if not job_requirement.required_skills and not job_requirement.preferred_skills:
            # If no skills specified, reduce skill weight
            weights['skill'] = 0.20
            weights['keyword'] += 0.10
            weights['experience'] += 0.10
        
        if not job_requirement.years_of_experience:
            weights['experience'] = 0.10
            weights['skill'] += 0.05
            weights['keyword'] += 0.05
        
        if not job_requirement.education_level:
            weights['education'] = 0.05
            weights['skill'] += 0.025
            weights['keyword'] += 0.025
        
        # Calculate weighted total
        total = (
            skill_score * weights['skill'] +
            keyword_score * weights['keyword'] +
            experience_score * weights['experience'] +
            education_score * weights['education'] +
            format_score * weights['format']
        )
        
        return total


