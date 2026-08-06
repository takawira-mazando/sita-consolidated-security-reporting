export const API_BASE = '/api/v1';

export const SEVERITY_COLORS: Record<string, string> = {
  critical: '#f87171',
  high: '#fbbf24',
  medium: '#1082ff',
  low: '#00af66',
  info: '#6f8299',
};

export const BUCKET_COLORS: Record<string, string> = {
  critical: '#f87171',
  monitored: '#fbbf24',
  safe: '#00af66',
};

export const ROLE_LABELS: Record<string, string> = {
  exec: 'Executive',
  soc: 'SOC Analyst',
  appsec: 'AppSec Engineer',
  dbsec: 'DB Security Engineer',
  compliance: 'Compliance Officer',
  sre: 'Service Operations',
};
