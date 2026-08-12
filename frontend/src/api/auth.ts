import api from './client';
import type { User } from '../types';

export interface LoginResponse {
  token: string;
  user: User;
}

export interface DemoAccount {
  email: string;
  label: string;
  role: string;
  province_id?: string;
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

export async function loginRequest(email: string, password: string): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/login', { email, password });
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

export async function fetchTenancy(): Promise<TenancyResponse> {
  const { data } = await api.get<TenancyResponse>('/auth/tenancy');
  return data;
}

export async function fetchDemoAccounts(): Promise<DemoAccount[]> {
  const { data } = await api.get<DemoAccount[]>('/auth/demo-accounts');
  return data;
}
