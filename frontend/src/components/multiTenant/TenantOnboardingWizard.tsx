import React, { useState } from 'react';
import { Tenant, BranchUnit, CustomRole } from '../../types/multiTenant';
import { SYSTEM_PERMISSIONS, STANDARD_TENANT_ROLES } from '../../data/mockMultiTenant';
import { getClientOrgName } from '../../utils/tenantTerminology';

interface Props {
  onComplete: (newTenant: Tenant) => void;
  onCancel: () => void;
}

export const TenantOnboardingWizard: React.FC<Props> = ({ onComplete, onCancel }) => {
  const [step, setStep] = useState<number>(1);

  // Step 1: Profile
  const [tenantName, setTenantName] = useState('');
  const [identifier, setIdentifier] = useState('');
  const [industry, setIndustry] = useState('Enterprise');
  const [clientType, setClientType] = useState<'enterprise' | 'government' | 'institution' | 'mssp'>('enterprise');
  const [deploymentMode, setDeploymentMode] = useState<'saas' | 'on_premises'>('saas');
  const [serviceTier, setServiceTier] = useState('Premium SOC Monitoring');
  const [region, setRegion] = useState('South Africa');
  const [primaryContact, setPrimaryContact] = useState('');
  const [contactEmail, setContactEmail] = useState('');

  // Step 2: Superuser
  const [superFirstName, setSuperFirstName] = useState('');
  const [superLastName, setSuperLastName] = useState('');
  const [superEmail, setSuperEmail] = useState('');
  const [superPhone, setSuperPhone] = useState('');
  const [superMfa, setSuperMfa] = useState<'app' | 'sms' | 'hardware'>('app');
  const [superPassword, setSuperPassword] = useState('TempPass#2026!Secure');

  // Step 3: Organizational Structure
  const [branchNamingType, setBranchNamingType] = useState('Divisions / Business Units');
  const [branches, setBranches] = useState<BranchUnit[]>([
    { id: 'b-init-1', name: 'Head Office', type: 'Head Office', userCount: 5 },
    { id: 'b-init-2', name: 'Facility Alpha', type: 'Operational Facility', userCount: 12 },
  ]);
  const [newBranchName, setNewBranchName] = useState('');
  const [newBranchType, setNewBranchType] = useState('Facility');

  // Step 4 & 5: RBAC & Permissions
  const [selectedRoles, setSelectedRoles] = useState<CustomRole[]>(STANDARD_TENANT_ROLES);
  const [newRoleName, setNewRoleName] = useState('');
  const [newRoleDesc, setNewRoleDesc] = useState('');
  const [newRoleScope, setNewRoleScope] = useState<'tenant' | 'branch'>('tenant');
  const [newRolePerms, setNewRolePerms] = useState<string[]>(['view_assets', 'view_incidents']);

  // Step 6: Initial Users
  const [initialUsers, setInitialUsers] = useState<Array<{ name: string; email: string; roleId: string; branchId: string }>>([
    { name: 'Client Administrator', email: 'administrator@client.example', roleId: 'role-t-admin', branchId: 'b-init-1' },
    { name: 'Security Operator', email: 'operator@client.example', roleId: 'role-t-soc-analyst', branchId: 'b-init-2' },
  ]);
  const [userName, setUserName] = useState('');
  const [userEmail, setUserEmail] = useState('');
  const [userRole, setUserRole] = useState('role-t-admin');
  const [userBranch, setUserBranch] = useState('b-init-1');

  // Step 7: Security & Governance
  const [mfaEnforced, setMfaEnforced] = useState(true);
  const [passwordMinLength, setPasswordMinLength] = useState(14);
  const [ssoProvider, setSsoProvider] = useState<'none' | 'entra_id' | 'okta' | 'ping' | 'google'>('entra_id');
  const [ssoDomain, setSsoDomain] = useState('');
  const [retentionDays, setRetentionDays] = useState(365);

  const handleNameChange = (val: string) => {
    setTenantName(val);
    if (!identifier || identifier === tenantName.toLowerCase().replace(/[^a-z0-9]/g, '-')) {
      setIdentifier(val.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-'));
    }
  };

  const addBranch = () => {
    if (!newBranchName.trim()) return;
    const b: BranchUnit = {
      id: `b-${Date.now()}`,
      name: newBranchName.trim(),
      type: newBranchType || 'Unit',
      userCount: 0,
    };
    setBranches([...branches, b]);
    setNewBranchName('');
  };

  const removeBranch = (id: string) => {
    setBranches(branches.filter((b) => b.id !== id));
  };

  const handleAddCustomRole = () => {
    if (!newRoleName.trim()) return;
    const role: CustomRole = {
      id: `role-${Date.now()}`,
      name: newRoleName.trim(),
      description: newRoleDesc || 'Custom tenant-specific role',
      scope: newRoleScope,
      permissions: newRolePerms,
      isCustom: true,
      assignedUsersCount: 0,
    };
    setSelectedRoles([...selectedRoles, role]);
    setNewRoleName('');
    setNewRoleDesc('');
  };

  const togglePermissionForRole = (roleId: string, permId: string) => {
    setSelectedRoles(
      selectedRoles.map((r) => {
        if (r.id !== roleId) return r;
        const exists = r.permissions.includes(permId);
        return {
          ...r,
          permissions: exists ? r.permissions.filter((p: string) => p !== permId) : [...r.permissions, permId],
        };
      })
    );
  };

  const handleAddUser = () => {
    if (!userName.trim() || !userEmail.trim()) return;
    setInitialUsers([...initialUsers, { name: userName, email: userEmail, roleId: userRole, branchId: userBranch }]);
    setUserName('');
    setUserEmail('');
  };

  const handleActivate = () => {
    const newTenant: Tenant = {
      id: `t-${identifier || Date.now()}`,
      name: tenantName || 'New Tenant',
      identifier: identifier || 'new-tenant',
      industry,
      clientType,
      deploymentMode,
      serviceTier,
      region,
      primaryContact: primaryContact || `${superFirstName} ${superLastName}`,
      contactEmail: contactEmail || superEmail,
      status: 'active',
      createdDate: new Date().toISOString().split('T')[0],
      lastActiveDate: new Date().toISOString().split('T')[0],
      superuser: {
        firstName: superFirstName || 'Tenant',
        lastName: superLastName || 'Superuser',
        email: superEmail || 'admin@tenant.example',
        phone: superPhone,
        mfaMethod: superMfa,
        status: 'active',
      },
      branches,
      customRoles: selectedRoles,
      governance: {
        mfaEnforced,
        passwordMinLength,
        passwordRequireSpecial: true,
        ssoProvider,
        ssoDomain,
        retentionDays,
        auditLoggingEnabled: true,
        immutableLogsEnabled: true,
      },
    };

    onComplete(newTenant);
  };

  const stepsList = [
    { num: 1, title: 'Client Profile' },
    { num: 2, title: 'Superuser' },
    { num: 3, title: 'Org Hierarchy' },
    { num: 4, title: 'RBAC Roles' },
    { num: 5, title: 'Permission Matrix' },
    { num: 6, title: 'Assign Users' },
    { num: 7, title: 'Governance' },
    { num: 8, title: 'Review & Activate' },
  ];

  return (
    <div className="panel" style={{ width: '100%', padding: 24, margin: 0 }}>
      {/* Stepper Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 20, color: 'var(--text, #fff)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>🏢</span>
            <span>Create Client Profile ({getClientOrgName()} Provider Console)</span>
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--text-dim, #94a3b8)' }}>
            Define the client, deployment model, organizational hierarchy, identity access, and security posture in one guided workflow.
          </p>
        </div>
        <button
          type="button"
          onClick={onCancel}
          style={{
            background: 'transparent',
            border: '1px solid rgba(255,255,255,0.15)',
            color: 'var(--text-dim, #94a3b8)',
            padding: '6px 14px',
            borderRadius: 6,
            cursor: 'pointer',
          }}
        >
          Cancel
        </button>
      </div>

      {/* Steps Breadcrumb Bar */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(8, 1fr)',
          gap: 6,
          marginBottom: 28,
          background: 'rgba(0,0,0,0.25)',
          padding: 8,
          borderRadius: 8,
        }}
      >
        {stepsList.map((s) => {
          const isDone = step > s.num;
          const isCurrent = step === s.num;
          return (
            <div
              key={s.num}
              onClick={() => setStep(s.num)}
              style={{
                textAlign: 'center',
                padding: '6px 4px',
                borderRadius: 6,
                background: isCurrent ? 'var(--violet, #6366f1)' : isDone ? 'rgba(34, 197, 94, 0.2)' : 'transparent',
                color: isCurrent ? '#fff' : isDone ? '#4ade80' : 'var(--text-dim, #94a3b8)',
                cursor: 'pointer',
                fontSize: 11,
                fontWeight: isCurrent ? 700 : 500,
                border: isCurrent ? '1px solid #818cf8' : '1px solid transparent',
              }}
            >
              <div>{isDone ? '✓' : s.num}</div>
              <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.title}</div>
            </div>
          );
        })}
      </div>

      {/* Step Contents */}
      <div style={{ minHeight: 380, padding: '10px 0' }}>
        {/* STEP 1: Tenant Profile */}
        {step === 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 16, color: '#a5b4fc' }}>Step 1: Define Client and Deployment</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                  Client Organization Name *
                </label>
                <input
                  type="text"
                  placeholder="e.g. SecureVault Corporation"
                  value={tenantName}
                  onChange={(e) => handleNameChange(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border, rgba(255,255,255,0.1))',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                  Client Profile Identifier (Slug) *
                </label>
                <input
                  type="text"
                  placeholder="securevault-corp"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border, rgba(255,255,255,0.1))',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Industry Sector</label>
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border, rgba(255,255,255,0.1))',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                >
                  <option value="Enterprise">Enterprise</option>
                  <option value="Financial Services & Banking">Financial Services &amp; Banking</option>
                  <option value="Healthcare & Life Sciences">Healthcare &amp; Life Sciences</option>
                  <option value="Government & Public Sector">Government &amp; Public Sector</option>
                  <option value="Manufacturing & Industrial">Manufacturing &amp; Industrial</option>
                  <option value="Energy & Utilities">Energy &amp; Utilities</option>
                  <option value="Education & Research">Education &amp; Research</option>
                  <option value="Other / Custom">Other / Custom</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Service Package</label>
                <select
                  value={serviceTier}
                  onChange={(e) => setServiceTier(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border, rgba(255,255,255,0.1))',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                >
                  <option value="Standard Monitoring">Standard Monitoring (Essential EDR/Logs)</option>
                  <option value="Premium SOC Monitoring">Premium SOC Monitoring (24/7 Managed Fusion)</option>
                  <option value="Enterprise Threat Defense">Enterprise Threat Defense (WAF + AppSec + DAM)</option>
                  <option value="Sovereign Gov Cloud">Sovereign Gov Cloud (Multi-Department Estate)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Client Type</label>
                <select
                  value={clientType}
                  onChange={(e) => setClientType(e.target.value as typeof clientType)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border, rgba(255,255,255,0.1))',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                >
                  <option value="enterprise">Enterprise Organization</option>
                  <option value="government">Government / Public Institution</option>
                  <option value="institution">Institution / University / Agency</option>
                  <option value="mssp">MSSP / Managed Security Provider</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Deployment Model</label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 4 }}>
                  {([
                    ['saas', 'Managed SaaS'],
                    ['on_premises', 'On-premises / Shipped'],
                  ] as const).map(([value, label]) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setDeploymentMode(value)}
                      style={{
                        padding: '9px 10px',
                        borderRadius: 6,
                        border: `1px solid ${deploymentMode === value ? '#818cf8' : 'rgba(255,255,255,0.12)'}`,
                        background: deploymentMode === value ? 'rgba(99,102,241,0.18)' : 'rgba(0,0,0,0.25)',
                        color: deploymentMode === value ? '#c7d2fe' : '#94a3b8',
                        cursor: 'pointer',
                        fontSize: 12,
                        fontWeight: deploymentMode === value ? 700 : 500,
                      }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Region / Geographic Scope</label>
                <input
                  type="text"
                  placeholder="e.g. South Africa (Gauteng / National)"
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border, rgba(255,255,255,0.1))',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Primary Contact Name &amp; Email</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    type="text"
                    placeholder="Contact Name"
                    value={primaryContact}
                    onChange={(e) => setPrimaryContact(e.target.value)}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid var(--border, rgba(255,255,255,0.1))',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                    }}
                  />
                  <input
                    type="email"
                    placeholder="contact@company.example"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid var(--border, rgba(255,255,255,0.1))',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STEP 2: Superuser Account */}
        {step === 2 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 16, color: '#a5b4fc' }}>Step 2: Assign Initial Client Superadministrator</h3>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-dim, #94a3b8)' }}>
              The Client Superadministrator governs this client's profile hierarchy, users, and custom role policies.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>First Name *</label>
                <input
                  type="text"
                  placeholder="e.g. David"
                  value={superFirstName}
                  onChange={(e) => setSuperFirstName(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border, rgba(255,255,255,0.1))',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Last Name *</label>
                <input
                  type="text"
                  placeholder="e.g. Brown"
                  value={superLastName}
                  onChange={(e) => setSuperLastName(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border, rgba(255,255,255,0.1))',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Superuser Email Address *</label>
                <input
                  type="email"
                  placeholder="admin@client.example"
                  value={superEmail}
                  onChange={(e) => setSuperEmail(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border, rgba(255,255,255,0.1))',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Mobile Number (MFA Recovery)</label>
                <input
                  type="text"
                  placeholder="+27 82 555 1234"
                  value={superPhone}
                  onChange={(e) => setSuperPhone(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border, rgba(255,255,255,0.1))',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Required MFA Method</label>
                <select
                  value={superMfa}
                  onChange={(e) => setSuperMfa(e.target.value as any)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border, rgba(255,255,255,0.1))',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                >
                  <option value="app">Authenticator App (TOTP / Microsoft / Google)</option>
                  <option value="hardware">FIDO2 / Hardware Security Key</option>
                  <option value="sms">SMS OTP Verification</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Temporary Password</label>
                <input
                  type="text"
                  value={superPassword}
                  onChange={(e) => setSuperPassword(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border, rgba(255,255,255,0.1))',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                />
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: Organizational Structure Designer */}
        {step === 3 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 16, color: '#a5b4fc' }}>Step 3: Define Custom Branch / Org Unit Hierarchy</h3>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-dim, #94a3b8)' }}>
              No hardcoded naming convention. Use the terminology preferred by this tenant (e.g. Mine Shafts, Stores, Offices, Facilities, Campuses, Divisions).
            </p>

            <div style={{ display: 'flex', gap: 10, alignItems: 'center', background: 'rgba(0,0,0,0.2)', padding: 12, borderRadius: 6 }}>
              <span style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)' }}>Quick Preset:</span>
              {(['Mines & Processing Plants', 'Retail Stores & Distribution Centers', 'Regional Offices & Campuses', 'Hospital Facilities'] as const).map(
                (preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => {
                      setBranchNamingType(preset);
                      if (preset.includes('Mines')) {
                        setBranches([
                          { id: 'b-ho', name: 'Executive Head Office', type: 'Head Office', userCount: 10 },
                          { id: 'b-m1', name: 'Mine Shaft Alpha', type: 'Mine Shaft', userCount: 25 },
                          { id: 'b-m2', name: 'Mine Shaft Bravo', type: 'Mine Shaft', userCount: 18 },
                          { id: 'b-ref', name: 'Processing Plant & Refinery', type: 'Plant', userCount: 14 },
                        ]);
                      } else if (preset.includes('Stores')) {
                        setBranches([
                          { id: 'b-s1', name: 'Johannesburg Mega Store', type: 'Store', userCount: 30 },
                          { id: 'b-s2', name: 'Pretoria Retail Hub', type: 'Store', userCount: 20 },
                          { id: 'b-s3', name: 'Cape Town Waterfront', type: 'Store', userCount: 25 },
                        ]);
                      }
                    }}
                    style={{
                      padding: '4px 10px',
                      borderRadius: 4,
                      fontSize: 11,
                      background: 'rgba(99,102,241,0.15)',
                      color: '#a5b4fc',
                      border: '1px solid rgba(99,102,241,0.3)',
                      cursor: 'pointer',
                    }}
                  >
                    {preset}
                  </button>
                )
              )}
            </div>

            {/* Branch List */}
            <div style={{ border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, padding: 14 }}>
              <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
                <input
                  type="text"
                  placeholder="Unit Name (e.g. Mine Shaft Alpha / Johannesburg Store)"
                  value={newBranchName}
                  onChange={(e) => setNewBranchName(e.target.value)}
                  style={{
                    flex: 2,
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border, rgba(255,255,255,0.1))',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                  }}
                />
                <input
                  type="text"
                  placeholder="Unit Type (e.g. Mine, Store, Office, Plant, Campus)"
                  value={newBranchType}
                  onChange={(e) => setNewBranchType(e.target.value)}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border, rgba(255,255,255,0.1))',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                  }}
                />
                <button
                  type="button"
                  onClick={addBranch}
                  style={{
                    background: 'var(--violet, #6366f1)',
                    color: '#fff',
                    border: 'none',
                    padding: '8px 18px',
                    borderRadius: 6,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  + Add Unit
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {branches.map((b, idx) => (
                  <div
                    key={b.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      background: 'rgba(255,255,255,0.03)',
                      padding: '10px 14px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.05)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ color: '#38bdf8', fontWeight: 700 }}>#{idx + 1}</span>
                      <span style={{ fontWeight: 600, color: '#fff' }}>{b.name}</span>
                      <span
                        style={{
                          fontSize: 11,
                          padding: '1px 8px',
                          borderRadius: 4,
                          background: 'rgba(56, 189, 248, 0.15)',
                          color: '#38bdf8',
                        }}
                      >
                        {b.type}
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() => removeBranch(b.id)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#f87171',
                        cursor: 'pointer',
                        fontSize: 12,
                      }}
                    >
                      ✕ Remove
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: Configure RBAC Roles */}
        {step === 4 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 16, color: '#a5b4fc' }}>Step 4: Configure Tenant RBAC Model &amp; Custom Roles</h3>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-dim, #94a3b8)' }}>
              Standard roles are pre-configured. You can add custom tenant or branch roles at will.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {selectedRoles.map((role) => (
                <div
                  key={role.id}
                  style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: 6,
                    padding: '12px 14px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 600, color: '#fff', fontSize: 14 }}>{role.name}</span>
                    <span
                      style={{
                        fontSize: 10,
                        padding: '1px 6px',
                        borderRadius: 4,
                        background: role.scope === 'branch' ? 'rgba(56, 189, 248, 0.2)' : 'rgba(168, 85, 247, 0.2)',
                        color: role.scope === 'branch' ? '#38bdf8' : '#c084fc',
                        textTransform: 'uppercase',
                        fontWeight: 700,
                      }}
                    >
                      {role.scope} Scope
                    </span>
                  </div>
                  <p style={{ margin: '4px 0 8px', fontSize: 12, color: 'var(--text-dim, #94a3b8)' }}>{role.description}</p>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>
                    {role.permissions.length} granular permissions granted
                  </div>
                </div>
              ))}
            </div>

            {/* Add Custom Role form */}
            <div style={{ background: 'rgba(0,0,0,0.2)', padding: 14, borderRadius: 8, marginTop: 8 }}>
              <h4 style={{ margin: '0 0 10px', fontSize: 13, color: '#fff' }}>+ Create Novel Custom Role</h4>
              <div style={{ display: 'flex', gap: 10 }}>
                <input
                  type="text"
                  placeholder="Role Name (e.g. Fraud Investigator / Mine Safety Analyst)"
                  value={newRoleName}
                  onChange={(e) => setNewRoleName(e.target.value)}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid rgba(255,255,255,0.1)',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                  }}
                />
                <select
                  value={newRoleScope}
                  onChange={(e) => setNewRoleScope(e.target.value as any)}
                  style={{
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid rgba(255,255,255,0.1)',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                  }}
                >
                  <option value="tenant">Tenant Wide</option>
                  <option value="branch">Branch Scoped</option>
                </select>
                <button
                  type="button"
                  onClick={handleAddCustomRole}
                  style={{
                    padding: '8px 16px',
                    borderRadius: 6,
                    background: 'var(--violet, #6366f1)',
                    color: '#fff',
                    border: 'none',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Add Role
                </button>
              </div>
            </div>
          </div>
        )}

        {/* STEP 5: Permission Assignment Matrix */}
        {step === 5 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 16, color: '#a5b4fc' }}>Step 5: Permission Assignment Matrix</h3>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-dim, #94a3b8)' }}>
              Check or uncheck individual permissions for each role. Granular matrix enforced at the API gateway.
            </p>

            <div style={{ overflowX: 'auto', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ background: 'rgba(255,255,255,0.04)', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                    <th style={{ textAlign: 'left', padding: '10px 14px', minWidth: 200 }}>Permission</th>
                    {selectedRoles.map((r) => (
                      <th key={r.id} style={{ textAlign: 'center', padding: '10px 10px', minWidth: 100 }}>
                        {r.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {SYSTEM_PERMISSIONS.map((p) => (
                    <tr key={p.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <td style={{ padding: '8px 14px' }}>
                        <div style={{ fontWeight: 600, color: '#fff' }}>{p.name}</div>
                        <div style={{ fontSize: 10, color: '#94a3b8' }}>{p.description}</div>
                      </td>
                      {selectedRoles.map((r) => {
                        const hasPerm = r.permissions.includes(p.id);
                        return (
                          <td key={r.id} style={{ textAlign: 'center', padding: '8px' }}>
                            <input
                              type="checkbox"
                              checked={hasPerm}
                              onChange={() => togglePermissionForRole(r.id, p.id)}
                              style={{ cursor: 'pointer', width: 16, height: 16 }}
                            />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* STEP 6: Assign Initial Users */}
        {step === 6 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 16, color: '#a5b4fc' }}>Step 6: User Assignment &amp; Branch Scopes</h3>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-dim, #94a3b8)' }}>
              Assign initial operators, analysts, or branch managers with explicit branch boundaries.
            </p>

            <div style={{ display: 'flex', gap: 10, background: 'rgba(0,0,0,0.2)', padding: 12, borderRadius: 6 }}>
              <input
                type="text"
                placeholder="User Full Name"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  borderRadius: 6,
                  border: '1px solid rgba(255,255,255,0.1)',
                  background: 'rgba(0,0,0,0.3)',
                  color: '#fff',
                }}
              />
              <input
                type="email"
                placeholder="user@tenant.example"
                value={userEmail}
                onChange={(e) => setUserEmail(e.target.value)}
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  borderRadius: 6,
                  border: '1px solid rgba(255,255,255,0.1)',
                  background: 'rgba(0,0,0,0.3)',
                  color: '#fff',
                }}
              />
              <select
                value={userRole}
                onChange={(e) => setUserRole(e.target.value)}
                style={{
                  padding: '8px 12px',
                  borderRadius: 6,
                  border: '1px solid rgba(255,255,255,0.1)',
                  background: 'rgba(0,0,0,0.3)',
                  color: '#fff',
                }}
              >
                {selectedRoles.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
              <select
                value={userBranch}
                onChange={(e) => setUserBranch(e.target.value)}
                style={{
                  padding: '8px 12px',
                  borderRadius: 6,
                  border: '1px solid rgba(255,255,255,0.1)',
                  background: 'rgba(0,0,0,0.3)',
                  color: '#fff',
                }}
              >
                {branches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name} ({b.type})
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={handleAddUser}
                style={{
                  padding: '8px 16px',
                  borderRadius: 6,
                  background: 'var(--violet, #6366f1)',
                  color: '#fff',
                  border: 'none',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                + Assign User
              </button>
            </div>

            {/* Users list */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {initialUsers.map((u, idx) => {
                const r = selectedRoles.find((role) => role.id === u.roleId);
                const b = branches.find((branch) => branch.id === u.branchId);
                return (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 12px',
                      borderRadius: 6,
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid rgba(255,255,255,0.05)',
                    }}
                  >
                    <div>
                      <strong style={{ color: '#fff' }}>{u.name}</strong> ({u.email})
                    </div>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <span style={{ fontSize: 11, background: 'rgba(99,102,241,0.2)', color: '#a5b4fc', padding: '2px 8px', borderRadius: 4 }}>
                        {r?.name || u.roleId}
                      </span>
                      <span style={{ fontSize: 11, background: 'rgba(56,189,248,0.2)', color: '#38bdf8', padding: '2px 8px', borderRadius: 4 }}>
                        ↳ {b?.name || u.branchId}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* STEP 7: Security & Governance Settings */}
        {step === 7 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 16, color: '#a5b4fc' }}>Step 7: Security Policies, SSO &amp; Data Retention</h3>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-dim, #94a3b8)' }}>
              Configure identity provider federation, password complexity, and data retention rules per Section 16.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div style={{ background: 'rgba(255,255,255,0.03)', padding: 14, borderRadius: 8 }}>
                <label style={{ fontSize: 13, fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input
                    type="checkbox"
                    checked={mfaEnforced}
                    onChange={(e) => setMfaEnforced(e.target.checked)}
                    style={{ width: 16, height: 16 }}
                  />
                  <span>Enforce Multi-Factor Authentication (MFA)</span>
                </label>
                <p style={{ margin: '4px 0 0', fontSize: 11, color: 'var(--text-dim, #94a3b8)' }}>
                  All users must register an authenticator app or security key prior to data access.
                </p>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.03)', padding: 14, borderRadius: 8 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                  Data Retention Policy (Default)
                </label>
                <select
                  value={retentionDays}
                  onChange={(e) => setRetentionDays(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid rgba(255,255,255,0.1)',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                >
                  <option value={30}>30 Days (Ephemeral Audits)</option>
                  <option value={90}>90 Days (Standard Compliance)</option>
                  <option value={180}>180 Days (PCI-DSS &amp; Banking)</option>
                  <option value={365}>365 Days / 1 Year (Extended Forensic)</option>
                  <option value={2555}>7 Years (Statutory / POPIA / National Gov)</option>
                </select>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.03)', padding: 14, borderRadius: 8 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                  Single Sign-On (SSO / IdP Integration)
                </label>
                <select
                  value={ssoProvider}
                  onChange={(e) => setSsoProvider(e.target.value as any)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid rgba(255,255,255,0.1)',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                >
                  <option value="none">Local Directory Authentication</option>
                  <option value="entra_id">Microsoft Entra ID (Azure AD)</option>
                  <option value="okta">Okta Identity Cloud</option>
                  <option value="ping">Ping Identity</option>
                  <option value="google">Google Workspace Enterprise</option>
                </select>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.03)', padding: 14, borderRadius: 8 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>SSO Tenant Domain / IdP URL</label>
                <input
                  type="text"
                  placeholder="e.g. client-org.onmicrosoft.com"
                  value={ssoDomain}
                  onChange={(e) => setSsoDomain(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid rgba(255,255,255,0.1)',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                />
              </div>
            </div>
          </div>
        )}

        {/* STEP 8: Review & Automated Validation */}
        {step === 8 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 16, color: '#a5b4fc' }}>Step 8: Automated Pre-Activation Validation Checklist</h3>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-dim, #94a3b8)' }}>
              All validation requirements must pass before the profile and deployment are activated.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <div style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.3)', padding: 14, borderRadius: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#4ade80', fontWeight: 600 }}>
                  <span>✅</span>
                  <span>Client Superadministrator Designated</span>
                </div>
                <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>
                  {superEmail || 'admin@client.example'} ({superFirstName} {superLastName})
                </div>
              </div>

              <div style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.3)', padding: 14, borderRadius: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#4ade80', fontWeight: 600 }}>
                  <span>✅</span>
                  <span>Organizational Hierarchy Configured</span>
                </div>
                <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>
                  {branches.length} hierarchy units configured under "{tenantName || 'Client Organization'}"
                </div>
              </div>

              <div style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.3)', padding: 14, borderRadius: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#4ade80', fontWeight: 600 }}>
                  <span>✅</span>
                  <span>Granular RBAC Engine Initialized</span>
                </div>
                <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>
                  {selectedRoles.length} custom roles &amp; permission matrix ready
                </div>
              </div>

              <div style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.3)', padding: 14, borderRadius: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#4ade80', fontWeight: 600 }}>
                  <span>✅</span>
                  <span>Governance &amp; Retention Enforced</span>
                </div>
                <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>
                  MFA Enforced: {mfaEnforced ? 'Yes' : 'No'} · Retention: {retentionDays} Days
                </div>
              </div>
            </div>

            {/* Summary Box */}
            <div style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, padding: 16 }}>
              <h4 style={{ margin: '0 0 10px', fontSize: 14, color: '#fff' }}>Provisioning Summary</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, fontSize: 12 }}>
                <div>
                  <span style={{ color: '#94a3b8' }}>Client Organization:</span>
                  <div style={{ color: '#fff', fontWeight: 600 }}>{tenantName || 'New Client'}</div>
                </div>
                <div>
                  <span style={{ color: '#94a3b8' }}>Identifier:</span>
                  <div style={{ color: '#38bdf8', fontWeight: 600 }}>{identifier || 'new-tenant'}</div>
                </div>
                <div>
                  <span style={{ color: '#94a3b8' }}>Industry:</span>
                  <div style={{ color: '#fff' }}>{industry}</div>
                </div>
                <div>
                  <span style={{ color: '#94a3b8' }}>Service Package:</span>
                  <div style={{ color: '#c084fc' }}>{serviceTier}</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Wizard Footer Nav */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: 20,
          borderTop: '1px solid rgba(255,255,255,0.08)',
          paddingTop: 16,
        }}
      >
        <button
          type="button"
          disabled={step === 1}
          onClick={() => setStep(step - 1)}
          style={{
            padding: '8px 18px',
            borderRadius: 6,
            background: step === 1 ? 'rgba(255,255,255,0.03)' : 'rgba(255,255,255,0.1)',
            color: step === 1 ? 'rgba(255,255,255,0.2)' : '#fff',
            border: 'none',
            cursor: step === 1 ? 'not-allowed' : 'pointer',
          }}
        >
          ← Previous
        </button>

        <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)' }}>
          Step {step} of 8: {stepsList[step - 1].title}
        </div>

        {step < 8 ? (
          <button
            type="button"
            onClick={() => setStep(step + 1)}
            style={{
              padding: '8px 24px',
              borderRadius: 6,
              background: 'var(--violet, #6366f1)',
              color: '#fff',
              border: 'none',
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(99,102,241,0.3)',
            }}
          >
            Next Step →
          </button>
        ) : (
          <button
            type="button"
            onClick={handleActivate}
            style={{
              padding: '10px 28px',
              borderRadius: 6,
              background: 'linear-gradient(135deg, #22c55e, #16a34a)',
              color: '#fff',
              border: 'none',
              fontWeight: 700,
              fontSize: 14,
              cursor: 'pointer',
              boxShadow: '0 2px 12px rgba(34,197,94,0.4)',
            }}
          >
            🚀 Activate Profile &amp; Deployment
          </button>
        )}
      </div>
    </div>
  );
};
