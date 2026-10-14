import React, { createContext, useState, useEffect, ReactNode } from 'react';
import { User, AuthContextType, LoginScope, TierAccess, TenancyTier } from '../types';
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

const HA_BRANCHES = [
  'dha-civic',
  'dha-digital',
  'dha-immigration',
  'dha-operations',
  'dha-hrmd',
  'dha-ccss',
  'dha-finance',
  'dha-planning',
];

export const FALLBACK_DEMO_ACCOUNTS: DemoAccount[] = [
  // Department of Home Affairs (DHA) — Official Live Demo Personas
  { email: 'soc-ha@example.com', label: 'SOC Analyst', role: 'soc-ha', department_ids: ['home-affairs-digital'], branch_ids: HA_BRANCHES, department_name: 'Department of Home Affairs' },
  { email: 'appsec-ha@example.com', label: 'AppSec Engineer', role: 'appsec-ha', department_ids: ['home-affairs-digital'], branch_ids: HA_BRANCHES, department_name: 'Department of Home Affairs' },
  { email: 'dbsec-ha@example.com', label: 'DB Security', role: 'dbsec-ha', department_ids: ['home-affairs-digital'], branch_ids: HA_BRANCHES, department_name: 'Department of Home Affairs' },
  { email: 'deptadmin-ha@example.com', label: 'Dept Admin', role: 'deptadmin-ha', department_ids: ['home-affairs-digital'], branch_ids: HA_BRANCHES, department_name: 'Department of Home Affairs' },
  { email: 'branchadmin-ha@example.com', label: 'Branch Admin', role: 'branchadmin-ha', department_ids: ['home-affairs-digital'], branch_ids: HA_BRANCHES, department_name: 'Department of Home Affairs' },
];

export const ADMIN_EMAIL = 'admin@example.com';
export const ALL_ROLES = ['exec', 'soc', 'appsec', 'dbsec', 'compliance', 'sre', 'ai'];
export const ALL_DASHBOARDS = ['exec', 'soc', 'appsec', 'dbsec', 'compliance', 'sre', 'ai'];

// ─── Tier-aware access resolution ─────────────────────────────────────────────
// Returns which dashboard keys are accessible at each tenancy tier,
// plus which admin pages the user can reach and transversal authority flags.
export function getTierAccess(roles: string[]): TierAccess {
  const sita     = new Set<string>();
  const national = new Set<string>();
  const dept     = new Set<string>();
  const branch   = new Set<string>();
  const adminTiers = new Set<TenancyTier>();
  let isSitaSuperadmin = false;
  let hasTransversalAccess = false;

  for (const r of roles) {
    // ── Overarching SITA Platform Provider / Transversal Super-Roles ─────────
    if (r === 'admin' || r === 'operator') {
      isSitaSuperadmin = true;
      hasTransversalAccess = true;
      ALL_DASHBOARDS.forEach((d) => {
        sita.add(d);
        national.add(d);
        dept.add(d);
        branch.add(d);
      });
      adminTiers.add('sita');
      adminTiers.add('national');
      adminTiers.add('dept');
      adminTiers.add('branch');
      break;
    }

    // ── Transversal admin: crosses all tiers from SITA Command Center ────────
    if (r === 'transversal-admin') {
      isSitaSuperadmin = true;
      hasTransversalAccess = true;
      ALL_DASHBOARDS.forEach((d) => {
        sita.add(d);
        national.add(d);
        dept.add(d);
        branch.add(d);
      });
      adminTiers.add('sita');
      adminTiers.add('national');
    }

    // ── National-tier roles ──────────────────────────────────────────────────
    if (r === 'exec') {
      national.add('exec'); national.add('compliance'); national.add('ai');
      // Exec can also read dept-level dashboards
      dept.add('exec'); dept.add('compliance'); dept.add('ai');
    }
    if (r === 'compliance') { national.add('compliance'); national.add('ai'); }
    if (r === 'sre')        { national.add('sre'); }

    // ── Dept / Provincial tier roles ─────────────────────────────────────────
    if (r === 'soc' || r === 'soc-ha') {
      dept.add('soc'); dept.add('appsec'); dept.add('dbsec'); dept.add('ai');
    }
    if (r === 'appsec' || r === 'appsec-ha') {
      dept.add('appsec'); dept.add('ai');
    }
    if (r === 'dbsec' || r === 'dbsec-ha') {
      dept.add('dbsec');
    }
    if (r === 'province-soc-lead') {
      dept.add('exec'); dept.add('soc'); dept.add('ai');
    }

    // ── Dept admin: all dept dashboards + branch access + admin ─────────────
    if (r === 'dept-admin' || r === 'deptadmin-ha' || r === 'province-dept-admin') {
      ALL_DASHBOARDS.forEach((d) => { dept.add(d); branch.add(d); });
      adminTiers.add('dept');
      adminTiers.add('branch');
    }

    // ── Branch tier roles ────────────────────────────────────────────────────
    if (r === 'local-appsec') {
      branch.add('appsec'); branch.add('ai');
    }

    // ── Branch admin: all branch dashboards + admin ──────────────────────────
    if (r === 'branch-admin' || r === 'branchadmin-ha') {
      ALL_DASHBOARDS.forEach((d) => branch.add(d));
      adminTiers.add('branch');
    }
  }

  const order = ALL_DASHBOARDS;
  return {
    sita:     order.filter((d) => sita.has(d)),
    national: order.filter((d) => national.has(d)),
    dept:     order.filter((d) => dept.has(d)),
    branch:   order.filter((d) => branch.has(d)),
    adminTiers: (['sita', 'national', 'dept', 'branch'] as TenancyTier[]).filter((t) => adminTiers.has(t)),
    isSitaSuperadmin,
    hasTransversalAccess,
  };
}

// ── Legacy shim — returns first non-empty tier for components not yet migrated ─
export function getAccessibleDashboards(roles: string[]): string[] {
  const access = getTierAccess(roles);
  return access.national.length ? access.national
    : access.dept.length        ? access.dept
    : access.branch.length      ? access.branch
    : ['exec'];
}


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