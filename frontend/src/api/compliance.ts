import api from './client';
import { ComplianceSnapshot, ComplianceGap } from '../types';

export async function fetchCompliance(framework?: string): Promise<ComplianceSnapshot> {
  const { data } = await api.get('/compliance', { params: { framework } });
  return data;
}

export async function fetchGaps(params?: {
  framework?: string; status?: string; sort_by?: string;
}): Promise<{ items: ComplianceGap[] }> {
  const { data } = await api.get('/compliance/gaps', { params });
  return data;
}

export async function fetchEvidence(gapId?: string): Promise<{
  available: number; missing: number; expiring: number; total: number;
}> {
  const { data } = await api.get('/compliance/evidence', { params: { gap_id: gapId } });
  return data;
}
