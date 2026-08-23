'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { GraduationCap, Building2, Mail, Lock, User, Phone, ShieldCheck } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { handleApiError } from '@/lib/errors';
import { UserRole } from '@/types/api';
import { authApi } from '@/lib/api';

export default function RegisterPage() {
  const [role, setRole] = useState<'student' | 'hr' | 'tpo'>('student');
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
    company: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { register, user } = useAuth();

  const validate = () => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.email) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Email is invalid';
    }
    
    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }
    
    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    
    if (!validate()) {
      return;
    }

    setIsLoading(true);
    try {
      await register(formData.email, formData.password, role);
      // Auto-login done inside register; get current user and redirect
      const userInfo = await authApi.getMe();
      if (userInfo.role === UserRole.STUDENT) {
        router.push('/student/onboarding');
      } else if (userInfo.role === UserRole.RECRUITER) {
        router.push('/hr/dashboard');
      } else if (userInfo.role === UserRole.TPO) {
        router.push('/tpo/dashboard');
      } else {
        router.push('/student/onboarding');
      }
    } catch (error) {
      const errorMessage = handleApiError(error);
      setErrors({ general: errorMessage });
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: '' }));
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-base-200 via-base-100 to-base-200 p-4 py-8">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="card bg-base-100 shadow-2xl w-full max-w-md"
      >
        <div className="card-body">
          {/* Header */}
          <div className="text-center mb-6">
            <motion.div
              initial={{ y: -20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="flex justify-center mb-4"
            >
              <GraduationCap className="w-12 h-12 text-primary" />
            </motion.div>
            <h1 className="text-3xl font-bold text-base-content mb-2">Create Account</h1>
            <p className="text-base-content/70">Join Campus Connect today</p>
          </div>

          {/* Role Selection */}
          <div className="flex flex-wrap gap-2 mb-6">
            <button
              type="button"
              onClick={() => setRole('student')}
              className={`flex-1 min-w-[80px] btn ${
                role === 'student' ? 'btn-primary' : 'btn-outline'
              }`}
            >
              <GraduationCap className="w-5 h-5 mr-2" />
              Student
            </button>
            <button
              type="button"
              onClick={() => setRole('hr')}
              className={`flex-1 min-w-[80px] btn ${
                role === 'hr' ? 'btn-secondary' : 'btn-outline'
              }`}
            >
              <Building2 className="w-5 h-5 mr-2" />
              HR
            </button>
            <button
              type="button"
              onClick={() => setRole('tpo')}
              className={`flex-1 min-w-[80px] btn ${
                role === 'tpo' ? 'btn-accent' : 'btn-outline'
              }`}
            >
              <ShieldCheck className="w-5 h-5 mr-2" />
              TPO
            </button>
          </div>

          {/* Error Message */}
          {errors.general && (
            <div className="alert alert-error mb-4">
              <span>{errors.general}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">

            {(role === 'hr' || role === 'tpo') && (
              <div>
                <label className="label">
                  <span className="label-text">{role === 'tpo' ? 'Institution' : 'Company Name'}</span>
                </label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-base-content/50" />
                  <input
                    type="text"
                    value={formData.company}
                    onChange={(e) => handleChange('company', e.target.value)}
                    placeholder={role === 'tpo' ? 'Your College / University' : 'Company Inc.'}
                    className={`input input-bordered w-full pl-10 ${
                      errors.company ? 'input-error' : ''
                    }`}
                  />
                </div>
                {errors.company && (
                  <label className="label">
                    <span className="label-text-alt text-error">{errors.company}</span>
                  </label>
                )}
              </div>
            )}

            <div>
              <label className="label">
                <span className="label-text">Email</span>
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-base-content/50" />
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleChange('email', e.target.value)}
                  placeholder="your.email@example.com"
                  className={`input input-bordered w-full pl-10 ${
                    errors.email ? 'input-error' : ''
                  }`}
                />
              </div>
              {errors.email && (
                <label className="label">
                  <span className="label-text-alt text-error">{errors.email}</span>
                </label>
              )}
            </div>


            <div>
              <label className="label">
                <span className="label-text">Password</span>
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-base-content/50" />
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => handleChange('password', e.target.value)}
                  placeholder="••••••••"
                  className={`input input-bordered w-full pl-10 ${
                    errors.password ? 'input-error' : ''
                  }`}
                />
              </div>
              {errors.password && (
                <label className="label">
                  <span className="label-text-alt text-error">{errors.password}</span>
                </label>
              )}
            </div>

            <div>
              <label className="label">
                <span className="label-text">Confirm Password</span>
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-base-content/50" />
                <input
                  type="password"
                  value={formData.confirmPassword}
                  onChange={(e) => handleChange('confirmPassword', e.target.value)}
                  placeholder="••••••••"
                  className={`input input-bordered w-full pl-10 ${
                    errors.confirmPassword ? 'input-error' : ''
                  }`}
                />
              </div>
              {errors.confirmPassword && (
                <label className="label">
                  <span className="label-text-alt text-error">{errors.confirmPassword}</span>
                </label>
              )}
            </div>

            <button 
              type="submit" 
              className="btn btn-primary w-full mt-6"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <span className="loading loading-spinner loading-sm"></span>
                  Creating account...
                </>
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          <div className="divider">OR</div>

          <p className="text-center text-sm text-base-content/70">
            Already have an account?{' '}
            <Link href="/auth/login" className="link link-primary font-semibold">
              Sign in
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
