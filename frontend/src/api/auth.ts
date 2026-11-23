import api from './client';
import type { DemoAccount, User } from '../types';

export type { DemoAccount } from '../types';

export interface LoginResponse {
  token: string;
  user: User;
}

export interface TenancyUnit {
  id: string;
  name: string;
  level: number;
  level_name: string;
  parent_id: string | null;
}

export interface TenancyResponse {
  counts: { units: number };
  units: TenancyUnit[];
  tenant_profile_id?: string;
  tenant_profile_name?: string;
  hierarchy_levels?: Array<{ level: number; name: string; label: string; plural_label: string }>;
}

export interface PublicSummary {
  generated_at: string;
  findings: { total: number; open: number; by_severity: Record<string, number> };
  assets: { apps: number; databases: number; monitored_databases: number; api_endpoints: number; agents: number; waf_blocks: number };
  latest_ingest: string | null;
  risk: {
    distribution: Record<string, number>;
    latest_score_date: string | null;
    trend: { date: string; avg_score: number }[];
    /** Fusion weights, served from the risk engine. Absent on older backends. */
    weights?: Record<string, number>;
    signal_labels?: Record<string, string>;
  };
  top_risky_apps: { app_name: string; score: number; bucket: string }[];
  connectors: { total: number; healthy: number; degraded: number; down: number };
}

export async function loginRequest(email: string, password: string): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/login', {
    email,
    password,
  });
  return data;
}

export async function demoLoginRequest(role: string): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/demo-login', {
    role,
  });
  return data;
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get<User>('/auth/me');
  return data;
}

export async function fetchDemoAccounts(): Promise<DemoAccount[]> {
  const { data } = await api.get<DemoAccount[]>('/auth/demo-accounts', {
    params: {},
  });
  return data;
}

export async function completeClientSuperadminInvitation(
  token: string,
  password: string,
): Promise<{ status: string; email: string }> {
  const { data } = await api.post('/auth/client-superadmin-invitations/complete', { token, password });
  return data;
}

export async function fetchSummary(): Promise<PublicSummary> {
  const { data } = await api.get<PublicSummary>('/public/summary');
  return data;
}
