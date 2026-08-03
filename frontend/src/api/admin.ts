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
