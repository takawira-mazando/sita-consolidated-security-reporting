import api from './client';
import { useDemoMode } from '../context/DemoContext';
import type { Finding, PaginatedResponse } from '../types';
import {
  getDemoFindings,
  getDemoFinding,
  getDemoFixRate,
  getDemoWafSummary,
  getDemoApiExposure,
  getDemoRisks,
  getDemoCompliance,
  getDemoPublicSummary,
  getDemoRiskScores,
} from '../data/demoData';

function withDemoParams(params: Record<string, any> = {}): Record<string, any> {
  return {
    ...params,
    _demo: 'true',
  };
}

// Backend API functions (used in real mode or when local demo data not available)
export async function fetchDemoFindings(params?: {
  app?: string; severity?: string; category?: string; source?: string;
  page?: number; size?: number;
}): Promise<PaginatedResponse<Finding>> {
  const { data } = await api.get('/findings', { params: withDemoParams(params) });
  return data;
}

export async function fetchDemoFinding(id: string): Promise<Finding> {
  const { data } = await api.get(`/findings/${id}`, { params: withDemoParams() });
  return data;
}

export async function fetchDemoFixRate() {
  const { data } = await api.get('/metrics/fix-rate', { params: withDemoParams() });
  return data;
}

export async function fetchDemoWafSummary() {
  const { data } = await api.get('/metrics/waf-summary', { params: withDemoParams() });
  return data;
}

export async function fetchDemoApiExposure() {
  const { data } = await api.get('/metrics/api-exposure', { params: withDemoParams() });
  return data;
}

export async function fetchDemoRisks(params?: { size?: number; page?: number }) {
  const { data } = await api.get('/risks', { params: withDemoParams(params) });
  return data;
}

export async function fetchDemoCompliance() {
  const { data } = await api.get('/compliance', { params: withDemoParams() });
  return data;
}

export async function fetchDemoPublicSummary() {
  const { data } = await api.get('/public/summary', { params: withDemoParams() });
  return data;
}

// Local demo data functions (used in demo mode)
export {
  getDemoFindings,
  getDemoFinding,
  getDemoFixRate,
  getDemoWafSummary,
  getDemoApiExposure,
  getDemoRisks,
  getDemoCompliance,
  getDemoPublicSummary,
  getDemoRiskScores,
} from '../data/demoData';

// Hook that returns the appropriate fetcher based on demo mode.
export function useDemoAwareFetcher<T>(
  realFetcher: () => Promise<T>,
  demoFetcher: () => Promise<T>
): () => Promise<T> {
  const { demoMode } = useDemoMode();
  return demoMode ? demoFetcher : realFetcher;
}