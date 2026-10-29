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
  // ── Tier 5: Platform Creator — System Operator (Developer / SITA IT) ─────
  { email: 'operator@example.com', label: 'Platform Creator / Developer (operator@)', role: 'operator', department_ids: [], is_nationwide: true },

  // ── Tier 4: SITA Command Center — Transversal Superadmin #1 ──────────────
  // Created by the Developer (operator). Our primary SITA client contact.
  // Provisions National Gov Transversal Superadmin (#2) and national-tier security roles.
  { email: 'admin@example.com', label: 'SITA Superadmin #1 · SITA Command Center (admin@)', role: 'admin', department_ids: [], is_nationwide: true },

  // ── Tier 3: National Security Estate — Transversal Superadmin #2 ─────────
  // Created by SITA Superadmin (#1). Provisions Department Superadmins across organs of state.
  { email: 'transversal@example.com', label: 'National Gov Transversal Superadmin #2 (transversal@)', role: 'transversal-admin', department_ids: [], is_nationwide: true },

  // ── Tier 3: National-tier Security Cockpit Roles (Data Plane) ─────────────
  { email: 'exec@example.com', label: 'Executive / National CISO (exec@)', role: 'exec', department_ids: [], is_nationwide: true },
  { email: 'compliance@example.com', label: 'Compliance Officer — POPIA / ISO 27001 (compliance@)', role: 'compliance', department_ids: [], is_nationwide: true },
  { email: 'sre@example.com', label: 'Service Reliability Engineer — SRE (sre@)', role: 'sre', department_ids: [], is_nationwide: true },

  // ── Tier 2: Department Superadmin — Home Affairs Testbed ─────────────────
  // Created by National Gov Transversal Superadmin (#2). Provisions Branch Admins and DHA cockpit roles.
  { email: 'deptadmin-ha@example.com', label: 'DHA Department Superadmin (deptadmin-ha@)', role: 'deptadmin-ha', department_ids: ['home-affairs-digital'], branch_ids: HA_BRANCHES, department_name: 'Department of Home Affairs' },

  // ── Tier 1: Operational Branch Tier — DDG Branches within DHA ────────────
  { email: 'branchadmin-ha@example.com', label: 'DHA Branch Admin (branchadmin-ha@)', role: 'branchadmin-ha', department_ids: ['home-affairs-digital'], branch_ids: HA_BRANCHES, department_name: 'Department of Home Affairs' },
  { email: 'soc-ha@example.com', label: 'SOC Security Analyst — DHA (soc-ha@)', role: 'soc-ha', department_ids: ['home-affairs-digital'], branch_ids: HA_BRANCHES, department_name: 'Department of Home Affairs' },
  { email: 'appsec-ha@example.com', label: 'AppSec Engineer — DHA (appsec-ha@)', role: 'appsec-ha', department_ids: ['home-affairs-digital'], branch_ids: HA_BRANCHES, department_name: 'Department of Home Affairs' },
  { email: 'dbsec-ha@example.com', label: 'DB Security Specialist — DHA (dbsec-ha@)', role: 'dbsec-ha', department_ids: ['home-affairs-digital'], branch_ids: HA_BRANCHES, department_name: 'Department of Home Affairs' },
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
    // ── Tier 5: Platform Creator (operator) — Control Plane ONLY ─────────────
    // Creates and provisions the SITA Superadmin (admin). No telemetry dashboards.
    if (r === 'operator') {
      isSitaSuperadmin = true;
      hasTransversalAccess = true;
      adminTiers.add('sita');
      adminTiers.add('national');
      adminTiers.add('dept');
      adminTiers.add('branch');
      // operator grants no data-plane dashboards — pure provisioning role
    }

    // ── Tier 4: SITA Superadmin (admin) — Control Plane ONLY ─────────────────
    // Transversal Superadmin #1. Created by operator. Provisions Transversal Superadmin #2
    // and national-level security cockpit roles. No telemetry dashboards of its own.
    if (r === 'admin') {
      isSitaSuperadmin = true;
      hasTransversalAccess = true;
      adminTiers.add('sita');
      adminTiers.add('national');
      adminTiers.add('dept');
      adminTiers.add('branch');
      // admin grants no data-plane dashboards — pure Control Plane provisioning role
    }

    // ── Transversal Superadmin #2 (transversal-admin) — National/Dept/Branch Control Plane ──
    // Created by SITA Superadmin #1. Provisions Department Superadmins across organs of state.
    // Scopes to national, dept, branch admin pages ONLY. Cannot reach sita tier.
    if (r === 'transversal-admin') {
      hasTransversalAccess = true;
      adminTiers.add('national');
      adminTiers.add('dept');
      adminTiers.add('branch');
    }

    // ── National-tier roles ──────────────────────────────────────────────────
    if (r === 'exec') {
      national.add('exec'); national.add('compliance'); national.add('ai');
      // Exec can also read dept-level dashboards
      dept.add('exec'); dept.add('compliance'); dept.add('ai');
    }
    if (r === 'compliance') { national.add('compliance'); national.add('ai'); }
    if (r === 'sre')        { national.add('sre'); }

    // ── Dept tier roles ──────────────────────────────────────────────────────
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
      dept.add('soc'); dept.add('ai');
    }

    // ── Dept admin: provisioning only — accesses dept + branch Admin pages ─────
    if (r === 'dept-admin' || r === 'deptadmin-ha' || r === 'province-dept-admin') {
      adminTiers.add('dept');
      adminTiers.add('branch');
    }

    // ── Branch tier roles ────────────────────────────────────────────────────
    if (r === 'local-appsec') {
      branch.add('appsec'); branch.add('ai');
    }

    // ── Branch admin: provisioning only — accesses branch Admin page ────────────
    if (r === 'branch-admin' || r === 'branchadmin-ha') {
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
        const u = JSON.parse(stored) as User;
        // Purge orphan provincial session anomalies
        if (u.email?.includes('provincesoc') || u.email?.includes('provdeptadmin') || u.email?.includes('localappsec')) {
          localStorage.removeItem('sita_user');
          localStorage.removeItem('sita_token');
          setUser(null);
        } else {
          setUser(u);
        }
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