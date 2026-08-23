'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  User,
  MapPin,
  Phone,
  GraduationCap,
  Briefcase,
  FileText,
  UploadCloud,
  CheckCircle,
  ArrowRight,
  ArrowLeft,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { candidatesApi, resumeApi } from '@/lib/api';
import { handleApiError } from '@/lib/errors';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

export default function StudentOnboarding() {
  const router = useRouter();
  const { user, refreshUser } = useAuth();
  
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    location: '',
    college: '',
    branch: '',
    graduationYear: '',
    cgpa: '',
    bio: '',
    experience: '',
    skills: [] as string[],
  });
  
  const [newSkill, setNewSkill] = useState('');
  const [resumeFile, setResumeFile] = useState<File | null>(null);

  const handleNext = () => setStep((prev) => Math.min(prev + 1, 4));
  const handleBack = () => setStep((prev) => Math.max(prev - 1, 1));

  const handleAddSkill = () => {
    if (newSkill.trim() && !formData.skills.includes(newSkill.trim())) {
      setFormData({ ...formData, skills: [...formData.skills, newSkill.trim()] });
      setNewSkill('');
    }
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setFormData({
      ...formData,
      skills: formData.skills.filter((skill) => skill !== skillToRemove),
    });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setResumeFile(e.target.files[0]);
    }
  };

  const handleSubmit = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // 1. Update Profile
      await candidatesApi.updateMe({
        name: formData.name || user?.email.split('@')[0],
        phone: formData.phone,
        location: formData.location,
        college: formData.college,
        branch: formData.branch,
        graduation_year: formData.graduationYear,
        cgpa: formData.cgpa,
        bio: formData.bio,
        experience: formData.experience,
        skills: formData.skills,
      });

      // 2. Upload Resume if provided
      if (resumeFile) {
        await resumeApi.upload(resumeFile);
      }

      await refreshUser();
      
      // Route to dashboard
      router.push('/student/dashboard');
    } catch (err) {
      setError(handleApiError(err));
      setIsLoading(false);
    }
  };

  const slideVariants = {
    hidden: { opacity: 0, x: 50 },
    visible: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -50 },
  };

  return (
    <ProtectedRoute requiredRole="student">
      <div className="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200 py-12 px-4 flex justify-center items-center">
        <div className="max-w-2xl w-full">
          {/* Header & Progress */}
          <div className="mb-10 text-center">
            <h1 className="text-4xl font-extrabold text-base-content mb-4 tracking-tight">
              Let's set up your profile 🚀
            </h1>
            <p className="text-base-content/70">Complete these steps to unlock AI job matching.</p>
            
            <div className="mt-8 relative pt-1">
              <div className="overflow-hidden h-2 mb-4 text-xs flex rounded-full bg-base-300">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(step / 4) * 100}%` }}
                  transition={{ duration: 0.5 }}
                  className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-primary"
                ></motion.div>
              </div>
              <div className="flex justify-between text-xs font-semibold text-base-content/60 px-1">
                <span className={step >= 1 ? 'text-primary' : ''}>Basics</span>
                <span className={step >= 2 ? 'text-primary' : ''}>Education</span>
                <span className={step >= 3 ? 'text-primary' : ''}>Experience</span>
                <span className={step >= 4 ? 'text-primary' : ''}>Skills</span>
              </div>
            </div>
          </div>

          {/* Form Card */}
          <div className="card bg-base-100 shadow-2xl border border-base-300 overflow-hidden min-h-[450px]">
            <div className="card-body relative p-8">
              
              {error && (
                <div className="alert alert-error shadow-lg mb-6">
                  <span>{error}</span>
                </div>
              )}

              <AnimatePresence mode="wait">
                {step === 1 && (
                  <motion.div
                    key="step1"
                    variants={slideVariants}
                    initial="hidden"
                    animate="visible"
                    exit="exit"
                    className="space-y-6"
                  >
                    <h2 className="text-2xl font-bold flex items-center gap-2 mb-6">
                      <User className="w-6 h-6 text-primary" /> Basic Info
                    </h2>
                    
                    <label className="form-control w-full">
                      <div className="label"><span className="label-text font-semibold flex items-center gap-2"><User className="w-4 h-4"/> Full Name</span></div>
                      <input 
                        type="text" 
                        className="input input-bordered focus:input-primary w-full" 
                        placeholder="e.g. John Doe"
                        value={formData.name}
                        onChange={(e) => setFormData({...formData, name: e.target.value})}
                      />
                    </label>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <label className="form-control w-full">
                        <div className="label"><span className="label-text font-semibold flex items-center gap-2"><Phone className="w-4 h-4"/> Phone</span></div>
                        <input 
                          type="tel" 
                          className="input input-bordered focus:input-primary w-full" 
                          placeholder="+1 234 567 8900"
                          value={formData.phone}
                          onChange={(e) => setFormData({...formData, phone: e.target.value})}
                        />
                      </label>
                      <label className="form-control w-full">
                        <div className="label"><span className="label-text font-semibold flex items-center gap-2"><MapPin className="w-4 h-4"/> Location</span></div>
                        <input 
                          type="text" 
                          className="input input-bordered focus:input-primary w-full" 
                          placeholder="City, Country"
                          value={formData.location}
                          onChange={(e) => setFormData({...formData, location: e.target.value})}
                        />
                      </label>
                    </div>
                  </motion.div>
                )}

                {step === 2 && (
                  <motion.div
                    key="step2"
                    variants={slideVariants}
                    initial="hidden"
                    animate="visible"
                    exit="exit"
                    className="space-y-6"
                  >
                    <h2 className="text-2xl font-bold flex items-center gap-2 mb-6">
                      <GraduationCap className="w-6 h-6 text-secondary" /> Education
                    </h2>
                    
                    <label className="form-control w-full">
                      <div className="label"><span className="label-text font-semibold">University / College</span></div>
                      <input 
                        type="text" 
                        className="input input-bordered focus:input-secondary w-full" 
                        placeholder="e.g. Stanford University"
                        value={formData.college}
                        onChange={(e) => setFormData({...formData, college: e.target.value})}
                      />
                    </label>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <label className="form-control w-full">
                        <div className="label"><span className="label-text font-semibold">Degree / Branch</span></div>
                        <input 
                          type="text" 
                          className="input input-bordered focus:input-secondary w-full" 
                          placeholder="e.g. B.S. Computer Science"
                          value={formData.branch}
                          onChange={(e) => setFormData({...formData, branch: e.target.value})}
                        />
                      </label>
                      <label className="form-control w-full">
                        <div className="label"><span className="label-text font-semibold">Graduation Year</span></div>
                        <input 
                          type="text" 
                          className="input input-bordered focus:input-secondary w-full" 
                          placeholder="e.g. 2024"
                          value={formData.graduationYear}
                          onChange={(e) => setFormData({...formData, graduationYear: e.target.value})}
                        />
                      </label>
                      <label className="form-control w-full">
                        <div className="label"><span className="label-text font-semibold">CGPA</span></div>
                        <input 
                          type="text" 
                          className="input input-bordered focus:input-secondary w-full" 
                          placeholder="e.g. 8.5"
                          value={formData.cgpa}
                          onChange={(e) => setFormData({...formData, cgpa: e.target.value})}
                        />
                      </label>
                    </div>
                  </motion.div>
                )}

                {step === 3 && (
                  <motion.div
                    key="step3"
                    variants={slideVariants}
                    initial="hidden"
                    animate="visible"
                    exit="exit"
                    className="space-y-6"
                  >
                    <h2 className="text-2xl font-bold flex items-center gap-2 mb-6">
                      <Briefcase className="w-6 h-6 text-accent" /> Experience & Bio
                    </h2>
                    
                    <label className="form-control w-full">
                      <div className="label"><span className="label-text font-semibold">Years of Experience</span></div>
                      <input 
                        type="text" 
                        className="input input-bordered focus:input-accent w-full" 
                        placeholder="e.g. 1 year, Internships, or Entry Level"
                        value={formData.experience}
                        onChange={(e) => setFormData({...formData, experience: e.target.value})}
                      />
                    </label>
                    
                    <label className="form-control w-full">
                      <div className="label"><span className="label-text font-semibold">Short Bio</span></div>
                      <textarea 
                        className="textarea textarea-bordered h-28 focus:textarea-accent w-full" 
                        placeholder="Tell recruiters a bit about your passions and goals..."
                        value={formData.bio}
                        onChange={(e) => setFormData({...formData, bio: e.target.value})}
                      ></textarea>
                    </label>
                  </motion.div>
                )}

                {step === 4 && (
                  <motion.div
                    key="step4"
                    variants={slideVariants}
                    initial="hidden"
                    animate="visible"
                    exit="exit"
                    className="space-y-6"
                  >
                    <h2 className="text-2xl font-bold flex items-center gap-2 mb-6">
                      <FileText className="w-6 h-6 text-info" /> Skills & Resume
                    </h2>
                    
                    <label className="form-control w-full">
                      <div className="label"><span className="label-text font-semibold">Top Skills</span></div>
                      <div className="flex flex-wrap gap-2 mb-3">
                        {formData.skills.map((skill) => (
                          <div key={skill} className="badge badge-info gap-1 p-3 shadow-sm font-medium">
                            {skill}
                            <button type="button" onClick={() => handleRemoveSkill(skill)} className="hover:text-error ml-1 opacity-70 hover:opacity-100 transition">×</button>
                          </div>
                        ))}
                      </div>
                      <div className="flex gap-2 w-full">
                        <input 
                          type="text" 
                          className="input input-bordered focus:input-info flex-1" 
                          placeholder="e.g. React, Python, Machine Learning"
                          value={newSkill}
                          onChange={(e) => setNewSkill(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddSkill())}
                        />
                        <button type="button" onClick={handleAddSkill} className="btn btn-outline btn-info">Add</button>
                      </div>
                    </label>

                    <div className="divider"></div>

                    <div className="form-control">
                      <label className="label"><span className="label-text font-semibold">Resume (Optional but highly recommended)</span></label>
                      <div className="border-2 border-dashed border-base-300 rounded-xl p-8 text-center hover:bg-base-200/50 hover:border-primary transition-colors cursor-pointer relative group">
                        <input 
                          type="file" 
                          accept=".pdf,.doc,.docx"
                          onChange={handleFileChange}
                          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        />
                        <div className="flex flex-col items-center gap-3">
                          <UploadCloud className={`w-10 h-10 ${resumeFile ? 'text-success' : 'text-base-content/40'} group-hover:text-primary transition-colors`} />
                          <div className="text-sm">
                            {resumeFile ? (
                              <span className="font-bold text-success flex items-center justify-center gap-2"><CheckCircle className="w-4 h-4"/> {resumeFile.name}</span>
                            ) : (
                              <span className="text-base-content/60 font-medium">Click to upload or drag and drop<br/><span className="text-xs">PDF or DOCX (max 5MB)</span></span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                  </motion.div>
                )}
              </AnimatePresence>

              {/* Navigation */}
              <div className="mt-10 flex justify-between items-center pt-6 border-t border-base-200">
                <button 
                  className={`btn btn-ghost ${step === 1 ? 'invisible' : ''}`}
                  onClick={handleBack}
                  disabled={isLoading}
                >
                  <ArrowLeft className="w-4 h-4 mr-2" /> Back
                </button>
                
                {step < 4 ? (
                  <button className="btn btn-primary px-8 shadow-lg shadow-primary/30" onClick={handleNext}>
                    Next <ArrowRight className="w-4 h-4 ml-2" />
                  </button>
                ) : (
                  <button 
                    className="btn btn-success px-8 text-white shadow-lg shadow-success/30" 
                    onClick={handleSubmit}
                    disabled={isLoading}
                  >
                    {isLoading ? <span className="loading loading-spinner loading-sm"></span> : 'Complete Setup'}
                  </button>
                )}
              </div>
            </div>
          </div>
          
        </div>
      </div>
    </ProtectedRoute>
  );
}
