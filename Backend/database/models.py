"""SQLAlchemy models for PostgreSQL database"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from .postgres import Base


class UserRole(str, enum.Enum):
    """User role enumeration"""
    STUDENT = "student"
    RECRUITER = "recruiter"
    ADMIN = "admin"
    TPO = "tpo"
    MENTOR = "mentor"


class ApplicationStatus(str, enum.Enum):
    """Application status enumeration"""
    PENDING = "pending"
    REVIEWING = "reviewing"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    ACCEPTED = "accepted"


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.STUDENT, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    jobs = relationship("Job", back_populates="creator")
    candidate = relationship(
        "Candidate",
        back_populates="user",
        uselist=False,
        foreign_keys="[Candidate.user_id]",
    )


class Job(Base):
    """Job posting model"""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False)
    description = Column(Text)
    location = Column(String(255))
    salary = Column(String(100))
    requirements_json = Column(JSON)  # Stores JobRequirement as JSON
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    creator = relationship("User", back_populates="jobs")
    applications = relationship("Application", back_populates="job")


class Candidate(Base):
    """Candidate model"""
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(50))
    skills_json = Column(JSON)  # List of skills as JSON
    resume_id = Column(String(100))  # Reference to MongoDB resume document
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    location = Column(String(255), nullable=True)
    education = Column(String(255), nullable=True)
    college = Column(String(255), nullable=True)
    branch = Column(String(255), nullable=True)
    graduation_year = Column(String(20), nullable=True)
    cgpa = Column(String(20), nullable=True)
    bio = Column(Text, nullable=True)
    experience = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="candidate", foreign_keys=[user_id])
    applications = relationship("Application", back_populates="candidate")
    candidate_badges = relationship("CandidateBadge", back_populates="candidate")
    test_attempts = relationship("TestAttempt", back_populates="candidate")
    mentorship_requests_sent = relationship("MentorshipRequest", back_populates="student")
    event_registrations = relationship("EventRegistration", back_populates="candidate")
    conversations = relationship("Conversation", back_populates="candidate")


class Badge(Base):
    """Skill-based badge definition"""
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    skill_key = Column(String(100), index=True)  # e.g. "python", "react"
    criteria_json = Column(JSON)  # e.g. {"min_score": 80, "min_matched_skills": 1}
    image_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CandidateBadge(Base):
    """Badge awarded to a candidate"""
    __tablename__ = "candidate_badges"
    __table_args__ = (UniqueConstraint("candidate_id", "badge_id", name="uq_candidate_badge"),)

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=False)
    awarded_at = Column(DateTime(timezone=True), server_default=func.now())
    source = Column(String(50))  # e.g. "ats", "practice", "tpo"

    # Relationships
    candidate = relationship("Candidate", back_populates="candidate_badges")
    badge = relationship("Badge")


class AptitudeTest(Base):
    """Aptitude test definition"""
    __tablename__ = "aptitude_tests"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    duration_minutes = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    questions = relationship("AptitudeQuestion", back_populates="test")


class AptitudeQuestion(Base):
    """Question belonging to an aptitude test"""
    __tablename__ = "aptitude_questions"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("aptitude_tests.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    options_json = Column(JSON)  # list of strings
    correct_index = Column(Integer, nullable=False)  # 0-based
    category = Column(String(50))  # e.g. quant, verbal
    difficulty = Column(String(20))

    test = relationship("AptitudeTest", back_populates="questions")


class TestAttempt(Base):
    """A candidate's attempt at an aptitude test"""
    __tablename__ = "test_attempts"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("aptitude_tests.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    score = Column(Float, nullable=True)
    passed = Column(Boolean, default=False)
    answers_json = Column(JSON)  # { question_id: selected_index }

    test = relationship("AptitudeTest")
    candidate = relationship("Candidate", back_populates="test_attempts")


class MentorProfile(Base):
    """Alumni mentor profile"""
    __tablename__ = "mentor_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    headline = Column(String(500))
    bio = Column(Text)
    skills_json = Column(JSON)  # list of strings
    company = Column(String(255))
    years_experience = Column(Integer)
    linkedin_url = Column(String(500))
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="mentor_profile")
    requests = relationship("MentorshipRequest", back_populates="mentor", foreign_keys="MentorshipRequest.mentor_id")


class MentorshipRequest(Base):
    """Student request to a mentor"""
    __tablename__ = "mentorship_requests"

    id = Column(Integer, primary_key=True, index=True)
    mentor_id = Column(Integer, ForeignKey("mentor_profiles.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)  # student as candidate
    message = Column(Text)
    status = Column(String(20), default="pending")  # pending, accepted, declined
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True))

    mentor = relationship("MentorProfile", back_populates="requests")
    student = relationship("Candidate", back_populates="mentorship_requests_sent")


class PrepModule(Base):
    """Company or JD-specific prep content"""
    __tablename__ = "prep_modules"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    company = Column(String(255))
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    job_title_pattern = Column(String(255))
    content = Column(Text, nullable=False)
    type = Column(String(50))  # e.g. "company_tips", "jd_checklist"
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Event(Base):
    """Hackathon, startup, workshop events"""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(50), nullable=False)  # hackathon, startup, workshop
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(255))
    registration_deadline = Column(DateTime(timezone=True))
    max_participants = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    registrations = relationship("EventRegistration", back_populates="event")


class EventRegistration(Base):
    """Student registration for an event"""
    __tablename__ = "event_registrations"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    status = Column(String(20), default="registered")  # registered, waitlist, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("event_id", "candidate_id", name="uq_event_candidate"),)

    event = relationship("Event", back_populates="registrations")
    candidate = relationship("Candidate", back_populates="event_registrations")


class Conversation(Base):
    """Conversation between recruiter (company) and candidate"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    company_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # recruiter
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_conversation_job_candidate"),)

    job = relationship("Job")
    company_user = relationship("User", foreign_keys=[company_user_id])
    candidate = relationship("Candidate", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")


class Message(Base):
    """Single message in a conversation"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])


class Application(Base):
    """Job application model"""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.PENDING, nullable=False)
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    job = relationship("Job", back_populates="applications")
    candidate = relationship("Candidate", back_populates="applications")
    evaluations = relationship("Evaluation", back_populates="application")


class Evaluation(Base):
    """ATS evaluation model"""
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    ats_score = Column(Float, nullable=False)
    passed = Column(Boolean, default=False, nullable=False)
    skill_match_score = Column(Float)
    education_score = Column(Float)
    experience_score = Column(Float)
    keyword_match_score = Column(Float)
    format_score = Column(Float)
    matched_skills_json = Column(JSON)
    missing_skills_json = Column(JSON)
    feedback_id = Column(String(100))  # Reference to MongoDB feedback document
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    application = relationship("Application", back_populates="evaluations")
