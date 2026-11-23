import React, { createContext, useContext, useEffect, useState } from 'react';
import { authApi } from '../services/api';
import { RegisterPayload, User, UserRole } from '../types';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  refreshUser: () => Promise<void>;
  hasRole: (roles: UserRole | UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const normalizeUser = (u: User): User => ({
    ...u,
    roll_number: u.roll_number ?? u.student_profile?.roll_number,
    student_profile_id: u.student_profile_id ?? u.student_profile?.id,
  });

  // Initialize session from localStorage on application mount
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = localStorage.getItem('access_token');
      const storedUser = localStorage.getItem('user');

      if (storedToken) {
        setToken(storedToken);
        if (storedUser) {
          try {
            setUser(normalizeUser(JSON.parse(storedUser)));
          } catch (e) {
            console.error('Failed to parse cached user object', e);
          }
        }
        // Verify with backend
        try {
          const freshUser = normalizeUser(await authApi.getMe());
          setUser(freshUser);
          localStorage.setItem('user', JSON.stringify(freshUser));
        } catch (error) {
          console.warn('Session verification failed, logging out.');
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          setToken(null);
          setUser(null);
        }
      }
      setIsLoading(false);
    };

    initializeAuth();
  }, []);

  const login = async (email: string, password: string): Promise<User> => {
    setIsLoading(true);
    try {
      const authData = await authApi.login(email, password);
      localStorage.setItem('access_token', authData.access_token);
      localStorage.setItem('refresh_token', authData.refresh_token);
      localStorage.setItem('user', JSON.stringify(authData.user));
      setToken(authData.access_token);
      setUser(authData.user);
      return authData.user;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (payload: RegisterPayload): Promise<User> => {
    setIsLoading(true);
    try {
      const authData: any = await authApi.register(payload);
      if (authData?.access_token && authData?.user) {
        localStorage.setItem('access_token', authData.access_token);
        localStorage.setItem('refresh_token', authData.refresh_token);
        localStorage.setItem('user', JSON.stringify(authData.user));
        setToken(authData.access_token);
        setUser(authData.user);
        return authData.user;
      }
      // If registration returns confirmation envelope, auto-login with submitted credentials
      return await login(payload.email, payload.password);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    setIsLoading(true);
    try {
      await authApi.logout();
    } catch (e) {
      // Proceed even if network request fails
    } finally {
      setToken(null);
      setUser(null);
      setIsLoading(false);
    }
  };

  const logoutAll = async (): Promise<void> => {
    setIsLoading(true);
    try {
      await authApi.logoutAll();
    } catch (e) {
      // Proceed even if network request fails
    } finally {
      setToken(null);
      setUser(null);
      setIsLoading(false);
    }
  };

  const refreshUser = async (): Promise<void> => {
    try {
      const freshUser = normalizeUser(await authApi.getMe());
      setUser(freshUser);
      localStorage.setItem('user', JSON.stringify(freshUser));
    } catch (e) {
      console.error('Failed to refresh user profile', e);
    }
  };

  const hasRole = (roles: UserRole | UserRole[]): boolean => {
    if (!user) return false;
    const roleList = Array.isArray(roles) ? roles : [roles];
    return roleList.includes(user.role);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        register,
        logout,
        logoutAll,
        refreshUser,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

