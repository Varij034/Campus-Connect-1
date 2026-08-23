import { Token, User, ApiError, Job, JobCreate, JobSearchResponse, ATSScoreRequest, ATSScoreResponse, EvaluationResponse, BatchScoreRequest, BatchScoreResponse, Candidate, ChatMessageRequest, ChatMessageResponse, StudentApplication, Badge, CandidateBadge, PrepModule, MentorProfile, MentorshipRequest, Event, EventRegistration, Conversation, Message, JDAnalyzerResponse, JDAnalyzeRequest } from '@/types/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Get token from localStorage
export const getToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth_token');
};

// Set token in localStorage
export const setToken = (token: string): void => {
  if (typeof window === 'undefined') return;
  localStorage.setItem('auth_token', token);
};

// Remove token from localStorage
export const removeToken = (): void => {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('auth_token');
};

// Get user from localStorage
export const getUser = (): User | null => {
  if (typeof window === 'undefined') return null;
  const userStr = localStorage.getItem('auth_user');
  return userStr ? JSON.parse(userStr) : null;
};

// Set user in localStorage
export const setUser = (user: User): void => {
  if (typeof window === 'undefined') return;
  localStorage.setItem('auth_user', JSON.stringify(user));
};

// Remove user from localStorage
export const removeUser = (): void => {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('auth_user');
};

// API Error class
export class ApiException extends Error {
  constructor(
    public status: number,
    public message: string,
    public data?: any
  ) {
    super(message);
    this.name = 'ApiException';
  }
}

// Base fetch wrapper with error handling
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  // Merge existing headers if they're a plain object
  if (options.headers) {
    if (options.headers instanceof Headers) {
      options.headers.forEach((value, key) => {
        headers[key] = value;
      });
    } else if (Array.isArray(options.headers)) {
      options.headers.forEach(([key, value]) => {
        headers[key] = value;
      });
    } else {
      Object.assign(headers, options.headers);
    }
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = `${API_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: headers as HeadersInit,
    });

    // Handle empty responses (like 204 No Content)
    if (response.status === 204) {
      return null as T;
    }

    const data = await response.json();

    if (!response.ok) {
      const errorMessage = data.detail || data.message || `HTTP ${response.status}`;
      throw new ApiException(response.status, errorMessage, data);
    }

    return data as T;
  } catch (error) {
    if (error instanceof ApiException) {
      throw error;
    }
    // Network or other errors
    throw new ApiException(0, error instanceof Error ? error.message : 'Network error');
  }
}

// Auth API
export const authApi = {
  login: async (email: string, password: string): Promise<Token> => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    
    const response = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    if (!response.ok) {
      const data = await response.json();
      const errorMessage = data.detail || data.message || `HTTP ${response.status}`;
      throw new ApiException(response.status, errorMessage, data);
    }

    return response.json();
  },

  register: async (email: string, password: string, role: 'student' | 'recruiter' | 'tpo'): Promise<User> => {
    return apiRequest<User>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, role }),
    });
  },

  getMe: async (): Promise<User> => {
    return apiRequest<User>('/api/v1/auth/me');
  },

  refreshToken: async (): Promise<Token> => {
    return apiRequest<Token>('/api/v1/auth/refresh', {
      method: 'POST',
    });
  },
};

// Jobs API
export const jobsApi = {
  list: async (skip = 0, limit = 100, company?: string, title?: string): Promise<Job[]> => {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    });
    if (company) params.append('company', company);
    if (title) params.append('title', title);
    
    return apiRequest<Job[]>(`/api/v1/jobs?${params.toString()}`);
  },

  get: async (jobId: number): Promise<Job> => {
    return apiRequest<Job>(`/api/v1/jobs/${jobId}`);
  },

  create: async (job: JobCreate): Promise<Job> => {
    return apiRequest<Job>('/api/v1/jobs', {
      method: 'POST',
      body: JSON.stringify(job),
    });
  },

  update: async (jobId: number, job: Partial<JobCreate>): Promise<Job> => {
    return apiRequest<Job>(`/api/v1/jobs/${jobId}`, {
      method: 'PUT',
      body: JSON.stringify(job),
    });
  },

  delete: async (jobId: number): Promise<void> => {
    return apiRequest<void>(`/api/v1/jobs/${jobId}`, {
      method: 'DELETE',
    });
  },
};

// Aptitude API – detailed results types
export interface QuestionResultDetail {
  question_id: number;
  question_text: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  correct_option: string;
  selected_option: string | null;
  is_correct: boolean;
  difficulty_level: string;
}

export interface DetailedTestResultsResponse {
  attempt_id: number;
  test_id: number;
  test_title: string;
  user_id: number;
  score: number;
  total_questions: number;
  correct_answers: number;
  incorrect_answers: number;
  skipped_questions: number;
  time_taken: number;
  submitted_at: string;
  questions: QuestionResultDetail[];
}

// Aptitude API
export const aptitudeApi = {
  listTests: async (): Promise<{ id: number; title: string; description?: string; duration_minutes: number; question_count: number }[]> =>
    apiRequest('/api/v1/aptitude/tests'),
  getTest: async (testId: number): Promise<{ id: number; title: string; description?: string; duration_minutes: number; question_count: number }> =>
    apiRequest(`/api/v1/aptitude/tests/${testId}`),
  startAttempt: async (testId: number): Promise<{
    attempt_id: number;
    test_id: number;
    questions: { id: number; question_text: string; options: string[]; category?: string; difficulty?: string }[];
    duration_minutes: number;
  }> => apiRequest(`/api/v1/aptitude/tests/${testId}/start`, { method: 'POST' }),
  submitAttempt: async (attemptId: number, answers: Record<string, number>): Promise<{
    attempt_id: number;
    score: number;
    passed: boolean;
    total_questions: number;
    correct_count: number;
  }> => apiRequest(`/api/v1/aptitude/attempts/${attemptId}/submit`, {
    method: 'POST',
    body: JSON.stringify({ answers }),
  }),
  myAttempts: async (): Promise<{ id: number; test_id: number; test_title?: string; started_at?: string; submitted_at?: string; score?: number; passed?: boolean }[]> =>
    apiRequest('/api/v1/aptitude/attempts/me'),
  getDetailedResults: async (attemptId: number): Promise<DetailedTestResultsResponse> =>
    apiRequest<DetailedTestResultsResponse>(`/api/v1/aptitude/attempts/${attemptId}/detailed-results`),
};

// Student API
export const studentApi = {
  searchJobs: async (query: string, studentSkills: string[], topK = 10): Promise<JobSearchResponse[]> => {
    return apiRequest<JobSearchResponse[]>('/api/v1/student/jobs/search', {
      method: 'POST',
      body: JSON.stringify({
        query,
        student_skills: studentSkills,
        top_k: topK,
      }),
    });
  },

  getApplications: async (): Promise<StudentApplication[]> => {
    return apiRequest<StudentApplication[]>('/api/v1/student/applications');
  },

  applyToJob: async (jobId: number): Promise<{ message: string; application_id?: number }> => {
    return apiRequest<{ message: string; application_id?: number }>(`/api/v1/student/jobs/${jobId}/apply`, {
      method: 'POST',
    });
  },

  analyzeSkillGap: async (jobId: number): Promise<any> => {
    return apiRequest<any>('/api/v1/student/skill-gap/analyze', {
      method: 'POST',
      body: JSON.stringify({ job_id: jobId }),
    });
  },

  getResumeFeedback: async (jobId?: number): Promise<any> => {
    return apiRequest<any>('/api/v1/student/resume/feedback', {
      method: 'POST',
      body: JSON.stringify({ job_id: jobId }),
    });
  },

  interpretRejection: async (feedbackId: string): Promise<any> => {
    return apiRequest<any>('/api/v1/student/rejection/interpret', {
      method: 'POST',
      body: JSON.stringify({ feedback_id: feedbackId }),
    });
  },
};

// ATS API
export const atsApi = {
  score: async (request: ATSScoreRequest): Promise<ATSScoreResponse> => {
    return apiRequest<ATSScoreResponse>('/api/v1/ats/score', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  getEvaluation: async (evaluationId: number): Promise<EvaluationResponse> => {
    return apiRequest<EvaluationResponse>(`/api/v1/ats/evaluation/${evaluationId}`);
  },

  batchScore: async (requests: ATSScoreRequest[]): Promise<BatchScoreResponse> => {
    return apiRequest<BatchScoreResponse>('/api/v1/ats/batch-score', {
      method: 'POST',
      body: JSON.stringify(requests),
    });
  },

  createEvaluation: async (candidateId: number, jobId: number): Promise<EvaluationResponse> => {
    return apiRequest<EvaluationResponse>('/api/v1/ats/create-evaluation', {
      method: 'POST',
      body: JSON.stringify({ candidate_id: candidateId, job_id: jobId }),
    });
  },
};

// JD Analyzer API
export const jdAnalyzerApi = {
  getJds: async (): Promise<{ available_jds: string[]; message?: string }> => {
    return apiRequest<{ available_jds: string[]; message?: string }>('/api/v1/jd-analyzer/jds');
  },

  analyze: async (params: JDAnalyzeRequest): Promise<JDAnalyzerResponse> => {
    return apiRequest<JDAnalyzerResponse>('/api/v1/jd-analyzer/analyze', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },
};

// HR Stats API
export const hrApi = {
  getStats: async (): Promise<{
    total_jobs: number;
    total_applications: number;
    shortlisted: number;
    avg_ats_score: number;
  }> => {
    return apiRequest('/api/v1/hr/stats');
  },

  getProfile: async (): Promise<any> => {
    return apiRequest<any>('/api/v1/hr/profile');
  },

  updateProfile: async (data: any): Promise<any> => {
    return apiRequest<any>('/api/v1/hr/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },
};

// Candidates API
export const candidatesApi = {
  list: async (
    skip = 0,
    limit = 100,
    passed?: boolean,
    jobId?: number
  ): Promise<Candidate[]> => {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    });
    if (passed === true) params.append('passed', 'true');
    if (jobId != null) params.append('job_id', jobId.toString());
    return apiRequest<Candidate[]>(`/api/v1/candidates?${params.toString()}`);
  },

  get: async (candidateId: number): Promise<Candidate> => {
    return apiRequest<Candidate>(`/api/v1/candidates/${candidateId}`);
  },

  getMe: async (): Promise<Candidate> => {
    return apiRequest<Candidate>('/api/v1/candidates/me');
  },

  updateMe: async (data: any): Promise<Candidate> => {
    return apiRequest<Candidate>('/api/v1/candidates/me', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  getEvaluations: async (candidateId: number): Promise<EvaluationResponse[]> => {
    return apiRequest<EvaluationResponse[]>(`/api/v1/candidates/${candidateId}/evaluations`);
  },
};

// Resume API
export const resumeApi = {
  upload: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    
    // We cannot use apiRequest because FormData shouldn't have Content-Type: application/json
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_URL}/api/v1/resume/upload`, {
      method: 'POST',
      headers: headers as HeadersInit,
      body: formData,
    });
    
    if (!response.ok) {
      const data = await response.json();
      throw new ApiException(response.status, data.detail || `HTTP ${response.status}`, data);
    }
    return response.json();
  },

  get: async (resumeId: string): Promise<{ resume_id: string; parsed_data: any; raw_text?: string; message: string }> => {
    return apiRequest<{ resume_id: string; parsed_data: any; raw_text?: string; message: string }>(`/api/v1/resume/${resumeId}`);
  },

  download: async (resumeId: string, filename: string = 'resume.txt'): Promise<void> => {
    const token = getToken();
    const headers: Record<string, string> = {};
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}/api/v1/resume/${resumeId}`, {
      headers: headers as HeadersInit,
    });

    if (!response.ok) {
      const data = await response.json();
      const errorMessage = data.detail || data.message || `HTTP ${response.status}`;
      throw new ApiException(response.status, errorMessage, data);
    }

    const data = await response.json();
    const rawText = data.raw_text || data.parsed_data?.raw_text || '';
    
    // Create a blob and download
    const blob = new Blob([rawText], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },
};

// Badges API
export const badgesApi = {
  list: async (): Promise<Badge[]> => apiRequest<Badge[]>('/api/v1/badges'),
  getMyBadges: async (): Promise<CandidateBadge[]> => apiRequest<CandidateBadge[]>('/api/v1/badges/me'),
  getCandidateBadges: async (candidateId: number): Promise<CandidateBadge[]> =>
    apiRequest<CandidateBadge[]>(`/api/v1/badges/candidates/${candidateId}`),
  award: async (candidateId: number, badgeId: number, source = 'tpo'): Promise<CandidateBadge> =>
    apiRequest<CandidateBadge>('/api/v1/badges/award', {
      method: 'POST',
      body: JSON.stringify({ candidate_id: candidateId, badge_id: badgeId, source }),
    }),
};

// TPO API
export const tpoApi = {
  listPendingVerification: async (skip = 0, limit = 100): Promise<Candidate[]> => {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    });
    return apiRequest<Candidate[]>(`/api/v1/tpo/candidates/pending-verification?${params.toString()}`);
  },

  verifyCandidate: async (candidateId: number): Promise<Candidate> => {
    return apiRequest<Candidate>(`/api/v1/tpo/candidates/${candidateId}/verify`, {
      method: 'POST',
    });
  },

  getStats: async (): Promise<{
    total_candidates: number;
    verified_count: number;
    total_applications: number;
    placements: number;
    active_jobs: number;
  }> => {
    return apiRequest('/api/v1/tpo/stats');
  },
};

// Prep API (company/JD-specific prep)
export const prepApi = {
  list: async (company?: string, jobId?: number): Promise<PrepModule[]> => {
    const params = new URLSearchParams();
    if (company) params.append('company', company);
    if (jobId != null) params.append('job_id', jobId.toString());
    return apiRequest<PrepModule[]>(`/api/v1/prep/modules?${params.toString()}`);
  },
  get: async (id: number): Promise<PrepModule> =>
    apiRequest<PrepModule>(`/api/v1/prep/modules/${id}`),
  forJob: async (jobId: number): Promise<PrepModule[]> =>
    apiRequest<PrepModule[]>(`/api/v1/prep/for-job/${jobId}`),
};

export const mentorshipApi = {
  listMentors: async (params?: { skill?: string; company?: string; is_available?: boolean }): Promise<MentorProfile[]> => {
    const search = new URLSearchParams();
    if (params?.skill) search.append('skill', params.skill);
    if (params?.company) search.append('company', params.company);
    if (params?.is_available != null) search.append('is_available', String(params.is_available));
    return apiRequest<MentorProfile[]>(`/api/v1/mentors?${search.toString()}`);
  },
  getMentor: async (mentorId: number): Promise<MentorProfile> =>
    apiRequest<MentorProfile>(`/api/v1/mentors/${mentorId}`),
  createRequest: async (mentorId: number, message?: string): Promise<MentorshipRequest> =>
    apiRequest<MentorshipRequest>('/api/v1/mentorship/requests', {
      method: 'POST',
      body: JSON.stringify({ mentor_id: mentorId, message: message || null }),
    }),
  listMyRequests: async (): Promise<MentorshipRequest[]> =>
    apiRequest<MentorshipRequest[]>('/api/v1/mentorship/requests/me'),
  respondRequest: async (requestId: number, status: 'accepted' | 'declined'): Promise<MentorshipRequest> =>
    apiRequest<MentorshipRequest>(`/api/v1/mentorship/requests/${requestId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
};

export const eventsApi = {
  list: async (params?: { type?: string; is_active?: boolean }): Promise<Event[]> => {
    const search = new URLSearchParams();
    if (params?.type) search.append('type', params.type);
    if (params?.is_active != null) search.append('is_active', String(params.is_active));
    return apiRequest<Event[]>(`/api/v1/events?${search.toString()}`);
  },
  get: async (eventId: number): Promise<Event> =>
    apiRequest<Event>(`/api/v1/events/${eventId}`),
  register: async (eventId: number): Promise<EventRegistration> =>
    apiRequest<EventRegistration>(`/api/v1/events/${eventId}/register`, { method: 'POST' }),
  myRegistrations: async (): Promise<EventRegistration[]> =>
    apiRequest<EventRegistration[]>('/api/v1/events/registrations/me'),
};

export const messagesApi = {
  listConversations: async (): Promise<Conversation[]> =>
    apiRequest<Conversation[]>('/api/v1/conversations'),
  getMessages: async (conversationId: number, limit?: number, offset?: number): Promise<Message[]> => {
    const params = new URLSearchParams();
    if (limit != null) params.append('limit', String(limit));
    if (offset != null) params.append('offset', String(offset));
    return apiRequest<Message[]>(`/api/v1/conversations/${conversationId}/messages?${params.toString()}`);
  },
  createConversation: async (body: { job_id?: number; candidate_id?: number; initial_message?: string }): Promise<Conversation> =>
    apiRequest<Conversation>('/api/v1/conversations', { method: 'POST', body: JSON.stringify(body) }),
  sendMessage: async (conversationId: number, body: string): Promise<Message> =>
    apiRequest<Message>(`/api/v1/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ body }),
    }),
};

// Job LLM API (JD Analyzer)
export const jobLlmApi = {
  extractRequirements: async (description: string): Promise<{
    job_title: string;
    required_skills: string[];
    preferred_skills: string[];
    education_level: string;
    years_of_experience: number;
    job_description: string;
  }> => {
    return apiRequest('/api/v1/llm/jobs/extract-requirements', {
      method: 'POST',
      body: JSON.stringify({ description }),
    });
  },

  generateDescription: async (prompt: string): Promise<{ job_description: string }> => {
    return apiRequest('/api/v1/llm/jobs/generate-description', {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    });
  },

  rewriteDescription: async (description: string, tone: string): Promise<{ job_description: string }> => {
    return apiRequest('/api/v1/llm/jobs/rewrite-description', {
      method: 'POST',
      body: JSON.stringify({ description, tone }),
    });
  },
};

// Recruiter LLM API (Matchmaker - resume summary per candidate/job)
export const recruiterLlmApi = {
  resumeSummary: async (
    candidateId: number,
    jobId?: number
  ): Promise<{
    candidate_id: number;
    job_id: number | null;
    headline: string;
    summary_bullets: string[];
    risks: string[];
    overall_fit: string;
  }> => {
    const params = new URLSearchParams({ candidate_id: candidateId.toString() });
    if (jobId != null) params.append('job_id', jobId.toString());
    return apiRequest(`/api/v1/llm/recruiter/resume-summary?${params.toString()}`, {
      method: 'POST',
    });
  },
};

// Chat API
export const chatApi = {
  sendMessage: async (message: string, conversationId?: string): Promise<ChatMessageResponse> => {
    return apiRequest<ChatMessageResponse>('/api/v1/chat/message', {
      method: 'POST',
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    });
  },
};

// Feedback API
export const feedbackApi = {
  generate: async (candidateId: number, jobId: number, rejectionReason?: string): Promise<any> => {
    return apiRequest('/api/v1/feedback/generate', {
      method: 'POST',
      body: JSON.stringify({
        candidate_id: candidateId,
        job_id: jobId,
        rejection_reason: rejectionReason,
      }),
    });
  },

  get: async (feedbackId: string): Promise<any> => {
    return apiRequest(`/api/v1/feedback/${feedbackId}`);
  },

  getByCandidate: async (candidateId: number): Promise<any[]> => {
    return apiRequest(`/api/v1/feedback/candidate/${candidateId}`);
  },
};
