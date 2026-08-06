import api from './client';
import {
  WafSummary,
  ApiExposureResponse,
  FixRate,
  SloMetrics,
  SystemMetrics,
  AgentInventory,
  DbInventoryResponse,
  ComplianceTrendPoint,
  ComplianceCalendarItem,
} from '../types';

export async function fetchWafSummary(): Promise<WafSummary> {
  const { data } = await api.get('/metrics/appsec/waf');
  return data;
}

export async function fetchApiExposure(): Promise<ApiExposureResponse> {
  const { data } = await api.get('/metrics/appsec/api-exposure');
  return data;
}

export async function fetchFixRate(): Promise<FixRate> {
  const { data } = await api.get('/metrics/appsec/fix-rate');
  return data;
}

export async function fetchSloMetrics(): Promise<SloMetrics> {
  const { data } = await api.get('/metrics/soc/slo');
  return data;
}

export async function fetchSystemMetrics(): Promise<SystemMetrics> {
  const { data } = await api.get('/metrics/sre/system');
  return data;
}

export async function fetchAgents(): Promise<AgentInventory> {
  const { data } = await api.get('/metrics/sre/agents');
  return data;
}

export async function fetchDbInventory(): Promise<DbInventoryResponse> {
  const { data } = await api.get('/metrics/dbsec/inventory');
  return data;
}

export async function fetchComplianceTrend(): Promise<{ items: ComplianceTrendPoint[] }> {
  const { data } = await api.get('/metrics/compliance/trend');
  return data;
}

export async function fetchRegulatoryCalendar(): Promise<{ items: ComplianceCalendarItem[] }> {
  const { data } = await api.get('/metrics/compliance/calendar');
  return data;
}
