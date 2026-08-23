"""
Resume Parser Module
Extracts structured information from resume files (PDF, DOCX) or raw text
"""

import re
import pdfplumber
from docx import Document
from typing import Dict, List, Optional


class ResumeParser:
    """Parses resumes from various formats and extracts structured data"""
    
    def __init__(self):
        self.skill_keywords = {
            'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'swift', 'kotlin'],
            'web': ['html', 'css', 'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring', 'express'],
            'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'oracle'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'ci/cd'],
            'ml_ai': ['machine learning', 'deep learning', 'tensorflow', 'pytorch', 'nlp', 'neural networks'],
            'tools': ['git', 'github', 'jira', 'agile', 'scrum', 'linux', 'unix']
        }
    
    def parse(self, file_path: Optional[str] = None, resume_text: Optional[str] = None) -> Dict:
        """
        Main parsing function that extracts information from resume
        
        Args:
            file_path: Path to resume file (PDF or DOCX)
            resume_text: Raw text content of resume
            
        Returns:
            Dictionary with parsed resume data
        """
        if file_path:
            text = self._extract_text_from_file(file_path)
        elif resume_text:
            text = resume_text
        else:
            raise ValueError("Either file_path or resume_text must be provided")
        
        # Extract various components
        parsed_data = {
            'name': self._extract_name(text),
            'email': self._extract_email(text),
            'phone': self._extract_phone(text),
            'skills': self._extract_skills(text),
            'education': self._extract_education(text),
            'experience': self._extract_experience(text),
            'certifications': self._extract_certifications(text),
            'projects': self._extract_projects(text),
            'raw_text': text
        }
        
        return parsed_data
    
    def _extract_text_from_file(self, file_path: str) -> str:
        """Extract text from PDF or DOCX file"""
        file_path_lower = file_path.lower()
        
        if file_path_lower.endswith('.pdf'):
            return self._extract_from_pdf(file_path)
        elif file_path_lower.endswith('.docx') or file_path_lower.endswith('.doc'):
            return self._extract_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            raise ValueError(f"Error reading PDF file: {str(e)}")
        return text
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except Exception as e:
            raise ValueError(f"Error reading DOCX file: {str(e)}")
    
    def _extract_name(self, text: str) -> Optional[str]:
        """Extract candidate name (usually first line or near contact info)"""
        lines = text.split('\n')[:10]  # Check first 10 lines
        for line in lines:
            line = line.strip()
            # Skip if looks like email, phone, or URL
            if '@' in line or 'phone' in line.lower() or 'http' in line.lower():
                continue
            # If line has 2-4 words and no special chars, likely name
            if 2 <= len(line.split()) <= 4 and not re.search(r'[^\w\s\-]', line):
                return line
        return None
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, text)
        return matches[0] if matches else None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number"""
        phone_patterns = [
            r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\+?\d{10,12}',
            r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}'
        ]
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        return None
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from resume text"""
        text_lower = text.lower()
        found_skills = []
        
        # Extract from skill keywords dictionary
        all_skills = []
        for category, skills in self.skill_keywords.items():
            all_skills.extend(skills)
        
        for skill in all_skills:
            if skill.lower() in text_lower:
                found_skills.append(skill)
        
        # Look for "Skills:" section
        skills_section_pattern = r'(?:skills?|technical skills?|proficiency):\s*([^\n]+(?:\n[^\n]+){0,10})'
        match = re.search(skills_section_pattern, text, re.IGNORECASE)
        if match:
            skills_text = match.group(1)
            # Split by commas, semicolons, or newlines
            skills_list = re.split(r'[,;|\n]', skills_text)
            for skill in skills_list:
                skill = skill.strip().strip('-•*').strip()
                if skill and len(skill) > 1:
                    found_skills.append(skill)
        
        # Remove duplicates and return
        return list(set(found_skills))
    
    def _extract_education(self, text: str) -> List[Dict]:
        """Extract education information"""
        education = []
        education_keywords = ['bachelor', 'master', 'phd', 'doctorate', 'degree', 'diploma', 
                             'university', 'college', 'institute', 'education']
        
        # Look for education section
        education_section_pattern = r'(?:education|academic|qualification):\s*([^\n]+(?:\n[^\n]+){0,15})'
        match = re.search(education_section_pattern, text, re.IGNORECASE)
        
        if match:
            edu_text = match.group(1)
            # Try to extract degree and institution
            degree_pattern = r'(bachelor|master|phd|doctorate|b\.?s\.?c\.?|m\.?s\.?c\.?|b\.?e\.?|m\.?e\.?|b\.?tech|m\.?tech)'
            degrees = re.findall(degree_pattern, edu_text, re.IGNORECASE)
            institutions = re.findall(r'([A-Z][a-zA-Z\s&]+(?:University|College|Institute|School))', edu_text)
            
            for i, degree in enumerate(degrees):
                edu_dict = {
                    'degree': degree.title(),
                    'institution': institutions[i] if i < len(institutions) else None,
                    'details': edu_text[:200]  # First 200 chars as details
                }
                education.append(edu_dict)
        
        return education
    
    def _extract_experience(self, text: str) -> List[Dict]:
        """Extract work experience information"""
        experience = []
        exp_keywords = ['experience', 'employment', 'work history', 'career']
        
        # Look for experience section
        exp_section_pattern = r'(?:experience|work history|employment|career):\s*([^\n]+(?:\n[^\n]+){0,30})'
        match = re.search(exp_section_pattern, text, re.IGNORECASE)
        
        if match:
            exp_text = match.group(1)
            # Extract job titles (lines with common job title patterns)
            title_pattern = r'(?:software engineer|developer|intern|analyst|manager|engineer|designer|consultant|specialist)'
            titles = re.findall(title_pattern, exp_text, re.IGNORECASE)
            
            # Extract years (experience duration)
            year_pattern = r'(\d{1,2}[\+\s]*(?:years?|months?|yrs?))'
            durations = re.findall(year_pattern, exp_text, re.IGNORECASE)
            
            for i, title in enumerate(titles):
                exp_dict = {
                    'title': title,
                    'duration': durations[i] if i < len(durations) else None,
                    'details': exp_text[:300]  # First 300 chars
                }
                experience.append(exp_dict)
        
        return experience
    
    def _extract_certifications(self, text: str) -> List[str]:
        """Extract certifications"""
        certifications = []
        cert_pattern = r'(?:certification|certified|certificate):\s*([^\n]+(?:\n[^\n]+){0,5})'
        match = re.search(cert_pattern, text, re.IGNORECASE)
        
        if match:
            cert_text = match.group(1)
            certs = re.split(r'[,;\n]', cert_text)
            for cert in certs:
                cert = cert.strip().strip('-•*').strip()
                if cert:
                    certifications.append(cert)
        
        return certifications
    
    def _extract_projects(self, text: str) -> List[Dict]:
        """Extract project information"""
        projects = []
        project_pattern = r'(?:project|portfolio):\s*([^\n]+(?:\n[^\n]+){0,10})'
        match = re.search(project_pattern, text, re.IGNORECASE)
        
        if match:
            project_text = match.group(1)
            # Split projects by common delimiters
            project_list = re.split(r'(?:\n{2,}|\d+\.|\-)', project_text)
            for proj in project_list:
                proj = proj.strip()
                if proj and len(proj) > 10:
                    projects.append({'title': proj[:100], 'description': proj})
        
        return projects[:5]  # Limit to 5 projects


