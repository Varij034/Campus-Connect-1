"""
CampusConnect AI Engine - Student Perspective
Production-ready MVP for college placement platform

This engine helps students:
- Discover jobs using natural language
- Get skill gap analysis
- Receive resume feedback
- Understand rejection reasons
"""

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import pipeline
import numpy as np
import re
from typing import List, Dict, Any, Optional
import json


class StudentJobMatchingEngine:
    """
    Handles natural language job search and determines
    Direct Apply vs Recommended status based on skill matching.
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the matching engine with a semantic model.
        
        Args:
            model_name: Sentence transformer model for embeddings
        """
        print("Loading AI Job Matching Engine...")
        self.model = SentenceTransformer(model_name)
        print("✓ Matching Engine Ready!")
    
    def search_jobs(self, 
                   student_query: str, 
                   jobs: List[Dict[str, Any]], 
                   student_skills: List[str],
                   top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search jobs using natural language query and determine application status.
        
        Args:
            student_query: Natural language prompt (e.g., "I want backend role with Python")
            jobs: List of job dictionaries with 'id', 'title', 'description', 'requirements'
            student_skills: List of student's skills (e.g., ["Python", "SQL", "Docker"])
            top_k: Number of top matches to return
            
        Returns:
            List of job matches with match_score, application_status, missing_skills, message
        """
        if not jobs:
            return []
        
        # Extract specific skills/technologies mentioned in the query
        query_skills = self._extract_skills_from_query(student_query)
        
        # Filter jobs to only include those that mention the required skills
        if query_skills:
            filtered_jobs = []
            query_skills_lower = [skill.lower() for skill in query_skills]
            for job in jobs:
                job_text = f"{job.get('title', '')} {job.get('description', '')} {job.get('requirements', '')}".lower()
                # Check if job contains any of the required skills (using word boundaries for exact matches)
                job_contains_skill = False
                for skill_lower in query_skills_lower:
                    # Use word boundaries to avoid partial matches (e.g., "javascript" matching "java")
                    pattern = r'\b' + re.escape(skill_lower) + r'\b'
                    if re.search(pattern, job_text):
                        job_contains_skill = True
                        break
                if job_contains_skill:
                    filtered_jobs.append(job)
            jobs = filtered_jobs
        
        if not jobs:
            return []
        
        # Encode student query for semantic search
        query_embedding = self.model.encode(student_query, normalize_embeddings=True)
        
        # Prepare job texts for encoding
        job_texts = []
        for job in jobs:
            job_text = f"{job.get('title', '')} {job.get('description', '')} {job.get('requirements', '')}"
            job_texts.append(job_text)
        
        # Encode all jobs
        job_embeddings = self.model.encode(job_texts, normalize_embeddings=True)
        
        # Calculate semantic similarity
        similarities = cosine_similarity([query_embedding], job_embeddings)[0]
        
        # Get top matches
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            job = jobs[idx]
            match_score = float(similarities[idx]) * 100
            
            # Extract required skills from job requirements
            required_skills = self._extract_skills(job.get('requirements', ''))
            
            # Determine application status and missing skills
            status_info = self._determine_application_status(
                student_skills, 
                required_skills,
                match_score
            )
            
            result = {
                "job_id": job.get('id', idx),
                "title": job.get('title', 'Unknown'),
                "company": job.get('company', 'Unknown'),
                "location": job.get('location', 'Not specified'),
                "salary": job.get('salary', 'Not specified'),
                "match_score": round(match_score, 2),
                "application_status": status_info['status'],
                "missing_skills": status_info['missing_skills'],
                "message": status_info['message'],
                "required_skills": required_skills,
                "matched_skills": status_info['matched_skills']
            }
            results.append(result)
        
        return results
    
    def _extract_skills_from_query(self, query: str) -> List[str]:
        """
        Extract specific skills/technologies mentioned in the user's query.
        This helps filter jobs to only show those that actually require the mentioned skills.
        """
        if not query:
            return []
        
        # Common tech skills to look for in queries
        skill_keywords = [
            'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'Go', 'Rust',
            'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring Boot',
            'SQL', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis',
            'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP',
            'REST API', 'GraphQL', 'Microservices',
            'TensorFlow', 'PyTorch', 'Machine Learning', 'Deep Learning',
            'Git', 'CI/CD', 'Linux', 'DevOps',
            'Pandas', 'NumPy', 'Data Analysis', 'Excel',
            'Backend', 'Frontend', 'Full Stack', 'Full-Stack'
        ]
        
        found_skills = []
        query_lower = query.lower()
        
        # Check for each skill keyword
        for skill in skill_keywords:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, query_lower):
                found_skills.append(skill)
        
        return found_skills
    
    def _extract_skills(self, requirements_text: str) -> List[str]:
        """
        Extract skills from job requirements text.
        Uses simple keyword extraction for MVP.
        """
        if not requirements_text:
            return []
        
        # Common tech skills to look for
        skill_keywords = [
            'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'Go', 'Rust',
            'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring Boot',
            'SQL', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis',
            'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP',
            'REST API', 'GraphQL', 'Microservices',
            'TensorFlow', 'PyTorch', 'Machine Learning', 'Deep Learning',
            'Git', 'CI/CD', 'Linux', 'DevOps',
            'Pandas', 'NumPy', 'Data Analysis', 'Excel'
        ]
        
        found_skills = []
        requirements_lower = requirements_text.lower()
        
        for skill in skill_keywords:
            if skill.lower() in requirements_lower:
                found_skills.append(skill)
        
        # Also extract skills mentioned explicitly (comma-separated)
        # Look for patterns like "Python, SQL, Docker"
        comma_separated = re.findall(r'\b([A-Z][a-zA-Z\s]+(?:API|SQL|ML|AI|CI/CD)?)\b', requirements_text)
        found_skills.extend([s.strip() for s in comma_separated if len(s.strip()) > 2])
        
        # Remove duplicates and normalize
        unique_skills = list(set([s.strip() for s in found_skills]))
        return unique_skills[:15]  # Limit to top 15 skills
    
    def _determine_application_status(self, 
                                     student_skills: List[str], 
                                     required_skills: List[str],
                                     match_score: float) -> Dict[str, Any]:
        """
        Determine if job is Direct Apply Eligible or Recommended.
        Returns status, missing skills, and motivational message.
        """
        if not required_skills:
            return {
                'status': 'Recommended',
                'missing_skills': [],
                'matched_skills': [],
                'message': 'This job matches your search query!'
            }
        
        # Normalize skills for comparison
        student_skills_lower = [s.lower().strip() for s in student_skills]
        required_skills_lower = [r.lower().strip() for r in required_skills]
        
        # Find matched and missing skills
        matched_skills = [r for r in required_skills if r.lower() in student_skills_lower]
        missing_skills = [r for r in required_skills if r.lower() not in student_skills_lower]
        
        # Calculate skill match percentage
        skill_match_ratio = len(matched_skills) / len(required_skills) if required_skills else 0
        
        # Determine status
        if skill_match_ratio >= 0.85:  # 85%+ skills match = Direct Apply Eligible (with consent)
            status = 'Direct Apply Eligible'
            message = f"Perfect match! You have {len(matched_skills)}/{len(required_skills)} required skills. This job is ready for direct application (with your consent)."
        elif skill_match_ratio >= 0.5:  # 50-85% = Recommended with encouragement
            status = 'Recommended'
            message = f"You're close! You have {len(matched_skills)}/{len(required_skills)} required skills. Learning {', '.join(missing_skills[:3])} could significantly improve your chances. Would you like to apply anyway?"
        else:  # <50% = Still recommended but with learning focus
            status = 'Recommended'
            message = f"This role requires skills like {', '.join(missing_skills[:3])}. Consider building these skills first, or apply to gain experience!"
        
        return {
            'status': status,
            'missing_skills': missing_skills,
            'matched_skills': matched_skills,
            'message': message
        }


class SkillGapAnalyzer:
    """
    Analyzes skill gaps between student and job requirements.
    Provides deterministic, explainable skill gap detection with learning paths.
    """
    
    def __init__(self):
        """Initialize skill gap analyzer with certification and learning path mappings."""
        self.certification_map = {
            'python': ['Python Professional Certification (PCAP)', 'Google IT Automation with Python'],
            'java': ['Oracle Certified Java Programmer (OCJP)', 'Java Programming Masterclass'],
            'javascript': ['JavaScript Algorithms and Data Structures (freeCodeCamp)', 'Modern JavaScript (Udemy)'],
            'react': ['React - The Complete Guide (Udemy)', 'Meta React Developer Certificate'],
            'node.js': ['Node.js - The Complete Guide', 'AWS Certified Developer'],
            'docker': ['Docker Certified Associate (DCA)', 'Docker & Kubernetes: The Practical Guide'],
            'kubernetes': ['Certified Kubernetes Administrator (CKA)', 'Kubernetes for the Absolute Beginners'],
            'aws': ['AWS Certified Solutions Architect', 'AWS Cloud Practitioner'],
            'sql': ['SQL for Data Science (Coursera)', 'Oracle Database SQL Certified Associate'],
            'machine learning': ['Machine Learning (Coursera - Andrew Ng)', 'TensorFlow Developer Certificate'],
            'rest api': ['REST API Design (Udemy)', 'API Design and Fundamentals of Google Cloud'],
            'git': ['Git & GitHub - The Practical Guide', 'Version Control with Git (Coursera)'],
            'postgresql': ['PostgreSQL for Everybody (Coursera)', 'Complete PostgreSQL Bootcamp'],
            'mongodb': ['MongoDB Certified Developer', 'The Complete Developers Guide to MongoDB'],
            'devops': ['DevOps Engineer (Udacity)', 'Google Cloud Professional DevOps Engineer'],
            'pandas': ['Data Analysis with Python (freeCodeCamp)', 'Pandas for Data Analysis (Udemy)']
        }
        
        self.learning_paths = {
            'backend': ['REST API', 'Database Design', 'System Design', 'API Security'],
            'frontend': ['React/Vue/Angular', 'State Management', 'Responsive Design', 'Web Performance'],
            'fullstack': ['Backend Fundamentals', 'Frontend Fundamentals', 'Database', 'Deployment'],
            'devops': ['Docker', 'Kubernetes', 'CI/CD', 'Cloud Platforms'],
            'data science': ['Python', 'Pandas', 'Machine Learning', 'Data Visualization'],
            'ml engineer': ['Python', 'TensorFlow/PyTorch', 'Deep Learning', 'MLOps']
        }
    
    def analyze_skill_gap(self, 
                          student_skills: List[str], 
                          job_skills: List[str],
                          job_role: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze skill gap between student and job requirements.
        
        Args:
            student_skills: List of student's skills
            job_skills: List of required job skills
            job_role: Optional role type (backend, frontend, etc.) for learning path
            
        Returns:
            Dictionary with missing_skills, matched_skills, recommendations, learning_path
        """
        # Normalize skills
        student_skills_normalized = [s.lower().strip() for s in student_skills]
        job_skills_normalized = [j.lower().strip() for j in job_skills]
        
        # Find missing and matched skills
        matched_skills = []
        missing_skills = []
        
        for job_skill in job_skills:
            job_skill_lower = job_skill.lower().strip()
            # Check for exact match or partial match
            is_matched = any(
                job_skill_lower in student_skill or student_skill in job_skill_lower
                for student_skill in student_skills_normalized
            )
            
            if is_matched:
                matched_skills.append(job_skill)
            else:
                missing_skills.append(job_skill)
        
        # Calculate metrics
        total_skills = len(job_skills)
        match_percentage = (len(matched_skills) / total_skills * 100) if total_skills > 0 else 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(missing_skills)
        
        # Get learning path if role is specified
        learning_path = None
        if job_role:
            learning_path = self._get_learning_path(job_role.lower())
        
        return {
            "missing_skills": missing_skills,
            "matched_skills": matched_skills,
            "match_percentage": round(match_percentage, 2),
            "total_required_skills": total_skills,
            "student_skill_count": len(student_skills),
            "recommendations": recommendations,
            "learning_path": learning_path,
            "explanation": self._generate_explanation(matched_skills, missing_skills, match_percentage)
        }
    
    def _generate_recommendations(self, missing_skills: List[str]) -> List[Dict[str, str]]:
        """Generate certification and learning recommendations for missing skills."""
        recommendations = []
        
        for skill in missing_skills[:10]:  # Limit to top 10
            skill_lower = skill.lower()
            
            # Find matching certifications
            certs = []
            for key, value in self.certification_map.items():
                if key in skill_lower or skill_lower in key:
                    certs = value
                    break
            
            if not certs:
                certs = [f"{skill} Certification Course", f"Learn {skill} - Online Course"]
            
            recommendations.append({
                "skill": skill,
                "recommended_certifications": certs,
                "estimated_time": "2-4 weeks" if len(skill) < 10 else "4-8 weeks",
                "priority": "High" if len(missing_skills) <= 3 else "Medium"
            })
        
        return recommendations
    
    def _get_learning_path(self, role: str) -> Optional[List[str]]:
        """Get learning path for a specific role."""
        for key, path in self.learning_paths.items():
            if key in role:
                return path
        return None
    
    def _generate_explanation(self, matched: List[str], missing: List[str], percentage: float) -> str:
        """Generate human-readable explanation of skill gap."""
        if percentage >= 85:
            return f"Excellent! You have {len(matched)} out of {len(matched) + len(missing)} required skills. You're well-prepared for this role."
        elif percentage >= 50:
            return f"You have {len(matched)} matching skills. Focus on learning {', '.join(missing[:3])} to strengthen your profile."
        else:
            return f"You have {len(matched)} matching skills. Consider building foundational skills: {', '.join(missing[:5])} before applying."


class ResumeFeedbackEngine:
    """
    Provides actionable resume feedback and ATS optimization suggestions.
    """
    
    def __init__(self):
        """Initialize resume feedback engine."""
        print("Loading Resume Feedback Engine...")
        # Use a lightweight text generation model for MVP
        try:
            self.generator = pipeline(
                "text-generation",
                model="gpt2",  # Lightweight for MVP
                max_length=200,
                device=-1  # CPU
            )
        except Exception as e:
            print(f"Note: Using fallback feedback generation (model loading issue: {e})")
            self.generator = None
        print("✓ Resume Feedback Engine Ready!")
    
    def generate_feedback(self,
                         resume_text: str,
                         job_description: str,
                         job_requirements: str,
                         skill_gap_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive resume feedback for ATS optimization.
        
        Args:
            resume_text: Student's resume text
            job_description: Full job description
            job_requirements: Job requirements text
            skill_gap_output: Output from SkillGapAnalyzer
            
        Returns:
            Dictionary with feedback, keyword_suggestions, ats_score, improvements
        """
        # Extract keywords from job description
        job_keywords = self._extract_keywords(job_description + " " + job_requirements)
        resume_keywords = self._extract_keywords(resume_text)
        
        # Find missing keywords
        missing_keywords = [kw for kw in job_keywords if kw.lower() not in resume_text.lower()]
        
        # Calculate ATS compatibility score
        ats_score = self._calculate_ats_score(resume_text, job_keywords, missing_keywords)
        
        # Generate feedback sections
        feedback_sections = {
            "strengths": self._identify_strengths(resume_text, job_keywords),
            "weaknesses": self._identify_weaknesses(resume_text, missing_keywords, skill_gap_output),
            "keyword_suggestions": missing_keywords[:15],  # Top 15 missing keywords
            "missing_skills_in_resume": skill_gap_output.get('missing_skills', [])[:10],
            "ats_score": ats_score,
            "actionable_improvements": self._generate_actionable_improvements(
                missing_keywords, 
                skill_gap_output
            )
        }
        
        # Generate overall feedback message
        overall_feedback = self._generate_overall_feedback(feedback_sections, ats_score)
        
        return {
            "overall_feedback": overall_feedback,
            "ats_score": ats_score,
            "ats_interpretation": self._interpret_ats_score(ats_score),
            **feedback_sections
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text."""
        if not text:
            return []
        
        # Common technical keywords
        tech_keywords = [
            'Python', 'Java', 'JavaScript', 'TypeScript', 'React', 'Node.js',
            'Django', 'Flask', 'Spring Boot', 'SQL', 'PostgreSQL', 'MongoDB',
            'Docker', 'Kubernetes', 'AWS', 'Azure', 'REST API', 'GraphQL',
            'Machine Learning', 'TensorFlow', 'PyTorch', 'Git', 'CI/CD',
            'Microservices', 'Agile', 'Scrum', 'DevOps', 'Data Analysis',
            'Pandas', 'NumPy', 'Excel', 'Tableau', 'Power BI'
        ]
        
        found_keywords = []
        text_lower = text.lower()
        
        for keyword in tech_keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        
        # Also extract capitalized terms (likely important)
        capitalized = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
        found_keywords.extend([c.strip() for c in capitalized if len(c.strip()) > 2])
        
        return list(set(found_keywords))
    
    def _calculate_ats_score(self, resume_text: str, job_keywords: List[str], missing_keywords: List[str]) -> float:
        """Calculate ATS compatibility score (0-100)."""
        if not job_keywords:
            return 75.0  # Default score if no keywords
        
        matched_keywords = len(job_keywords) - len(missing_keywords)
        score = (matched_keywords / len(job_keywords)) * 100
        
        # Bonus for resume structure
        if 'experience' in resume_text.lower() or 'education' in resume_text.lower():
            score += 5
        if 'projects' in resume_text.lower() or 'skills' in resume_text.lower():
            score += 5
        
        return min(100.0, max(0.0, round(score, 2)))
    
    def _identify_strengths(self, resume_text: str, job_keywords: List[str]) -> List[str]:
        """Identify strengths in the resume."""
        strengths = []
        resume_lower = resume_text.lower()
        
        matched = [kw for kw in job_keywords if kw.lower() in resume_lower]
        if matched:
            strengths.append(f"Resume includes relevant keywords: {', '.join(matched[:5])}")
        
        if 'project' in resume_lower or 'experience' in resume_lower:
            strengths.append("Resume includes project/experience details")
        
        if any(word in resume_lower for word in ['github', 'portfolio', 'linkedin']):
            strengths.append("Includes links to portfolio/GitHub")
        
        return strengths if strengths else ["Resume has basic structure"]
    
    def _identify_weaknesses(self, resume_text: str, missing_keywords: List[str], skill_gap: Dict[str, Any]) -> List[str]:
        """Identify weaknesses in the resume."""
        weaknesses = []
        
        if missing_keywords:
            weaknesses.append(f"Missing important keywords: {', '.join(missing_keywords[:5])}")
        
        missing_skills = skill_gap.get('missing_skills', [])
        if missing_skills:
            weaknesses.append(f"Missing required skills in resume: {', '.join(missing_skills[:5])}")
        
        if len(resume_text) < 200:
            weaknesses.append("Resume is too short - add more details about projects and experience")
        
        if 'quantify' not in resume_text.lower() and 'achievement' not in resume_text.lower():
            weaknesses.append("Consider adding quantified achievements and metrics")
        
        return weaknesses
    
    def _generate_actionable_improvements(self, missing_keywords: List[str], skill_gap: Dict[str, Any]) -> List[str]:
        """Generate actionable improvement suggestions."""
        improvements = []
        
        if missing_keywords:
            improvements.append(f"Add these keywords naturally: {', '.join(missing_keywords[:5])}")
        
        missing_skills = skill_gap.get('missing_skills', [])
        if missing_skills:
            improvements.append(f"Highlight or add projects demonstrating: {', '.join(missing_skills[:3])}")
        
        improvements.append("Use action verbs: 'Developed', 'Implemented', 'Optimized', 'Designed'")
        improvements.append("Quantify achievements: 'Improved performance by 30%', 'Handled 1000+ requests/day'")
        improvements.append("Include relevant certifications and courses in Education section")
        
        return improvements
    
    def _generate_overall_feedback(self, feedback_sections: Dict[str, Any], ats_score: float) -> str:
        """Generate overall feedback message."""
        if ats_score >= 80:
            return f"Your resume is well-optimized for ATS (Score: {ats_score}/100). It includes most relevant keywords and skills. Minor improvements could make it even stronger."
        elif ats_score >= 60:
            return f"Your resume has good potential (Score: {ats_score}/100). Adding missing keywords and skills will significantly improve ATS compatibility and your chances."
        else:
            return f"Your resume needs optimization (Score: {ats_score}/100). Focus on adding missing keywords, highlighting relevant skills, and quantifying achievements to improve ATS compatibility."
    
    def _interpret_ats_score(self, score: float) -> str:
        """Interpret ATS score in human-readable terms."""
        if score >= 80:
            return "Excellent - High ATS compatibility"
        elif score >= 60:
            return "Good - Moderate ATS compatibility"
        elif score >= 40:
            return "Fair - Needs improvement for better ATS compatibility"
        else:
            return "Poor - Significant optimization needed"


class RejectionFeedbackInterpreter:
    """
    Translates company-side rejection feedback into student-friendly,
    motivating explanations with actionable improvement suggestions.
    
    NOTE: This class takes rejection feedback as INPUT from the company-side AI.
    It does NOT generate rejection decisions - it only interprets existing feedback.
    """
    
    def __init__(self):
        """Initialize rejection feedback interpreter."""
        self.rejection_patterns = {
            'skill_mismatch': ['skills', 'qualification', 'technical', 'experience'],
            'test_performance': ['test', 'assessment', 'coding', 'aptitude', 'score'],
            'resume_issues': ['resume', 'cv', 'profile', 'documentation'],
            'communication': ['communication', 'interview', 'soft skills', 'presentation'],
            'cultural_fit': ['culture', 'fit', 'values', 'team'],
            'overqualified': ['overqualified', 'overqualified', 'senior'],
            'underqualified': ['underqualified', 'entry', 'junior', 'experience required']
        }
        
        self.improvement_suggestions = {
            'skill_mismatch': [
                "Focus on building the missing technical skills through projects",
                "Take relevant online courses or certifications",
                "Contribute to open-source projects to demonstrate skills",
                "Build a portfolio project showcasing the required skills"
            ],
            'test_performance': [
                "Practice coding problems on platforms like LeetCode, HackerRank",
                "Take mock assessments to improve test-taking skills",
                "Review fundamental concepts and data structures",
                "Time yourself while solving problems to improve speed"
            ],
            'resume_issues': [
                "Optimize your resume with relevant keywords",
                "Quantify achievements and impact in your projects",
                "Highlight skills that match job requirements",
                "Get your resume reviewed by mentors or career services"
            ],
            'communication': [
                "Practice mock interviews with peers or mentors",
                "Join public speaking clubs or toastmasters",
                "Record yourself answering common interview questions",
                "Work on explaining technical concepts clearly"
            ],
            'cultural_fit': [
                "Research the company culture before applying",
                "Align your application with company values",
                "Showcase relevant experiences in your cover letter",
                "Network with current employees to understand culture"
            ]
        }
    
    def interpret_rejection(self, 
                           rejection_feedback: str,
                           job_title: str,
                           student_skills: List[str]) -> Dict[str, Any]:
        """
        Interpret company rejection feedback and provide student-friendly explanation.
        
        IMPORTANT: This method takes rejection_feedback as INPUT from the company-side AI.
        The company AI handles the rejection decision - this engine only interprets and
        translates that feedback into student-friendly explanations.
        
        Args:
            rejection_feedback: Raw rejection feedback from company-side AI (REQUIRED INPUT)
            job_title: Title of the job applied for
            student_skills: List of student's current skills
            
        Returns:
            Dictionary with explanation, category, suggestions, motivational_message
        """
        if not rejection_feedback:
            return self._generate_default_feedback(job_title)
        
        # Categorize rejection reason
        category = self._categorize_rejection(rejection_feedback)
        
        # Generate student-friendly explanation
        explanation = self._generate_explanation(rejection_feedback, category, job_title)
        
        # Get improvement suggestions
        suggestions = self.improvement_suggestions.get(category, [
            "Continue building relevant skills",
            "Apply to more positions to gain experience",
            "Network with professionals in the field",
            "Seek feedback from mentors"
        ])
        
        # Generate motivational message
        motivational_message = self._generate_motivational_message(category, job_title)
        
        return {
            "rejection_category": category,
            "student_friendly_explanation": explanation,
            "improvement_suggestions": suggestions,
            "motivational_message": motivational_message,
            "next_steps": self._generate_next_steps(category, student_skills),
            "raw_feedback": rejection_feedback  # Keep original for reference
        }
    
    def _categorize_rejection(self, feedback: str) -> str:
        """Categorize rejection feedback into predefined categories."""
        feedback_lower = feedback.lower()
        
        category_scores = {}
        for category, keywords in self.rejection_patterns.items():
            score = sum(1 for keyword in keywords if keyword in feedback_lower)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        return 'general'
    
    def _generate_explanation(self, feedback: str, category: str, job_title: str) -> str:
        """Generate student-friendly explanation of rejection."""
        explanations = {
            'skill_mismatch': f"While you have strong foundational skills, this {job_title} role requires some additional technical competencies that weren't fully demonstrated in your application.",
            'test_performance': f"Your application showed promise, but the technical assessment results didn't meet the threshold for this {job_title} position. This is common and can be improved with practice.",
            'resume_issues': f"Your resume could be better optimized to highlight your relevant skills and experiences for the {job_title} role. ATS systems may have missed key qualifications.",
            'communication': f"Your technical skills are solid, but there were concerns about communication or presentation during the interview process for this {job_title} role.",
            'cultural_fit': f"While you're qualified, the company felt there might be a better alignment with their team culture for this {job_title} position.",
            'overqualified': f"You're highly qualified for this {job_title} role, but the company is looking for someone at a different experience level.",
            'underqualified': f"This {job_title} role requires more experience or specific skills than currently demonstrated. Consider entry-level positions or building those skills first.",
            'general': f"Unfortunately, you weren't selected for this {job_title} position. This is a competitive process, and many factors contribute to hiring decisions."
        }
        
        return explanations.get(category, explanations['general'])
    
    def _generate_motivational_message(self, category: str, job_title: str) -> str:
        """Generate motivating message to encourage the student."""
        messages = {
            'skill_mismatch': "Don't be discouraged! Every rejection is a learning opportunity. Focus on building the missing skills, and you'll be ready for the next opportunity.",
            'test_performance': "Technical assessments can be challenging, but they're also learnable. With consistent practice, you'll see improvement. Keep going!",
            'resume_issues': "Your resume is your first impression. With some optimization, you can significantly improve your chances. You've got this!",
            'communication': "Communication is a skill that improves with practice. Keep interviewing, and you'll become more confident. Your technical skills are valuable!",
            'cultural_fit': "Not every company is the right fit, and that's okay! The right opportunity that matches your values and work style is out there.",
            'general': "Rejection is part of the journey. Every successful professional has faced rejections. Learn from this, improve, and keep applying. Your breakthrough is coming!"
        }
        
        return messages.get(category, messages['general'])
    
    def _generate_next_steps(self, category: str, student_skills: List[str]) -> List[str]:
        """Generate actionable next steps based on rejection category."""
        next_steps = []
        
        if category == 'skill_mismatch':
            next_steps = [
                "Identify 2-3 missing skills and create learning projects",
                "Apply to similar roles after building those skills",
                "Update your portfolio with new projects"
            ]
        elif category == 'test_performance':
            next_steps = [
                "Dedicate 30 minutes daily to coding practice",
                "Take 2-3 mock assessments this week",
                "Review data structures and algorithms fundamentals"
            ]
        elif category == 'resume_issues':
            next_steps = [
                "Get your resume reviewed and optimized",
                "Update resume with quantified achievements",
                "Apply to 5 new positions with the improved resume"
            ]
        else:
            next_steps = [
                "Continue applying to relevant positions",
                "Network with professionals in your field",
                "Keep building your skills and portfolio"
            ]
        
        return next_steps
    
    def _generate_default_feedback(self, job_title: str) -> Dict[str, Any]:
        """Generate default feedback when no specific rejection reason is provided."""
        return {
            "rejection_category": "general",
            "student_friendly_explanation": f"Unfortunately, you weren't selected for this {job_title} position. The hiring process is competitive, and many qualified candidates apply.",
            "improvement_suggestions": [
                "Continue building relevant technical skills",
                "Optimize your resume for ATS systems",
                "Practice coding and technical assessments",
                "Network and seek mentorship opportunities"
            ],
            "motivational_message": "Every rejection brings you closer to the right opportunity. Stay persistent, keep learning, and your breakthrough will come!",
            "next_steps": [
                "Apply to 3-5 similar positions this week",
                "Update your portfolio with recent projects",
                "Seek feedback from mentors or career advisors"
            ],
            "raw_feedback": "No specific feedback provided"
        }


# ============ MAIN ENGINE CLASS (Orchestrator) ============

class CampusConnectStudentEngine:
    """
    Main orchestrator class that combines all student-facing AI capabilities.
    This is the primary interface for the student perspective.
    
    Core Capabilities:
    1. Natural Language Job Search - Students can search with prompts like "I want backend job with Python"
    2. Auto-Apply Detection - Jobs matching student skills are marked "Direct Apply Eligible" (requires consent)
    3. Skill Gap Recommendations - Jobs with partial matches are recommended with missing skills and motivating messages
    4. Rejection Explanation - Interprets company-side rejection feedback into student-friendly explanations
    5. Resume Optimization - Provides ATS-compatible resume feedback based on job requirements and student skills
    """
    
    def __init__(self):
        """Initialize all engine components."""
        print("\n" + "="*50)
        print("🚀 Initializing CampusConnect Student AI Engine")
        print("="*50)
        
        self.job_matcher = StudentJobMatchingEngine()
        self.skill_analyzer = SkillGapAnalyzer()
        self.resume_engine = ResumeFeedbackEngine()
        self.rejection_interpreter = RejectionFeedbackInterpreter()
        
        print("\n✅ All engines loaded successfully!")
        print("="*50 + "\n")
    
    def search_jobs(self, 
                    student_query: str,
                    jobs: List[Dict[str, Any]],
                    student_skills: List[str],
                    top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search jobs using natural language query.
        
        This method:
        - Matches student's natural language prompt against job descriptions
        - Compares student skills with job requirements
        - Returns jobs with "Direct Apply Eligible" status if skills match (85%+)
        - Returns jobs with "Recommended" status if partial match, with missing skills and motivating message
        
        Args:
            student_query: Natural language prompt (e.g., "I want backend role with Python and APIs")
            jobs: List of job dictionaries
            student_skills: List of student's skills
            top_k: Number of results to return
            
        Returns:
            List of job matches with application_status, missing_skills, and messages
        """
        return self.job_matcher.search_jobs(student_query, jobs, student_skills, top_k)
    
    def analyze_skill_gap(self,
                          student_skills: List[str],
                          job_skills: List[str],
                          job_role: Optional[str] = None) -> Dict[str, Any]:
        """Analyze skill gap between student and job requirements."""
        return self.skill_analyzer.analyze_skill_gap(student_skills, job_skills, job_role)
    
    def get_resume_feedback(self,
                           resume_text: str,
                           job_description: str,
                           job_requirements: str,
                           skill_gap_output: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive resume feedback and ATS optimization suggestions."""
        return self.resume_engine.generate_feedback(
            resume_text, job_description, job_requirements, skill_gap_output
        )
    
    def interpret_rejection(self,
                           rejection_feedback: str,
                           job_title: str,
                           student_skills: List[str]) -> Dict[str, Any]:
        """
        Interpret company rejection feedback into student-friendly explanation.
        
        IMPORTANT: This method takes rejection_feedback as INPUT from the company-side AI.
        The company AI makes the rejection decision - this engine only interprets and
        translates that feedback into student-friendly, motivating explanations.
        
        Args:
            rejection_feedback: Raw rejection feedback from company-side AI (REQUIRED INPUT)
            job_title: Title of the job that student applied for
            student_skills: List of student's current skills
            
        Returns:
            Dictionary with student-friendly explanation, improvement suggestions, and next steps
        """
        return self.rejection_interpreter.interpret_rejection(
            rejection_feedback, job_title, student_skills
        )
