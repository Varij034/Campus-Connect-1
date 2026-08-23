# 🎓 Campus Connect

> **AI-powered campus recruitment platform bridging colleges and companies.**

Campus Connect is a full-stack application that streamlines the campus placement process with intelligent resume screening, AI-driven job matching, real-time feedback, and seamless communication between students, recruiters, TPOs, and mentors.

---

## ✨ Key Features

### 🤖 AI-Powered ATS Engine
- **Resume Parsing** — Extracts structured data from PDF & DOCX resumes
- **Multi-Criteria Scoring** — Weighted evaluation across Skills (40%), Keywords (25%), Experience (20%), Education (10%), and Format (5%)
- **Real-Time Feedback** — Rejected candidates receive actionable improvement suggestions, missing skills, and resume highlights

### 🎯 Smart Job Matching
- **Semantic Search** — Natural language job search powered by sentence-transformers and Qdrant vector DB
- **Skill Gap Analysis** — Identifies missing skills and generates personalized learning paths
- **JD-Resume Matching** — Compares resumes against specific job descriptions for skill coverage analysis

### 💬 Intelligent Chat
- **LLM-Powered Assistants** — Role-aware chatbots for students, recruiters, and HR powered by Groq (Llama 3.1)
- **Intent Classification** — Automatically routes queries to the right service

### 👥 Role-Based Portals
- **Students** — Job search, applications, aptitude tests, skill badges, event registration, mentorship
- **Recruiters/HR** — Job postings, candidate management, ATS evaluation, messaging
- **TPO** — Placement oversight, candidate verification, analytics
- **Mentors** — Profile management, mentorship requests

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 16, React 19, TypeScript, TailwindCSS 4, DaisyUI, Framer Motion |
| **Backend** | Python, FastAPI, Uvicorn |
| **Databases** | PostgreSQL (relational), MongoDB (documents), Qdrant (vectors) |
| **AI/ML** | Sentence-Transformers, scikit-learn, Transformers |
| **LLM** | Groq API (Llama 3.1 8B) |
| **Auth** | JWT (python-jose), bcrypt |
| **Storage** | Cloudinary (resume file uploads) |
| **DevOps** | Docker, Docker Compose, Render (backend), Vercel (frontend) |

---

## 📁 Project Structure

```
Campus-Connect-1/
├── client/                      # Next.js Frontend
│   ├── app/                     # App Router pages
│   │   ├── auth/                #   Login & Register
│   │   ├── student/             #   Student portal (dashboard, jobs, chat, etc.)
│   │   ├── hr/                  #   HR/Recruiter portal (postings, ATS, candidates)
│   │   └── tpo/                 #   TPO portal (placement oversight)
│   ├── components/              # Reusable UI components
│   ├── contexts/                # React context providers
│   ├── hooks/                   # Custom React hooks
│   ├── lib/                     # Utility libraries
│   └── types/                   # TypeScript type definitions
│
├── Backend/                     # FastAPI Backend
│   ├── main.py                  # Application entry point
│   ├── config.py                # Configuration & environment variables
│   ├── schemas/                 # Pydantic models
│   │   ├── domain.py            #   Domain models (JobRequirement, ResumeData, etc.)
│   │   └── api.py               #   API request/response schemas
│   ├── services/                # Business logic layer
│   │   ├── ats_engine.py        #   ATS scoring engine
│   │   ├── resume_parser.py     #   Resume text extraction
│   │   ├── feedback_generator.py#   Rejection feedback generator
│   │   ├── student_engine.py    #   Semantic job matching & skill gap
│   │   ├── chat_engine.py       #   Chat orchestrator
│   │   └── jd_analyzer/         #   JD vs Resume analysis
│   ├── routers/                 # API route handlers (22 routers)
│   ├── database/                # DB connections & ORM models
│   ├── auth/                    # JWT authentication & security
│   ├── llm/                     # Groq LLM integrations
│   ├── vector/                  # Qdrant vector DB client
│   ├── utils/                   # Utilities (Cloudinary, etc.)
│   └── alembic/                 # Database migrations
│
└── render.yaml                  # Render deployment config
```

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** ≥ 18
- **Python** ≥ 3.11
- **Docker & Docker Compose** (for local development with databases)

### 1. Clone the Repository

```bash
git clone https://github.com/Varij034/Campus-Connect-1.git
cd Campus-Connect-1
```

### 2. Start the Backend

```bash
cd Backend

# Copy environment variables
cp .env.example .env
# Edit .env and add your API keys (GROQ_API_KEY, etc.)

# Start all services (PostgreSQL, MongoDB, Qdrant, Backend)
docker compose up --build
```

The API will be available at **http://localhost:8000**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

#### Seed Demo Data (Optional)

```bash
docker exec -it campus_connect_backend python seed_database.py
```

### 3. Start the Frontend

```bash
cd client

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend will be available at **http://localhost:3000**

---

## 🔌 API Overview

| Category | Prefix | Description |
|---|---|---|
| **Auth** | `/api/v1/auth` | Register, login, token refresh |
| **Resume** | `/api/v1/resume` | Parse text, upload PDF/DOCX, retrieve parsed data |
| **ATS** | `/api/v1/ats` | Score resumes, batch scoring, evaluations |
| **Feedback** | `/api/v1/feedback` | Generate & retrieve rejection feedback |
| **Student** | `/api/v1/student` | Job search, skill gap analysis, resume feedback |
| **Jobs** | `/api/v1/jobs` | CRUD job postings |
| **Candidates** | `/api/v1/candidates` | Manage & evaluate candidates |
| **Chat** | `/api/v1/chat` | LLM-powered role-aware chat |
| **JD Analyzer** | `/api/v1/jd-analyzer` | Resume vs JD skill matching |
| **Mentorship** | `/api/v1/mentorship` | Mentor profiles & requests |
| **Events** | `/api/v1/events` | Hackathons, workshops, registrations |
| **Aptitude** | `/api/v1/aptitude` | Aptitude tests & scoring |
| **Badges** | `/api/v1/badges` | Skill badge awards |
| **Messages** | `/api/v1/conversations` | Recruiter-candidate messaging |
| **TPO** | `/api/v1/tpo` | Placement management |
| **HR** | `/api/v1/hr` | HR analytics |
| **Notifications** | `/api/v1/notifications` | SSE real-time notifications |
| **Vector** | `/api/v1/vector` | Vector DB indexing |
| **LLM Tools** | `/api/v1/llm/*` | Recruiter, job, and analytics AI tools |

---

## 🌐 Deployment

| Component | Platform | Config |
|---|---|---|
| **Backend** | [Render](https://render.com) | `render.yaml` (Docker web service) |
| **Frontend** | [Vercel](https://vercel.com) | Auto-detected Next.js |
| **PostgreSQL** | Render / Neon / Supabase | Managed PostgreSQL |
| **MongoDB** | [MongoDB Atlas](https://www.mongodb.com/atlas) | Free tier available |
| **Qdrant** | [Qdrant Cloud](https://cloud.qdrant.io) | Free tier available |

### Environment Variables Required

| Variable | Description |
|---|---|
| `POSTGRES_URL` | PostgreSQL connection string |
| `MONGODB_URL` | MongoDB connection string |
| `QDRANT_URL` | Qdrant vector DB URL |
| `QDRANT_API_KEY` | Qdrant API key |
| `GROQ_API_KEY` | Groq LLM API key |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name |
| `CLOUDINARY_API_KEY` | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret |
| `JWT_SECRET_KEY` | Secret key for JWT tokens |

---

## 📄 License

This project is licensed under the [MIT License](Backend/LICENSE).

---

<p align="center">
  Built with ❤️ for campus recruitment
</p>
