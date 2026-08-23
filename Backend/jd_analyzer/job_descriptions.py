"""
Predefined job descriptions for various roles
"""

JOB_DESCRIPTIONS = {
    "software_engineer": """
    Software Engineer - Full Stack Developer
    
    We are seeking a talented Software Engineer to join our dynamic development team. 
    The ideal candidate will have strong experience in building scalable web applications 
    and working with modern technologies.
    
    Requirements:
    - Bachelor's degree in Computer Science or related field
    - 3+ years of professional software development experience
    - Strong proficiency in Python, JavaScript, and TypeScript
    - Experience with React, Node.js, and Express frameworks
    - Solid understanding of RESTful API design and development
    - Experience with databases: PostgreSQL, MongoDB, and Redis
    - Knowledge of cloud platforms: AWS, Azure, or GCP
    - Experience with Docker and Kubernetes
    - Familiarity with CI/CD pipelines and Jenkins
    - Strong problem-solving skills and attention to detail
    - Excellent communication and teamwork abilities
    - Experience with Git version control
    - Knowledge of Agile/Scrum methodologies
    
    Preferred Qualifications:
    - Experience with FastAPI or Django
    - Knowledge of microservices architecture
    - Experience with Terraform or Infrastructure as Code
    - Understanding of machine learning concepts
    """,
    
    "finance_analyst": """
    Financial Analyst
    
    We are looking for a detail-oriented Financial Analyst to join our finance team. 
    The candidate will be responsible for financial modeling, analysis, and reporting 
    to support strategic decision-making.
    
    Requirements:
    - Bachelor's degree in Finance, Accounting, Economics, or related field
    - 2+ years of experience in financial analysis or related role
    - Strong proficiency in Excel and financial modeling
    - Experience with DCF (Discounted Cash Flow) valuation models
    - Knowledge of GAAP and financial reporting standards
    - Strong analytical and quantitative skills
    - Experience with budgeting and forecasting
    - Proficiency in financial analysis and risk assessment
    - Excellent communication skills, both written and verbal
    - Attention to detail and accuracy
    
    Preferred Qualifications:
    - CFA or CPA certification
    - Master's degree in Finance or MBA
    - Experience with Bloomberg, Reuters, or FactSet
    - Knowledge of portfolio management
    - Experience with derivatives and options
    - Proficiency in VBA for Excel automation
    - Understanding of fixed income securities
    """,
    
    "data_scientist": """
    Data Scientist
    
    We are seeking a Data Scientist to help us extract insights from complex datasets 
    and build predictive models. The ideal candidate will have strong statistical and 
    programming skills.
    
    Requirements:
    - Master's degree in Data Science, Statistics, Computer Science, or related field
    - 3+ years of experience in data science or machine learning
    - Strong programming skills in Python and R
    - Experience with machine learning frameworks: TensorFlow, PyTorch, or scikit-learn
    - Proficiency in data analysis libraries: pandas, numpy, scipy
    - Strong SQL skills for data extraction
    - Experience with data visualization tools: Tableau or Power BI
    - Solid understanding of statistics and statistical modeling
    - Experience with ETL processes and data warehousing
    - Knowledge of big data technologies: Hadoop or Spark
    - Strong problem-solving and analytical thinking
    - Excellent communication skills to present findings
    
    Preferred Qualifications:
    - PhD in a quantitative field
    - Experience with deep learning
    - Knowledge of cloud platforms: AWS, Azure, or GCP
    - Experience with MLOps and model deployment
    - Published research in data science or machine learning
    """,
    
    "product_manager": """
    Product Manager
    
    We are looking for an experienced Product Manager to drive product strategy and 
    execution. The candidate will work closely with engineering, design, and business 
    teams to deliver exceptional products.
    
    Requirements:
    - Bachelor's degree in Business, Engineering, or related field
    - 4+ years of product management experience
    - Strong analytical and problem-solving skills
    - Experience with Agile and Scrum methodologies
    - Excellent communication and leadership skills
    - Ability to work collaboratively with cross-functional teams
    - Experience with project management tools
    - Strong understanding of user experience principles
    - Data-driven decision making approach
    - Experience with product analytics and metrics
    
    Preferred Qualifications:
    - MBA degree
    - Technical background or experience with software development
    - Experience with A/B testing
    - Knowledge of SQL for data analysis
    - PMP certification
    """,
    
    "devops_engineer": """
    DevOps Engineer
    
    We are seeking a DevOps Engineer to help build and maintain our cloud infrastructure 
    and CI/CD pipelines. The ideal candidate will have strong experience with automation 
    and cloud technologies.
    
    Requirements:
    - Bachelor's degree in Computer Science or related field
    - 3+ years of DevOps or infrastructure engineering experience
    - Strong experience with AWS, Azure, or GCP
    - Proficiency with Docker and Kubernetes
    - Experience with CI/CD tools: Jenkins, GitLab CI, or GitHub Actions
    - Knowledge of Infrastructure as Code: Terraform or Ansible
    - Strong scripting skills: Python, Bash, or PowerShell
    - Experience with monitoring and logging tools
    - Knowledge of Linux/Unix systems
    - Understanding of networking and security best practices
    - Experience with Git version control
    
    Preferred Qualifications:
    - AWS Certified Solutions Architect or similar certification
    - Experience with microservices architecture
    - Knowledge of service mesh technologies
    - Experience with cloud security and compliance
    """
}

def get_job_description(jd_name: str = None):
    """
    Get job description by name or return all available JDs
    
    Args:
        jd_name: Name of the job description to retrieve (None to get all)
        
    Returns:
        Job description text, dictionary of all JDs, or None if not found
    """
    if jd_name is None:
        return JOB_DESCRIPTIONS
    
    jd_name_lower = jd_name.lower().replace(" ", "_")
    
    if jd_name_lower in JOB_DESCRIPTIONS:
        return JOB_DESCRIPTIONS[jd_name_lower]
    
    # Try to find partial match
    for key, value in JOB_DESCRIPTIONS.items():
        if jd_name_lower in key or key in jd_name_lower:
            return value
    
    return None

