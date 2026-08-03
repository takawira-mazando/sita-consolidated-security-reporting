export interface User {
  sub: string;
  email: string;
  roles: string[];
  name?: string;
}

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email?: string, password?: string) => Promise<{ ok: boolean; error?: string }>;
  logout: () => void;
}

export interface RiskScore {
  app_name: string;
  score_date: string;
  fused_score: number;
  signal_appscan?: number;
  signal_imperva?: number;
  signal_api_exposure?: number;
  signal_compliance_penalty?: number;
  bucket: string;
  computed_at: string;
}

export interface RiskTrend {
  app_name: string;
  trend: RiskScore[];
}

export interface Finding {
  id: string;
  source: string;
  external_id: string;
  app_name: string;
  severity: string;
  title: string;
  description?: string;
  category?: string;
  first_seen: string;
  last_seen: string;
  status: string;
  version: number;
}

export interface ComplianceSnapshot {
  framework: string;
  snapshot_date: string;
  overall_score: number;
  total_controls: number;
  passed_controls: number;
  details?: Record<string, number>;
}

export interface ComplianceGap {
  id: string;
  framework: string;
  control_id: string;
  domain?: string;
  description: string;
  owner?: string;
  severity: string;
  due_date?: string;
  status: string;
}

export interface Alert {
  id: string;
  rule_id: string;
  title: string;
  description?: string;
  severity: string;
  source?: string;
  target_id?: string;
  status: string;
  acknowledged_by?: string;
  acknowledged_at?: string;
  first_triggered: string;
  last_triggered: string;
  created_at: string;
}

export interface ConnectorHealth {
  name: string;
  source: string;
  status: string;
  last_poll_at?: string;
  last_success_at?: string;
  latency_ms?: number;
  events_per_hour?: number;
  error_count: number;
  circuit_state: string;
}

export interface RejectedRecord {
  id: string;
  batch_id: string;
  source: string;
  rejection_reason: string;
  rejection_code: string;
  rejected_at: string;
  reprocessed: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
