export type TenantLifecycleState =
  | 'draft'
  | 'provisioning'
  | 'active'
  | 'suspended'
  | 'retention_hold'
  | 'archived'
  | 'deleted';

export type TenantScopeLevel = 'platform' | 'mssp' | 'tenant' | 'branch';

export interface BranchUnit {
  id: string;
  name: string;
  type: string; // e.g. "Mine", "Store", "Office", "Facility", "Branch", "Division", "Campus"
  parentId?: string;
  managerEmail?: string;
  userCount?: number;
  children?: BranchUnit[];
}

export interface CustomRole {
  id: string;
  name: string;
  description: string;
  scope: TenantScopeLevel;
  permissions: string[];
  isCustom?: boolean;
  inheritedFrom?: string;
  assignedUsersCount?: number;
}

export interface TenantSuperuser {
  firstName: string;
  lastName: string;
  email: string;
  phone?: string;
  mfaMethod: 'app' | 'sms' | 'hardware';
  status: 'active' | 'pending_invite';
}

export interface TenantGovernanceSettings {
  mfaEnforced: boolean;
  passwordMinLength: number;
  passwordRequireSpecial: boolean;
  ssoProvider: 'none' | 'entra_id' | 'okta' | 'ping' | 'google';
  ssoDomain?: string;
  retentionDays: number; // 30, 90, 180, 365
  auditLoggingEnabled: boolean;
  immutableLogsEnabled: boolean;
}

export interface MSSPSuperuser {
  firstName: string;
  lastName: string;
  email: string;
  phone?: string;
  mfaMethod: 'app' | 'sms' | 'hardware';
  status: 'active' | 'pending_invite' | 'suspended';
  lastLogin?: string;
  accessKeyId?: string;
}

export interface MSSPOrganization {
  id: string;
  name: string;
  code: string;
  type: 'government_agency' | 'commercial_mssp' | 'telecom_mssp' | 'enterprise_mssp';
  region: string;
  serviceTier: 'Sovereign Gov Cloud' | 'Enterprise MSSP' | 'Premium Fusion MSSP';
  slaTier: '24/7 Sovereign Critical' | '99.99% Platinum Enterprise' | '24/7 Premium SOC';
  maxTenants: number;
  status: 'active' | 'provisioning' | 'suspended';
  superuser: MSSPSuperuser;
  allowedModules: string[]; // ['soc', 'appsec', 'dbsec', 'compliance', 'ai_suite']
  createdDate: string;
  notes?: string;
}

export interface Tenant {
  id: string;
  msspId?: string;
  name: string;
  identifier: string; // unique slug
  industry: string;
  clientType?: 'enterprise' | 'government' | 'institution' | 'mssp';
  deploymentMode?: 'saas' | 'on_premises';
  serviceTier: string;
  region: string;
  primaryContact: string;
  contactEmail: string;
  status: TenantLifecycleState;
  superuser: TenantSuperuser;
  branches: BranchUnit[];
  customRoles: CustomRole[];
  governance: TenantGovernanceSettings;
  createdDate: string;
  lastActiveDate: string;
  suspendedReason?: string;
  suspendedAt?: string;
  archivedAt?: string;
  profileDescription?: string;
  profileLevels?: string[];
  profileUnitCount?: number;
  profileSubUnitCount?: number;
}

export interface PermissionDefinition {
  id: string;
  name: string;
  category: 'Assets' | 'Incidents' | 'Identity & RBAC' | 'Audit & Compliance' | 'Operations';
  description: string;
}
