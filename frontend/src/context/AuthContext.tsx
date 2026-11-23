import React, { createContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { User, AuthContextType, TierAccess, TenancyTier, PlatformTier } from '../types';
import {
  loginRequest,
  demoLoginRequest,
  fetchDemoAccounts,
  fetchMe,
  DemoAccount,
} from '../api/auth';

export const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  demoAccounts: [],
  refreshDemoAccounts: async () => [],
  sessionNonce: 0,
  login: async () => ({ ok: true }),
  loginDemo: async () => ({ ok: true }),
  logout: () => {},
});

export const ADMIN_EMAIL = 'admin@example.com';
export const ALL_ROLES = ['exec', 'soc', 'appsec', 'dbsec', 'compliance', 'sre', 'ai'];
export const ALL_DASHBOARDS = ['exec', 'soc', 'appsec', 'dbsec', 'compliance', 'sre', 'ai'];
export const TENANT_WORKSPACE_STORAGE_KEY = 'platform_active_tenant_workspace';

export function rolesForTenantWorkspace(user: User, workspaceId?: string | null): string[] {
  if (!user.tenant_workspace_access?.length) return user.roles;
  const platformRoles = user.platform_roles
    ?? user.roles.filter((role) => !ALL_ROLES.includes(role));
  const selectedWorkspaceId = workspaceId
    || localStorage.getItem(TENANT_WORKSPACE_STORAGE_KEY)
    || user.tenant_workspace_access?.[0]?.workspace_id;
  const workspaceRoles = user.tenant_workspace_access?.find(
    (workspace) => workspace.workspace_id === selectedWorkspaceId,
  );
  return [...new Set([
    ...platformRoles,
    ...Object.keys(workspaceRoles?.cockpit_scopes ?? {}),
  ])];
}

// Returns dashboard access separately from platform and workspace administration.
export function getTierAccess(roles: string[]): TierAccess {
  const platform = new Set<string>();
  const adminTiers = new Set<PlatformTier>();
  const workspace = new Set<string>();
  let isPlatformAdministrator = false;
  let hasTransversalAccess = false;

  for (const r of roles) {
    if (r === 'operator') {
      hasTransversalAccess = true;
      adminTiers.add('platform');
    }
    if (r === 'admin') {
      adminTiers.add('workspace');
    }
    if (r === 'tenant-admin' || r === 'transversal-admin') {
      adminTiers.add('workspace');
    }

    if (r === 'exec') ['exec', 'compliance', 'ai'].forEach((key) => workspace.add(key));
    if (r === 'compliance') ['compliance', 'ai'].forEach((key) => workspace.add(key));
    if (r === 'soc') ['soc', 'ai'].forEach((key) => workspace.add(key));
    if (r === 'appsec') ['appsec', 'ai'].forEach((key) => workspace.add(key));
    if (r === 'dbsec') workspace.add('dbsec');
    if (r === 'sre') workspace.add('sre');
  }

  isPlatformAdministrator = roles.includes('operator');
  const order = ALL_DASHBOARDS;
  return {
    platform: order.filter((d) => platform.has(d)),
    workspace: order.filter((d) => workspace.has(d)),
    adminTiers: (['platform', 'workspace'] as TenancyTier[]).filter((t) => adminTiers.has(t)),
    isPlatformAdministrator,
    hasTransversalAccess,
  };
}

export function getAccessibleDashboards(roles: string[]): string[] {
  const access = getTierAccess(roles);
  return access.workspace.length ? access.workspace
    : ['exec'];
}


export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionNonce, setSessionNonce] = useState(0);
  const [demoAccounts, setDemoAccounts] = useState<DemoAccount[]>([]);

  const refreshDemoAccounts = useCallback(async () => {
    const accounts = await fetchDemoAccounts();
    setDemoAccounts(accounts);
    return accounts;
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem('platform_user');
    if (stored) {
      try {
        const u = JSON.parse(stored) as User;
        const validIds = (u.tenant_workspace_access ?? []).map((item) => item.workspace_id);
        const storedWorkspaceId = localStorage.getItem(TENANT_WORKSPACE_STORAGE_KEY);
        const activeWorkspaceId = storedWorkspaceId && validIds.includes(storedWorkspaceId)
          ? storedWorkspaceId
          : u.active_tenant_workspace_id || validIds[0] || null;
        if (activeWorkspaceId) {
          localStorage.setItem(TENANT_WORKSPACE_STORAGE_KEY, activeWorkspaceId);
        } else {
          localStorage.removeItem(TENANT_WORKSPACE_STORAGE_KEY);
        }
        const sessionUser = { ...u, active_tenant_workspace_id: activeWorkspaceId };
        localStorage.setItem('platform_user', JSON.stringify(sessionUser));
        setUser(sessionUser);
      } catch {
        localStorage.removeItem('platform_user');
      }
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const token = localStorage.getItem('platform_token');
    if (token) {
      fetchMe()
        .then((u) => {
          if (cancelled) return;
          const validIds = (u.tenant_workspace_access ?? []).map((item) => item.workspace_id);
          const storedWorkspaceId = localStorage.getItem(TENANT_WORKSPACE_STORAGE_KEY);
          const activeWorkspaceId = storedWorkspaceId && validIds.includes(storedWorkspaceId)
            ? storedWorkspaceId
            : u.active_tenant_workspace_id || validIds[0] || null;
          if (activeWorkspaceId) {
            localStorage.setItem(TENANT_WORKSPACE_STORAGE_KEY, activeWorkspaceId);
          } else {
            localStorage.removeItem(TENANT_WORKSPACE_STORAGE_KEY);
          }
          const sessionUser = { ...u, active_tenant_workspace_id: activeWorkspaceId };
          setUser(sessionUser);
          localStorage.setItem('platform_user', JSON.stringify(sessionUser));
        })
        .catch(() => {});
    }
    return () => {
      cancelled = true;
    };
  }, []);

  const storeSession = (u: User, token: string): User => {
    const workspaceIds = (u.tenant_workspace_access ?? []).map((item) => item.workspace_id);
    const storedWorkspaceId = localStorage.getItem(TENANT_WORKSPACE_STORAGE_KEY);
    const activeWorkspaceId = storedWorkspaceId && workspaceIds.includes(storedWorkspaceId)
      ? storedWorkspaceId
      : u.active_tenant_workspace_id || workspaceIds[0] || null;
    if (activeWorkspaceId) {
      localStorage.setItem(TENANT_WORKSPACE_STORAGE_KEY, activeWorkspaceId);
    } else {
      localStorage.removeItem(TENANT_WORKSPACE_STORAGE_KEY);
    }
    const sessionUser = { ...u, active_tenant_workspace_id: activeWorkspaceId };
    localStorage.setItem('platform_token', token);
    localStorage.setItem('platform_user', JSON.stringify(sessionUser));
    return sessionUser;
  };

  const login = async (email?: string, password?: string): Promise<{ ok: boolean; error?: string }> => {
    try {
      const { token, user: u } = await loginRequest((email || '').trim().toLowerCase(), password || '');
      setUser(storeSession(u, token));
      setSessionNonce((n) => n + 1);
      return { ok: true };
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Login failed';
      return { ok: false, error: message };
    }
  };

  const loginDemo = async (role: string): Promise<{ ok: boolean; error?: string }> => {
    try {
      const { token, user: u } = await demoLoginRequest(role);
      setUser(storeSession(u, token));
      setSessionNonce((n) => n + 1);
      return { ok: true };
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Demo login failed';
      return { ok: false, error: message };
    }
  };

  const logout = () => {
    localStorage.removeItem('platform_user');
    localStorage.removeItem('platform_token');
    localStorage.removeItem(TENANT_WORKSPACE_STORAGE_KEY);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{ user, isLoading, demoAccounts, refreshDemoAccounts, sessionNonce, login, loginDemo, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}
