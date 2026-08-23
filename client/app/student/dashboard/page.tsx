'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import StatCard from '@/components/ui/StatCard';
import JobCard from '@/components/ui/JobCard';
import ProfileSection from '@/components/student/ProfileSection';
import SkillBar from '@/components/student/SkillBar';
import StudentJobCard from '@/components/student/StudentJobCard';
import { FileText, Calendar, Eye, TrendingUp, Briefcase, Search, Flame } from 'lucide-react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { jobsApi, authApi, candidatesApi, studentApi } from '@/lib/api';
import { Job, StudentApplication } from '@/types/api';
import { handleApiError } from '@/lib/errors';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

export default function StudentDashboard() {
  const { user } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // TODO: Fetch streak from backend once implemented
  const currentStreak = 0;
  const jobMatchesCount = jobs.length;

  const [profileData, setProfileData] = useState<any>(null);
  const [applications, setApplications] = useState<StudentApplication[]>([]);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [fetchedJobs, fetchedProfile, fetchedApps] = await Promise.all([
        jobsApi.list(0, 6),
        candidatesApi.getMe().catch(() => null), // Gracefully handle if candidate record is missing
        studentApi.getApplications().catch(() => []),
      ]);
      setJobs(fetchedJobs);
      setApplications(fetchedApps);
      
      if (fetchedProfile) {
        const fieldsToCheck = [
          fetchedProfile.name,
          fetchedProfile.email,
          fetchedProfile.phone,
          (fetchedProfile as any).education,
          (fetchedProfile as any).location,
          (fetchedProfile as any).bio,
          (fetchedProfile as any).experience,
          fetchedProfile.resume_id,
        ];
        const filledFields = fieldsToCheck.filter(Boolean).length;
        const hasSkills = fetchedProfile.skills_json && fetchedProfile.skills_json.length > 0;
        const totalScore = Math.round(((filledFields + (hasSkills ? 1 : 0)) / 9) * 100);

        setProfileData({
          sid: fetchedProfile.id.toString(),
          name: fetchedProfile.name || user?.email.split('@')[0],
          email: fetchedProfile.email || user?.email,
          phone: fetchedProfile.phone || '',
          college: (fetchedProfile as any).college || '',
          branch: (fetchedProfile as any).branch || '',
          cgpa: (fetchedProfile as any).cgpa || '',
          location: (fetchedProfile as any).location || '',
          resume: {
            name: fetchedProfile.resume_id ? 'Resume Uploaded' : 'No Resume',
            url: '#',
          },
          isVerified: fetchedProfile.is_verified,
          profileCompletion: totalScore,
          skills: fetchedProfile.skills_json || [],
        });
      } else {
        // Fallback if Candidate doesn't exist
        setProfileData({
          sid: user?.id.toString() || 'STU2024001',
          name: user?.email.split('@')[0] || 'Student',
          email: user?.email || '',
          phone: '',
          college: 'Please update your profile',
          branch: '',
          cgpa: '',
          location: '',
          resume: { name: 'No Resume', url: '#' },
          isVerified: false,
          profileCompletion: 20,
          skills: [],
        });
      }
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return '1 day ago';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return `${Math.floor(diffDays / 30)} months ago`;
  };

  return (
    <ProtectedRoute requiredRole="student">
      <div className="space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-3xl sm:text-4xl font-bold text-base-content mb-2">
          Welcome back, {user?.email.split('@')[0] || 'Student'}!
        </h1>
        <p className="text-base-content/70">Here's your job hunting overview</p>
      </motion.div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Profile Score"
          value={`${profileData?.profileCompletion || 0}%`}
          icon={TrendingUp}
          color="success"
          delay={0.1}
        />
        <StatCard
          title="Job Matches"
          value={jobMatchesCount}
          icon={Briefcase}
          color="primary"
          delay={0.2}
        />
        <StatCard
          title="Applications"
          value={applications.length}
          icon={FileText}
          color="secondary"
          delay={0.3}
        />
        <StatCard
          title="Current Streak"
          value={`${currentStreak}🔥`}
          icon={Flame}
          color="warning"
          delay={0.4}
        />
      </div>

      {/* Profile Section and AI Recommended Jobs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {profileData && (
          <ProfileSection 
            profileData={profileData} 
            stats={{ 
              applications: applications.length, 
              interviews: applications.filter(a => a.status === 'interview' || a.status === 'accepted').length 
            }} 
          />
        )}

        {/* AI Recommended Jobs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="card bg-base-100 shadow-lg"
        >
          <div className="card-body">
            <h3 className="card-title text-xl text-base-content mb-4 flex items-center gap-2">
              <Search className="w-5 h-5" />
              AI Recommended Jobs
            </h3>
            {isLoading ? (
              <div className="flex justify-center py-4">
                <span className="loading loading-spinner"></span>
              </div>
            ) : error ? (
              <div className="alert alert-error">
                <span>{error}</span>
              </div>
            ) : jobs.length === 0 ? (
              <p className="text-base-content/70">No recommended jobs at the moment.</p>
            ) : (
              <div className="space-y-3">
                {jobs.slice(0, 3).map((job, index) => (
                  <div key={job.id} onClick={() => window.location.href = `/student/jobs/${job.id}`} className="cursor-pointer">
                    <StudentJobCard 
                      job={{
                        id: job.id,
                        company: job.company,
                        role: job.title,
                        match: '85%',
                        location: job.location || 'Not specified',
                        type: job.salary || 'Full-time',
                        salary: job.salary || 'Not specified',
                      }}
                      delay={0.1 * index}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Skill Insights and Application Status Side by Side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Skill Insights */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="card bg-base-100 shadow-lg"
        >
          <div className="card-body">
            <h3 className="card-title text-xl text-base-content mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Your Skills Overview
            </h3>
            <div className="space-y-3">
              {profileData?.skills && profileData.skills.length > 0 ? (
                profileData.skills.map((skill: string, index: number) => (
                  <SkillBar key={index} skill={skill} level={70 + (index % 3) * 10} />
                ))
              ) : (
                <p className="text-base-content/70">Add skills to your profile to see insights.</p>
              )}
            </div>
            <p className="text-sm text-base-content/70 mt-4 italic">
              💡 View detailed skill gap analysis for each job in the job details page!
            </p>
          </div>
        </motion.div>

        {/* Application Status Overview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="card bg-base-100 shadow-lg"
        >
          <div className="card-body">
            <h2 className="card-title text-xl text-base-content mb-4">Application Status</h2>
            <div className="space-y-4">
              {applications.length === 0 ? (
                <p className="text-base-content/70">No applications yet. Start applying to jobs!</p>
              ) : (
                applications.slice(0, 3).map((app, index) => (
                  <div key={app.id || index} className="flex items-center justify-between p-4 bg-base-200 rounded-xl">
                    <div>
                      <p className="font-semibold text-base-content">{app.job_title}</p>
                      <p className="text-sm text-base-content/70">Applied {formatDate(app.applied_at || new Date().toISOString())}</p>
                    </div>
                    <div className={`badge ${
                      app.status === 'accepted' ? 'badge-success' : 
                      app.status === 'rejected' ? 'badge-error' : 
                      app.status === 'shortlisted' ? 'badge-info' : 'badge-primary'
                    }`}>{app.status.toUpperCase()}</div>
                  </div>
                ))
              )}
            </div>
            <div className="card-actions justify-end mt-4">
              <Link href="/student/applications" className="btn btn-primary btn-sm">
                View All Applications
              </Link>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Recent Job Recommendations */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.7 }}
      >
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-base-content">Recommended for You</h2>
          <Link href="/student/jobs" className="link link-primary">
            View All
          </Link>
        </div>
        {isLoading ? (
          <div className="flex justify-center py-12">
            <span className="loading loading-spinner loading-lg"></span>
          </div>
        ) : error ? (
          <div className="alert alert-error">
            <span>{error}</span>
            <button onClick={fetchDashboardData} className="btn btn-sm btn-ghost">Retry</button>
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-base-content/70">No jobs available at the moment.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {jobs.map((job, index) => (
              <div
                key={job.id}
                onClick={() => window.location.href = `/student/jobs/${job.id}`}
                className="cursor-pointer"
              >
                <JobCard
                  title={job.title}
                  company={job.company}
                  location={job.location || 'Not specified'}
                  type={job.salary || 'Full-time'}
                  posted={formatDate(job.created_at)}
                  description={job.description || ''}
                  delay={index * 0.1}
                />
              </div>
            ))}
          </div>
        )}
      </motion.div>
      </div>
    </ProtectedRoute>
  );
}
