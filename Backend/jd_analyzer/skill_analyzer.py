"""
Module for analyzing resumes and extracting missing skills from job descriptions
"""
import re
from typing import Dict, List, Set
from collections import Counter

# Common skill keywords organized by category
SKILL_CATEGORIES = {
    "programming_languages": [
        "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
        "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "sql", "html",
        "css", "perl", "shell", "bash", "powershell"
    ],
    "frameworks": [
        "react", "angular", "vue", "django", "flask", "fastapi", "spring",
        "express", "node.js", "asp.net", "laravel", "rails", "tensorflow",
        "pytorch", "keras", "scikit-learn", "pandas", "numpy"
    ],
    "databases": [
        "mysql", "postgresql", "mongodb", "redis", "oracle", "sqlite",
        "cassandra", "elasticsearch", "dynamodb", "firebase"
    ],
    "cloud_platforms": [
        "aws", "azure", "gcp", "google cloud", "docker", "kubernetes",
        "jenkins", "ci/cd", "terraform", "ansible"
    ],
    "finance_skills": [
        "financial modeling", "valuation", "dcf", "discounted cash flow",
        "excel", "vba", "financial analysis", "budgeting", "forecasting",
        "risk analysis", "portfolio management", "derivatives", "options",
        "fixed income", "equity research", "cfa", "cpa", "gaap", "ifrs",
        "financial reporting", "accounting", "audit", "tax", "bloomberg",
        "reuters", "factset", "capital iq"
    ],
    "data_skills": [
        "data analysis", "data science", "machine learning", "deep learning",
        "statistics", "data visualization", "tableau", "power bi", "sql",
        "etl", "data warehousing", "big data", "hadoop", "spark"
    ],
    "soft_skills": [
        "leadership", "communication", "teamwork", "problem solving",
        "project management", "agile", "scrum", "collaboration"
    ]
}

def normalize_text(text: str) -> str:
    """Normalize text for better matching"""
    text = text.lower()
    # Remove special characters but keep spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    # Normalize whitespace
    text = ' '.join(text.split())
    return text

def extract_skills_from_text(text: str) -> Set[str]:
    """
    Extract skills from text by matching against skill keywords
    
    Args:
        text: Input text to extract skills from
        
    Returns:
        Set of found skills
    """
    normalized_text = normalize_text(text)
    found_skills = set()
    
    # Check all skill categories
    for category, skills in SKILL_CATEGORIES.items():
        for skill in skills:
            # Use word boundaries for better matching
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, normalized_text, re.IGNORECASE):
                found_skills.add(skill.lower())
    
    return found_skills

def extract_requirements_from_jd(jd_text: str) -> Dict[str, List[str]]:
    """
    Extract requirements and skills from job description
    
    Args:
        jd_text: Job description text
        
    Returns:
        Dictionary with extracted requirements organized by category
    """
    normalized_jd = normalize_text(jd_text)
    requirements = {
        "skills": [],
        "experience": [],
        "education": [],
        "certifications": [],
        "other_requirements": []
    }
    
    # Extract skills
    jd_skills = extract_skills_from_text(jd_text)
    requirements["skills"] = list(jd_skills)
    
    # Extract experience requirements (years of experience)
    experience_patterns = [
        r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
        r'minimum\s*(\d+)\s*years?',
        r'at\s*least\s*(\d+)\s*years?'
    ]
    for pattern in experience_patterns:
        matches = re.findall(pattern, normalized_jd, re.IGNORECASE)
        requirements["experience"].extend(matches)
    
    # Extract education requirements
    education_keywords = ["bachelor", "master", "phd", "degree", "bs", "ms", "mba"]
    for keyword in education_keywords:
        if re.search(r'\b' + keyword + r'\b', normalized_jd, re.IGNORECASE):
            requirements["education"].append(keyword)
    
    # Extract certifications
    cert_keywords = ["certified", "certification", "cfa", "cpa", "pmp", "aws certified"]
    for keyword in cert_keywords:
        if re.search(r'\b' + keyword + r'\b', normalized_jd, re.IGNORECASE):
            requirements["education"].append(keyword)
    
    return requirements

def analyze_missing_skills(resume_text: str, jd_text: str) -> Dict:
    """
    Analyze resume against job description and identify missing skills
    
    Args:
        resume_text: Text extracted from resume
        jd_text: Job description text
        
    Returns:
        Dictionary containing analysis results with missing skills
    """
    # Extract skills from resume and JD
    resume_skills = extract_skills_from_text(resume_text)
    jd_requirements = extract_requirements_from_jd(jd_text)
    jd_skills = set(jd_requirements["skills"])
    
    # Find missing skills
    missing_skills = jd_skills - resume_skills
    
    # Find matching skills
    matching_skills = resume_skills & jd_skills
    
    # Categorize missing skills
    missing_by_category = {}
    for category, skills in SKILL_CATEGORIES.items():
        category_missing = [s for s in missing_skills if s in skills]
        if category_missing:
            missing_by_category[category.replace("_", " ").title()] = category_missing
    
    # Calculate match percentage
    total_jd_skills = len(jd_skills)
    match_percentage = (len(matching_skills) / total_jd_skills * 100) if total_jd_skills > 0 else 0
    
    return {
        "resume_skills": sorted(list(resume_skills)),
        "jd_required_skills": sorted(list(jd_skills)),
        "matching_skills": sorted(list(matching_skills)),
        "missing_skills": sorted(list(missing_skills)),
        "missing_skills_by_category": missing_by_category,
        "match_percentage": round(match_percentage, 2),
        "jd_requirements": jd_requirements,
        "summary": {
            "total_jd_skills": total_jd_skills,
            "resume_skills_count": len(resume_skills),
            "matching_skills_count": len(matching_skills),
            "missing_skills_count": len(missing_skills)
        }
    }

