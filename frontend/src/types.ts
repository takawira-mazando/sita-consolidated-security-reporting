export type TenancyTier = 'platform' | 'workspace';

export type PlatformTier = TenancyTier;

export interface TierAccess {
  platform: string[];
  workspace: string[];
  adminTiers: PlatformTier[];
  isPlatformAdministrator: boolean;
  hasTransversalAccess: boolean;
}

export interface HierarchyLevelInfo {
  level: number;
  name: string;
  label: string;
  plural_label: string;
}

export interface TenantProfileSummary {
  id: string;
  name: string;
  description: string;
  client_type: string;
  is_active: boolean;
  levels: string[];
  org_unit_count: number;
  sub_unit_count: number;
  group_count: number;
}

export interface ClientOrganization {
  id: string;
  identifier: string;
  name: string;
  description: string;
  client_type: string;
  deployment_model: 'saas' | 'on_premises';
  status: string;
  status_options: string[];
  primary_contact_name: string;
  primary_contact_email: string;
  superadmin_name: string;
  superadmin_email: string;
  access_setup_status: 'pending_client_workspace' | string;
  created_at: string;
  updated_at: string;
}

export interface MsspCockpit {
  id: 'exec' | 'soc' | 'appsec' | 'dbsec' | 'compliance' | 'sre';
  name: string;
}

export interface TenantHierarchyLevel {
  key: string;
  label: string;
  plural_label?: string;
  parent_key?: string | null;
}

export interface TenantOrganizationUnit {
  id: string;
  name: string;
  level_key: string;
  parent_id: string | null;
}

export interface TenantAccessRole {
  id: string;
  name: string;
  description: string;
  cockpit_ids: MsspCockpit['id'][];
  scope_level_keys?: string[];
  can_manage_members: boolean;
}

export interface TenantAccessAssignment {
  id: string;
  email: string;
  display_name: string;
  role_ids: string[];
  scope_unit_id: string | null;
  admin_access?: boolean;
  access_status:
    | 'active'
    | 'account_disabled'
    | 'pending_first_sign_in'
    | 'identity_integration_required';
}

export type TenantAccessAssignmentInput = Omit<TenantAccessAssignment, 'access_status'>;

export interface TenantRbacAssignmentInput {
  id: string;
  email: string;
  display_name: string;
  role_ids: string[];
  scope_unit_id: string | null;
}

export interface MsspTenantWorkspace {
  id: string;
  client_organization_id: string;
  identifier: string;
  name: string;
  status: 'active' | 'inactive' | 'suspended';
  root_label: string;
  administration_model: 'mssp_managed' | 'delegated' | 'shared';
  hierarchy_levels: TenantHierarchyLevel[];
  org_units: TenantOrganizationUnit[];
  roles: TenantAccessRole[];
  assignments: TenantAccessAssignment[];
  created_at: string;
  updated_at: string;
}

export interface TenantDirectoryReadiness {
  status: 'enabled' | 'disabled' | 'not_configured';
  name: string;
}

export interface MsspTenantWorkspaceCreate {
  identifier: string;
  name: string;
  root_label: string;
  administration_model: MsspTenantWorkspace['administration_model'];
  hierarchy_levels: TenantHierarchyLevel[];
}

export type MsspTenantWorkspaceConfiguration = Omit<
  Pick<
    MsspTenantWorkspace,
    'root_label' | 'administration_model' | 'hierarchy_levels' | 'org_units' | 'roles' | 'assignments' | 'status'
  >,
  'assignments'
> & {
  assignments: TenantAccessAssignmentInput[];
};

export type ClientOrganizationCreate = Pick<
  ClientOrganization,
  | 'identifier'
  | 'name'
  | 'description'
  | 'client_type'
  | 'deployment_model'
  | 'primary_contact_name'
  | 'primary_contact_email'
  | 'superadmin_name'
  | 'superadmin_email'
>;

export type ClientOrganizationUpdate = Partial<
  Omit<ClientOrganization, 'id' | 'identifier' | 'status_options' | 'created_at' | 'updated_at' | 'access_setup_status'>
>;

export interface TierRoleAssignment {
  group_name: string;
  roles: string[];
  tier: number;
  default_scope?: string[];
  description?: string;
}

export interface TenantDirectorySummary {
  tenant_id: string;
  tenant_name: string;
  client_name: string;
  server_url: string;
  base_dn: string;
  preset_profile: string;
  enabled: boolean;
  mock_mode: boolean;
  tier_mappings_count: number;
}

export interface User {
  sub: string;
  email: string;
  roles: string[];
  platform_roles?: string[];
  tenant_workspace_ids?: string[];
  tenant_scope_unit_ids?: string[];
  tenant_can_manage_members?: boolean;
  tenant_workspace_access?: Array<{
    workspace_id: string;
    workspace_name: string;
    administration_model: 'mssp_managed' | 'delegated' | 'shared';
    admin_scope_level_keys: string[];
    cockpit_scopes: Record<string, string[]>;
  }>;
  active_tenant_workspace_id?: string | null;
  name?: string;
}

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  demoAccounts: DemoAccount[];
  refreshDemoAccounts: () => Promise<DemoAccount[]>;
  sessionNonce: number;
  login: (email?: string, password?: string) => Promise<{ ok: boolean; error?: string }>;
  loginDemo: (role: string) => Promise<{ ok: boolean; error?: string }>;
  logout: () => void;
}

export interface DemoAccount {
  email: string;
  label: string;
  role: string;
  password?: string;
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
  owasp_id?: string | null;
  owasp_name?: string | null;
  cwe_id?: string | null;
  owasp_status?: OwaspStatus | null;
  taxonomy_version?: string | null;
  first_seen: string;
  last_seen: string;
  status: string;
  version: number;
  cve?: string;
  cvss_score?: number;
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

export type OwaspStatus = 'classified' | 'unmapped' | 'not_applicable' | 'absent';

export interface OwaspCategoryCount {
  id: string;
  name: string;
  count: number;
  by_severity: Record<string, number>;
  by_source: Record<string, number>;
}

export interface OwaspRegistryEntry {
  id: string;
  name: string;
  summary: string;
  taxonomy_version: string;
}

export interface OwaspPosture {
  taxonomy_version: string;
  total_classified: number;
  by_category: OwaspCategoryCount[];
  coverage: Record<OwaspStatus, number>;
  registry: OwaspRegistryEntry[];
}

export interface RiskBand {
  bucket: string;
  max: number;
}

export interface FrameworkDescriptor {
  id: string;
  name: string;
  instrument: string;
  applicability: 'applies' | 'conditional' | 'partial' | 'not_applicable';
  applicable: boolean;
  regulator: string;
  rationale: string;
  coverage: string;
  gaps: string[];
}

export interface AlertRuleDescriptor {
  id: string;
  name: string;
  severity: string;
  condition_type: string;
  channels: string[];
  window_minutes: number | null;
  max_alerts: number | null;
}

export interface PlatformModel {
  risk_model: {
    weights: Record<string, number>;
    signal_labels: Record<string, string>;
    severity_weights: Record<string, number>;
    bands: RiskBand[];
    appscan_ceiling_percentile: number;
  };
  compliance_model: {
    weights: Record<string, Record<string, number>>;
    frameworks: FrameworkDescriptor[];
    scores_are_seeded: boolean;
    scored_by: string | null;
  };
  alert_model: {
    count: number;
    rules: AlertRuleDescriptor[];
  };
}

export interface NarrativeFacts {
  riskWeightSummary?: string;
  owaspTaxonomy?: string;
  owaspClassifiedPct?: number | null;
  owaspUnmapped?: number;
  owaspNotApplicable?: number;
  riskSignalLabels?: Record<string, string>;
  safeMax?: number;
  monitoredMax?: number;
  bandSummary?: string;
  popiaDomains?: string[];
  popiaDomainLabels?: string[];
  isoDomainCount?: number;
  evidenceExpiryDays?: number;
  alertRuleCount?: number;
  alertRules?: AlertRuleDescriptor[];
  complianceScoresSeeded?: boolean;
  applicableFrameworks?: string[];
  notApplicableFrameworks?: string[];
  applicabilitySummary?: string;
}
