import api from './client';
import type { DemoAccount, User } from '../types';

export type { DemoAccount } from '../types';

export interface LoginResponse {
  token: string;
  user: User;
}

export interface TenancyBranch {
  id: string;
  name: string;
}

export interface TenancyDepartment {
  id: string;
  name: string;
  branch_count: number;
  branches: TenancyBranch[];
  province_id?: string | null;
}

export interface TenancyProvince {
  id: string;
  name: string;
  department_count: number;
}

export interface TenancyResponse {
  counts: { departments: number; branches: number; provinces: number; provincial_departments: number };
  departments: TenancyDepartment[];
  provinces: TenancyProvince[];
}

export interface LoginScope {
  department_id: string | null;
  branch_id: string | null;
  province_id?: string | null;
}

export interface TenantScope {
  department_id?: string | null;
  branch_id?: string | null;
  province_id?: string | null;
}

export interface PublicSummary {
  generated_at: string;
  findings: { total: number; open: number; by_severity: Record<string, number> };
  assets: { apps: number; databases: number; monitored_databases: number; api_endpoints: number; agents: number; waf_blocks: number };
  latest_ingest: string | null;
  risk: { distribution: Record<string, number>; latest_score_date: string | null; trend: { date: string; avg_score: number }[] };
  top_risky_apps: { app_name: string; score: number; bucket: string }[];
  connectors: { total: number; healthy: number; degraded: number; down: number };
  tenancy: { departments: number; branches: number; provinces: number; provincial_departments: number };
}

export const NATIONWIDE_ROLES = ['exec', 'compliance', 'sre', 'admin', 'transversal-admin'];

export interface TenancyEntitlement {
  isNationwide: boolean;
  provinceIds: string[];
  departmentIds: string[];
}

export function entitlementFromUser(user: User): TenancyEntitlement {
  return {
    isNationwide: (user.roles || []).some((r) => NATIONWIDE_ROLES.includes(r)),
    provinceIds: user.province_ids || [],
    departmentIds: user.department_ids || [],
  };
}

export function filterTenancy(tenancy: TenancyResponse, ent: TenancyEntitlement): TenancyResponse {
  if (ent.isNationwide) return tenancy;
  const provinces = ent.provinceIds.length
    ? tenancy.provinces.filter((p) => ent.provinceIds.includes(p.id))
    : [];
  let departments = tenancy.departments.filter((d) => ent.departmentIds.includes(d.id));
  if (ent.provinceIds.length) {
    const provincial = tenancy.departments.filter((d) => ent.provinceIds.includes(d.province_id || ''));
    departments = departments.concat(provincial.filter((d) => !ent.departmentIds.includes(d.id)));
  }
  return { ...tenancy, provinces, departments };
}

export async function loginRequest(email: string, password: string, scope?: TenantScope): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/login', {
    email,
    password,
    ...(scope?.province_id ? { province_id: scope.province_id } : {}),
    ...(scope?.department_id ? { department_id: scope.department_id } : {}),
    ...(scope?.department_id && scope.branch_id ? { branch_id: scope.branch_id } : {}),
  });
  return data;
}

export async function demoLoginRequest(role: string, scope?: LoginScope): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/demo-login', {
    role,
    ...(scope?.province_id ? { province_id: scope.province_id } : {}),
    ...(scope?.department_id ? { department_id: scope.department_id } : {}),
    ...(scope?.department_id && scope.branch_id ? { branch_id: scope.branch_id } : {}),
  });
  return data;
}

export async function switchTenantRequest(scope: TenantScope = {}): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/switch-tenant', {
    ...(scope.province_id ? { province_id: scope.province_id } : {}),
    ...(scope.department_id ? { department_id: scope.department_id } : {}),
    ...(scope.department_id && scope.branch_id ? { branch_id: scope.branch_id } : {}),
  });
  return data;
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get<User>('/auth/me');
  return data;
}

export async function fetchTenancy(): Promise<TenancyResponse> {
  const { data } = await api.get<TenancyResponse>('/auth/tenancy');
  return data;
}

export async function fetchDemoAccounts(): Promise<DemoAccount[]> {
  const { data } = await api.get<DemoAccount[]>('/auth/demo-accounts');
  return data;
}

export async function fetchSummary(): Promise<PublicSummary> {
  const { data } = await api.get<PublicSummary>('/public/summary');
  return data;
}