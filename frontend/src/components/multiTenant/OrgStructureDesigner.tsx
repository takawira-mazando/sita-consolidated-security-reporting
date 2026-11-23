import React, { useState } from 'react';
import { Tenant, BranchUnit } from '../../types/multiTenant';

interface Props {
  tenants: Tenant[];
  selectedTenantId: string;
  onSelectTenantId: (id: string) => void;
  onUpdateBranches: (tenantId: string, newBranches: BranchUnit[]) => void;
}

export const OrgStructureDesigner: React.FC<Props> = ({
  tenants,
  selectedTenantId,
  onSelectTenantId,
  onUpdateBranches,
}) => {
  const currentTenant = tenants.find((t) => t.id === selectedTenantId) || tenants[0];

  const [newUnitName, setNewUnitName] = useState('');
  const [newUnitType, setNewUnitType] = useState('Branch');
  const [managerEmail, setManagerEmail] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  if (!currentTenant) {
    return <div className="panel" style={{ padding: 24 }}>No tenants available.</div>;
  }

  const branches = currentTenant.branches || [];

  const handleAdd = () => {
    if (!newUnitName.trim()) return;
    const newUnit: BranchUnit = {
      id: `b-${Date.now()}`,
      name: newUnitName.trim(),
      type: newUnitType || 'Branch',
      managerEmail: managerEmail.trim(),
      userCount: 0,
    };
    onUpdateBranches(currentTenant.id, [...branches, newUnit]);
    setNewUnitName('');
    setManagerEmail('');
  };

  const handleDelete = (id: string) => {
    onUpdateBranches(
      currentTenant.id,
      branches.filter((b) => b.id !== id)
    );
  };

  const handleSaveEdit = (id: string) => {
    onUpdateBranches(
      currentTenant.id,
      branches.map((b) => (b.id === id ? { ...b, name: editName } : b))
    );
    setEditingId(null);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Tenant Context Selector */}
      <div
        className="panel"
        style={{
          padding: '16px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
            Selected Client Organization / Profile:
          </span>
          <select
            value={currentTenant.id}
            onChange={(e) => onSelectTenantId(e.target.value)}
            style={{
              padding: '8px 14px',
              borderRadius: 6,
              border: '1px solid var(--violet, #6366f1)',
              background: 'rgba(99,102,241,0.1)',
              color: '#fff',
              fontWeight: 600,
              fontSize: 14,
            }}
          >
            {tenants.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.industry})
              </option>
            ))}
          </select>
        </div>

        <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)' }}>
          Active Units: <strong style={{ color: '#38bdf8' }}>{branches.length}</strong> · Hierarchy Depth:{' '}
          <strong style={{ color: '#4ade80' }}>2 Levels (Flexible)</strong>
        </div>
      </div>

      {/* Main Designer Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20 }}>
        {/* Visual Org Tree */}
        <div className="panel" style={{ padding: 20 }}>
          <h3 style={{ margin: '0 0 4px', fontSize: 16, color: '#fff', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>🌿</span>
            <span>{currentTenant.name} — Organizational Tree</span>
          </h3>
          <p style={{ margin: '0 0 20px', fontSize: 12, color: 'var(--text-dim, #94a3b8)' }}>
            Per Section 5: The platform never enforces a fixed naming convention. Units reflect the tenant's domain (e.g.
            Mine Shafts, Stores, Offices, Facilities, Divisions).
          </p>

          {/* Root Node */}
          <div
            style={{
              background: 'rgba(99, 102, 241, 0.15)',
              border: '1px solid rgba(99, 102, 241, 0.4)',
              padding: '14px 18px',
              borderRadius: 8,
              marginBottom: 16,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <div style={{ fontSize: 11, textTransform: 'uppercase', color: '#818cf8', fontWeight: 700 }}>
                Tenant Root Organization
              </div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#fff', marginTop: 2 }}>{currentTenant.name}</div>
              <div style={{ fontSize: 11, color: 'var(--text-dim, #94a3b8)' }}>
                Identifier: <code>{currentTenant.identifier}</code> · Superuser: {currentTenant.superuser.email}
              </div>
            </div>

            <span
              style={{
                fontSize: 11,
                padding: '4px 10px',
                borderRadius: 4,
                background: 'rgba(34, 197, 94, 0.2)',
                color: '#4ade80',
                fontWeight: 600,
              }}
            >
              Estate Level
            </span>
          </div>

          {/* Tree Branches */}
          <div style={{ paddingLeft: 24, borderLeft: '2px dashed rgba(255,255,255,0.15)', display: 'flex', flexDirection: 'column', gap: 12 }}>
            {branches.length === 0 ? (
              <div style={{ padding: 20, color: 'var(--text-dim, #94a3b8)' }}>
                No branches configured. Use the form on the right to add your first operational unit.
              </div>
            ) : (
              branches.map((b) => (
                <div
                  key={b.id}
                  style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: 8,
                    padding: '12px 16px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{ fontSize: 16 }}>↳</span>
                    <div>
                      {editingId === b.id ? (
                        <div style={{ display: 'flex', gap: 6 }}>
                          <input
                            type="text"
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            style={{
                              padding: '4px 8px',
                              borderRadius: 4,
                              background: 'rgba(0,0,0,0.4)',
                              border: '1px solid #6366f1',
                              color: '#fff',
                              fontSize: 13,
                            }}
                          />
                          <button
                            type="button"
                            onClick={() => handleSaveEdit(b.id)}
                            style={{ background: '#22c55e', color: '#fff', border: 'none', borderRadius: 4, padding: '4px 8px', cursor: 'pointer' }}
                          >
                            Save
                          </button>
                        </div>
                      ) : (
                        <div style={{ fontWeight: 600, color: '#fff', fontSize: 14 }}>{b.name}</div>
                      )}
                      <div style={{ fontSize: 11, color: 'var(--text-dim, #94a3b8)', marginTop: 2 }}>
                        Type: <strong style={{ color: '#38bdf8' }}>{b.type}</strong>
                        {b.managerEmail && ` · Lead: ${b.managerEmail}`}
                        {b.userCount !== undefined && ` · ${b.userCount} Active Identities`}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 6 }}>
                    <button
                      type="button"
                      onClick={() => {
                        setEditingId(b.id);
                        setEditName(b.name);
                      }}
                      style={{
                        background: 'transparent',
                        border: '1px solid rgba(255,255,255,0.15)',
                        color: 'var(--text-dim, #94a3b8)',
                        padding: '3px 8px',
                        borderRadius: 4,
                        fontSize: 11,
                        cursor: 'pointer',
                      }}
                    >
                      Rename
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(b.id)}
                      style={{
                        background: 'rgba(239, 68, 68, 0.15)',
                        border: '1px solid rgba(239, 68, 68, 0.3)',
                        color: '#f87171',
                        padding: '3px 8px',
                        borderRadius: 4,
                        fontSize: 11,
                        cursor: 'pointer',
                      }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Add Branch / Unit Form */}
        <div className="panel" style={{ padding: 20 }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 15, color: '#a5b4fc' }}>+ Add Organizational Unit</h3>
          <p style={{ margin: '0 0 16px', fontSize: 12, color: 'var(--text-dim, #94a3b8)' }}>
            Create branches, stores, mines, or offices with custom attribution.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Unit Name *</label>
              <input
                type="text"
                placeholder="e.g. Mine Shaft Bravo / Cape Town Hub"
                value={newUnitName}
                onChange={(e) => setNewUnitName(e.target.value)}
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

            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Unit Type Terminology</label>
              <select
                value={newUnitType}
                onChange={(e) => setNewUnitType(e.target.value)}
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
                <option value="Mine Shaft">Mine Shaft</option>
                <option value="Store">Retail Store</option>
                <option value="Processing Plant">Processing Plant</option>
                <option value="Office">Office / Facility</option>
                <option value="Hospital Facility">Hospital Facility</option>
                <option value="Campus">Campus</option>
                <option value="Division">Division / Segment</option>
                <option value="Region">Geographic Region</option>
                <option value="Site">Field Site</option>
                <option value="Branch">General Branch</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Unit Lead / Manager Email</label>
              <input
                type="email"
                placeholder="unit.manager@tenant.example"
                value={managerEmail}
                onChange={(e) => setManagerEmail(e.target.value)}
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

            <button
              type="button"
              onClick={handleAdd}
              style={{
                marginTop: 8,
                padding: '10px 16px',
                borderRadius: 6,
                background: 'var(--violet, #6366f1)',
                color: '#fff',
                border: 'none',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              + Create Unit
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
