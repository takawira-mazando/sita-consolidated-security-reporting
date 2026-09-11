import api from './client';
import { useAuth } from '../hooks/useAuth';
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

// Home Affairs is the official demo tenant
const DEMO_DEPARTMENT_ID = 'home-affairs-digital';

function withDemoParams(params: Record<string, any> = {}, branchId?: string): Record<string, any> {
  return {
    ...params,
    department_id: DEMO_DEPARTMENT_ID,
    ...(branchId ? { branch_id: branchId } : {}),
    _demo: 'true',
  };
}

// Backend API functions (used in real mode or when local demo data not available)
export async function fetchDemoFindings(params?: {
  app?: string; severity?: string; category?: string; source?: string;
  page?: number; size?: number;
  branch_id?: string;
}): Promise<PaginatedResponse<Finding>> {
  const { data } = await api.get('/findings', { params: withDemoParams(params, params?.branch_id) });
  return data;
}

export async function fetchDemoFinding(id: string, branchId?: string): Promise<Finding> {
  const { data } = await api.get(`/findings/${id}`, { params: withDemoParams({}, branchId) });
  return data;
}

export async function fetchDemoFixRate(branchId?: string) {
  const { data } = await api.get('/metrics/fix-rate', { params: withDemoParams({}, branchId) });
  return data;
}

export async function fetchDemoWafSummary(branchId?: string) {
  const { data } = await api.get('/metrics/waf-summary', { params: withDemoParams({}, branchId) });
  return data;
}

export async function fetchDemoApiExposure(branchId?: string) {
  const { data } = await api.get('/metrics/api-exposure', { params: withDemoParams({}, branchId) });
  return data;
}

export async function fetchDemoRisks(params?: { size?: number; page?: number; branch_id?: string }) {
  const { data } = await api.get('/risks', { params: withDemoParams(params, params?.branch_id) });
  return data;
}

export async function fetchDemoCompliance(branchId?: string) {
  const { data } = await api.get('/compliance', { params: withDemoParams({}, branchId) });
  return data;
}

export async function fetchDemoPublicSummary(branchId?: string) {
  const { data } = await api.get('/public/summary', { params: withDemoParams({}, branchId) });
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

// Hook that returns the appropriate fetcher based on demo mode
// and passes the user's branch scope for branch-scoped personas
export function useDemoAwareFetcher<T>(
  realFetcher: () => Promise<T>,
  demoFetcher: (branchId?: string) => Promise<T>
): () => Promise<T> {
  const { demoMode } = useDemoMode();
  const { user } = useAuth();
  
  return demoMode ? () => demoFetcher(user?.branch_ids?.[0]) : realFetcher;
}