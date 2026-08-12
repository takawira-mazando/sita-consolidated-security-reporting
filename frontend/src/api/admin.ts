import { adminApi } from './client';
import { ConnectorHealth, RejectedRecord, PaginatedResponse } from '../types';

export async function fetchConnectors(): Promise<{ items: ConnectorHealth[] }> {
  const { data } = await adminApi.get('/connectors');
  return data;
}

export async function fetchDeadLetter(params?: {
  source?: string; page?: number; size?: number;
}): Promise<PaginatedResponse<RejectedRecord>> {
  const { data } = await adminApi.get('/dead-letter', { params });
  return data;
}

export async function resetConnector(name: string): Promise<{ status: string }> {
  const { data } = await adminApi.post(`/connectors/${name}/reset`);
  return data;
}

export async function reprocessDLQ(id: string): Promise<{ status: string }> {
  const { data } = await adminApi.post(`/dead-letter/reprocess/${id}`);
  return data;
}

export interface AdminUser {
  id: string;
  email: string;
  display_name?: string | null;
  roles: string[];
  department_ids: string[];
  branch_ids: string[];
  branch_names?: string[];
  department_id?: string | null;
  department_name?: string | null;
  province_ids?: string[];
  province_name?: string | null;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface UserPayload {
  email?: string;
  display_name?: string;
  password?: string;
  roles?: string[];
  department_ids?: string[];
  branch_ids?: string[];
  province_ids?: string[];
  is_active?: boolean;
}

export interface DepartmentOption {
  id: string;
  name: string;
}

export interface BranchOption {
  id: string;
  name: string;
  department_id: string;
}

export async function fetchDepartments(): Promise<{ items: DepartmentOption[] }> {
  const { data } = await adminApi.get('/departments');
  return data;
}

export async function fetchBranches(departmentId?: string): Promise<{ items: BranchOption[] }> {
  const { data } = await adminApi.get('/branches', {
    params: departmentId ? { department_id: departmentId } : undefined,
  });
  return data;
}

export async function fetchUsers(): Promise<{ items: AdminUser[]; total: number }> {
  const { data } = await adminApi.get('/users', { params: { page: 1, size: 200 } });
  return data;
}

export async function createUser(payload: UserPayload): Promise<AdminUser> {
  const { data } = await adminApi.post('/users', payload);
  return data;
}

export async function updateUser(id: string, payload: UserPayload): Promise<AdminUser> {
  const { data } = await adminApi.patch(`/users/${id}`, payload);
  return data;
}

export async function deleteUser(id: string): Promise<{ status: string }> {
  const { data } = await adminApi.delete(`/users/${id}`);
  return data;
}
