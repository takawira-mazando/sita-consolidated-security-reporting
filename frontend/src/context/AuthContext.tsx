import React, { createContext, useState, useEffect, ReactNode } from 'react';
import { User, AuthContextType } from '../types';
import {
  loginRequest,
  demoLoginRequest,
  fetchDemoAccounts,
  DemoAccount,
  LoginScope,
} from '../api/auth';

export const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  demoAccounts: [],
  login: async () => ({ ok: true }),
  loginDemo: async () => ({ ok: true }),
  logout: () => {},
});

export const FALLBACK_DEMO_ACCOUNTS: DemoAccount[] = [
  { email: 'exec@example.com', label: 'Executive', role: 'exec' },
  { email: 'soc@example.com', label: 'SOC Analyst', role: 'soc' },
  { email: 'appsec@example.com', label: 'AppSec', role: 'appsec' },
  { email: 'dbsec@example.com', label: 'DB Security', role: 'dbsec' },
  { email: 'compliance@example.com', label: 'Compliance', role: 'compliance' },
  { email: 'sre@example.com', label: 'Service Ops', role: 'sre' },
  { email: 'transversal@example.com', label: 'Transversal Admin', role: 'transversal-admin' },
  { email: 'provincesoc@example.com', label: 'Provincial SOC Lead', role: 'province-soc-lead' },
  { email: 'admin@example.com', label: 'Admin', role: 'admin' },
];

export const ADMIN_EMAIL = 'admin@example.com';
export const ALL_ROLES = ['exec', 'soc', 'appsec', 'dbsec', 'compliance', 'sre'];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [demoAccounts, setDemoAccounts] = useState<DemoAccount[]>(FALLBACK_DEMO_ACCOUNTS);

  useEffect(() => {
    const stored = localStorage.getItem('sita_user');
    if (stored) {
      try {
        setUser(JSON.parse(stored) as User);
      } catch {
        localStorage.removeItem('sita_user');
      }
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchDemoAccounts()
      .then((accounts) => {
        if (!cancelled && accounts.length) setDemoAccounts(accounts);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const storeSession = (u: User, token: string) => {
    localStorage.setItem('sita_token', token);
    localStorage.setItem('sita_user', JSON.stringify(u));
  };

  const login = async (email?: string, password?: string): Promise<{ ok: boolean; error?: string }> => {
    try {
      const { token, user: u } = await loginRequest((email || '').trim().toLowerCase(), password || '');
      storeSession(u, token);
      setUser(u);
      return { ok: true };
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Login failed';
      return { ok: false, error: message };
    }
  };

  const loginDemo = async (role: string, scope?: LoginScope): Promise<{ ok: boolean; error?: string }> => {
    try {
      const { token, user: u } = await demoLoginRequest(role, scope);
      storeSession(u, token);
      setUser(u);
      return { ok: true };
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Demo login failed';
      return { ok: false, error: message };
    }
  };

  const logout = () => {
    localStorage.removeItem('sita_user');
    localStorage.removeItem('sita_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, demoAccounts, login, loginDemo, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
