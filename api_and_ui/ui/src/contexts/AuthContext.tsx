import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi } from '../services/api';
import type { UserInfo, TokenResponse, LoginRequest } from '../types';

interface AuthContextType {
  user: UserInfo | null;
  token: string | null;
  isAdmin: boolean;
  loading: boolean;
  login: (data: LoginRequest) => Promise<TokenResponse>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('access_token'));
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async (tokenOverride?: string) => {
    const activeToken = tokenOverride ?? token;
    if (!activeToken) {
      setLoading(false);
      return;
    }
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      localStorage.removeItem('access_token');
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (data: LoginRequest): Promise<TokenResponse> => {
    const resp = await authApi.login(data);
    localStorage.setItem('access_token', resp.access_token);
    setToken(resp.access_token);
    await refreshUser(resp.access_token);
    return resp;
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    setToken(null);
    setUser(null);
    authApi.logout().catch(() => {});
  };

  return (
    <AuthContext.Provider value={{ user, token, isAdmin: user?.is_admin ?? false, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
