import api from './client';
import { RiskScore, RiskTrend, PaginatedResponse } from '../types';

export async function fetchRisks(params?: {
  app?: string; bucket?: string; date_from?: string; date_to?: string;
  page?: number; size?: number;
}): Promise<PaginatedResponse<RiskScore>> {
  const { data } = await api.get('/risks', { params });
  return data;
}

export async function fetchRiskTrend(appName: string, days = 30): Promise<RiskTrend> {
  const { data } = await api.get(`/risks/${appName}/trend`, { params: { days } });
  return data;
}
