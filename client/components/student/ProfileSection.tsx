'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, Eye, FileText, User, Mail, Phone, GraduationCap, Award, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import BadgeList from './BadgeList';
import { badgesApi } from '@/lib/api';
import { CandidateBadge } from '@/types/api';

interface ProfileFieldProps {
  label: string;
  value: string;
  icon?: React.ReactNode;
}

const ProfileField = ({ label, value, icon }: ProfileFieldProps) => (
  <div className="flex items-center gap-2">
    {icon && <span className="text-base-content/50">{icon}</span>}
    <span className="text-sm text-base-content/70">{label}:</span>
    <span className="ml-auto font-medium text-base-content">{value}</span>
  </div>
);

interface ProfileData {
  sid: string;
  name: string;
  email: string;
  phone: string;
  college: string;
  branch: string;
  cgpa: string;
  location: string;
  resume?: {
    name: string;
    url: string;
  };
  isVerified?: boolean;
  profileCompletion?: number;
}

interface ProfileSectionProps {
  profileData: ProfileData;
  stats?: {
    applications: number;
    interviews: number;
  };
  onEditProfile?: () => void;
}

export default function ProfileSection({ 
  profileData, 
  stats = { applications: 0, interviews: 0 }, 
  onEditProfile 
}: ProfileSectionProps) {
  const [badges, setBadges] = useState<CandidateBadge[]>([]);
  const { 
    sid, 
    name, 
    email, 
    phone, 
    college,
    branch,
    cgpa,
    resume, 
    isVerified,
    profileCompletion = 85
  } = profileData;

  useEffect(() => {
    badgesApi.getMyBadges().then(setBadges).catch(() => setBadges([]));
  }, []);

  const handleViewResume = () => {
    if (resume) {
      window.open(resume.url, '_blank');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="card bg-base-100 shadow-lg"
    >
      <div className="card-body">
        <div className="flex items-center justify-between mb-4">
          <h3 className="card-title text-xl text-base-content flex items-center gap-2">
            <User className="w-5 h-5" />
            Your Profile
          </h3>
          {isVerified && (
            <div className="badge badge-success gap-2">
              <CheckCircle className="w-4 h-4" />
              Verified
            </div>
          )}
        </div>

        {/* Profile Completion */}
        <div className="mb-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-base-content">Profile Completion</span>
            <span className="text-sm font-bold text-primary">{profileCompletion}%</span>
          </div>
          <progress 
            className="progress progress-primary w-full" 
            value={profileCompletion} 
            max="100"
          ></progress>
        </div>

        <div className="space-y-3">
          <ProfileField label="Student ID" value={sid} icon={<User className="w-4 h-4" />} />
          <ProfileField label="Name" value={name} icon={<User className="w-4 h-4" />} />
          <ProfileField label="Email" value={email} icon={<Mail className="w-4 h-4" />} />
          <ProfileField label="Phone" value={phone} icon={<Phone className="w-4 h-4" />} />
          
          <div className="divider my-2"></div>
          
          <ProfileField label="College" value={college} icon={<GraduationCap className="w-4 h-4" />} />
          <ProfileField label="Branch" value={branch} icon={<Award className="w-4 h-4" />} />
          <ProfileField label="CGPA" value={cgpa} icon={<TrendingUp className="w-4 h-4" />} />
          
          {/* Resume Section */}
          <div className="pt-2 border-t border-base-300">
            <span className="text-sm text-base-content/70 block mb-2 font-medium">Resume:</span>
            {resume ? (
              <div className="flex items-center justify-between bg-success/10 border border-success/30 rounded-lg p-3">
                <div className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-success" />
                  <span className="text-sm font-medium text-success">{resume.name}</span>
                </div>
                <button
                  onClick={handleViewResume}
                  className="btn btn-success btn-sm"
                >
                  <Eye className="w-4 h-4" />
                  View
                </button>
              </div>
            ) : (
              <div className="bg-base-200 border border-base-300 rounded-lg p-3 text-center">
                <span className="text-sm text-base-content/50">No resume uploaded</span>
              </div>
            )}
          </div>

          {/* Skill Badges */}
          <div className="pt-2 border-t border-base-300">
            <span className="text-sm text-base-content/70 block mb-2 font-medium">Skill Badges:</span>
            <BadgeList badges={badges} emptyMessage="Earn badges by passing ATS evaluations." />
          </div>

          {/* Quick Stats */}
          <div className="pt-2 border-t border-base-300">
            <span className="text-sm text-base-content/70 block mb-2 font-medium">Quick Stats:</span>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-primary/10 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-primary">{stats.applications}</div>
                <div className="text-xs text-base-content/70">Applications</div>
              </div>
              <div className="bg-success/10 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-success">{stats.interviews}</div>
                <div className="text-xs text-base-content/70">Interviews</div>
              </div>
            </div>
          </div>
        </div>
        <div className="card-actions justify-end mt-4">
          <Link 
            href="/student/profile"
            className="btn btn-primary"
            onClick={onEditProfile}
          >
            Update Profile
          </Link>
        </div>
      </div>
    </motion.div>
  );
}
