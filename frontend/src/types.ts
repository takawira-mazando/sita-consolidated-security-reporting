export interface User {
  sub: string;
  email: string;
  roles: string[];
  name?: string;
  department_ids?: string[];
  branch_ids?: string[];
  branch_names?: string[];
  department_id?: string | null;
  department_name?: string | null;
  province_ids?: string[];
  province_name?: string | null;
}

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  demoAccounts: DemoAccount[];
  sessionNonce: number;
  login: (email?: string, password?: string, scope?: LoginScope) => Promise<{ ok: boolean; error?: string }>;
  loginDemo: (role: string, scope?: LoginScope) => Promise<{ ok: boolean; error?: string }>;
  switchTenant: (scope: LoginScope) => Promise<{ ok: boolean; error?: string }>;
  logout: () => void;
}

export interface LoginScope {
  department_id: string | null;
  branch_id: string | null;
  province_id?: string | null;
}

export interface DemoAccount {
  email: string;
  label: string;
  role: string;
  department_ids?: string[];
  province_ids?: string[];
  department_name?: string | null;
  province_name?: string | null;
  is_nationwide?: boolean;
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
  last_dispatched_at?: string;
  resolved_at?: string;
  dedup_count?: number;
  channels?: string[];
  enriched_data?: {
    owner?: string;
    team?: string;
    tier?: string;
    priority?: number;
    external_id?: string;
    dashboard_link?: string;
    enriched_at?: string;
  };
  created_at: string;
}

export interface DispatchLogEntry {
  channel: string;
  status: string;
  error?: string;
  attempted_at: string;
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

export interface WafBlock {
  id: string;
  app_name: string;
  attack_type?: string;
  request_uri?: string;
  action?: string;
  src_ip?: string;
  block_time?: string;
}

export interface WafSummary {
  total: number;
  window_days: number;
  by_type: { type: string; count: number }[];
  items: WafBlock[];
}

export interface ApiExposure {
  id: string;
  app_name: string;
  endpoint: string;
  method: string;
  is_shadow: boolean;
  exposure_score: number;
  discovered_at?: string;
  last_seen?: string;
}

export interface ApiExposureResponse {
  total: number;
  shadow_total: number;
  items: ApiExposure[];
}

export interface FixRate {
  window_days: number;
  total: number;
  fixed: number;
  fix_rate: number;
}

export interface SloPoint {
  week: string;
  value_hours: number;
}

export interface SloMetrics {
  mttd: SloPoint[];
  mttr: SloPoint[];
  backlog: {
    total: number;
    oldest_hours: number;
    buckets: { bucket: string; count: number }[];
  };
}

export interface SystemMetricRow {
  metric: string;
  value: number;
  unit: string;
  recorded_at?: string;
}

export interface SystemMetrics {
  items: SystemMetricRow[];
  uptime?: number | null;
}

export interface AgentRow {
  id: string;
  name: string;
  role: string;
  version: string;
  status: string;
  host?: string;
  last_seen?: string;
}

export interface AgentInventory {
  total: number;
  online: number;
  degraded: number;
  items: AgentRow[];
  by_role: { role: string; count: number }[];
  versions: { version: string; count: number }[];
}

export interface DatabaseInventory {
  id: string;
  name: string;
  engine?: string;
  monitored: boolean;
  agent_version?: string;
  last_heartbeat?: string;
}

export interface DbInventoryResponse {
  total: number;
  monitored: number;
  unmonitored: number;
  coverage_pct: number;
  items: DatabaseInventory[];
}

export interface ComplianceTrendPoint {
  framework: string;
  snapshot_date: string;
  overall_score: number;
  total_controls: number;
  passed_controls: number;
}

export interface ComplianceCalendarItem {
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
