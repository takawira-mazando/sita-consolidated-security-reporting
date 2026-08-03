import api from './client';
import { Alert, PaginatedResponse } from '../types';

export async function fetchAlerts(params?: {
  severity?: string; status?: string; source?: string; since?: string;
  page?: number; size?: number;
}): Promise<PaginatedResponse<Alert>> {
  const { data } = await api.get('/alerts', { params });
  return data;
}

export async function acknowledgeAlert(id: string): Promise<Alert> {
  const { data } = await api.patch(`/alerts/${id}/acknowledge`);
  return data;
}

export async function resolveAlert(id: string): Promise<Alert> {
  const { data } = await api.patch(`/alerts/${id}/resolve`);
  return data;
}
