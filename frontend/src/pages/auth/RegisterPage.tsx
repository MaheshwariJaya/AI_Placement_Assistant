import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { orgApi } from '../../services/api';
import { UserRole, RegisterPayload, Institution, Department } from '../../types';
import {
  GraduationCap,
  Briefcase,
  AlertCircle,
  UserPlus,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  Building,
} from 'lucide-react';
import { ThemeToggle } from '../../components/common/ThemeToggle';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [role, setRole] = useState<UserRole>('student');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Student-specific fields
  const [institutionId, setInstitutionId] = useState<number>(0);
  const [departmentId, setDepartmentId] = useState<number>(0);
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loadingInstitutions, setLoadingInstitutions] = useState<boolean>(false);
  const [loadingDepartments, setLoadingDepartments] = useState<boolean>(false);
  const [rollNumber, setRollNumber] = useState('');
  const [graduationYear, setGraduationYear] = useState<number>(new Date().getFullYear());
  const [cgpa, setCgpa] = useState<string>('');
  const [activeBacklogs, setActiveBacklogs] = useState<number>(0);

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Load active institutions from live API on mount
  useEffect(() => {
    let isMounted = true;
    setLoadingInstitutions(true);
    orgApi.getInstitutions()
      .then((data) => {
        if (!isMounted) return;
        setInstitutions(data);
        if (data && data.length > 0) {
          setInstitutionId(data[0].id);
        }
      })
      .catch((err) => {
        console.error('Failed to load institutions from API:', err);
        if (isMounted) {
          setError('Failed to load collegiate institutions. Please verify the backend connection.');
        }
      })
      .finally(() => {
        if (isMounted) setLoadingInstitutions(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Reload departments dynamically whenever selected institution changes
  useEffect(() => {
    if (!institutionId) {
      setDepartments([]);
      setDepartmentId(0);
      return;
    }

    let isMounted = true;
    setLoadingDepartments(true);
    orgApi.getDepartments(institutionId)
      .then((data) => {
        if (!isMounted) return;
        setDepartments(data);
        if (data && data.length > 0) {
          setDepartmentId(data[0].id);
        } else {
          setDepartmentId(0);
        }
      })
      .catch((err) => {
        console.error('Failed to load departments from API:', err);
        if (isMounted) {
          setDepartments([]);
          setDepartmentId(0);
        }
      })
      .finally(() => {
        if (isMounted) setLoadingDepartments(false);
      });

    return () => {
      isMounted = false;
    };
  }, [institutionId]);

  // Live password validation checks
  const hasMinLength = password.length >= 8;
  const hasDigit = /\d/.test(password);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
  const passwordsMatch = password.length > 0 && password === confirmPassword;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!hasMinLength || !hasDigit || !hasSpecial) {
      setError('Password does not fulfill security requirements.');
      return;
    }

    if (!passwordsMatch) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);

    try {
      const payload: RegisterPayload = {
        email,
        password,
        full_name: fullName,
        phone: phone || undefined,
        role,
      };

      if (role === 'student') {
        payload.institution_id = Number(institutionId);
        payload.department_id = Number(departmentId);
        payload.student_data = {
          roll_number: rollNumber.trim(),
          graduation_year: Number(graduationYear),
          cgpa: parseFloat(cgpa),
          active_backlogs: Number(activeBacklogs),
          total_backlogs: Number(activeBacklogs),
        };
      }

      const user = await register(payload);
      navigate(`/dashboard/${user.role}`, { replace: true });
    } catch (err: any) {
      const data = err.response?.data;
      const detail = data?.detail;
      const errorObj = data?.error;
      if (typeof detail === 'object' && detail?.message) {
        setError(detail.message);
      } else if (typeof detail === 'string') {
        setError(detail);
      } else if (errorObj?.details?.validation_errors?.length > 0) {
        const firstErr = errorObj.details.validation_errors[0];
        setError(`${firstErr.message} (${firstErr.field})`);
      } else if (errorObj?.message) {
        setError(errorObj.message);
      } else if (err.message) {
        setError(`Registration error: ${err.message}`);
      } else {
        setError('Registration failed. Please check your information or connection.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-slate-50 dark:bg-slate-950 relative transition-colors">
      <div className="absolute top-4 right-4 sm:top-6 sm:right-6">
        <ThemeToggle />
      </div>
      <div className="sm:mx-auto sm:w-full sm:max-w-xl text-center">
        <div className="inline-flex items-center justify-center p-3 bg-indigo-600 text-white rounded-2xl shadow-md mb-4">
          <UserPlus className="w-8 h-8" />
        </div>
        <h2 className="text-3xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">Create Your Account</h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          Join the Placement Intelligence Platform
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-xl px-4 sm:px-0">
        <Card className="py-8 px-6 sm:px-10 shadow-lg border-slate-200 dark:border-slate-800">
          {/* Role Selection Tabs */}
          <div className="flex rounded-lg bg-slate-100 dark:bg-slate-800 p-1 mb-6 border border-slate-200 dark:border-slate-700">
            <button
              type="button"
              onClick={() => setRole('student')}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-md text-sm font-semibold transition-all ${
                role === 'student'
                  ? 'bg-white dark:bg-slate-900 text-indigo-700 dark:text-indigo-400 shadow-sm'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              <GraduationCap className="w-4 h-4" />
              Student Candidate
            </button>
            <button
              type="button"
              onClick={() => setRole('recruiter')}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-md text-sm font-semibold transition-all ${
                role === 'recruiter'
                  ? 'bg-white dark:bg-slate-900 text-emerald-700 dark:text-emerald-400 shadow-sm'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              <Briefcase className="w-4 h-4" />
              Company Recruiter
            </button>
          </div>

          {error && (
            <div className="mb-6 p-4 rounded-lg bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-rose-600 dark:text-rose-400 mt-0.5 shrink-0" />
              <div className="text-sm text-rose-800 dark:text-rose-200 leading-snug">{error}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Full Name"
                type="text"
                required
                placeholder="Dr. John Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                disabled={loading}
              />
              <Input
                label="Phone Number"
                type="tel"
                placeholder="+1 555-0199"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                disabled={loading}
              />
            </div>

            <Input
              label="Email Address"
              type="email"
              required
              placeholder={role === 'student' ? 'student@institution.edu' : 'recruiter@company.com'}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
            />

            {/* Student-specific Academic Details */}
            {role === 'student' && (
              <div className="p-4 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-lg space-y-4">
                <div className="text-xs font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
                  <Building className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                  Academic Enrollment Scoping
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Institution</label>
                    <select
                      value={institutionId || ''}
                      onChange={(e) => setInstitutionId(Number(e.target.value))}
                      disabled={loading || loadingInstitutions}
                      className="w-full text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-slate-900 dark:text-slate-100 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed"
                    >
                      {institutions.length === 0 ? (
                        <option value="">{loadingInstitutions ? 'Loading institutions...' : 'No institutions available'}</option>
                      ) : (
                        institutions.map((inst) => (
                          <option key={inst.id} value={inst.id}>
                            {inst.name} ({inst.code})
                          </option>
                        ))
                      )}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Department</label>
                    <select
                      value={departmentId || ''}
                      onChange={(e) => setDepartmentId(Number(e.target.value))}
                      disabled={loading || loadingDepartments || departments.length === 0}
                      className="w-full text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-slate-900 dark:text-slate-100 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed"
                    >
                      {departments.length === 0 ? (
                        <option value="">{loadingDepartments ? 'Loading departments...' : 'No departments available'}</option>
                      ) : (
                        departments.map((dept) => (
                          <option key={dept.id} value={dept.id}>
                            {dept.name} ({dept.code})
                          </option>
                        ))
                      )}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <Input
                    label="Roll Number"
                    type="text"
                    required
                    placeholder="2026CS101"
                    value={rollNumber}
                    onChange={(e) => setRollNumber(e.target.value)}
                    disabled={loading}
                  />

                  <Input
                    label="Graduation Year"
                    type="number"
                    required
                    min={2020}
                    max={2035}
                    value={graduationYear}
                    onChange={(e) => setGraduationYear(Number(e.target.value))}
                    disabled={loading}
                  />

                  <Input
                    label="CGPA (0 - 10)"
                    type="number"
                    step="0.01"
                    min="0"
                    max="10"
                    required
                    placeholder="8.50"
                    value={cgpa}
                    onChange={(e) => setCgpa(e.target.value)}
                    disabled={loading}
                  />
                </div>

                <div>
                  <Input
                    label="Active Academic Backlogs"
                    type="number"
                    min={0}
                    value={activeBacklogs}
                    onChange={(e) => setActiveBacklogs(Number(e.target.value))}
                    disabled={loading}
                  />
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Password"
                type="password"
                required
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
              />
              <Input
                label="Confirm Password"
                type="password"
                required
                placeholder="••••••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={loading}
              />
            </div>

            {/* Password Validation Checklist */}
            <div className="p-3 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-lg text-xs space-y-1">
              <div className="font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-1.5 mb-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                Security Standards:
              </div>
              <div className="flex items-center gap-2">
                {hasMinLength ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                )}
                <span className={hasMinLength ? 'text-emerald-700 dark:text-emerald-400 font-medium' : 'text-slate-500 dark:text-slate-400'}>
                  At least 8 characters
                </span>
              </div>
              <div className="flex items-center gap-2">
                {hasDigit ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                )}
                <span className={hasDigit ? 'text-emerald-700 dark:text-emerald-400 font-medium' : 'text-slate-500 dark:text-slate-400'}>
                  Contains at least one number (0-9)
                </span>
              </div>
              <div className="flex items-center gap-2">
                {hasSpecial ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                )}
                <span className={hasSpecial ? 'text-emerald-700 dark:text-emerald-400 font-medium' : 'text-slate-500 dark:text-slate-400'}>
                  Contains at least one special character (!@#$%^&*)
                </span>
              </div>
              {password.length > 0 && confirmPassword.length > 0 && (
                <div className="flex items-center gap-2">
                  {passwordsMatch ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-rose-500 dark:text-rose-400" />
                  )}
                  <span className={passwordsMatch ? 'text-emerald-700 dark:text-emerald-400 font-medium' : 'text-rose-600 dark:text-rose-400'}>
                    {passwordsMatch ? 'Passwords match' : 'Passwords do not match'}
                  </span>
                </div>
              )}
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full flex items-center justify-center gap-2 shadow-md mt-6"
              disabled={loading || !hasMinLength || !hasDigit || !hasSpecial || !passwordsMatch}
            >
              <UserPlus className="w-4 h-4" />
              {loading ? 'Creating Account...' : 'Complete Registration'}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
            Already have an account?{' '}
            <Link to="/login" className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 font-semibold">
              Sign In
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
};

