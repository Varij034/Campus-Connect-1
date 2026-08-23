"""
Feedback Generator Module
Generates detailed feedback and recommendations for rejected candidates
"""

from typing import Dict, List
from schemas.domain import JobRequirement


class FeedbackGenerator:
    """Generates comprehensive feedback for rejected candidates"""
    
    def __init__(self):
        pass
    
    def generate_feedback(self, ats_result: Dict, resume_data: Dict, 
                         job_requirement: JobRequirement) -> Dict:
        """
        Generate detailed feedback for rejected candidates
        
        Args:
            ats_result: Results from ATS scoring
            resume_data: Parsed resume data
            job_requirement: Job requirements
            
        Returns:
            Dictionary containing comprehensive feedback
        """
        if ats_result['passed']:
            return None  # No feedback needed if passed
        
        rejection_reasons = []
        resume_strengths = []
        resume_weaknesses = []
        improvement_recommendations = []
        mistake_highlights = []
        
        # Analyze skill gaps
        if ats_result['skill_match_score'] < 70:
            rejection_reasons.append(
                f"Insufficient skill match ({ats_result['skill_match_score']:.1f}%). "
                f"Missing {len(ats_result['missing_skills'])} required skills."
            )
            if ats_result['missing_skills']:
                improvement_recommendations.append(
                    f"Add these required skills to your resume: {', '.join(ats_result['missing_skills'][:5])}"
                )
                mistake_highlights.append(
                    f"Critical missing skills: {', '.join(ats_result['missing_skills'])}"
                )
        
        # Analyze education gaps
        if ats_result['education_score'] < 60:
            rejection_reasons.append(
                f"Education requirement not fully met ({ats_result['education_score']:.1f}%). "
                f"Required: {job_requirement.education_level or 'Not specified'}"
            )
            if job_requirement.education_level:
                improvement_recommendations.append(
                    f"Consider highlighting your educational qualifications more prominently, "
                    f"especially if you have {job_requirement.education_level} or equivalent"
                )
        
        # Analyze experience gaps
        if ats_result['experience_score'] < 60:
            rejection_reasons.append(
                f"Insufficient experience ({ats_result['experience_score']:.1f}%). "
                f"Required: {job_requirement.years_of_experience or 'Not specified'} years"
            )
            if job_requirement.years_of_experience:
                improvement_recommendations.append(
                    f"Include more detailed experience descriptions. Highlight relevant projects, "
                    f"internships, or work experience that demonstrates {job_requirement.years_of_experience}+ years of relevant work"
                )
            mistake_highlights.append(
                "Experience section needs more detail or better formatting"
            )
        
        # Analyze keyword matching
        if ats_result['keyword_match_score'] < 60:
            rejection_reasons.append(
                f"Low keyword relevance ({ats_result['keyword_match_score']:.1f}%). "
                "Resume may not align well with job description keywords."
            )
            improvement_recommendations.append(
                "Review the job description and incorporate relevant keywords naturally into your resume. "
                "Focus on technical terms and domain-specific vocabulary used in the job posting."
            )
        
        # Analyze format issues
        if ats_result['format_score'] < 80:
            rejection_reasons.append(
                f"Resume format needs improvement ({ats_result['format_score']:.1f}%)."
            )
            if ats_result['format_issues']:
                for issue in ats_result['format_issues'][:3]:
                    mistake_highlights.append(issue)
                    if "Missing" in issue:
                        improvement_recommendations.append(f"Ensure your resume includes: {issue}")
        
        # Identify strengths
        if ats_result['skill_match_score'] >= 50:
            matched_count = len(ats_result['matched_skills'])
            resume_strengths.append(
                f"Good skill alignment: {matched_count} matching skills found"
            )
        
        if ats_result['matched_skills']:
            resume_strengths.append(
                f"Strong technical skills: {', '.join(ats_result['matched_skills'][:5])}"
            )
        
        if len(resume_data.get('experience', [])) >= 2:
            resume_strengths.append("Good experience history with multiple positions")
        
        if len(resume_data.get('certifications', [])) > 0:
            resume_strengths.append("Has professional certifications")
        
        if len(resume_data.get('projects', [])) > 0:
            resume_strengths.append("Has project portfolio")
        
        # Identify weaknesses
        if not resume_data.get('email'):
            resume_weaknesses.append("Missing contact email")
        
        if len(resume_data.get('skills', [])) < 5:
            resume_weaknesses.append("Limited skills listed - expand your skills section")
        
        if not resume_data.get('experience') and not resume_data.get('projects'):
            resume_weaknesses.append("No work experience or projects highlighted")
        
        # General recommendations based on score gaps
        score_gap = job_requirement.minimum_ats_score - ats_result['ats_score']
        
        if score_gap > 20:
            improvement_recommendations.append(
                "Significant improvement needed. Consider: "
                "1) Adding more relevant work experience, "
                "2) Highlighting required skills more prominently, "
                "3) Getting feedback from industry professionals"
            )
        elif score_gap > 10:
            improvement_recommendations.append(
                "Minor improvements could help. Focus on: "
                "1) Enhancing skill descriptions, "
                "2) Better keyword optimization, "
                "3) Improving resume format and structure"
            )
        
        # Specific recommendations for each low-scoring area
        if ats_result['skill_match_score'] < ats_result['ats_score']:
            improvement_recommendations.append(
                "Priority: Add missing required skills. If you have these skills but haven't listed them, "
                "make sure to include them in your skills section and mention them in your experience descriptions."
            )
        
        if ats_result['format_score'] < 90:
            improvement_recommendations.append(
                "Improve resume formatting: Ensure all sections are clearly labeled, "
                "use consistent formatting, and make sure contact information is easily visible."
            )
        
        # Critical skills missing
        missing_critical_skills = ats_result.get('missing_skills', [])[:3]
        
        return {
            'rejection_reasons': rejection_reasons if rejection_reasons else [
                f"ATS score ({ats_result['ats_score']:.1f}%) below minimum threshold "
                f"({job_requirement.minimum_ats_score}%)"
            ],
            'missing_critical_skills': missing_critical_skills,
            'resume_strengths': resume_strengths if resume_strengths else [
                "Resume has basic structure in place"
            ],
            'resume_weaknesses': resume_weaknesses if resume_weaknesses else [
                "Overall resume needs enhancement to meet job requirements"
            ],
            'improvement_recommendations': improvement_recommendations if improvement_recommendations else [
                "Review job requirements carefully and tailor your resume to match them better",
                "Ensure all required skills are mentioned in your resume",
                "Add more detail to experience and education sections"
            ],
            'format_issues': ats_result.get('format_issues', []),
            'mistake_highlights': mistake_highlights if mistake_highlights else [
                f"ATS score {ats_result['ats_score']:.1f}% is {score_gap:.1f}% below required threshold"
            ]
        }

