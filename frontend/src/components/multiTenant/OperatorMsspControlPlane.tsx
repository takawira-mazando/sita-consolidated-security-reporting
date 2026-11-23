import React, { useState } from 'react';
import { MSSPOrganization, MSSPSuperuser, Tenant } from '../../types/multiTenant';

interface Props {
  mssps: MSSPOrganization[];
  tenants: Tenant[];
  onSaveMssps: (updated: MSSPOrganization[]) => void;
  onSelectMsspForPortal: (mssp: MSSPOrganization) => void;
}

export const OperatorMsspControlPlane: React.FC<Props> = ({
  mssps,
  tenants,
  onSaveMssps,
  onSelectMsspForPortal,
}) => {
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Modals state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingSuperuserMssp, setEditingSuperuserMssp] = useState<MSSPOrganization | null>(null);
  const [editingQuotaMssp, setEditingQuotaMssp] = useState<MSSPOrganization | null>(null);

  // New Client Form State
  const [formName, setFormName] = useState('');
  const [formCode, setFormCode] = useState('');
  const [formType, setFormType] = useState<MSSPOrganization['type']>('government_agency');
  const [formRegion, setFormRegion] = useState('South Africa (National Government Estate)');
  const [formServiceTier, setFormServiceTier] = useState<MSSPOrganization['serviceTier']>('Sovereign Gov Cloud');
  const [formSlaTier, setFormSlaTier] = useState<MSSPOrganization['slaTier']>('24/7 Sovereign Critical');
  const [formMaxTenants, setFormMaxTenants] = useState(50);
  const [formNotes, setFormNotes] = useState('');

  // Superuser fields
  const [suFirstName, setSuFirstName] = useState('');
  const [suLastName, setSuLastName] = useState('');
  const [suEmail, setSuEmail] = useState('');
  const [suPhone, setSuPhone] = useState('');
  const [suMfaMethod, setSuMfaMethod] = useState<'app' | 'hardware' | 'sms'>('hardware');
  const [suStatus, setSuStatus] = useState<'active' | 'pending_invite'>('active');

  // Modules
  const [modSoc, setModSoc] = useState(true);
  const [modAppsec, setModAppsec] = useState(true);
  const [modDbsec, setModDbsec] = useState(true);
  const [modCompliance, setModCompliance] = useState(true);
  const [modAi, setModAi] = useState(true);

  // Edit Superuser Modal State
  const [editSuFirst, setEditSuFirst] = useState('');
  const [editSuLast, setEditSuLast] = useState('');
  const [editSuEmail, setEditSuEmail] = useState('');
  const [editSuPhone, setEditSuPhone] = useState('');
  const [editSuMfa, setEditSuMfa] = useState<'app' | 'hardware' | 'sms'>('hardware');
  const [editSuStatus, setEditSuStatus] = useState<'active' | 'pending_invite' | 'suspended'>('active');

  // Edit Quota Modal State
  const [editMaxTenants, setEditMaxTenants] = useState(50);
  const [editServiceTier, setEditServiceTier] = useState<MSSPOrganization['serviceTier']>('Sovereign Gov Cloud');
  const [editSlaTier, setEditSlaTier] = useState<MSSPOrganization['slaTier']>('24/7 Sovereign Critical');
  const [editModules, setEditModules] = useState<string[]>([]);

  // Filtering
  const filteredMssps = mssps.filter((m) => {
    const matchesSearch =
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      m.code.toLowerCase().includes(search.toLowerCase()) ||
      m.region.toLowerCase().includes(search.toLowerCase()) ||
      m.superuser.email.toLowerCase().includes(search.toLowerCase()) ||
      `${m.superuser.firstName} ${m.superuser.lastName}`.toLowerCase().includes(search.toLowerCase());
    const matchesType = typeFilter === 'all' || m.type === typeFilter;
    const matchesStatus = statusFilter === 'all' || m.status === statusFilter;
    return matchesSearch && matchesType && matchesStatus;
  });

  const totalTenantsCount = tenants.length;
  const activeMsspsCount = mssps.filter((m) => m.status === 'active').length;

  const handleOpenCreate = () => {
    setFormName('');
    setFormCode('');
    setFormType('government_agency');
    setFormRegion('South Africa (National Government Estate)');
    setFormServiceTier('Sovereign Gov Cloud');
    setFormSlaTier('24/7 Sovereign Critical');
    setFormMaxTenants(50);
    setFormNotes('');
    setSuFirstName('');
    setSuLastName('');
    setSuEmail('');
    setSuPhone('');
    setSuMfaMethod('hardware');
    setSuStatus('active');
    setModSoc(true);
    setModAppsec(true);
    setModDbsec(true);
    setModCompliance(true);
    setModAi(true);
    setShowCreateModal(true);
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim() || !formCode.trim() || !suEmail.trim()) return;

    const allowedMods: string[] = [];
    if (modSoc) allowedMods.push('soc');
    if (modAppsec) allowedMods.push('appsec');
    if (modDbsec) allowedMods.push('dbsec');
    if (modCompliance) allowedMods.push('compliance');
    if (modAi) allowedMods.push('ai_suite');

    const newMssp: MSSPOrganization = {
      id: `mssp-${formCode.trim().toLowerCase().replace(/[^a-z0-9-]/g, '-')}`,
      name: formName.trim(),
      code: formCode.trim().toUpperCase(),
      type: formType,
      region: formRegion.trim(),
      serviceTier: formServiceTier,
      slaTier: formSlaTier,
      maxTenants: Number(formMaxTenants) || 50,
      status: 'active',
      superuser: {
        firstName: suFirstName.trim() || 'Client',
        lastName: suLastName.trim() || 'Superuser',
        email: suEmail.trim(),
        phone: suPhone.trim() || undefined,
        mfaMethod: suMfaMethod,
        status: suStatus,
        lastLogin: 'Never',
        accessKeyId: `hosi_sec_${formCode.toLowerCase()}_${Math.random().toString(36).substring(2, 7)}`,
      },
      allowedModules: allowedMods,
      createdDate: new Date().toISOString().split('T')[0],
      notes: formNotes.trim() || undefined,
    };

    onSaveMssps([newMssp, ...mssps]);
    setShowCreateModal(false);
  };

  const handleOpenEditSuperuser = (m: MSSPOrganization) => {
    setEditingSuperuserMssp(m);
    setEditSuFirst(m.superuser.firstName);
    setEditSuLast(m.superuser.lastName);
    setEditSuEmail(m.superuser.email);
    setEditSuPhone(m.superuser.phone || '');
    setEditSuMfa(m.superuser.mfaMethod);
    setEditSuStatus(m.superuser.status);
  };

  const handleSaveSuperuser = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingSuperuserMssp) return;

    const updatedMssps = mssps.map((m) => {
      if (m.id === editingSuperuserMssp.id) {
        return {
          ...m,
          superuser: {
            ...m.superuser,
            firstName: editSuFirst.trim(),
            lastName: editSuLast.trim(),
            email: editSuEmail.trim(),
            phone: editSuPhone.trim() || undefined,
            mfaMethod: editSuMfa,
            status: editSuStatus,
          },
        };
      }
      return m;
    });

    onSaveMssps(updatedMssps);
    setEditingSuperuserMssp(null);
  };

  const handleOpenEditQuota = (m: MSSPOrganization) => {
    setEditingQuotaMssp(m);
    setEditMaxTenants(m.maxTenants);
    setEditServiceTier(m.serviceTier);
    setEditSlaTier(m.slaTier);
    setEditModules([...m.allowedModules]);
  };

  const handleSaveQuota = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingQuotaMssp) return;

    const updatedMssps = mssps.map((m) => {
      if (m.id === editingQuotaMssp.id) {
        return {
          ...m,
          maxTenants: Number(editMaxTenants) || m.maxTenants,
          serviceTier: editServiceTier,
          slaTier: editSlaTier,
          allowedModules: editModules,
        };
      }
      return m;
    });

    onSaveMssps(updatedMssps);
    setEditingQuotaMssp(null);
  };

  const handleToggleStatus = (m: MSSPOrganization) => {
    const nextStatus = m.status === 'active' ? 'suspended' : 'active';
    const updated: MSSPOrganization[] = mssps.map((item) =>
      item.id === m.id ? { ...item, status: nextStatus } : item
    );
    onSaveMssps(updated);
  };

  const getTypeBadge = (type: MSSPOrganization['type']) => {
    switch (type) {
      case 'government_agency':
        return { label: 'Government Agency', bg: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', border: 'rgba(59, 130, 246, 0.3)' };
      case 'commercial_mssp':
        return { label: 'Commercial MSSP', bg: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: 'rgba(168, 85, 247, 0.3)' };
      case 'telecom_mssp':
        return { label: 'Telecom MSSP', bg: 'rgba(234, 179, 8, 0.15)', color: '#facc15', border: 'rgba(234, 179, 8, 0.3)' };
      default:
        return { label: 'Enterprise MSSP', bg: 'rgba(34, 197, 94, 0.15)', color: '#4ade80', border: 'rgba(34, 197, 94, 0.3)' };
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Operator Banner */}
      <div
        className="panel"
        style={{
          padding: '20px 24px',
          background: 'linear-gradient(135deg, rgba(30, 27, 75, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%)',
          border: '1px solid rgba(139, 92, 246, 0.35)',
          borderRadius: 12,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 16,
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 24 }}>⚡</span>
            <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: '#f8fafc' }}>
              Hosi Technologies — Developer & Master Operator Console
            </h2>
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                padding: '3px 8px',
                borderRadius: 4,
                background: 'rgba(139, 92, 246, 0.25)',
                color: '#c084fc',
                border: '1px solid rgba(139, 92, 246, 0.4)',
              }}
            >
              Master Operator
            </span>
          </div>
          <p style={{ margin: '8px 0 0', fontSize: 13, color: 'var(--text-dim, #94a3b8)', maxWidth: 840 }}>
            Platform Developer &amp; Owner Administration. Provision and govern Client Organizations, commercial partners, and enterprise partners,
            allocate multi-tenant capacity quotas, and grant operator-provisioned Client Superuser credentials.
          </p>
        </div>

        <button
          type="button"
          onClick={handleOpenCreate}
          style={{
            padding: '10px 20px',
            fontSize: 13,
            fontWeight: 700,
            borderRadius: 8,
            background: 'linear-gradient(135deg, #7c3aed, #4f46e5)',
            color: '#fff',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            boxShadow: '0 4px 14px rgba(124, 58, 237, 0.35)',
          }}
        >
          <span>✨</span> + Provision Client / MSSP
        </button>
      </div>

      {/* Top Metric Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: 16,
        }}
      >
        <div className="panel" style={{ padding: '16px 20px', borderLeft: '4px solid #8b5cf6' }}>
          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim, #94a3b8)' }}>
            Client Organizations (MSSPs)
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#c084fc', marginTop: 4 }}>
            {mssps.length}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)', marginTop: 4 }}>
            {activeMsspsCount} active client organizations
          </div>
        </div>

        <div className="panel" style={{ padding: '16px 20px', borderLeft: '4px solid #38bdf8' }}>
          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim, #94a3b8)' }}>
            Total Managed Client Tenants
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#38bdf8', marginTop: 4 }}>
            {totalTenantsCount}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)', marginTop: 4 }}>
            Distributed across provisioned MSSPs
          </div>
        </div>

        <div className="panel" style={{ padding: '16px 20px', borderLeft: '4px solid #22c55e' }}>
          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim, #94a3b8)' }}>
            Client Superusers Provisioned
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#4ade80', marginTop: 4 }}>
            {mssps.filter((m) => m.superuser?.status === 'active').length}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)', marginTop: 4 }}>
            100% MFA Enforced (FIDO2 Hardware &amp; App)
          </div>
        </div>

        <div className="panel" style={{ padding: '16px 20px', borderLeft: '4px solid #facc15' }}>
          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim, #94a3b8)' }}>
            Platform Modules Governed
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#facc15', marginTop: 4 }}>
            5 / 5
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)', marginTop: 4 }}>
            SOC, AppSec, DBSec, Compliance, AI Suite
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div
        className="panel"
        style={{
          padding: '14px 20px',
          display: 'flex',
          flexWrap: 'wrap',
          gap: 12,
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', gap: 10, flex: 1, minWidth: 260, alignItems: 'center' }}>
          <input
            type="text"
            placeholder="Search client name, code, superuser email, region..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: 6,
              border: '1px solid rgba(255,255,255,0.1)',
              background: 'rgba(0,0,0,0.3)',
              color: '#fff',
              fontSize: 13,
            }}
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch('')}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-dim, #94a3b8)',
                cursor: 'pointer',
                fontSize: 12,
              }}
            >
              Clear
            </button>
          )}
        </div>

        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            style={{
              padding: '8px 12px',
              borderRadius: 6,
              border: '1px solid rgba(255,255,255,0.1)',
              background: 'rgba(0,0,0,0.3)',
              color: '#fff',
              fontSize: 13,
            }}
          >
            <option value="all">All Organization Types</option>
            <option value="government_agency">Government Agency</option>
            <option value="commercial_mssp">Commercial MSSP</option>
            <option value="telecom_mssp">Telecom MSSP</option>
            <option value="enterprise_mssp">Enterprise MSSP</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{
              padding: '8px 12px',
              borderRadius: 6,
              border: '1px solid rgba(255,255,255,0.1)',
              background: 'rgba(0,0,0,0.3)',
              color: '#fff',
              fontSize: 13,
            }}
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="provisioning">Provisioning</option>
            <option value="suspended">Suspended</option>
          </select>
        </div>
      </div>

      {/* Client Organizations (MSSPs) List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {filteredMssps.length === 0 ? (
          <div className="panel" style={{ padding: 40, textAlign: 'center', color: 'var(--text-dim, #94a3b8)' }}>
            <div style={{ fontSize: 32, marginBottom: 10 }}>🛡️</div>
            <div style={{ fontSize: 16, fontWeight: 600, color: '#fff' }}>No Client Organizations Found</div>
            <p style={{ fontSize: 13, marginTop: 4 }}>
              No clients match the current search or filters. Click &quot;+ Provision Client / MSSP&quot; to onboard an organization.
            </p>
          </div>
        ) : (
          filteredMssps.map((m) => {
            const tb = getTypeBadge(m.type);
            const clientTenants = tenants.filter((t) => t.msspId === m.id);
            const tenantUsagePercent = Math.min(100, Math.round((clientTenants.length / (m.maxTenants || 1)) * 100));

            return (
              <div
                key={m.id}
                className="panel"
                style={{
                  padding: 24,
                  border: m.status === 'suspended' ? '1px solid rgba(234, 179, 8, 0.4)' : '1px solid rgba(255,255,255,0.08)',
                  background: 'rgba(15, 23, 42, 0.65)',
                  borderRadius: 10,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 16,
                }}
              >
                {/* Header row: Name, Code, Badges, Actions */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
                  <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
                    <div
                      style={{
                        width: 48,
                        height: 48,
                        borderRadius: 8,
                        background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(168, 85, 247, 0.3))',
                        border: '1px solid rgba(139, 92, 246, 0.4)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 20,
                        fontWeight: 700,
                        color: '#c084fc',
                      }}
                    >
                      {m.code.substring(0, 2)}
                    </div>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 18, fontWeight: 700, color: '#fff' }}>{m.name}</span>
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: 4,
                            background: tb.bg,
                            color: tb.color,
                            border: `1px solid ${tb.border}`,
                          }}
                        >
                          {tb.label}
                        </span>
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 600,
                            padding: '2px 8px',
                            borderRadius: 4,
                            background: m.status === 'active' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(234, 179, 8, 0.15)',
                            color: m.status === 'active' ? '#4ade80' : '#facc15',
                            border: m.status === 'active' ? '1px solid rgba(34, 197, 94, 0.3)' : '1px solid rgba(234, 179, 8, 0.3)',
                          }}
                        >
                          {m.status.toUpperCase()}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)', marginTop: 4, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                        <span>📍 {m.region}</span>
                        <span>·</span>
                        <span>🛡️ Tier: <strong style={{ color: '#e2e8f0' }}>{m.serviceTier}</strong></span>
                        <span>·</span>
                        <span>⏱️ SLA: <strong style={{ color: '#e2e8f0' }}>{m.slaTier}</strong></span>
                      </div>
                    </div>
                  </div>

                  {/* Actions for this client */}
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      onClick={() => onSelectMsspForPortal(m)}
                      title="Switch to Client Command Center to view & manage this client's tenants"
                      style={{
                        padding: '8px 14px',
                        fontSize: 12,
                        fontWeight: 700,
                        borderRadius: 6,
                        background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
                        color: '#fff',
                        border: 'none',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                      }}
                    >
                      <span>🚀</span> Launch Client Command Center
                    </button>

                    <button
                      type="button"
                      onClick={() => handleOpenEditSuperuser(m)}
                      style={{
                        padding: '8px 12px',
                        fontSize: 12,
                        fontWeight: 600,
                        borderRadius: 6,
                        background: 'rgba(255,255,255,0.06)',
                        color: '#cbd5e1',
                        border: '1px solid rgba(255,255,255,0.15)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                      }}
                    >
                      <span>🔑</span> Superuser Access
                    </button>

                    <button
                      type="button"
                      onClick={() => handleOpenEditQuota(m)}
                      style={{
                        padding: '8px 12px',
                        fontSize: 12,
                        fontWeight: 600,
                        borderRadius: 6,
                        background: 'rgba(255,255,255,0.06)',
                        color: '#cbd5e1',
                        border: '1px solid rgba(255,255,255,0.15)',
                        cursor: 'pointer',
                      }}
                    >
                      ✏️ Quotas &amp; Modules
                    </button>

                    <button
                      type="button"
                      onClick={() => handleToggleStatus(m)}
                      style={{
                        padding: '8px 12px',
                        fontSize: 12,
                        fontWeight: 600,
                        borderRadius: 6,
                        background: m.status === 'active' ? 'rgba(239, 68, 68, 0.12)' : 'rgba(34, 197, 94, 0.12)',
                        color: m.status === 'active' ? '#f87171' : '#4ade80',
                        border: m.status === 'active' ? '1px solid rgba(239, 68, 68, 0.25)' : '1px solid rgba(34, 197, 94, 0.25)',
                        cursor: 'pointer',
                      }}
                    >
                      {m.status === 'active' ? '⏸️ Suspend' : '▶️ Activate'}
                    </button>
                  </div>
                </div>

                {/* Middle details: Superuser Card & Quotas */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                    gap: 14,
                    background: 'rgba(0,0,0,0.25)',
                    padding: 16,
                    borderRadius: 8,
                    border: '1px solid rgba(255,255,255,0.05)',
                  }}
                >
                  {/* Superuser Box (The core Operator Provisioning highlight) */}
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#c084fc', marginBottom: 6 }}>
                      👑 Operator-Provisioned Client Superuser
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#fff' }}>
                      {m.superuser.firstName} {m.superuser.lastName}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)', marginTop: 2 }}>
                      ✉️ {m.superuser.email} {m.superuser.phone ? `· 📞 ${m.superuser.phone}` : ''}
                    </div>
                    <div style={{ display: 'flex', gap: 8, marginTop: 8, alignItems: 'center' }}>
                      <span
                        style={{
                          fontSize: 11,
                          padding: '2px 8px',
                          borderRadius: 4,
                          background: 'rgba(56, 189, 248, 0.15)',
                          color: '#38bdf8',
                          border: '1px solid rgba(56, 189, 248, 0.3)',
                        }}
                      >
                        MFA: {m.superuser.mfaMethod.toUpperCase()}
                      </span>
                      <span
                        style={{
                          fontSize: 11,
                          padding: '2px 8px',
                          borderRadius: 4,
                          background: m.superuser.status === 'active' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(234, 179, 8, 0.15)',
                          color: m.superuser.status === 'active' ? '#4ade80' : '#facc15',
                        }}
                      >
                        {m.superuser.status.replace('_', ' ').toUpperCase()}
                      </span>
                      {m.superuser.accessKeyId && (
                        <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-dim, #94a3b8)' }}>
                          Key: {m.superuser.accessKeyId}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Tenant Capacity Quota */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim, #94a3b8)' }}>
                        Client Tenant Quota &amp; Capacity
                      </span>
                      <span style={{ fontSize: 12, fontWeight: 700, color: '#fff' }}>
                        {clientTenants.length} / {m.maxTenants} Tenants ({tenantUsagePercent}%)
                      </span>
                    </div>

                    <div style={{ width: '100%', height: 8, background: 'rgba(255,255,255,0.1)', borderRadius: 4, overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${tenantUsagePercent}%`,
                          height: '100%',
                          background: tenantUsagePercent > 80 ? '#f87171' : '#38bdf8',
                          borderRadius: 4,
                        }}
                      />
                    </div>

                    <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)', marginTop: 8 }}>
                      {clientTenants.length > 0 ? (
                        <span>
                          Active Tenants: <strong style={{ color: '#e2e8f0' }}>{clientTenants.map((t) => t.name).join(', ')}</strong>
                        </span>
                      ) : (
                        <span>No client profiles provisioned yet. Create the organization profile and deployment through the provider workflow.</span>
                      )}
                    </div>
                  </div>

                  {/* Allowed Modules */}
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim, #94a3b8)', marginBottom: 6 }}>
                      Licensed Security Engines
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {m.allowedModules.map((mod) => (
                        <span
                          key={mod}
                          style={{
                            fontSize: 11,
                            padding: '3px 8px',
                            borderRadius: 4,
                            background: 'rgba(255,255,255,0.06)',
                            color: '#cbd5e1',
                            border: '1px solid rgba(255,255,255,0.1)',
                          }}
                        >
                          {mod === 'soc' && '🛡️ SOC'}
                          {mod === 'appsec' && '💻 AppSec'}
                          {mod === 'dbsec' && '🗄️ DBSec'}
                          {mod === 'compliance' && '📋 Compliance'}
                          {mod === 'ai_suite' && '🤖 AI Intel'}
                        </span>
                      ))}
                    </div>
                    {m.notes && (
                      <div style={{ fontSize: 11, color: 'var(--text-dim, #94a3b8)', marginTop: 8, fontStyle: 'italic' }}>
                        {m.notes}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* MODAL 1: PROVISION NEW CLIENT / MSSP */}
      {showCreateModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: 20,
          }}
        >
          <div
            className="panel"
            style={{
              width: '100%',
              maxWidth: 720,
              maxHeight: '90vh',
              overflowY: 'auto',
              background: '#0f172a',
              border: '1px solid rgba(139, 92, 246, 0.4)',
              borderRadius: 12,
              padding: 24,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: 14, marginBottom: 18 }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#fff' }}>
                  ✨ Provision New Client Organization / MSSP
                </h3>
                <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)', marginTop: 4 }}>
                  Operator-level provisioning for government, commercial, telecom, or enterprise clients.
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: 18, cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Organization Info */}
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1' }}>Organization Full Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. SecureVault Enterprise or National Technology Agency"
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                      fontSize: 13,
                    }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1' }}>Code / Identifier *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. ACME or NTA"
                    value={formCode}
                    onChange={(e) => setFormCode(e.target.value.toUpperCase())}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                      fontSize: 13,
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1' }}>Organization Type</label>
                  <select
                    value={formType}
                    onChange={(e) => setFormType(e.target.value as any)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                      fontSize: 13,
                    }}
                  >
                    <option value="government_agency">Government Agency</option>
                    <option value="commercial_mssp">Commercial MSSP</option>
                    <option value="telecom_mssp">Telecom MSSP</option>
                    <option value="enterprise_mssp">Enterprise MSSP</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1' }}>Service Tier</label>
                  <select
                    value={formServiceTier}
                    onChange={(e) => setFormServiceTier(e.target.value as any)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                      fontSize: 13,
                    }}
                  >
                    <option value="Sovereign Gov Cloud">Sovereign Gov Cloud</option>
                    <option value="Enterprise MSSP">Enterprise MSSP</option>
                    <option value="Premium Fusion MSSP">Premium Fusion MSSP</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1' }}>SLA Commitment</label>
                  <select
                    value={formSlaTier}
                    onChange={(e) => setFormSlaTier(e.target.value as any)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                      fontSize: 13,
                    }}
                  >
                    <option value="24/7 Sovereign Critical">24/7 Sovereign Critical</option>
                    <option value="99.99% Platinum Enterprise">99.99% Platinum Enterprise</option>
                    <option value="24/7 Premium SOC">24/7 Premium SOC</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1' }}>Max Tenant Quota</label>
                  <input
                    type="number"
                    min="1"
                    max="1000"
                    value={formMaxTenants}
                    onChange={(e) => setFormMaxTenants(Number(e.target.value))}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                      fontSize: 13,
                    }}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1' }}>Operational Region</label>
                <input
                  type="text"
                  value={formRegion}
                  onChange={(e) => setFormRegion(e.target.value)}
                  placeholder="e.g. South Africa (National Public Sector) or EMEA / Sub-Saharan Africa"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid rgba(255,255,255,0.15)',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                    fontSize: 13,
                  }}
                />
              </div>

              {/* Client Superuser Access Section */}
              <div
                style={{
                  background: 'rgba(139, 92, 246, 0.08)',
                  border: '1px solid rgba(139, 92, 246, 0.25)',
                  borderRadius: 8,
                  padding: 16,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 12,
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 700, color: '#c084fc', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>👑</span> Client Superuser Credentials (Operator Provisioned)
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <div>
                    <label style={{ fontSize: 12, color: '#cbd5e1' }}>First Name</label>
                    <input
                      type="text"
                      placeholder="e.g. Alex / Client Superuser"
                      value={suFirstName}
                      onChange={(e) => setSuFirstName(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '7px 10px',
                        borderRadius: 6,
                        border: '1px solid rgba(255,255,255,0.15)',
                        background: 'rgba(0,0,0,0.3)',
                        color: '#fff',
                        marginTop: 4,
                        fontSize: 12,
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, color: '#cbd5e1' }}>Last Name</label>
                    <input
                      type="text"
                      placeholder="e.g. Administrator / Mokoena"
                      value={suLastName}
                      onChange={(e) => setSuLastName(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '7px 10px',
                        borderRadius: 6,
                        border: '1px solid rgba(255,255,255,0.15)',
                        background: 'rgba(0,0,0,0.3)',
                        color: '#fff',
                        marginTop: 4,
                        fontSize: 12,
                      }}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 10 }}>
                  <div>
                    <label style={{ fontSize: 12, color: '#cbd5e1' }}>Official Superuser Email *</label>
                    <input
                      type="email"
                      required
                      placeholder="e.g. superuser@tenant.example"
                      value={suEmail}
                      onChange={(e) => setSuEmail(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '7px 10px',
                        borderRadius: 6,
                        border: '1px solid rgba(255,255,255,0.15)',
                        background: 'rgba(0,0,0,0.3)',
                        color: '#fff',
                        marginTop: 4,
                        fontSize: 12,
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, color: '#cbd5e1' }}>Emergency Phone</label>
                    <input
                      type="text"
                      placeholder="+27 12 482 3000"
                      value={suPhone}
                      onChange={(e) => setSuPhone(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '7px 10px',
                        borderRadius: 6,
                        border: '1px solid rgba(255,255,255,0.15)',
                        background: 'rgba(0,0,0,0.3)',
                        color: '#fff',
                        marginTop: 4,
                        fontSize: 12,
                      }}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <div>
                    <label style={{ fontSize: 12, color: '#cbd5e1' }}>MFA Enforcement</label>
                    <select
                      value={suMfaMethod}
                      onChange={(e) => setSuMfaMethod(e.target.value as any)}
                      style={{
                        width: '100%',
                        padding: '7px 10px',
                        borderRadius: 6,
                        border: '1px solid rgba(255,255,255,0.15)',
                        background: 'rgba(0,0,0,0.3)',
                        color: '#fff',
                        marginTop: 4,
                        fontSize: 12,
                      }}
                    >
                      <option value="hardware">Hardware Security Key (FIDO2 / YubiKey)</option>
                      <option value="app">Mobile Authenticator App (TOTP)</option>
                      <option value="sms">SMS OTP</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: 12, color: '#cbd5e1' }}>Account Status</label>
                    <select
                      value={suStatus}
                      onChange={(e) => setSuStatus(e.target.value as any)}
                      style={{
                        width: '100%',
                        padding: '7px 10px',
                        borderRadius: 6,
                        border: '1px solid rgba(255,255,255,0.15)',
                        background: 'rgba(0,0,0,0.3)',
                        color: '#fff',
                        marginTop: 4,
                        fontSize: 12,
                      }}
                    >
                      <option value="active">Active &amp; Provisioned</option>
                      <option value="pending_invite">Pending Invite / Setup</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Module Licensing */}
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', marginBottom: 8, display: 'block' }}>
                  Licensed Platform Modules
                </label>
                <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#fff', cursor: 'pointer' }}>
                    <input type="checkbox" checked={modSoc} onChange={(e) => setModSoc(e.target.checked)} />
                    🛡️ SOC Monitoring
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#fff', cursor: 'pointer' }}>
                    <input type="checkbox" checked={modAppsec} onChange={(e) => setModAppsec(e.target.checked)} />
                    💻 AppSec Intel
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#fff', cursor: 'pointer' }}>
                    <input type="checkbox" checked={modDbsec} onChange={(e) => setModDbsec(e.target.checked)} />
                    🗄️ Database Security
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#fff', cursor: 'pointer' }}>
                    <input type="checkbox" checked={modCompliance} onChange={(e) => setModCompliance(e.target.checked)} />
                    📋 Compliance Suite
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#fff', cursor: 'pointer' }}>
                    <input type="checkbox" checked={modAi} onChange={(e) => setModAi(e.target.checked)} />
                    🤖 AI Intel &amp; Alerts
                  </label>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 10, borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 14 }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  style={{
                    padding: '8px 16px',
                    borderRadius: 6,
                    border: '1px solid rgba(255,255,255,0.15)',
                    background: 'transparent',
                    color: '#cbd5e1',
                    fontSize: 13,
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{
                    padding: '8px 20px',
                    borderRadius: 6,
                    border: 'none',
                    background: 'linear-gradient(135deg, #7c3aed, #4f46e5)',
                    color: '#fff',
                    fontWeight: 700,
                    fontSize: 13,
                    cursor: 'pointer',
                  }}
                >
                  ⚡ Provision Client &amp; Superuser
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: EDIT CLIENT SUPERUSER */}
      {editingSuperuserMssp && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: 20,
          }}
        >
          <div
            className="panel"
            style={{
              width: '100%',
              maxWidth: 520,
              background: '#0f172a',
              border: '1px solid rgba(139, 92, 246, 0.4)',
              borderRadius: 12,
              padding: 24,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: 14, marginBottom: 18 }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#fff' }}>
                  🔑 Manage Superuser: {editingSuperuserMssp.name}
                </h3>
                <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)', marginTop: 2 }}>
                  Operator-governed superuser credentials and authentication policies.
                </div>
              </div>
              <button
                type="button"
                onClick={() => setEditingSuperuserMssp(null)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: 18, cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveSuperuser} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div>
                  <label style={{ fontSize: 12, color: '#cbd5e1' }}>First Name</label>
                  <input
                    type="text"
                    value={editSuFirst}
                    onChange={(e) => setEditSuFirst(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                      fontSize: 12,
                    }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 12, color: '#cbd5e1' }}>Last Name</label>
                  <input
                    type="text"
                    value={editSuLast}
                    onChange={(e) => setEditSuLast(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                      fontSize: 12,
                    }}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: 12, color: '#cbd5e1' }}>Official Superuser Email</label>
                <input
                  type="email"
                  required
                  value={editSuEmail}
                  onChange={(e) => setEditSuEmail(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '7px 10px',
                    borderRadius: 6,
                    border: '1px solid rgba(255,255,255,0.15)',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                    fontSize: 12,
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, color: '#cbd5e1' }}>Emergency Phone</label>
                <input
                  type="text"
                  value={editSuPhone}
                  onChange={(e) => setEditSuPhone(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '7px 10px',
                    borderRadius: 6,
                    border: '1px solid rgba(255,255,255,0.15)',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                    fontSize: 12,
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div>
                  <label style={{ fontSize: 12, color: '#cbd5e1' }}>MFA Enforcement</label>
                  <select
                    value={editSuMfa}
                    onChange={(e) => setEditSuMfa(e.target.value as any)}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                      fontSize: 12,
                    }}
                  >
                    <option value="hardware">Hardware Key (FIDO2)</option>
                    <option value="app">Mobile Authenticator (TOTP)</option>
                    <option value="sms">SMS OTP</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 12, color: '#cbd5e1' }}>Status</label>
                  <select
                    value={editSuStatus}
                    onChange={(e) => setEditSuStatus(e.target.value as any)}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                      fontSize: 12,
                    }}
                  >
                    <option value="active">Active</option>
                    <option value="pending_invite">Pending Invite</option>
                    <option value="suspended">Suspended</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 12, borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 14 }}>
                <button
                  type="button"
                  onClick={() => setEditingSuperuserMssp(null)}
                  style={{
                    padding: '8px 14px',
                    borderRadius: 6,
                    border: '1px solid rgba(255,255,255,0.15)',
                    background: 'transparent',
                    color: '#cbd5e1',
                    fontSize: 12,
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{
                    padding: '8px 18px',
                    borderRadius: 6,
                    border: 'none',
                    background: 'linear-gradient(135deg, #7c3aed, #4f46e5)',
                    color: '#fff',
                    fontWeight: 700,
                    fontSize: 12,
                    cursor: 'pointer',
                  }}
                >
                  Save Superuser Details
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: EDIT QUOTAS & MODULES */}
      {editingQuotaMssp && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: 20,
          }}
        >
          <div
            className="panel"
            style={{
              width: '100%',
              maxWidth: 520,
              background: '#0f172a',
              border: '1px solid rgba(139, 92, 246, 0.4)',
              borderRadius: 12,
              padding: 24,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: 14, marginBottom: 18 }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#fff' }}>
                  ✏️ Quotas &amp; Licensing: {editingQuotaMssp.name}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setEditingQuotaMssp(null)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: 18, cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveQuota} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ fontSize: 12, color: '#cbd5e1' }}>Max Tenant Allocation Quota</label>
                <input
                  type="number"
                  min="1"
                  max="1000"
                  value={editMaxTenants}
                  onChange={(e) => setEditMaxTenants(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '7px 10px',
                    borderRadius: 6,
                    border: '1px solid rgba(255,255,255,0.15)',
                    background: 'rgba(0,0,0,0.3)',
                    color: '#fff',
                    marginTop: 4,
                    fontSize: 12,
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div>
                  <label style={{ fontSize: 12, color: '#cbd5e1' }}>Service Tier</label>
                  <select
                    value={editServiceTier}
                    onChange={(e) => setEditServiceTier(e.target.value as any)}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                      fontSize: 12,
                    }}
                  >
                    <option value="Sovereign Gov Cloud">Sovereign Gov Cloud</option>
                    <option value="Enterprise MSSP">Enterprise MSSP</option>
                    <option value="Premium Fusion MSSP">Premium Fusion MSSP</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 12, color: '#cbd5e1' }}>SLA Commitment</label>
                  <select
                    value={editSlaTier}
                    onChange={(e) => setEditSlaTier(e.target.value as any)}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.15)',
                      background: 'rgba(0,0,0,0.3)',
                      color: '#fff',
                      marginTop: 4,
                      fontSize: 12,
                    }}
                  >
                    <option value="24/7 Sovereign Critical">24/7 Sovereign Critical</option>
                    <option value="99.99% Platinum Enterprise">99.99% Platinum Enterprise</option>
                    <option value="24/7 Premium SOC">24/7 Premium SOC</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: 12, color: '#cbd5e1', marginBottom: 6, display: 'block' }}>Licensed Modules</label>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  {['soc', 'appsec', 'dbsec', 'compliance', 'ai_suite'].map((mKey) => (
                    <label key={mKey} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#fff', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={editModules.includes(mKey)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setEditModules([...editModules, mKey]);
                          } else {
                            setEditModules(editModules.filter((x) => x !== mKey));
                          }
                        }}
                      />
                      {mKey.toUpperCase()}
                    </label>
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 12, borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 14 }}>
                <button
                  type="button"
                  onClick={() => setEditingQuotaMssp(null)}
                  style={{
                    padding: '8px 14px',
                    borderRadius: 6,
                    border: '1px solid rgba(255,255,255,0.15)',
                    background: 'transparent',
                    color: '#cbd5e1',
                    fontSize: 12,
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{
                    padding: '8px 18px',
                    borderRadius: 6,
                    border: 'none',
                    background: 'linear-gradient(135deg, #7c3aed, #4f46e5)',
                    color: '#fff',
                    fontWeight: 700,
                    fontSize: 12,
                    cursor: 'pointer',
                  }}
                >
                  Save Quotas &amp; Modules
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
