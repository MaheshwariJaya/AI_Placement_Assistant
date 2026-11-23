import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { Card, CardHeader } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { useAuth } from '../../context/AuthContext';
import { ThemeMode, useTheme } from '../../context/ThemeContext';
import { authApi, userApi } from '../../services/api';
import {
  AlertCircle,
  BadgeCheck,
  Building,
  CheckCircle2,
  KeyRound,
  LogOut,
  Monitor,
  Moon,
  Save,
  Shield,
  Sliders,
  Sun,
  User as UserIcon,
  XCircle,
} from 'lucide-react';

type SettingsTab = 'profile' | 'appearance' | 'security';

const ROLE_WORKSPACE_SHORTCUT: Record<string, { label: string; to: string }> = {
  student: { label: 'Open Academic Portfolio', to: '/student/profile' },
  tpo: { label: 'Manage Recruitment Drives', to: '/tpo/jobs' },
  recruiter: { label: 'Company & Job Postings', to: '/recruiter/jobs' },
  admin: { label: 'System Registry Overview', to: '/admin' },
};

export const SettingsPage: React.FC = () => {
  const { user, logout, logoutAll, refreshUser } = useAuth();
  const {
    theme,
    resolvedTheme,
    setTheme,
    compactMode,
    setCompactMode,
    reducedMotion,
    setReducedMotion,
    confirmActions,
    setConfirmActions,
  } = useTheme();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const paramTab = searchParams.get('tab');
  const initialTab: SettingsTab =
    paramTab === 'appearance' || paramTab === 'security' || paramTab === 'profile'
      ? paramTab
      : 'profile';
  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);

  // Sync tab with URL query param
  useEffect(() => {
    if (paramTab === 'appearance' || paramTab === 'security' || paramTab === 'profile') {
      setActiveTab(paramTab);
    }
  }, [paramTab]);

  const handleTabChange = (tab: SettingsTab) => {
    setActiveTab(tab);
    setSearchParams({ tab }, { replace: true });
    setStatusMessage(null);
  };

  // Profile Form State
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [phone, setPhone] = useState(user?.phone || '');
  const [savingProfile, setSavingProfile] = useState(false);

  // Sync user fields when user refreshes
  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '');
      setPhone(user.phone || '');
    }
  }, [user?.full_name, user?.phone]);

  // Change Password Form State
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [savingPassword, setSavingPassword] = useState(false);

  // Session actions
  const [signingOut, setSigningOut] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const hasMinLength = newPassword.length >= 8;
  const hasDigit = /\d/.test(newPassword);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(newPassword);
  const passwordsMatch = newPassword.length > 0 && newPassword === confirmNewPassword;

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatusMessage(null);

    if (fullName.trim().length < 2) {
      setStatusMessage({ type: 'error', text: 'Full name must be at least 2 characters.' });
      return;
    }

    setSavingProfile(true);
    try {
      await userApi.updateMe({
        full_name: fullName.trim(),
        phone: phone.trim(),
      });
      await refreshUser();
      setStatusMessage({ type: 'success', text: 'Account profile saved successfully.' });
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail?.message ||
        err?.response?.data?.detail ||
        'Failed to update account profile.';
      setStatusMessage({ type: 'error', text: String(msg) });
    } finally {
      setSavingProfile(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatusMessage(null);

    if (!currentPassword) {
      setStatusMessage({ type: 'error', text: 'Please enter your current password.' });
      return;
    }
    if (!hasMinLength || !hasDigit || !hasSpecial) {
      setStatusMessage({ type: 'error', text: 'New password does not satisfy complexity rules.' });
      return;
    }
    if (!passwordsMatch) {
      setStatusMessage({ type: 'error', text: 'New password and confirmation do not match.' });
      return;
    }

    setSavingPassword(true);
    try {
      const res = await authApi.changePassword(currentPassword, newPassword);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmNewPassword('');
      setStatusMessage({
        type: 'success',
        text: res.message || 'Password updated successfully.',
      });
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail?.message ||
        err?.response?.data?.detail ||
        'Failed to update password.';
      setStatusMessage({ type: 'error', text: String(msg) });
    } finally {
      setSavingPassword(false);
    }
  };

  const handleSignOutThisDevice = async () => {
    setSigningOut(true);
    try {
      await logout();
      navigate('/login');
    } finally {
      setSigningOut(false);
    }
  };

  const handleSignOutAllDevices = async () => {
    if (
      confirmActions &&
      !window.confirm('Sign out across all browsers and revoke all active refresh sessions?')
    ) {
      return;
    }
    setSigningOut(true);
    try {
      await logoutAll();
      navigate('/login');
    } finally {
      setSigningOut(false);
    }
  };

  const role = user?.role || 'student';
  const shortcut = ROLE_WORKSPACE_SHORTCUT[role];

  const themeOptions: {
    mode: ThemeMode;
    label: string;
    description: string;
    icon: React.ComponentType<{ className?: string }>;
    previewClass: string;
  }[] = [
    {
      mode: 'light',
      label: 'Light Mode',
      description: 'Crisp high-clarity bright workspace',
      icon: Sun,
      previewClass: 'bg-slate-50 border-slate-200 text-slate-800',
    },
    {
      mode: 'dark',
      label: 'Dark Mode',
      description: 'Low-glare slate theme for extended focus',
      icon: Moon,
      previewClass: 'bg-slate-900 border-slate-700 text-slate-100',
    },
    {
      mode: 'system',
      label: 'System Default',
      description: `Follows your OS setting (currently ${resolvedTheme})`,
      icon: Monitor,
      previewClass: 'bg-gradient-to-r from-slate-50 via-slate-200 to-slate-900 border-slate-400 text-slate-900',
    },
  ];

  return (
    <DashboardLayout
      role={role}
      title="Account & App Settings"
      subtitle="Manage your identity details, light/dark appearance preferences, password security, and active sessions."
    >
      {/* Status Banner */}
      {statusMessage && (
        <div
          className={`p-4 rounded-xl mb-6 flex items-center justify-between text-xs font-semibold ${
            statusMessage.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-200 border border-emerald-200 dark:border-emerald-800'
              : 'bg-rose-50 dark:bg-rose-950/60 text-rose-800 dark:text-rose-200 border border-rose-200 dark:border-rose-800'
          }`}
        >
          <div className="flex items-center gap-2">
            {statusMessage.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
            )}
            <span>{statusMessage.text}</span>
          </div>
          <button
            type="button"
            onClick={() => setStatusMessage(null)}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            ✕
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 mb-6 bg-white dark:bg-slate-900 p-1.5 rounded-xl border border-slate-200 dark:border-slate-800 w-fit">
        <button
          type="button"
          onClick={() => handleTabChange('profile')}
          className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
            activeTab === 'profile'
              ? 'bg-brand-600 text-white shadow-xs'
              : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <UserIcon className="w-3.5 h-3.5" />
          Account Profile
        </button>
        <button
          type="button"
          onClick={() => handleTabChange('appearance')}
          className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
            activeTab === 'appearance'
              ? 'bg-brand-600 text-white shadow-xs'
              : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Sliders className="w-3.5 h-3.5" />
          Appearance &amp; Preferences
        </button>
        <button
          type="button"
          onClick={() => handleTabChange('security')}
          className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
            activeTab === 'security'
              ? 'bg-brand-600 text-white shadow-xs'
              : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Shield className="w-3.5 h-3.5" />
          Security &amp; Sessions
        </button>
      </div>

      {/* Tab 1: Account Profile */}
      {activeTab === 'profile' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Card>
              <CardHeader
                title="Personal Information"
                subtitle="Changes here save directly to your account and update across all portals."
              />
              <form onSubmit={handleSaveProfile} className="space-y-4">
                <Input
                  label="Full Name"
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Your full name"
                />
                <Input
                  label="Phone Number"
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+91 9876543210"
                  helperText="Optional contact number for placement coordinators or recruiters."
                />
                <Input
                  label="Registered Email Address"
                  type="email"
                  value={user?.email || ''}
                  disabled
                  helperText="Primary account login identifier (managed by institutional registry)."
                />
                <div className="pt-2 flex flex-wrap items-center justify-between gap-3">
                  {shortcut && (
                    <Link
                      to={shortcut.to}
                      className="text-xs font-semibold text-brand-600 dark:text-brand-400 hover:underline"
                    >
                      {shortcut.label} &rarr;
                    </Link>
                  )}
                  <Button
                    type="submit"
                    isLoading={savingProfile}
                    icon={<Save className="w-4 h-4" />}
                  >
                    Save Profile Changes
                  </Button>
                </div>
              </form>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader
                title="Identity &amp; Scope"
                subtitle="Assigned role &amp; institutional bounds"
              />
              <div className="space-y-3 text-xs">
                <div className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-800">
                  <span className="text-slate-500 dark:text-slate-400">Assigned Role</span>
                  <Badge variant="brand" size="sm" className="uppercase">
                    {user?.role}
                  </Badge>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-800">
                  <span className="text-slate-500 dark:text-slate-400">Account Verification</span>
                  {user?.is_verified ? (
                    <Badge variant="success" size="sm">
                      <BadgeCheck className="w-3 h-3 mr-1" />
                      Verified
                    </Badge>
                  ) : (
                    <Badge variant="warning" size="sm">
                      Pending
                    </Badge>
                  )}
                </div>
                {user?.institution_name && (
                  <div className="flex items-start justify-between gap-2 py-2 border-b border-slate-100 dark:border-slate-800">
                    <span className="text-slate-500 dark:text-slate-400 flex items-center gap-1 shrink-0">
                      <Building className="w-3.5 h-3.5" /> Institution
                    </span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200 text-right">
                      {user.institution_name}
                    </span>
                  </div>
                )}
                {user?.department_name && (
                  <div className="flex items-start justify-between gap-2 py-2 border-b border-slate-100 dark:border-slate-800">
                    <span className="text-slate-500 dark:text-slate-400 shrink-0">Department</span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200 text-right">
                      {user.department_name}
                    </span>
                  </div>
                )}
                {user?.roll_number && (
                  <div className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-800">
                    <span className="text-slate-500 dark:text-slate-400">Roll Number</span>
                    <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                      {user.roll_number}
                    </span>
                  </div>
                )}
                {user?.created_at && (
                  <div className="flex items-center justify-between py-2">
                    <span className="text-slate-500 dark:text-slate-400">Member Since</span>
                    <span className="font-medium text-slate-700 dark:text-slate-300">
                      {new Date(user.created_at).toLocaleDateString()}
                    </span>
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* Tab 2: Appearance & Preferences */}
      {activeTab === 'appearance' && (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Color Theme"
              subtitle="Choose light, dark, or sync automatically with your operating system."
            />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {themeOptions.map((opt) => {
                const Icon = opt.icon;
                const selected = theme === opt.mode;
                return (
                  <button
                    key={opt.mode}
                    type="button"
                    onClick={() => setTheme(opt.mode)}
                    className={`text-left p-4 rounded-xl border-2 transition-all cursor-pointer ${
                      selected
                        ? 'border-brand-600 bg-brand-50/40 dark:bg-brand-950/30 shadow-sm'
                        : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-white dark:bg-slate-900'
                    }`}
                  >
                    <div className={`h-14 rounded-lg border mb-3 flex items-center justify-center ${opt.previewClass}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-bold text-slate-900 dark:text-slate-100">
                        {opt.label}
                      </span>
                      {selected && (
                        <Badge variant="brand" size="sm">
                          Active
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                      {opt.description}
                    </p>
                  </button>
                );
              })}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Workspace Preferences"
              subtitle="Saved automatically in your browser for this workstation."
            />
            <div className="divide-y divide-slate-100 dark:divide-slate-800">
              <label className="flex items-center justify-between py-3.5 cursor-pointer gap-4">
                <div>
                  <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    Compact Layout Density
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    Reduces card padding and grid gaps to fit more rows and metrics on screen.
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={compactMode}
                  onChange={(e) => setCompactMode(e.target.checked)}
                  className="w-4 h-4 rounded border-slate-300 dark:border-slate-700 text-brand-600 focus:ring-brand-500"
                />
              </label>

              <label className="flex items-center justify-between py-3.5 cursor-pointer gap-4">
                <div>
                  <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    Reduce Interface Motion
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    Minimizes CSS hover animations and transitions across dashboards.
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={reducedMotion}
                  onChange={(e) => setReducedMotion(e.target.checked)}
                  className="w-4 h-4 rounded border-slate-300 dark:border-slate-700 text-brand-600 focus:ring-brand-500"
                />
              </label>

              <label className="flex items-center justify-between py-3.5 cursor-pointer gap-4">
                <div>
                  <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    Confirm Critical Session Actions
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    Prompts for confirmation before revoking all active sessions across devices.
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={confirmActions}
                  onChange={(e) => setConfirmActions(e.target.checked)}
                  className="w-4 h-4 rounded border-slate-300 dark:border-slate-700 text-brand-600 focus:ring-brand-500"
                />
              </label>
            </div>
          </Card>
        </div>
      )}

      {/* Tab 3: Security & Sessions */}
      {activeTab === 'security' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader
              title="Change Account Password"
              subtitle="Use a strong password with at least 8 characters, one number, and one special character."
            />
            <form onSubmit={handleChangePassword} className="space-y-4">
              <Input
                label="Current Password"
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Enter current password"
              />
              <Input
                label="New Password"
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Minimum 8 characters"
              />
              <Input
                label="Confirm New Password"
                type="password"
                required
                value={confirmNewPassword}
                onChange={(e) => setConfirmNewPassword(e.target.value)}
                placeholder="Re-enter new password"
              />

              {/* Password Strength Checklist */}
              <div className="grid grid-cols-2 gap-2 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 text-[11px]">
                <div className={`flex items-center gap-1.5 ${hasMinLength ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-500 dark:text-slate-400'}`}>
                  {hasMinLength ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                  8+ characters
                </div>
                <div className={`flex items-center gap-1.5 ${hasDigit ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-500 dark:text-slate-400'}`}>
                  {hasDigit ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                  At least 1 digit
                </div>
                <div className={`flex items-center gap-1.5 ${hasSpecial ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-500 dark:text-slate-400'}`}>
                  {hasSpecial ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                  Special character
                </div>
                <div className={`flex items-center gap-1.5 ${passwordsMatch ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-500 dark:text-slate-400'}`}>
                  {passwordsMatch ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                  Passwords match
                </div>
              </div>

              <div className="pt-1 flex justify-end">
                <Button
                  type="submit"
                  isLoading={savingPassword}
                  icon={<KeyRound className="w-4 h-4" />}
                >
                  Update Password
                </Button>
              </div>
            </form>
          </Card>

          <Card>
            <CardHeader
              title="Session &amp; Sign Out Control"
              subtitle="Manage JWT authentication sessions for this browser and all other signed-in devices."
            />
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                    Current Session
                  </span>
                  <Badge variant="success" size="sm">
                    Active
                  </Badge>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed mb-3">
                  Signed in as <span className="font-semibold text-slate-700 dark:text-slate-200">{user?.email}</span>.
                  Signing out revokes this device's refresh token immediately.
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleSignOutThisDevice}
                  disabled={signingOut}
                  icon={<LogOut className="w-3.5 h-3.5" />}
                >
                  Sign Out This Device
                </Button>
              </div>

              <div className="p-4 rounded-xl bg-rose-50/70 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/70">
                <div className="text-xs font-bold text-rose-900 dark:text-rose-200 mb-1">
                  Revoke All Active Sessions
                </div>
                <p className="text-xs text-rose-700 dark:text-rose-300/90 leading-relaxed mb-3">
                  Immediately logs out every browser and device currently signed into your account.
                </p>
                <Button
                  type="button"
                  variant="danger"
                  size="sm"
                  onClick={handleSignOutAllDevices}
                  disabled={signingOut}
                  icon={<Shield className="w-3.5 h-3.5" />}
                >
                  Sign Out All Devices
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </DashboardLayout>
  );
};

