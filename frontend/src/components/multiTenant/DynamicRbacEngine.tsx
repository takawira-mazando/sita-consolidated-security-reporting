import React, { useState } from 'react';
import { Tenant, CustomRole } from '../../types/multiTenant';
import { SYSTEM_PERMISSIONS } from '../../data/mockMultiTenant';
import { getClientOrgName } from '../../utils/tenantTerminology';

interface Props {
  tenants: Tenant[];
  selectedTenantId: string;
  onSelectTenantId: (id: string) => void;
  onUpdateRoles: (tenantId: string, roles: CustomRole[]) => void;
}

export const DynamicRbacEngine: React.FC<Props> = ({
  tenants,
  selectedTenantId,
  onSelectTenantId,
  onUpdateRoles,
}) => {
  const currentTenant = tenants.find((t) => t.id === selectedTenantId) || tenants[0];

  const [newRoleName, setNewRoleName] = useState('');
  const [newRoleDesc, setNewRoleDesc] = useState('');
  const [newRoleScope, setNewRoleScope] = useState<'tenant' | 'branch'>('tenant');
  const [filterScope, setFilterScope] = useState<'all' | 'tenant' | 'branch'>('all');

  if (!currentTenant) {
    return <div className="panel" style={{ padding: 24 }}>No tenants available.</div>;
  }

  const roles = currentTenant.customRoles || [];

  const handleToggle = (roleId: string, permId: string) => {
    const updated = roles.map((r) => {
      if (r.id !== roleId) return r;
      const exists = r.permissions.includes(permId);
      return {
        ...r,
        permissions: exists ? r.permissions.filter((p) => p !== permId) : [...r.permissions, permId],
      };
    });
    onUpdateRoles(currentTenant.id, updated);
  };

  const handleCreateRole = () => {
    if (!newRoleName.trim()) return;
    const newRole: CustomRole = {
      id: `role-${Date.now()}`,
      name: newRoleName.trim(),
      description: newRoleDesc.trim() || 'Custom tenant-specific role',
      scope: newRoleScope,
      permissions: ['view_assets', 'view_incidents'],
      isCustom: true,
      assignedUsersCount: 0,
    };
    onUpdateRoles(currentTenant.id, [...roles, newRole]);
    setNewRoleName('');
    setNewRoleDesc('');
  };

  const handleCloneRole = (sourceRole: CustomRole) => {
    const cloned: CustomRole = {
      id: `role-clone-${Date.now()}`,
      name: `${sourceRole.name} (Copy)`,
      description: `Cloned from ${sourceRole.name}: ${sourceRole.description}`,
      scope: sourceRole.scope,
      permissions: [...sourceRole.permissions],
      isCustom: true,
      assignedUsersCount: 0,
    };
    onUpdateRoles(currentTenant.id, [...roles, cloned]);
  };

  const handleDeleteRole = (roleId: string) => {
    onUpdateRoles(
      currentTenant.id,
      roles.filter((r) => r.id !== roleId)
    );
  };

  const visibleRoles = roles.filter((r) => filterScope === 'all' || r.scope === filterScope);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Scope Architecture Infobox */}
      <div
        className="panel"
        style={{
          padding: '16px 20px',
          background: 'linear-gradient(135deg, rgba(99,102,241,0.1), rgba(168,85,247,0.05))',
          borderLeft: '4px solid var(--violet, #6366f1)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div>
          <div style={{ fontWeight: 700, color: '#fff', fontSize: 14 }}>
            Hierarchical Dynamic RBAC Architecture (Section 6 &amp; 8)
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)', marginTop: 2 }}>
            Scope-based inheritance: <strong style={{ color: '#818cf8' }}>Platform</strong> ↓{' '}
            <strong style={{ color: '#c084fc' }}>{getClientOrgName()}</strong> ↓ <strong style={{ color: '#38bdf8' }}>Tenant</strong> ↓{' '}
            <strong style={{ color: '#4ade80' }}>Branch / Unit</strong>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)' }}>Tenant Context:</span>
          <select
            value={currentTenant.id}
            onChange={(e) => onSelectTenantId(e.target.value)}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              border: '1px solid var(--violet, #6366f1)',
              background: 'rgba(0,0,0,0.3)',
              color: '#fff',
              fontWeight: 600,
            }}
          >
            {tenants.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Branch-Level Permissions Example Banner (Section 7) */}
      <div
        className="panel"
        style={{
          padding: '14px 20px',
          background: 'rgba(56, 189, 248, 0.05)',
          border: '1px solid rgba(56, 189, 248, 0.2)',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 12,
          fontSize: 12,
        }}
      >
        <div style={{ borderLeft: '3px solid #38bdf8', paddingLeft: 10 }}>
          <strong style={{ color: '#fff' }}>Single-Branch Scope:</strong>
          <div style={{ color: 'var(--text-dim, #94a3b8)' }}>John Smith ➔ Bound only to {currentTenant.branches[0]?.name || 'Branch 1'}</div>
        </div>
        <div style={{ borderLeft: '3px solid #c084fc', paddingLeft: 10 }}>
          <strong style={{ color: '#fff' }}>Multi-Branch Scope:</strong>
          <div style={{ color: 'var(--text-dim, #94a3b8)' }}>Sarah Jones ➔ Bound to {currentTenant.branches[0]?.name || 'Branch 1'} &amp; {currentTenant.branches[1]?.name || 'Branch 2'}</div>
        </div>
        <div style={{ borderLeft: '3px solid #4ade80', paddingLeft: 10 }}>
          <strong style={{ color: '#fff' }}>Tenant-Wide Scope:</strong>
          <div style={{ color: 'var(--text-dim, #94a3b8)' }}>David Brown ➔ Universal access to all branches across {currentTenant.name}</div>
        </div>
      </div>

      {/* Controls & Filter */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)' }}>Filter Scope:</span>
          {(['all', 'tenant', 'branch'] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setFilterScope(s)}
              style={{
                padding: '4px 10px',
                borderRadius: 4,
                fontSize: 11,
                border: '1px solid',
                borderColor: filterScope === s ? '#818cf8' : 'rgba(255,255,255,0.1)',
                background: filterScope === s ? 'rgba(99,102,241,0.2)' : 'transparent',
                color: filterScope === s ? '#a5b4fc' : 'var(--text-dim, #94a3b8)',
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {s === 'all' ? 'All Scopes' : `${s}-Level`}
            </button>
          ))}
        </div>

        <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)' }}>
          Showing <strong style={{ color: '#fff' }}>{visibleRoles.length}</strong> active RBAC roles
        </div>
      </div>

      {/* Permission Assignment Matrix Grid (Screen 6) */}
      <div className="panel" style={{ padding: 0, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
              <th style={{ textAlign: 'left', padding: '12px 16px', minWidth: 240 }}>
                Granular Permissions (Matrix)
              </th>
              {visibleRoles.map((r) => (
                <th
                  key={r.id}
                  style={{
                    textAlign: 'center',
                    padding: '12px 10px',
                    minWidth: 130,
                    borderLeft: '1px solid rgba(255,255,255,0.05)',
                  }}
                >
                  <div style={{ color: '#fff', fontWeight: 600 }}>{r.name}</div>
                  <div style={{ fontSize: 10, color: r.scope === 'branch' ? '#38bdf8' : '#c084fc', textTransform: 'uppercase' }}>
                    {r.scope} Scope
                  </div>
                  <div style={{ display: 'flex', gap: 4, justifyContent: 'center', marginTop: 4 }}>
                    <button
                      type="button"
                      onClick={() => handleCloneRole(r)}
                      style={{
                        padding: '1px 6px',
                        fontSize: 9,
                        background: 'rgba(255,255,255,0.1)',
                        color: '#fff',
                        border: 'none',
                        borderRadius: 3,
                        cursor: 'pointer',
                      }}
                      title="Clone role into template"
                    >
                      Clone
                    </button>
                    {r.isCustom && (
                      <button
                        type="button"
                        onClick={() => handleDeleteRole(r.id)}
                        style={{
                          padding: '1px 6px',
                          fontSize: 9,
                          background: 'rgba(239,68,68,0.2)',
                          color: '#f87171',
                          border: 'none',
                          borderRadius: 3,
                          cursor: 'pointer',
                        }}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {SYSTEM_PERMISSIONS.map((perm) => (
              <tr key={perm.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <td style={{ padding: '10px 16px' }}>
                  <div style={{ fontWeight: 600, color: '#fff' }}>{perm.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-dim, #94a3b8)' }}>{perm.description}</div>
                </td>

                {visibleRoles.map((r) => {
                  const hasPerm = r.permissions.includes(perm.id);
                  return (
                    <td
                      key={r.id}
                      style={{
                        textAlign: 'center',
                        padding: '10px',
                        borderLeft: '1px solid rgba(255,255,255,0.05)',
                        background: hasPerm ? 'rgba(34, 197, 94, 0.04)' : 'transparent',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={hasPerm}
                        onChange={() => handleToggle(r.id, perm.id)}
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

      {/* Role Creator Panel */}
      <div className="panel" style={{ padding: 18 }}>
        <h4 style={{ margin: '0 0 10px', fontSize: 14, color: '#a5b4fc' }}>+ Create Custom Tenant or Branch Role</h4>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 180px 140px', gap: 10 }}>
          <input
            type="text"
            placeholder="Role Name (e.g. Audit Investigator / Local SOC Lead)"
            value={newRoleName}
            onChange={(e) => setNewRoleName(e.target.value)}
            style={{
              padding: '8px 12px',
              borderRadius: 6,
              border: '1px solid rgba(255,255,255,0.1)',
              background: 'rgba(0,0,0,0.3)',
              color: '#fff',
            }}
          />
          <input
            type="text"
            placeholder="Role Description / Functional Scope"
            value={newRoleDesc}
            onChange={(e) => setNewRoleDesc(e.target.value)}
            style={{
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
            <option value="tenant">Tenant-Wide</option>
            <option value="branch">Branch-Scoped</option>
          </select>
          <button
            type="button"
            onClick={handleCreateRole}
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
            + Add Role
          </button>
        </div>
      </div>
    </div>
  );
};
