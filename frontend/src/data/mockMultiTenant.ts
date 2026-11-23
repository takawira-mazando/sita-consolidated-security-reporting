import { PermissionDefinition, CustomRole } from '../types/multiTenant';

export const SYSTEM_PERMISSIONS: PermissionDefinition[] = [
  { id: 'view_assets', name: 'View Assets & Telemetry', category: 'Assets', description: 'Monitor infrastructure, datastores, and perimeter telemetry' },
  { id: 'manage_assets', name: 'Manage Assets & Repos', category: 'Assets', description: 'Add, onboard, and tag assets within scope' },
  { id: 'view_incidents', name: 'View Security Incidents', category: 'Incidents', description: 'Inspect real-time SOC incident queue and alerts' },
  { id: 'close_incidents', name: 'Triage & Close Incidents', category: 'Incidents', description: 'Update status, assign remediations, and resolve cases' },
  { id: 'view_users', name: 'View User Directory', category: 'Identity & RBAC', description: 'Read user accounts and branch attributions' },
  { id: 'create_users', name: 'Create & Invite Users', category: 'Identity & RBAC', description: 'Provision new tenant and branch user accounts' },
  { id: 'delete_users', name: 'Suspend / Delete Users', category: 'Identity & RBAC', description: 'Deactivate credentials and revoke access' },
  { id: 'manage_rbac', name: 'Manage Custom RBAC', category: 'Identity & RBAC', description: 'Create and edit tenant-level and branch-level roles' },
  { id: 'configure_branches', name: 'Configure Org Units / Branches', category: 'Operations', description: 'Define, rename, and nest branch structures' },
  { id: 'export_data', name: 'Export Operational & Audit Data', category: 'Audit & Compliance', description: 'Generate CSV/XLSX/JSON compliance packages' },
  { id: 'view_audit_logs', name: 'View Immutable Audit Trail', category: 'Audit & Compliance', description: 'Access tamper-proof regulatory WORM logs' },
  { id: 'manage_lifecycle', name: 'Tenant Lifecycle & Offboarding', category: 'Operations', description: 'Initiate suspension, archival, and restore workflows' },
];

export const STANDARD_TENANT_ROLES: CustomRole[] = [
  { id: 'role-t-super', name: 'Tenant Superuser', description: 'Supreme administrator within tenant scope.', scope: 'tenant', permissions: SYSTEM_PERMISSIONS.map(p => p.id), isCustom: false, assignedUsersCount: 1 },
  { id: 'role-t-admin', name: 'Tenant Administrator', description: 'Delegated operational administrator.', scope: 'tenant', permissions: ['view_assets', 'view_incidents', 'close_incidents', 'view_users', 'create_users', 'delete_users', 'configure_branches', 'export_data', 'view_audit_logs'], isCustom: false, assignedUsersCount: 3 },
  { id: 'role-t-sec-mgr', name: 'Security Manager', description: 'Oversees threat detection and remediation.', scope: 'tenant', permissions: ['view_assets', 'view_incidents', 'close_incidents', 'view_users', 'export_data', 'view_audit_logs'], isCustom: false, assignedUsersCount: 2 },
  { id: 'role-t-soc-analyst', name: 'SOC Analyst', description: 'Dedicated frontline security operator.', scope: 'tenant', permissions: ['view_assets', 'view_incidents', 'close_incidents'], isCustom: false, assignedUsersCount: 6 },
  { id: 'role-b-admin', name: 'Branch Administrator', description: 'Scoped to a designated branch or unit.', scope: 'branch', permissions: ['view_assets', 'view_incidents', 'view_users', 'create_users'], isCustom: false, assignedUsersCount: 8 },
  { id: 'role-t-viewer', name: 'Auditor & Read-Only User', description: 'Read-only regulatory and compliance visibility.', scope: 'tenant', permissions: ['view_assets', 'view_incidents', 'view_users', 'view_audit_logs'], isCustom: false, assignedUsersCount: 2 },
];
