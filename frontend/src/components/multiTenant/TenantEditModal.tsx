import React, { useState } from 'react';
import { Tenant } from '../../types/multiTenant';
import { setClientOrgName } from '../../utils/tenantTerminology';

interface Props {
  tenant: Tenant;
  onClose: () => void;
  onSave: (updated: Tenant) => void;
}

export const TenantEditModal: React.FC<Props> = ({ tenant, onClose, onSave }) => {
  const [name, setName] = useState(tenant.name);
  const [identifier, setIdentifier] = useState(tenant.identifier);
  const [industry, setIndustry] = useState(tenant.industry);
  const [serviceTier, setServiceTier] = useState(tenant.serviceTier);
  const [region, setRegion] = useState(tenant.region);
  const [primaryContact, setPrimaryContact] = useState(tenant.primaryContact);
  const [contactEmail, setContactEmail] = useState(tenant.contactEmail);

  // Superuser state
  const [superFirstName, setSuperFirstName] = useState(tenant.superuser.firstName);
  const [superLastName, setSuperLastName] = useState(tenant.superuser.lastName);
  const [superEmail, setSuperEmail] = useState(tenant.superuser.email);
  const [superPhone, setSuperPhone] = useState(tenant.superuser.phone || '');
  const [mfaMethod, setMfaMethod] = useState(tenant.superuser.mfaMethod || 'app');

  // Governance state
  const [ssoProvider, setSsoProvider] = useState(tenant.governance?.ssoProvider || 'none');
  const [ssoDomain, setSsoDomain] = useState(tenant.governance?.ssoDomain || '');
  const [retentionDays, setRetentionDays] = useState(tenant.governance?.retentionDays || 90);
  const [mfaEnforced, setMfaEnforced] = useState(tenant.governance?.mfaEnforced ?? true);

  const [activeTab, setActiveTab] = useState<'profile' | 'superuser' | 'governance'>('profile');
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const updated: Tenant = {
      ...tenant,
      name: name.trim() || tenant.name,
      identifier: identifier.trim() || tenant.identifier,
      industry: industry.trim() || tenant.industry,
      serviceTier: serviceTier.trim() || tenant.serviceTier,
      region: region.trim() || tenant.region,
      primaryContact: primaryContact.trim() || tenant.primaryContact,
      contactEmail: contactEmail.trim() || tenant.contactEmail,
      superuser: {
        ...tenant.superuser,
        firstName: superFirstName.trim() || tenant.superuser.firstName,
        lastName: superLastName.trim() || tenant.superuser.lastName,
        email: superEmail.trim() || tenant.superuser.email,
        phone: superPhone.trim(),
        mfaMethod,
      },
      governance: {
        ...tenant.governance,
        ssoProvider,
        ssoDomain: ssoDomain.trim(),
        retentionDays: Number(retentionDays) || 90,
        mfaEnforced,
      },
      lastActiveDate: new Date().toISOString().split('T')[0],
    };

    // Propagate dynamic client organization name update if this tenant is modified
    setClientOrgName(updated.name);
    onSave(updated);
    setSaveSuccess(true);
    setTimeout(() => {
      onClose();
    }, 600);
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.8)',
        backdropFilter: 'blur(5px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1100,
        padding: 20,
      }}
    >
      <div
        className="panel"
        style={{
          width: '100%',
          maxWidth: 680,
          background: 'var(--panel-bg, #111827)',
          border: '1px solid rgba(99, 102, 241, 0.3)',
          borderRadius: 12,
          boxShadow: '0 25px 50px rgba(0,0,0,0.7)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '90vh',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '18px 24px',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'rgba(255,255,255,0.02)',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 18 }}>✏️</span>
              <h3 style={{ margin: 0, fontSize: 18, color: '#fff', fontWeight: 700 }}>
                Edit Tenant — {tenant.name}
              </h3>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)', marginTop: 4 }}>
              Update client organization profile, superuser credentials, and governance policies
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              fontSize: 20,
              cursor: 'pointer',
              padding: 4,
            }}
          >
            ✕
          </button>
        </div>

        {/* Tab Selector */}
        <div
          style={{
            display: 'flex',
            gap: 2,
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            background: 'rgba(0,0,0,0.2)',
            padding: '0 24px',
          }}
        >
          {[
            { key: 'profile', label: '🏢 Organization Profile' },
            { key: 'superuser', label: '👤 Superuser Admin' },
            { key: 'governance', label: '🔒 Governance & SSO' },
          ].map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setActiveTab(t.key as any)}
              style={{
                padding: '12px 16px',
                fontSize: 13,
                fontWeight: activeTab === t.key ? 700 : 500,
                color: activeTab === t.key ? '#fff' : 'var(--text-dim, #94a3b8)',
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === t.key ? '3px solid var(--violet, #6366f1)' : '3px solid transparent',
                cursor: 'pointer',
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ overflowY: 'auto', padding: '20px 24px', flex: 1 }}>
          {activeTab === 'profile' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                  Organization Name *
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. SecureVault Corp or National Treasury"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid rgba(255,255,255,0.15)',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                />
                <div style={{ fontSize: 11, color: '#38bdf8', marginTop: 4 }}>
                  ℹ️ Updating this name dynamically replaces the "MSSP" term across all platform dashboards and dashboards.
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                    Tenant Identifier (Slug) *
                  </label>
                  <input
                    type="text"
                    required
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    placeholder="e.g. securevault-corp"
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                    }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                    Industry Sector
                  </label>
                  <input
                    type="text"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    placeholder="e.g. Financial Services, Mining, Government"
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                    Service Package
                  </label>
                  <select
                    value={serviceTier}
                    onChange={(e) => setServiceTier(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                    }}
                  >
                    <option value="Premium SOC Monitoring">Premium SOC Monitoring</option>
                    <option value="Enterprise Threat Defense">Enterprise Threat Defense</option>
                    <option value="Sovereign Gov Cloud + DAM">Sovereign Gov Cloud + DAM</option>
                    <option value="Standard Monitoring">Standard Monitoring</option>
                    <option value="POPIA/HIPAA Compliance">POPIA/HIPAA Compliance</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                    Operational Region
                  </label>
                  <input
                    type="text"
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                    placeholder="e.g. South Africa, EMEA, Global"
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                    Primary Contact Person
                  </label>
                  <input
                    type="text"
                    value={primaryContact}
                    onChange={(e) => setPrimaryContact(e.target.value)}
                    placeholder="e.g. David Brown (Group CISO)"
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                    }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                    Contact Email Address
                  </label>
                  <input
                    type="email"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    placeholder="e.g. contact@client.example"
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                    }}
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'superuser' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ background: 'rgba(99, 102, 241, 0.08)', padding: 12, borderRadius: 6, border: '1px solid rgba(99, 102, 241, 0.2)' }}>
                <div style={{ fontWeight: 600, fontSize: 13, color: '#a5b4fc' }}>Client Superuser Account</div>
                <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)', marginTop: 2 }}>
                  This administrator has universal control within this client organization and can onboard operational teams, configure branches, and manage tenant RBAC.
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                    First Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={superFirstName}
                    onChange={(e) => setSuperFirstName(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                    }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                    Last Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={superLastName}
                    onChange={(e) => setSuperLastName(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                    }}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                  Superuser Email Address *
                </label>
                <input
                  type="email"
                  required
                  value={superEmail}
                  onChange={(e) => setSuperEmail(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid rgba(255,255,255,0.15)',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                    Phone Number
                  </label>
                  <input
                    type="text"
                    value={superPhone}
                    onChange={(e) => setSuperPhone(e.target.value)}
                    placeholder="+27..."
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                    }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                    MFA Verification Method
                  </label>
                  <select
                    value={mfaMethod}
                    onChange={(e) => setMfaMethod(e.target.value as any)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                    }}
                  >
                    <option value="app">Authenticator App (TOTP / FreeOTP)</option>
                    <option value="hardware">Hardware Security Key (FIDO2 / WebAuthn)</option>
                    <option value="sms">SMS OTP (Fallback)</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'governance' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                    SSO / Identity Provider
                  </label>
                  <select
                    value={ssoProvider}
                    onChange={(e) => setSsoProvider(e.target.value as any)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                    }}
                  >
                    <option value="none">None (Local RBAC Database)</option>
                    <option value="entra_id">Microsoft Entra ID / Azure AD</option>
                    <option value="okta">Okta Identity Cloud</option>
                    <option value="ping">Ping Identity</option>
                    <option value="google">Google Workspace</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                    SSO Domain (if configured)
                  </label>
                  <input
                    type="text"
                    value={ssoDomain}
                    onChange={(e) => setSsoDomain(e.target.value)}
                    placeholder="e.g. client.onmicrosoft.com"
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                    }}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                  Audit &amp; Telemetry Retention Window (Days)
                </label>
                <select
                  value={retentionDays}
                  onChange={(e) => setRetentionDays(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid rgba(255,255,255,0.15)',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                  }}
                >
                  <option value={30}>30 Days (Standard Operations)</option>
                  <option value={90}>90 Days (Recommended / SOC Baseline)</option>
                  <option value={180}>180 Days (Extended Regulatory)</option>
                  <option value={365}>365 Days (POPIA / Sovereign / Banking WORM)</option>
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
                <input
                  type="checkbox"
                  id="mfaEnforcedCheck"
                  checked={mfaEnforced}
                  onChange={(e) => setMfaEnforced(e.target.checked)}
                />
                <label htmlFor="mfaEnforcedCheck" style={{ fontSize: 13, color: '#fff', cursor: 'pointer' }}>
                  Enforce Multi-Factor Authentication (MFA) for all tenant operators
                </label>
              </div>
            </div>
          )}

          {/* Footer Actions */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginTop: 24,
              paddingTop: 16,
              borderTop: '1px solid rgba(255,255,255,0.08)',
            }}
          >
            {saveSuccess ? (
              <span style={{ color: '#4ade80', fontSize: 13, fontWeight: 600 }}>
                ✓ Tenant changes saved successfully!
              </span>
            ) : (
              <span style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)' }}>
                All updates are signed and recorded to the immutable audit log.
              </span>
            )}

            <div style={{ display: 'flex', gap: 10 }}>
              <button
                type="button"
                onClick={onClose}
                style={{
                  padding: '8px 16px',
                  borderRadius: 6,
                  background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.15)',
                  color: '#fff',
                  cursor: 'pointer',
                  fontSize: 13,
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                style={{
                  padding: '8px 20px',
                  borderRadius: 6,
                  background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
                  color: '#fff',
                  fontWeight: 600,
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: 13,
                  boxShadow: '0 2px 8px rgba(99,102,241,0.3)',
                }}
              >
                💾 Save Tenant Changes
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
