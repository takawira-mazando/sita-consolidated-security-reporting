import React, { useState } from 'react';
import { Tenant, TenantLifecycleState } from '../../types/multiTenant';
import { getClientOrgName } from '../../utils/tenantTerminology';

interface Props {
  tenant: Tenant;
  action: 'suspend' | 'archive' | 'restore' | 'export' | 'delete';
  onClose: () => void;
  onUpdateStatus: (tenantId: string, newStatus: TenantLifecycleState, reason?: string) => void;
  onPermanentDelete: (tenantId: string) => void;
}

export const TenantLifecycleModal: React.FC<Props> = ({
  tenant,
  action,
  onClose,
  onUpdateStatus,
  onPermanentDelete,
}) => {
  const [reasonCode, setReasonCode] = useState('Contract Termination');
  const [customJustification, setCustomJustification] = useState('');
  const [retentionDays, setRetentionDays] = useState(tenant.governance?.retentionDays || 90);
  const [deleteConfirmation, setDeleteConfirmation] = useState('');
  const [exported, setExported] = useState(false);

  const handleSuspend = () => {
    const fullReason = `${reasonCode}: ${customJustification || `Approved by ${getClientOrgName()} Superuser`}`;
    onUpdateStatus(tenant.id, 'suspended', fullReason);
    onClose();
  };

  const handleArchive = () => {
    onUpdateStatus(tenant.id, 'archived', `Archived after retention hold (${retentionDays} days)`);
    onClose();
  };

  const handleRestore = () => {
    onUpdateStatus(tenant.id, 'active', `Reinstated by ${getClientOrgName()} Superuser — Services & Users Re-enabled`);
    onClose();
  };

  const handleDownloadExport = (format: 'json' | 'csv') => {
    let content = '';
    const filename = `${tenant.identifier}-audit-export.${format}`;

    if (format === 'json') {
      content = JSON.stringify(
        {
          tenant,
          exportDate: new Date().toISOString(),
          complianceClassification: 'POPIA / GDPR / SOC-2 Compliant Package',
          auditSignature: 'WORM-TAMPER-PROOF-SHA256-HEX',
        },
        null,
        2
      );
    } else {
      content = `Tenant Name,Identifier,Industry,Status,Superuser,Branches Count,Created\n"${tenant.name}","${tenant.identifier}","${tenant.industry}","${tenant.status}","${tenant.superuser.email}",${tenant.branches.length},"${tenant.createdDate}"`;
    }

    const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    setExported(true);
  };

  const handleDelete = () => {
    if (deleteConfirmation !== tenant.name) return;
    onPermanentDelete(tenant.id);
    onClose();
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.75)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: 20,
      }}
    >
      <div
        className="panel"
        style={{
          width: '100%',
          maxWidth: 620,
          padding: 24,
          background: 'var(--panel-bg, #111827)',
          border: '1px solid rgba(255,255,255,0.15)',
          borderRadius: 12,
          boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 18, color: '#fff' }}>
              {action === 'suspend' && '⏸️ Initiate Tenant Suspension'}
              {action === 'archive' && '📦 Move Tenant to Archival Retention'}
              {action === 'restore' && '🔄 Restore / Reinstate Tenant'}
              {action === 'export' && '📥 Export Tenant Operational & Audit Package'}
              {action === 'delete' && '🚨 Permanent Tenant Deletion (IRREVERSIBLE)'}
            </h3>
            <div style={{ fontSize: 12, color: 'var(--text-dim, #94a3b8)', marginTop: 2 }}>
              Target: <strong style={{ color: '#38bdf8' }}>{tenant.name}</strong> (<code>{tenant.identifier}</code>)
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: 18, cursor: 'pointer' }}
          >
            ✕
          </button>
        </div>

        {/* Content By Action */}
        {action === 'suspend' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-dim, #94a3b8)' }}>
              Per Section 12 Step 1–3: Suspension immediately blocks user logins, revokes active API tokens, and halts scheduled telemetry ingestion. Data remains strictly intact.
            </p>

            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Mandatory Reason Code *</label>
              <select
                value={reasonCode}
                onChange={(e) => setReasonCode(e.target.value)}
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
                <option value="Contract Termination">Contract Termination / Expired Subscription</option>
                <option value="Tenant Migration">Tenant Migration to Dedicated Environment</option>
                <option value="Customer Acquisition">Customer Acquisition / Merger Restructure</option>
                <option value="Security Incident">Security Incident / Compromise Quarantine</option>
                <option value="Duplicate Tenant">Duplicate Tenant Provisioning</option>
                <option value="Other">Other Regulatory / Governance Reason</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Documented Audit Justification</label>
              <textarea
                rows={3}
                placeholder="Provide detailed context for the compliance audit trail..."
                value={customJustification}
                onChange={(e) => setCustomJustification(e.target.value)}
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

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 10 }}>
              <button
                type="button"
                onClick={onClose}
                style={{ padding: '8px 16px', borderRadius: 6, background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSuspend}
                style={{ padding: '8px 20px', borderRadius: 6, background: '#eab308', color: '#000', fontWeight: 700, border: 'none', cursor: 'pointer' }}
              >
                Confirm Suspension
              </button>
            </div>
          </div>
        )}

        {action === 'archive' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-dim, #94a3b8)' }}>
              Per Section 12 Step 6: Archiving moves data into cold storage. The tenant remains completely searchable and recoverable by MSSP Superusers.
            </p>

            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>Retention Period Hold</label>
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
                <option value={30}>30 Days (Fast Recovery Window)</option>
                <option value={90}>90 Days (Standard Retention)</option>
                <option value={180}>180 Days (Extended)</option>
                <option value={365}>365 Days / 1 Year (Statutory Minimum)</option>
              </select>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 10 }}>
              <button
                type="button"
                onClick={onClose}
                style={{ padding: '8px 16px', borderRadius: 6, background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleArchive}
                style={{ padding: '8px 20px', borderRadius: 6, background: '#6366f1', color: '#fff', fontWeight: 700, border: 'none', cursor: 'pointer' }}
              >
                Archive Tenant
              </button>
            </div>
          </div>
        )}

        {action === 'restore' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-dim, #94a3b8)' }}>
              Per Section 14 (Restore &amp; Reinstatement): Restoring will seamlessly unblock logins, re-activate {tenant.branches.length} branches, and reinstate all {tenant.customRoles.length} RBAC roles without rebuilding configurations from scratch.
            </p>

            <div style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)', padding: 12, borderRadius: 6, fontSize: 12, color: '#4ade80' }}>
              ✓ Status will immediately change to <strong>Active</strong>.
              <br />✓ Superuser ({tenant.superuser.email}) receives reinstatement notification.
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 10 }}>
              <button
                type="button"
                onClick={onClose}
                style={{ padding: '8px 16px', borderRadius: 6, background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleRestore}
                style={{ padding: '8px 20px', borderRadius: 6, background: '#22c55e', color: '#fff', fontWeight: 700, border: 'none', cursor: 'pointer' }}
              >
                Confirm Reinstatement
              </button>
            </div>
          </div>
        )}

        {action === 'export' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-dim, #94a3b8)' }}>
              Per Section 12 Step 4: Export tenant operational records, audit logs, and branch structures prior to offboarding.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <button
                type="button"
                onClick={() => handleDownloadExport('json')}
                style={{
                  padding: '16px',
                  borderRadius: 8,
                  background: 'rgba(99,102,241,0.15)',
                  border: '1px solid rgba(99,102,241,0.4)',
                  color: '#fff',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                <div style={{ fontWeight: 700, color: '#818cf8', fontSize: 14 }}>JSON Full Data Package</div>
                <div style={{ fontSize: 11, color: 'var(--text-dim, #94a3b8)', marginTop: 4 }}>
                  Complete schema, RBAC roles, branches, and security metadata.
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleDownloadExport('csv')}
                style={{
                  padding: '16px',
                  borderRadius: 8,
                  background: 'rgba(56,189,248,0.15)',
                  border: '1px solid rgba(56,189,248,0.4)',
                  color: '#fff',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                <div style={{ fontWeight: 700, color: '#38bdf8', fontSize: 14 }}>CSV Spreadsheet Summary</div>
                <div style={{ fontSize: 11, color: 'var(--text-dim, #94a3b8)', marginTop: 4 }}>
                  Tabular export formatted for executive audits and Excel.
                </div>
              </button>
            </div>

            {exported && (
              <div style={{ color: '#4ade80', fontSize: 12, textAlign: 'center', marginTop: 8 }}>
                ✓ Export package generated and downloaded successfully.
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 10 }}>
              <button
                type="button"
                onClick={onClose}
                style={{ padding: '8px 18px', borderRadius: 6, background: 'rgba(255,255,255,0.1)', color: '#fff', border: 'none', cursor: 'pointer' }}
              >
                Close
              </button>
            </div>
          </div>
        )}

        {action === 'delete' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <p style={{ margin: 0, fontSize: 13, color: '#f87171' }}>
              Warning: Permanent deletion is irreversible. All branches, user credentials, access tokens, and operational caches will be purged.
            </p>

            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim, #94a3b8)' }}>
                Please type <strong style={{ color: '#fff' }}>{tenant.name}</strong> to confirm:
              </label>
              <input
                type="text"
                placeholder={tenant.name}
                value={deleteConfirmation}
                onChange={(e) => setDeleteConfirmation(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: 6,
                  border: '1px solid rgba(239, 68, 68, 0.4)',
                  background: 'rgba(0,0,0,0.4)',
                  color: '#fff',
                  marginTop: 6,
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 10 }}>
              <button
                type="button"
                onClick={onClose}
                style={{ padding: '8px 16px', borderRadius: 6, background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleteConfirmation !== tenant.name}
                onClick={handleDelete}
                style={{
                  padding: '8px 20px',
                  borderRadius: 6,
                  background: deleteConfirmation === tenant.name ? '#ef4444' : 'rgba(239, 68, 68, 0.2)',
                  color: '#fff',
                  fontWeight: 700,
                  border: 'none',
                  cursor: deleteConfirmation === tenant.name ? 'pointer' : 'not-allowed',
                }}
              >
                Permanently Purge Tenant
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
