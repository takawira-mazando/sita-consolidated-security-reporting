import api from './client';

export interface DashboardSummary {
  current_risk_score: number;
  monitored_apps: number;
  critical_apps: number;
  monitored_apps_count: number;
  safe_apps: number;
  active_alerts: number;
  unread_alerts: number;
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await api.get('/dashboard/summary');
  return data;
}
