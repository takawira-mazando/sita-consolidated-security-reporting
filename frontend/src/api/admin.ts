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
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface UserPayload {
  email?: string;
  display_name?: string;
  password?: string;
  roles?: string[];
  is_active?: boolean;
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
