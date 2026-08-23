'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Building2, Mail, Phone, MapPin, Globe, Save, User } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { hrApi } from '@/lib/api';
import { handleApiError } from '@/lib/errors';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

export default function HRProfilePage() {
  const { user, refreshUser } = useAuth();
  const [formData, setFormData] = useState({
    companyName: '',
    email: '',
    phone: '',
    location: '',
    website: '',
    description: '',
    industry: 'Technology',
    companySize: '100-500',
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
      const profile = await hrApi.getProfile();
      setFormData({
        companyName: profile.company_name || '',
        email: profile.email || user?.email || '',
        phone: profile.phone || '',
        location: profile.location || '',
        website: profile.website || '',
        description: profile.description || '',
        industry: profile.industry || 'Technology',
        companySize: profile.company_size || '100-500',
      });
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await hrApi.updateProfile({
        company_name: formData.companyName,
        phone: formData.phone,
        location: formData.location,
        website: formData.website,
        description: formData.description,
        industry: formData.industry,
        company_size: formData.companySize,
      });
      await refreshUser();
      alert('Profile updated successfully!');
    } catch (err) {
      alert('Failed to update profile: ' + handleApiError(err));
    }
  };

  if (isLoading) {
    return (
      <ProtectedRoute requiredRole="hr">
        <div className="flex justify-center items-center py-12">
          <span className="loading loading-spinner loading-lg"></span>
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute requiredRole="hr">
      <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-4xl font-bold text-base-content mb-2">Company Profile</h1>
        <p className="text-base-content/70">Manage your company information</p>
      </motion.div>

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Profile Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Company Information */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="card bg-base-100 shadow-lg"
            >
              <div className="card-body">
                <h2 className="card-title text-2xl text-base-content mb-4">Company Information</h2>
                <div className="space-y-4">
                  <div>
                    <label className="label">
                      <span className="label-text">Company Name</span>
                    </label>
                    <div className="relative">
                      <Building2 className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-base-content/50" />
                      <input
                        type="text"
                        value={formData.companyName}
                        onChange={(e) => setFormData({ ...formData, companyName: e.target.value })}
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
                  <div>
                    <label className="label">
                      <span className="label-text">Website</span>
                    </label>
                    <div className="relative">
                      <Globe className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-base-content/50" />
                      <input
                        type="text"
                        value={formData.website}
                        onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                        className="input input-bordered w-full pl-10"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Company Description */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="card bg-base-100 shadow-lg"
            >
              <div className="card-body">
                <h2 className="card-title text-2xl text-base-content mb-4">Company Description</h2>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="textarea textarea-bordered w-full h-32"
                  placeholder="Tell us about your company..."
                />
              </div>
            </motion.div>

            {/* Additional Details */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="card bg-base-100 shadow-lg"
            >
              <div className="card-body">
                <h2 className="card-title text-2xl text-base-content mb-4">Additional Details</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="label">
                      <span className="label-text">Industry</span>
                    </label>
                    <select
                      value={formData.industry}
                      onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                      className="select select-bordered w-full"
                    >
                      <option>Technology</option>
                      <option>Finance</option>
                      <option>Healthcare</option>
                      <option>Education</option>
                      <option>Retail</option>
                      <option>Other</option>
                    </select>
                  </div>
                  <div>
                    <label className="label">
                      <span className="label-text">Company Size</span>
                    </label>
                    <select
                      value={formData.companySize}
                      onChange={(e) => setFormData({ ...formData, companySize: e.target.value })}
                      className="select select-bordered w-full"
                    >
                      <option>1-10</option>
                      <option>11-50</option>
                      <option>51-100</option>
                      <option>100-500</option>
                      <option>500-1000</option>
                      <option>1000+</option>
                    </select>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* HR Contact */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="card bg-base-100 shadow-lg"
            >
              <div className="card-body">
                <h2 className="card-title text-xl text-base-content mb-4">HR Contact</h2>
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="avatar placeholder">
                      <div className="bg-primary text-primary-content rounded-full w-12">
                        <span>HR</span>
                      </div>
                    </div>
                    <div>
                      <p className="font-semibold text-base-content">HR Manager</p>
                      <p className="text-sm text-base-content/70">{formData.email}</p>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>

        {/* Save Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
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
