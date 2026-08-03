import api from './client';
import { Finding, PaginatedResponse } from '../types';

export async function fetchFindings(params?: {
  app?: string; severity?: string; category?: string; source?: string;
  page?: number; size?: number;
}): Promise<PaginatedResponse<Finding>> {
  const { data } = await api.get('/findings', { params });
  return data;
}

export async function fetchFinding(id: string): Promise<Finding> {
  const { data } = await api.get(`/findings/${id}`);
  return data;
}
