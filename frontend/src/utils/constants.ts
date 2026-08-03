export const API_BASE = '/api/v1';

export const SEVERITY_COLORS: Record<string, string> = {
  critical: '#f87171',
  high: '#f59e0b',
  medium: '#3b82f6',
  low: '#22c77e',
  info: '#6b7a99',
};

export const BUCKET_COLORS: Record<string, string> = {
  critical: '#f87171',
  monitored: '#f59e0b',
  safe: '#22c77e',
};

export const ROLE_LABELS: Record<string, string> = {
  exec: 'Executive',
  soc: 'SOC Analyst',
  appsec: 'AppSec Engineer',
  dbsec: 'DB Security Engineer',
  compliance: 'Compliance Officer',
  sre: 'Service Operations',
};
