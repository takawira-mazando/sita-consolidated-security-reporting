import React, { createContext, useState, useEffect, ReactNode } from 'react';
import { User, AuthContextType, LoginScope } from '../types';
import {
  loginRequest,
  demoLoginRequest,
  switchTenantRequest,
  fetchDemoAccounts,
  fetchMe,
  DemoAccount,
} from '../api/auth';

export const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  demoAccounts: [],
  sessionNonce: 0,
  login: async () => ({ ok: true }),
  loginDemo: async () => ({ ok: true }),
  switchTenant: async () => ({ ok: true }),
  logout: () => {},
});

export const FALLBACK_DEMO_ACCOUNTS: DemoAccount[] = [
  { email: 'exec@example.com', label: 'Executive', role: 'exec', is_nationwide: true },
  { email: 'soc@example.com', label: 'SOC Analyst', role: 'soc', department_ids: ['home-affairs-digital'] },
  { email: 'appsec@example.com', label: 'AppSec', role: 'appsec', department_ids: ['treasury'] },
  { email: 'dbsec@example.com', label: 'DB Security', role: 'dbsec', department_ids: ['dpsa-hr'] },
  { email: 'compliance@example.com', label: 'Compliance', role: 'compliance', is_nationwide: true },
  { email: 'sre@example.com', label: 'Service Ops', role: 'sre', is_nationwide: true },
  { email: 'deptadmin@example.com', label: 'Dept Admin', role: 'dept-admin', department_ids: ['treasury'] },
  { email: 'branchadmin@example.com', label: 'Branch Admin', role: 'branch-admin', department_ids: ['treasury'] },
  { email: 'transversal@example.com', label: 'Transversal Admin', role: 'transversal-admin', is_nationwide: true },
  { email: 'provincesoc@example.com', label: 'Provincial SOC Lead', role: 'province-soc-lead', province_ids: ['gp'] },
  { email: 'admin@example.com', label: 'Admin', role: 'admin', is_nationwide: true },
];

export const ADMIN_EMAIL = 'admin@example.com';
export const ALL_ROLES = ['exec', 'soc', 'appsec', 'dbsec', 'compliance', 'sre'];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionNonce, setSessionNonce] = useState(0);
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
    const token = localStorage.getItem('sita_token');
    if (token) {
      fetchMe()
        .then((u) => {
          if (cancelled) return;
          setUser(u);
          localStorage.setItem('sita_user', JSON.stringify(u));
        })
        .catch(() => {});
    }
    return () => {
      cancelled = true;
    };
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

  const login = async (email?: string, password?: string, scope?: LoginScope): Promise<{ ok: boolean; error?: string }> => {
    try {
      const { token, user: u } = await loginRequest((email || '').trim().toLowerCase(), password || '', scope);
      storeSession(u, token);
      setUser(u);
      setSessionNonce((n) => n + 1);
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
      setSessionNonce((n) => n + 1);
      return { ok: true };
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Demo login failed';
      return { ok: false, error: message };
    }
  };

  const switchTenant = async (scope: LoginScope): Promise<{ ok: boolean; error?: string }> => {
    try {
      const { token, user: u } = await switchTenantRequest(scope);
      storeSession(u, token);
      setUser(u);
      setSessionNonce((n) => n + 1);
      return { ok: true };
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Tenant switch failed';
      return { ok: false, error: message };
    }
  };

  const logout = () => {
    localStorage.removeItem('sita_user');
    localStorage.removeItem('sita_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{ user, isLoading, demoAccounts, sessionNonce, login, loginDemo, switchTenant, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}