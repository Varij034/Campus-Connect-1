'use client';

import {
  ArrowLeft,
  Award,
  Briefcase,
  Building2,
  Calendar,
  CheckCircle,
  Clock,
  DollarSign,
  FileText,
  Globe,
  MapPin,
  Target,
  TrendingUp,
  Users,
  Video,
  Mail
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import SkillGapCard from '@/components/student/SkillGapCard';
import { jobsApi, messagesApi, studentApi } from '@/lib/api';
import { Job } from '@/types/api';
import { handleApiError } from '@/lib/errors';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

export default function JobDetailsPage() {
  const router = useRouter();
  const params = useParams();
  const [job, setJob] = useState<Job | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isApplied, setIsApplied] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [contacting, setContacting] = useState(false);

  const jobId = params?.id as string;

  useEffect(() => {
    if (jobId) {
      fetchJob();
    }
  }, [jobId]);

  const fetchJob = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const jobData = await jobsApi.get(parseInt(jobId));
      setJob(jobData);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (showToast) {
      const timer = setTimeout(() => {
        setShowToast(false);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [showToast]);

  const handleApply = async () => {
    try {
      setIsApplied(true);
      await studentApi.applyToJob(parseInt(jobId));
      setToastMessage(`Application submitted successfully for ${job?.title} at ${job?.company}!`);
      setShowToast(true);
      setTimeout(() => {
        router.push('/student/jobs');
      }, 2000);
    } catch (err: any) {
      setIsApplied(false);
      setError(handleApiError(err));
    }
  };

  if (isLoading) {
    return (
      <ProtectedRoute requiredRole="student">
        <div className="min-h-screen flex items-center justify-center">
          <span className="loading loading-spinner loading-lg"></span>
        </div>
      </ProtectedRoute>
    );
  }

  if (error || !job) {
    return (
      <ProtectedRoute requiredRole="student">
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-base-content mb-4">
              {error || 'Job not found'}
            </h2>
            <button
              onClick={() => router.push('/student/jobs')}
              className="btn btn-primary"
            >
              Back to Jobs
            </button>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  // Extract requirements from requirements_json if available
  const requirements = job.requirements_json?.requirements || 
    job.requirements_json?.required_skills?.map((skill: string) => `Experience with ${skill}`) || 
    [];
  
  const requiredSkills = job.requirements_json?.required_skills || [];

  return (
    <ProtectedRoute requiredRole="student">
      <div className="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
      {/* Toast Notification */}
      {showToast && (
        <div className="fixed top-4 right-4 z-50 animate-in slide-in-from-top">
          <div className="alert alert-success shadow-lg">
            <CheckCircle className="w-6 h-6" />
            <div>
              <h3 className="font-bold">Application Submitted! 🎉</h3>
              <div className="text-xs">{toastMessage}</div>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Back Button */}
        <button
          onClick={() => router.push('/student/jobs')}
          className="btn btn-ghost gap-2 mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Jobs
        </button>

        {/* Job Header Card */}
        <div className="card bg-gradient-to-r from-primary to-secondary text-primary-content shadow-2xl mb-6">
          <div className="card-body p-8">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-3 bg-base-content/20 rounded-lg backdrop-blur-sm">
                    <Building2 className="w-8 h-8" />
                  </div>
                  <div>
                    <h1 className="text-3xl md:text-4xl font-bold">{job.title}</h1>
                    <p className="text-xl opacity-90">{job.company}</p>
                  </div>
                </div>
                
                {/* Quick Info Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
                  {job.location && (
                    <div className="flex items-center gap-2 bg-base-content/10 backdrop-blur-sm rounded-lg px-3 py-2">
                      <MapPin className="w-4 h-4" />
                      <span className="text-sm">{job.location}</span>
                    </div>
                  )}
                  {job.salary && (
                    <div className="flex items-center gap-2 bg-base-content/10 backdrop-blur-sm rounded-lg px-3 py-2">
                      <DollarSign className="w-4 h-4" />
                      <span className="text-sm font-semibold">{job.salary}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2 bg-base-content/10 backdrop-blur-sm rounded-lg px-3 py-2">
                    <Calendar className="w-4 h-4" />
                    <span className="text-sm">Posted: {new Date(job.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Column - 2/3 width */}
          <div className="lg:col-span-2 space-y-6">
            {/* Job Description */}
            <div className="card bg-base-100 shadow-lg border border-base-300">
              <div className="card-body">
                <h2 className="text-2xl font-bold text-base-content mb-4 flex items-center gap-2">
                  <Briefcase className="w-6 h-6 text-primary" />
                  Job Description
                </h2>
                <div className="text-base-content/80 whitespace-pre-line leading-relaxed">
                  {job.description || 'No description available.'}
                </div>
                <div className="flex flex-wrap gap-2 mt-2">
                  <Link
                    href={`/student/prep/for-job/${job.id}`}
                    className="btn btn-outline btn-sm gap-2"
                  >
                    <FileText className="w-4 h-4" />
                    Prep for this role
                  </Link>
                  <button
                    onClick={async () => {
                      setContacting(true);
                      try {
                        const conv = await messagesApi.createConversation({ job_id: job.id });
                        router.push(`/student/messages/${conv.id}`);
                      } catch (err) {
                        setError(handleApiError(err));
                      } finally {
                        setContacting(false);
                      }
                    }}
                    disabled={contacting}
                    className="btn btn-outline btn-sm gap-2"
                  >
                    {contacting ? <span className="loading loading-spinner loading-sm" /> : <Mail className="w-4 h-4" />}
                    Contact company
                  </button>
                </div>
              </div>
            </div>

            {/* Requirements */}
            <div className="card bg-base-100 shadow-lg border border-base-300">
              <div className="card-body">
                <h2 className="text-2xl font-bold text-base-content mb-4 flex items-center gap-2">
                  <CheckCircle className="w-6 h-6 text-success" />
                  Requirements
                </h2>
                {requirements.length > 0 ? (
                  <ul className="space-y-3">
                    {requirements.map((req: string, index: number) => (
                      <li key={index} className="flex items-start gap-3 bg-base-200 rounded-lg p-3">
                        <CheckCircle className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
                        <span className="text-base-content/80">{req}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-base-content/60">No specific requirements listed.</p>
                )}
              </div>
            </div>

            {/* Skill Gap Analysis - Full Width */}
            {requiredSkills.length > 0 && (
              <div className="card bg-gradient-to-br from-secondary/10 to-primary/10 border-2 border-secondary/30 shadow-lg">
                <div className="card-body">
                  <h2 className="text-2xl font-bold text-base-content mb-2 flex items-center gap-2">
                    <TrendingUp className="w-6 h-6 text-secondary" />
                    Required Skills
                  </h2>
                  <p className="text-sm text-base-content/70 mb-6">
                    Skills required for this position:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {requiredSkills.map((skill: string, index: number) => (
                      <div key={index} className="badge badge-primary badge-lg">
                        {skill}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Sidebar - 1/3 width */}
          <div className="space-y-6">
            {/* Company Info Card */}
            <div className="card bg-base-100 shadow-lg border border-base-300">
              <div className="card-body">
                <h2 className="text-xl font-bold text-base-content mb-4 flex items-center gap-2">
                  <Building2 className="w-6 h-6 text-primary" />
                  About Company
                </h2>
                <div className="space-y-4">
                  <div className="p-3 bg-base-200 rounded-lg">
                    <p className="text-xs text-base-content/60 mb-1">Company Name</p>
                    <p className="font-bold text-base-content">{job.company}</p>
                  </div>
                  {job.location && (
                    <div className="p-3 bg-base-200 rounded-lg">
                      <p className="text-xs text-base-content/60 mb-1">Location</p>
                      <p className="font-semibold text-base-content">{job.location}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Apply Button Card */}
            <div className="card bg-gradient-to-r from-primary to-secondary shadow-xl">
              <div className="card-body">
                <button
                  onClick={handleApply}
                  disabled={isApplied}
                  className={`btn w-full text-lg font-bold ${
                    isApplied
                      ? 'btn-success cursor-not-allowed'
                      : 'btn-base-100 text-primary hover:bg-base-200'
                  }`}
                >
                  {isApplied ? (
                    <span className="flex items-center justify-center gap-2">
                      <CheckCircle className="w-6 h-6" />
                      Applied Successfully
                    </span>
                  ) : (
                    `Apply for ${job.title} →`
                  )}
                </button>

                {!isApplied && (
                  <p className="text-xs text-primary-content/80 text-center mt-3">
                    ✨ One click away from your dream job!
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    </ProtectedRoute>
  );
}
