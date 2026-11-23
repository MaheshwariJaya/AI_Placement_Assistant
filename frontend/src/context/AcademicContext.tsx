import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { StudentAcademicContext } from '../types';
import { studentApi } from '../services/api';
import { useAuth } from './AuthContext';

interface AcademicContextType {
  academicContext: StudentAcademicContext | null;
  loading: boolean;
  error: string | null;
  isBranchVerified: boolean;
  officialBranchName: string;
  officialBranchCode: string;
  careerInterests: string[];
  refreshContext: () => Promise<void>;
  updateCareerInterests: (interests: string[]) => Promise<void>;
}

const AcademicContext = createContext<AcademicContextType | undefined>(undefined);

export const AcademicProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isAuthenticated } = useAuth();
  const [academicContext, setAcademicContext] = useState<StudentAcademicContext | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchContext = useCallback(async () => {
    const canAccessStudentContext =
      user?.role === 'student' ||
      user?.email === 'maheshwarijaya03@gmail.com' ||
      user?.role === 'admin' ||
      user?.role === 'tpo';

    if (!isAuthenticated || !canAccessStudentContext) {
      setAcademicContext(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await studentApi.getAcademicContext();
      setAcademicContext(data);
    } catch (err: any) {
      console.warn('Could not load authoritative student academic context:', err);
      // For non-students or fallback, do not throw fatal error
      setError(err?.response?.data?.detail || 'Failed to load verified academic context.');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, user]);

  useEffect(() => {
    fetchContext();
  }, [fetchContext]);

  const updateCareerInterests = async (interests: string[]) => {
    try {
      const updated = await studentApi.updateCareerInterests(interests);
      setAcademicContext(updated);
    } catch (err: any) {
      throw new Error(err?.response?.data?.detail || 'Failed to update career interests.');
    }
  };

  const userDept = (user as any)?.department;
  const isBranchVerified = academicContext
    ? academicContext.is_branch_verified
    : Boolean(userDept?.name && userDept?.code !== 'GEN');
  const officialBranchName = academicContext?.official_department_name || userDept?.name || 'Department Unassigned';
  const officialBranchCode = academicContext?.official_department_code || userDept?.code || '';
  const careerInterests = academicContext?.career_interests || [];

  return (
    <AcademicContext.Provider
      value={{
        academicContext,
        loading,
        error,
        isBranchVerified,
        officialBranchName,
        officialBranchCode,
        careerInterests,
        refreshContext: fetchContext,
        updateCareerInterests,
      }}
    >
      {children}
    </AcademicContext.Provider>
  );
};

export const useAcademicContext = (): AcademicContextType => {
  const ctx = useContext(AcademicContext);
  if (!ctx) {
    throw new Error('useAcademicContext must be used within an AcademicProvider');
  }
  return ctx;
};

export const useAcademic = useAcademicContext;
