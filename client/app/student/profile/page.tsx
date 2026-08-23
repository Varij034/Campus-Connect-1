'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { User, Mail, Phone, MapPin, Briefcase, GraduationCap, Save } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { authApi, candidatesApi, resumeApi } from '@/lib/api';
import { handleApiError } from '@/lib/errors';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    location: '',
    bio: '',
    skills: [] as string[],
    college: '',
    branch: '',
    graduationYear: '',
    cgpa: '',
    experience: '',
    resume: '',
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchUserData();
  }, []);

  const fetchUserData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const candidate = await candidatesApi.getMe();
      setFormData({
        name: candidate.name || '',
        email: candidate.email || '',
        phone: candidate.phone || '',
        location: (candidate as any).location || '',
        bio: (candidate as any).bio || '',
        skills: Array.isArray(candidate.skills_json) ? candidate.skills_json : ((candidate.skills_json as any)?.skills || []),
        college: (candidate as any).college || '',
        branch: (candidate as any).branch || '',
        graduationYear: (candidate as any).graduation_year || '',
        cgpa: (candidate as any).cgpa || '',
        experience: (candidate as any).experience || '',
        resume: candidate.resume_id || '',
      });
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  const [newSkill, setNewSkill] = useState('');

  const handleAddSkill = () => {
    if (newSkill.trim() && !formData.skills.includes(newSkill.trim())) {
      setFormData({
        ...formData,
        skills: [...formData.skills, newSkill.trim()],
      });
      setNewSkill('');
    }
  };

  const handleRemoveSkill = (skill: string) => {
    setFormData({
      ...formData,
      skills: formData.skills.filter((s) => s !== skill),
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await candidatesApi.updateMe({
        name: formData.name,
        phone: formData.phone,
        location: formData.location,
        bio: formData.bio,
        skills: formData.skills,
        college: formData.college,
        branch: formData.branch,
        graduation_year: formData.graduationYear,
        cgpa: formData.cgpa,
        experience: formData.experience,
      });
      await refreshUser();
      alert('Profile updated successfully!');
    } catch (err) {
      alert('Failed to update profile: ' + handleApiError(err));
    }
  };

  const [isUploading, setIsUploading] = useState(false);
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setIsUploading(true);
    try {
      const result = await resumeApi.upload(file);
      setFormData({ ...formData, resume: result.resume_id || 'Uploaded' });
      alert('Resume uploaded successfully!');
    } catch (err) {
      alert('Failed to upload resume: ' + handleApiError(err));
    } finally {
      setIsUploading(false);
    }
  };

  if (isLoading) {
    return (
      <ProtectedRoute requiredRole="student">
        <div className="flex justify-center items-center py-12">
          <span className="loading loading-spinner loading-lg"></span>
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute requiredRole="student">
      <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-4xl font-bold text-base-content mb-2">My Profile</h1>
        <p className="text-base-content/70">Manage your profile information</p>
      </motion.div>

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Profile Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Basic Information */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="card bg-base-100 shadow-lg"
            >
              <div className="card-body">
                <h2 className="card-title text-2xl text-base-content mb-4">Basic Information</h2>
                <div className="space-y-4">
                  <div>
                    <label className="label">
                      <span className="label-text">Full Name</span>
                    </label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-base-content/50" />
                      <input
                        type="text"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        className="input input-bordered w-full pl-10"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="label">
                      <span className="label-text">Email</span>
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-base-content/50" />
                      <input
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        className="input input-bordered w-full pl-10"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="label">
                      <span className="label-text">Phone</span>
                    </label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-base-content/50" />
                      <input
                        type="tel"
                        value={formData.phone}
                        onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                        className="input input-bordered w-full pl-10"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="label">
                      <span className="label-text">Location</span>
                    </label>
                    <div className="relative">
                      <MapPin className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-base-content/50" />
                      <input
                        type="text"
                        value={formData.location}
                        onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                        className="input input-bordered w-full pl-10"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Bio */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="card bg-base-100 shadow-lg"
            >
              <div className="card-body">
                <h2 className="card-title text-2xl text-base-content mb-4">Bio</h2>
                <textarea
                  value={formData.bio}
                  onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                  className="textarea textarea-bordered w-full h-32"
                  placeholder="Tell us about yourself..."
                />
              </div>
            </motion.div>

            {/* Education & Experience */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="card bg-base-100 shadow-lg"
            >
              <div className="card-body">
                <h2 className="card-title text-2xl text-base-content mb-4">Education & Experience</h2>
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="label"><span className="label-text">College</span></label>
                      <div className="relative">
                        <GraduationCap className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-base-content/50" />
                        <input
                          type="text"
                          value={formData.college}
                          onChange={(e) => setFormData({ ...formData, college: e.target.value })}
                          className="input input-bordered w-full pl-10"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="label"><span className="label-text">Branch</span></label>
                      <input
                        type="text"
                        value={formData.branch}
                        onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
                        className="input input-bordered w-full"
                      />
                    </div>
                    <div>
                      <label className="label"><span className="label-text">Graduation Year</span></label>
                      <input
                        type="text"
                        value={formData.graduationYear}
                        onChange={(e) => setFormData({ ...formData, graduationYear: e.target.value })}
                        className="input input-bordered w-full"
                      />
                    </div>
                    <div>
                      <label className="label"><span className="label-text">CGPA</span></label>
                      <input
                        type="text"
                        value={formData.cgpa}
                        onChange={(e) => setFormData({ ...formData, cgpa: e.target.value })}
                        className="input input-bordered w-full"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="label">
                      <span className="label-text">Experience</span>
                    </label>
                    <div className="relative">
                      <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-base-content/50" />
                      <input
                        type="text"
                        value={formData.experience}
                        onChange={(e) => setFormData({ ...formData, experience: e.target.value })}
                        className="input input-bordered w-full pl-10"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Skills */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="card bg-base-100 shadow-lg"
            >
              <div className="card-body">
                <h2 className="card-title text-xl text-base-content mb-4">Skills</h2>
                <div className="flex flex-wrap gap-2 mb-4">
                  {formData.skills.map((skill) => (
                    <div key={skill} className="badge badge-primary gap-2">
                      {skill}
                      <button
                        type="button"
                        onClick={() => handleRemoveSkill(skill)}
                        className="hover:text-error"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newSkill}
                    onChange={(e) => setNewSkill(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddSkill())}
                    placeholder="Add skill"
                    className="input input-bordered input-sm flex-1"
                  />
                  <button
                    type="button"
                    onClick={handleAddSkill}
                    className="btn btn-primary btn-sm"
                  >
                    Add
                  </button>
                </div>
              </div>
            </motion.div>

            {/* Resume Upload */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.5 }}
              className="card bg-base-100 shadow-lg"
            >
              <div className="card-body">
                <h2 className="card-title text-xl text-base-content mb-4">Resume</h2>
                <input
                  type="file"
                  accept=".pdf,.doc,.docx"
                  onChange={handleFileUpload}
                  disabled={isUploading}
                  className="file-input file-input-bordered w-full"
                />
                {isUploading && <p className="text-sm text-info mt-2">Uploading resume...</p>}
                {formData.resume && (
                  <p className="text-sm text-base-content/70 mt-2">Current: {formData.resume}</p>
                )}
              </div>
            </motion.div>
          </div>
        </div>

        {/* Save Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="flex justify-end"
        >
          <button type="submit" className="btn btn-primary btn-lg">
            <Save className="w-5 h-5 mr-2" />
            Save Changes
          </button>
        </motion.div>
      </form>
      </div>
    </ProtectedRoute>
  );
}
