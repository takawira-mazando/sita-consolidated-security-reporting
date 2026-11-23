import { adminApi } from './client';
import {
  ConnectorHealth,
  RejectedRecord,
  PaginatedResponse,
  TenantProfileSummary,
  TierRoleAssignment,
  TenantDirectorySummary,
  ClientOrganization,
  ClientOrganizationCreate,
  ClientOrganizationUpdate,
  MsspCockpit,
  MsspTenantWorkspace,
  MsspTenantWorkspaceConfiguration,
  MsspTenantWorkspaceCreate,
  TenantDirectoryReadiness,
  TenantAccessAssignment,
  TenantRbacAssignmentInput,
  TenantAccessRole,
  TenantHierarchyLevel,
} from '../types';

export async function fetchConnectors(): Promise<{ items: ConnectorHealth[] }> {
  const { data } = await adminApi.get('/connectors');
  return data;
}

export async function fetchDeadLetter(params?: {
  source?: string; page?: number; size?: number;
}): Promise<PaginatedResponse<RejectedRecord>> {
  const { data } = await adminApi.get('/dead-letter', { params });
  return data;
}

export async function resetConnector(name: string): Promise<{ status: string }> {
  const { data } = await adminApi.post(`/connectors/${name}/reset`);
  return data;
}

export async function reprocessDLQ(id: string): Promise<{ status: string }> {
  const { data } = await adminApi.post(`/dead-letter/reprocess/${id}`);
  return data;
}

export interface AdminUser {
  id: string;
  email: string;
  display_name?: string | null;
  roles: string[];
  department_ids: string[];
  branch_ids: string[];
  branch_names?: string[];
  department_id?: string | null;
  department_name?: string | null;
  province_ids?: string[];
  province_name?: string | null;
  person_id?: string | null;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface PersonRecord {
  id: string;
  employee_number?: string | null;
  email?: string | null;
  title?: string | null;
  initials?: string | null;
  surname?: string | null;
  display_name?: string | null;
  id_number?: string | null;
  job_title?: string | null;
  org_unit?: string | null;
  department_id?: string | null;
  department_name?: string | null;
  branch_id?: string | null;
  branch_name?: string | null;
  manager_name?: string | null;
  work_phone?: string | null;
  location?: string | null;
  employment_status?: string | null;
  source?: string | null;
  is_active?: boolean;
}

export interface UserPayload {
  email?: string;
  display_name?: string;
  password?: string;
  roles?: string[];
  department_ids?: string[];
  branch_ids?: string[];
  province_ids?: string[];
  person_id?: string;
  identifier_scheme?: string;
  identifier_value?: string;
  is_active?: boolean;
}

export interface DepartmentOption {
  id: string;
  name: string;
}

export interface BranchOption {
  id: string;
  name: string;
  department_id: string;
}

export interface DirectoryUserRecord {
  username: string;
  display_name: string;
  surname: string;
  initials?: string;
  position: string;
  employee_code: string;
  email?: string;
  department_id?: string;
  branch_id?: string;
  groups: string[];
  suggested_roles: string[];
  dn: string;
  source_system: string;
  scheme: string;
}

export interface TenantDirectoryEmployee {
  username: string;
  display_name: string;
  position: string;
  email: string;
}

export interface LDAPConfig {
  enabled: boolean;
  server_url: string;
  use_ssl: boolean;
  start_tls: boolean;
  timeout_seconds: number;
  bind_dn: string;
  bind_password?: string;
  base_dn: string;
  user_search_base: string;
  user_search_filter: string;
  user_login_filter: string;
  group_search_base: string;
  client_name: string;
  preset_profile: string;
  attribute_mapping: Record<string, string>;
  role_mapping: Record<string, string[]>;
  mock_mode: boolean;
}

export interface LDAPTestResult {
  success: boolean;
  status: string;
  message: string;
  server_url?: string;
  client_name?: string;
  base_dn?: string;
  entries_found?: number;
  mock_mode?: boolean;
}

export async function fetchDirectoryConfig(tenantId?: string): Promise<LDAPConfig> {
  const { data } = await adminApi.get('/directory/config', {
    params: tenantId ? { tenant_id: tenantId } : undefined,
  });
  return data;
}

export async function updateDirectoryConfig(
  payload: Partial<LDAPConfig>,
  tenantId?: string
): Promise<{ status: string; client_name: string; config: LDAPConfig }> {
  const { data } = await adminApi.put('/directory/config', payload, {
    params: tenantId ? { tenant_id: tenantId } : undefined,
  });
  return data;
}

export async function applyDirectoryPreset(
  preset: 'active_directory' | 'openldap' | 'freeipa',
  tenantId?: string
): Promise<{ status: string; preset: string; client_name: string; config: LDAPConfig }> {
  const { data } = await adminApi.post(`/directory/preset/${preset}`, null, {
    params: tenantId ? { tenant_id: tenantId } : undefined,
  });
  return data;
}

export async function testDirectoryConnection(
  payload?: Partial<LDAPConfig>,
  tenantId?: string
): Promise<LDAPTestResult> {
  const { data } = await adminApi.post('/directory/test', payload || {}, {
    params: tenantId ? { tenant_id: tenantId } : undefined,
  });
  return data;
}

export async function searchDirectoryUsers(
  q?: string,
  departmentId?: string,
  tenantId?: string
): Promise<{ client_name: string; total: number; items: DirectoryUserRecord[] }> {
  const { data } = await adminApi.get('/directory/search', {
    params: { q, department_id: departmentId, tenant_id: tenantId },
  });
  return data;
}

export async function searchMsspWorkspaceEmployees(
  workspaceId: string,
  q: string,
): Promise<{
  organization_name: string;
  directory_name: string;
  items: TenantDirectoryEmployee[];
}> {
  const { data } = await adminApi.get(
    `/mssp/workspaces/${workspaceId}/directory/search`,
    { params: { q } },
  );
  return data;
}

export async function importDirectoryUser(payload: {
  username_or_code: string;
  create_user_account?: boolean;
  assigned_roles?: string[];
  department_id?: string;
  branch_id?: string;
  tenant_id?: string;
}): Promise<{
  status: string;
  person_id: string;
  employee_code: string;
  surname: string;
  position: string;
  department_id?: string;
  branch_id?: string;
  email?: string;
  source: string;
  user_account?: { id: string; email: string; roles: string[] };
}> {
  const { data } = await adminApi.post('/directory/import', payload);
  return data;
}

export async function fetchDirectoryTenants(): Promise<{ tenants: TenantDirectorySummary[] }> {
  const { data } = await adminApi.get('/directory/tenants');
  return data;
}

export async function fetchTenantTierMappings(tenantId: string): Promise<{
  tenant_id: string;
  tenant_name: string;
  tier_mappings: TierRoleAssignment[];
}> {
  const { data } = await adminApi.get(`/directory/tenants/${tenantId}/tier-mappings`);
  return data;
}

export async function updateTenantTierMappings(
  tenantId: string,
  mappings: TierRoleAssignment[]
): Promise<{ status: string; tenant_id: string; tier_mappings: TierRoleAssignment[] }> {
  const { data } = await adminApi.put(`/directory/tenants/${tenantId}/tier-mappings`, {
    tier_mappings: mappings,
  });
  return data;
}

export async function fetchTenantProfiles(): Promise<{
  profiles: TenantProfileSummary[];
  active_profile: string;
}> {
  const { data } = await adminApi.get('/tenant-profiles');
  return data;
}

export async function fetchClientOrganizations(): Promise<ClientOrganization[]> {
  const { data } = await adminApi.get('/client-organizations');
  return data.items;
}

export async function createClientOrganization(
  payload: ClientOrganizationCreate,
): Promise<ClientOrganization> {
  const { data } = await adminApi.post('/client-organizations', payload);
  return data;
}

export async function updateClientOrganization(
  clientId: string,
  payload: ClientOrganizationUpdate,
): Promise<ClientOrganization> {
  const { data } = await adminApi.patch(`/client-organizations/${clientId}`, payload);
  return data;
}

export async function provisionClientSuperadmin(
  clientId: string,
): Promise<{
  status: string;
  email: string;
  temporary_password: string;
  email_status: 'sent' | 'not_configured' | 'delivery_failed';
  client: ClientOrganization;
}> {
  const { data } = await adminApi.post(`/client-organizations/${clientId}/superadmin-account`);
  return data;
}

export async function rotateClientSuperadminPassword(
  clientId: string,
): Promise<{
  status: string;
  email: string;
  temporary_password: string;
  email_status: 'sent' | 'not_configured' | 'delivery_failed';
  client: ClientOrganization;
}> {
  const { data } = await adminApi.post(`/client-organizations/${clientId}/superadmin-account/password`);
  return data;
}

export async function fetchMsspCockpits(): Promise<{ items: MsspCockpit[] }> {
  const { data } = await adminApi.get('/mssp/cockpits');
  return data;
}

export async function fetchMsspTenantWorkspaces(): Promise<{
  organization_name: string;
  directory: TenantDirectoryReadiness;
  items: MsspTenantWorkspace[];
}> {
  const { data } = await adminApi.get('/mssp/workspaces');
  return data;
}

export async function createMsspTenantWorkspace(
  payload: MsspTenantWorkspaceCreate
): Promise<MsspTenantWorkspace> {
  const { data } = await adminApi.post('/mssp/workspaces', payload);
  return data;
}

export async function updateMsspTenantWorkspace(
  workspaceId: string,
  payload: MsspTenantWorkspaceConfiguration
): Promise<MsspTenantWorkspace> {
  const { data } = await adminApi.put(`/mssp/workspaces/${workspaceId}`, payload);
  return data;
}

export interface ManagedTenantMembers {
  workspace_id: string;
  workspace_name: string;
  hierarchy_levels: TenantHierarchyLevel[];
  allowed_scope_level_keys: string[];
  directory: TenantDirectoryReadiness;
  roles: TenantAccessRole[];
  assignments: TenantAccessAssignment[];
}

export async function fetchManagedTenantMembers(workspaceId: string): Promise<ManagedTenantMembers> {
  const { data } = await adminApi.get(`/mssp/workspaces/${workspaceId}/members`);
  return data;
}

export async function searchManagedTenantEmployees(
  workspaceId: string,
  query: string,
): Promise<{ directory_name: string; items: TenantDirectoryEmployee[] }> {
  const { data } = await adminApi.get(
    `/mssp/workspaces/${workspaceId}/members/directory/search`,
    { params: { q: query } },
  );
  return data;
}

export async function updateManagedTenantMembers(
  workspaceId: string,
  assignments: TenantRbacAssignmentInput[],
): Promise<{ workspace_id: string; assignments: TenantAccessAssignment[] }> {
  const { data } = await adminApi.put(
    `/mssp/workspaces/${workspaceId}/members`,
    { assignments },
  );
  return data;
}

export async function activateTenantProfile(profileId: string): Promise<{
  status: string;
  active_profile: string;
  name: string;
  hierarchy_levels: Array<{ level: number; name: string; label: string; plural_label: string }>;
}> {
  const { data } = await adminApi.post(`/tenant-profiles/${profileId}/activate`);
  return data;
}

export async function createTenantProfile(payload: {
  id: string;
  name: string;
  description?: string;
  client_type?: string;
}): Promise<{ status: string; id: string; name: string; client_type: string }> {
  const { data } = await adminApi.post('/tenant-profiles', payload);
  return data;
}

export async function updateTenantProfile(profileId: string, payload: {
  name?: string;
  description?: string;
  client_type?: string;
}): Promise<{ status: string; id: string; name: string; description: string; client_type: string }> {
  const { data } = await adminApi.put(`/tenant-profiles/${profileId}`, payload);
  return data;
}

export async function deleteTenantProfile(profileId: string): Promise<{ status: string; id: string; detail: string }> {
  const { data } = await adminApi.delete(`/tenant-profiles/${profileId}`);
  return data;
}

export async function fetchDepartments(): Promise<{ items: DepartmentOption[] }> {
  const { data } = await adminApi.get('/departments');
  return data;
}

export async function fetchBranches(departmentId?: string): Promise<{ items: BranchOption[] }> {
  const { data } = await adminApi.get('/branches', {
    params: departmentId ? { department_id: departmentId } : undefined,
  });
  return data;
}

export async function fetchUsers(): Promise<{ items: AdminUser[]; total: number }> {
  const { data } = await adminApi.get('/users', { params: { page: 1, size: 200 } });
  return data;
}

export async function fetchPersons(q?: string): Promise<{ items: PersonRecord[]; total: number }> {
  const { data } = await adminApi.get('/persons', {
    params: { q, size: 200, employment_status: 'active' },
  });
  return data;
}

export async function createUser(payload: UserPayload): Promise<AdminUser> {
  const { data } = await adminApi.post('/users', payload);
  return data;
}

export async function updateUser(id: string, payload: UserPayload): Promise<AdminUser> {
  const { data } = await adminApi.patch(`/users/${id}`, payload);
  return data;
}

export async function deleteUser(id: string): Promise<{ status: string }> {
  const { data } = await adminApi.delete(`/users/${id}`);
  return data;
}
