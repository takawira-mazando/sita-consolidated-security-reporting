import React, { useState } from 'react';
import { Tenant, TenantLifecycleState } from '../../types/multiTenant';

interface Props {
  tenants: Tenant[];
  onSelectTenant: (tenant: Tenant) => void;
  onManageRbac: (tenant: Tenant) => void;
  onEditTenant?: (tenant: Tenant) => void;
}

export const TenantCommandCenter: React.FC<Props> = ({
  tenants,
  onSelectTenant,
  onManageRbac,
  onEditTenant,
}) => {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | TenantLifecycleState>('all');
  const [selectedIndustry, setSelectedIndustry] = useState<string>('all');

  const industries = Array.from(new Set(tenants.map((t) => t.industry)));

  const filtered = tenants.filter((t) => {
    const matchesSearch =
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.identifier.toLowerCase().includes(search.toLowerCase()) ||
      t.superuser.email.toLowerCase().includes(search.toLowerCase()) ||
      t.region.toLowerCase().includes(search.toLowerCase());

    const matchesStatus = statusFilter === 'all' || t.status === statusFilter;
    const matchesIndustry = selectedIndustry === 'all' || t.industry === selectedIndustry;

    return matchesSearch && matchesStatus && matchesIndustry;
  });

  const totalBranches = tenants.reduce(
    (acc, t) => acc + (t.profileUnitCount ?? t.branches?.length ?? 0),
    0
  );
  const getStatusBadge = (status: TenantLifecycleState) => {
    switch (status) {
      case 'active':
        return { label: 'Selected', bg: 'rgba(34, 197, 94, 0.15)', color: '#4ade80', border: 'rgba(34, 197, 94, 0.3)' };
      case 'provisioning':
        return { label: 'Provisioning', bg: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: 'rgba(56, 189, 248, 0.3)' };
      case 'draft':
        return { label: 'Draft', bg: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8', border: 'rgba(148, 163, 184, 0.3)' };
      case 'suspended':
        return { label: 'Suspended', bg: 'rgba(234, 179, 8, 0.15)', color: '#facc15', border: 'rgba(234, 179, 8, 0.3)' };
      case 'retention_hold':
        return { label: 'Retention Hold', bg: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: 'rgba(168, 85, 247, 0.3)' };
      case 'archived':
        return { label: 'Archived', bg: 'rgba(100, 116, 139, 0.25)', color: '#cbd5e1', border: 'rgba(100, 116, 139, 0.4)' };
      case 'deleted':
        return { label: 'Deleted', bg: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: 'rgba(239, 68, 68, 0.3)' };
      default:
        return { label: status, bg: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8', border: 'rgba(148, 163, 184, 0.3)' };
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Top Metric Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 16,
        }}
      >
        <div className="panel" style={{ padding: '16px 20px', borderLeft: '4px solid var(--violet, #6366f1)' }}>
          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim, #94a3b8)' }}>
            Client Profiles
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text, #f8fafc)', marginTop: 4 }}>
            {tenants.length}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)', marginTop: 4 }}>
            {tenants.length === 1 ? 'Client organization' : 'Client organizations'}
          </div>
        </div>

        <div className="panel" style={{ padding: '16px 20px', borderLeft: '4px solid #38bdf8' }}>
          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim, #94a3b8)' }}>
            Client types
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#38bdf8', marginTop: 4 }}>
            {industries.length}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)', marginTop: 4 }}>
            {industries.length === 1 ? 'Industry represented' : 'Industries represented'}
          </div>
        </div>

        <div className="panel" style={{ padding: '16px 20px', borderLeft: '4px solid #c084fc' }}>
          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim, #94a3b8)' }}>
            Organization units
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#c084fc', marginTop: 4 }}>
            {totalBranches}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)', marginTop: 4 }}>
            Configured hierarchy units
          </div>
        </div>
      </div>

      {/* Search and filters */}
      <div
        className="panel"
        style={{
          padding: '16px 20px',
          display: 'flex',
          flexWrap: 'wrap',
          gap: 14,
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', gap: 10, flex: 1, minWidth: 280, alignItems: 'center' }}>
          <input
            type="text"
            placeholder="Search client, profile, identifier, region..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              flex: 1,
              padding: '8px 14px',
              borderRadius: 6,
              border: '1px solid var(--border, rgba(255,255,255,0.1))',
              background: 'rgba(0,0,0,0.25)',
              color: 'var(--text, #fff)',
              fontSize: 13,
            }}
          />

          <select
            value={selectedIndustry}
            onChange={(e) => setSelectedIndustry(e.target.value)}
            style={{
              padding: '8px 12px',
              borderRadius: 6,
              border: '1px solid var(--border, rgba(255,255,255,0.1))',
              background: 'rgba(0,0,0,0.3)',
              color: 'var(--text, #fff)',
              fontSize: 13,
            }}
          >
            <option value="all">All Client Types</option>
            {industries.map((ind) => (
              <option key={ind} value={ind}>
                {ind}
              </option>
            ))}
          </select>
        </div>

        {/* Status Filter Buttons */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {(['all', 'active', 'suspended', 'retention_hold', 'archived'] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setStatusFilter(s)}
              style={{
                padding: '6px 12px',
                borderRadius: 5,
                fontSize: 12,
                fontWeight: statusFilter === s ? 700 : 500,
                border: '1px solid',
                borderColor: statusFilter === s ? 'var(--violet, #6366f1)' : 'rgba(255,255,255,0.08)',
                background: statusFilter === s ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                color: statusFilter === s ? '#a5b4fc' : 'var(--text-dim, #94a3b8)',
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {s === 'all' ? 'All Profiles' : s.replace('_', ' ')}
            </button>
          ))}

        </div>
      </div>

      {/* Tenants Table */}
      <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="users-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'rgba(255, 255, 255, 0.02)', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
              <th style={{ textAlign: 'left', padding: '14px 16px' }}>Client Organization / Profile</th>
              <th style={{ textAlign: 'left', padding: '14px 16px' }}>Client type</th>
              <th style={{ textAlign: 'left', padding: '14px 16px' }}>Organization structure</th>
              <th style={{ textAlign: 'left', padding: '14px 16px' }}>Profile state</th>
              <th style={{ textAlign: 'right', padding: '14px 16px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-dim, #94a3b8)' }}>
                  {tenants.length === 0
                    ? 'No client profiles yet. Use Create client profile in the navigation to get started.'
                    : `No client profiles found matching "${search}". Adjust your search or filters.`}
                </td>
              </tr>
            ) : (
              filtered.map((tenant) => {
                const badge = getStatusBadge(tenant.status);
                return (
                  <tr
                    key={tenant.id}
                    style={{
                      borderBottom: '1px solid rgba(255,255,255,0.05)',
                      transition: 'background 0.15s ease',
                    }}
                  >
                    {/* Tenant Organization */}
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div
                          style={{
                            width: 36,
                            height: 36,
                            borderRadius: 8,
                            background: 'rgba(99, 102, 241, 0.15)',
                            border: '1px solid rgba(99, 102, 241, 0.3)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 700,
                            color: '#818cf8',
                            fontSize: 14,
                          }}
                        >
                          {tenant.name.charAt(0)}
                        </div>
                        <div>
                          <div style={{ fontWeight: 600, color: 'var(--text, #f8fafc)', fontSize: 14 }}>
                            {tenant.name}
                          </div>
                          <div style={{ fontSize: 11, color: 'var(--text-dim, #94a3b8)', display: 'flex', gap: 6, alignItems: 'center' }}>
                            <code>{tenant.identifier}</code>
                          </div>
                          {tenant.profileDescription && (
                            <div
                              title={tenant.profileDescription}
                              style={{ maxWidth: 280, marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 11, color: 'var(--text-dim, #94a3b8)' }}
                            >
                              {tenant.profileDescription}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* Client type */}
                    <td style={{ padding: '14px 16px' }}>
                      <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text, #f8fafc)', textTransform: 'capitalize' }}>
                        {tenant.industry.replace(/_/g, ' ')}
                      </span>
                    </td>

                    {/* Organization structure */}
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text, #f8fafc)' }}>
                        {tenant.profileUnitCount ?? tenant.branches?.length ?? 0} organization units
                      </div>
                      <div
                        style={{
                          fontSize: 11,
                          color: 'var(--text-dim, #94a3b8)',
                          marginTop: 4,
                          maxWidth: 260,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {tenant.profileLevels?.length ? tenant.profileLevels.join(' → ') : 'No custom hierarchy levels'}
                        {tenant.profileSubUnitCount ? ` · ${tenant.profileSubUnitCount} sub-units` : ''}
                      </div>
                    </td>

                    {/* Profile state */}
                    <td style={{ padding: '14px 16px' }}>
                      <span
                        style={{
                          display: 'inline-block',
                          padding: '3px 10px',
                          borderRadius: 999,
                          fontSize: 11,
                          fontWeight: 600,
                          background: badge.bg,
                          color: badge.color,
                          border: `1px solid ${badge.border}`,
                        }}
                      >
                        {badge.label}
                      </span>
                      {tenant.suspendedReason && (
                        <div
                          style={{
                            fontSize: 10,
                            color: '#facc15',
                            marginTop: 4,
                            maxWidth: 160,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                          title={tenant.suspendedReason}
                        >
                          ⚠️ {tenant.suspendedReason}
                        </div>
                      )}
                    </td>

                    {/* Actions */}
                    <td style={{ textAlign: 'right', padding: '14px 16px' }}>
                      <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                        <button
                          type="button"
                          onClick={() => onEditTenant ? onEditTenant(tenant) : onSelectTenant(tenant)}
                          style={{
                            padding: '4px 8px',
                            borderRadius: 4,
                            fontSize: 11,
                            background: 'rgba(56, 189, 248, 0.15)',
                            color: '#38bdf8',
                            border: '1px solid rgba(56, 189, 248, 0.3)',
                            cursor: 'pointer',
                          }}
                          title="Edit client profile"
                        >
                          ✏️ Edit
                        </button>

                        <button
                          type="button"
                          onClick={() => onSelectTenant(tenant)}
                          style={{
                            padding: '4px 10px',
                            borderRadius: 4,
                            fontSize: 11,
                            background: 'rgba(99, 102, 241, 0.15)',
                            color: '#a5b4fc',
                            border: '1px solid rgba(99, 102, 241, 0.3)',
                            cursor: 'pointer',
                          }}
                        >
                          Hierarchy
                        </button>

                        <button
                          type="button"
                          onClick={() => onManageRbac(tenant)}
                          style={{
                            padding: '4px 10px',
                            borderRadius: 4,
                            fontSize: 11,
                            background: 'rgba(168, 85, 247, 0.15)',
                            color: '#c084fc',
                            border: '1px solid rgba(168, 85, 247, 0.3)',
                            cursor: 'pointer',
                          }}
                        >
                          Access
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
