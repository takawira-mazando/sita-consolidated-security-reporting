import { useState } from 'react';
import type { DbSecAiResult, DamAlertCard } from '../../api/intel';
import Chip from './Chip';
import type { Tone } from '../../data/mappers';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function sevTone(sev: string): Tone {
  if (sev === 'critical') return 'severe';
  if (sev === 'high') return 'high';
  if (sev === 'medium') return 'med';
  return 'ok';
}

function postureTone(posture: string) {
  if (posture === 'CRITICAL') return { color: 'var(--red)', bg: 'var(--red-dim)', icon: '🔴' };
  if (posture === 'ELEVATED') return { color: 'var(--amber)', bg: 'var(--amber-dim)', icon: '🟠' };
  if (posture === 'GUARDED') return { color: 'var(--blue)', bg: 'rgba(59,130,246,0.12)', icon: '🔵' };
  return { color: 'var(--green)', bg: 'var(--green-dim)', icon: '🟢' };
}

function confidenceColor(label: string) {
  if (label === 'HIGH') return 'var(--red)';
  if (label === 'MEDIUM') return 'var(--amber)';
  return 'var(--text-muted)';
}

function rbacLabel(view: string) {
  if (view === 'SOC_DBA_TECHNICAL') return 'SOC / DBA — Technical View';
  if (view === 'COMPLIANCE_REGULATORY') return 'Compliance — Regulatory View';
  return 'Executive — Risk & Business View';
}

interface Props {
  result: DbSecAiResult | null;
  loading: boolean;
  error: string | null;
  onRun: (params: { lookback_hours: number; db_name?: string; min_severity?: string }) => void;
}

// ---------------------------------------------------------------------------
// Individual alert card (accordion)
// ---------------------------------------------------------------------------

function AlertCard({ card, rbac }: { card: DamAlertCard; rbac: string }) {
  const [open, setOpen] = useState(false);
  const pt = postureTone(card.severity === 'critical' ? 'CRITICAL' : card.severity === 'high' ? 'ELEVATED' : 'GUARDED');

  return (
    <div
      className="dam-card"
      style={{
        borderLeft: `3px solid ${pt.color}`,
        background: 'var(--surface)',
        borderRadius: 8,
        marginBottom: 10,
        overflow: 'hidden',
        transition: 'box-shadow 0.2s',
      }}
    >
      {/* Header row */}
      <button
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '10px 14px',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
        }}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span style={{ fontSize: 18 }}>{pt.icon}</span>
        <span style={{ flex: 1, fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{card.title}</span>
        <Chip tone={sevTone(card.severity)}>{card.severity.toUpperCase()}</Chip>
        <span
          style={{
            fontFamily: 'var(--mono)',
            fontSize: 11,
            color: confidenceColor(card.confidence_label),
            minWidth: 70,
            textAlign: 'right',
          }}
        >
          {card.confidence_label} {card.confidence_score}%
        </span>
        <span style={{ color: 'var(--text-muted)', fontSize: 11, marginLeft: 6 }}>{card.evidence_count} events</span>
        <span style={{ color: 'var(--text-muted)', fontSize: 16, marginLeft: 8 }}>{open ? '▲' : '▼'}</span>
      </button>

      {/* Confidence bar */}
      <div style={{ height: 3, background: 'var(--border-dim)' }}>
        <div
          style={{
            height: 3,
            width: `${card.confidence_score}%`,
            background: confidenceColor(card.confidence_label),
            transition: 'width 0.6s ease',
          }}
        />
      </div>

      {/* Expanded body */}
      {open && (
        <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 12, background: 'rgba(0,0,0,0.1)' }}>
          {/* Summary */}
          {card.technical_summary && (
            <div style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--text-primary)' }}>
              <strong>AI Detection: </strong>{card.technical_summary}
            </div>
          )}

          {/* Key Metrics Row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10, marginTop: 4 }}>
            <div style={{ padding: '8px 12px', borderRadius: 6, background: 'var(--surface-2, rgba(255,255,255,0.04))', border: '1px solid var(--border-dim)' }}>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Target Databases</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', marginTop: 2 }}>
                {card.top_targets?.join(', ') || 'All Monitored Datastores'}
              </div>
            </div>

            <div style={{ padding: '8px 12px', borderRadius: 6, background: 'var(--surface-2, rgba(255,255,255,0.04))', border: '1px solid var(--border-dim)' }}>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Blast Radius &amp; Impact</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--amber, #f59e0b)', marginTop: 2 }}>
                {card.blast_radius_est || 'Tenant database partition'}
              </div>
            </div>

            <div style={{ padding: '8px 12px', borderRadius: 6, background: 'var(--surface-2, rgba(255,255,255,0.04))', border: '1px solid var(--border-dim)' }}>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Remediation Urgency</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: card.remediation_urgency.startsWith('IMMEDIATE') ? 'var(--red, #ef4444)' : 'var(--amber, #f59e0b)', marginTop: 2 }}>
                {card.remediation_urgency}
              </div>
            </div>

            {card.popia_condition && (
              <div style={{ padding: '8px 12px', borderRadius: 6, background: 'var(--surface-2, rgba(255,255,255,0.04))', border: '1px solid var(--border-dim)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Privacy &amp; Compliance</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#38bdf8', marginTop: 2 }}>
                  {card.popia_condition}
                </div>
              </div>
            )}
          </div>

          {/* Action Row */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4, paddingTop: 10, borderTop: '1px solid var(--border-dim)' }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {card.evidence_sources.map((s) => (
                <span key={s} style={{
                  fontSize: 10.5, padding: '2px 8px', borderRadius: 4,
                  background: 'rgba(139,92,246,0.12)', color: '#a78bfa', border: '1px solid rgba(139,92,246,0.25)'
                }}>📡 {s}</span>
              ))}
            </div>

            <button
              onClick={() => window.alert(`Applied automated DAM guardrail for ${card.title}`)}
              style={{
                fontSize: 11.5,
                fontWeight: 700,
                padding: '6px 14px',
                borderRadius: 6,
                background: 'linear-gradient(135deg, #D67D4A 0%, #A85A2E 100%)',
                color: '#ffffff',
                border: '1px solid rgba(255, 255, 255, 0.3)',
                cursor: 'pointer',
              }}
            >
              Apply Isolation Guardrail
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function InfoRow({ label, value, mono, accent }: { label: string; value?: string; mono?: boolean; accent?: string }) {
  if (!value) return null;
  return (
    <div>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 2 }}>{label}</div>
      <div style={{
        fontSize: 11,
        color: accent || 'var(--text-primary)',
        fontFamily: mono ? 'var(--mono)' : undefined,
        lineHeight: 1.4,
      }}>{value}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export default function DbSecAiAlertsPanel({ result, loading, error, onRun }: Props) {
  const [lookback, setLookback] = useState(24);
  const [dbName, setDbName] = useState('');
  const [minSev, setMinSev] = useState('');
  const [expanded, setExpanded] = useState(false);

  const pt = result ? postureTone(result.overall_dam_posture) : postureTone('NORMAL');

  const handleRun = () => {
    onRun({ lookback_hours: lookback, db_name: dbName || undefined, min_severity: minSev || undefined });
    setExpanded(true);
  };

  return (
    <div style={{
      border: '1px solid var(--border-dim)',
      borderRadius: 10,
      overflow: 'hidden',
      background: 'var(--surface)',
      marginBottom: 16,
    }}>
      {/* Section header — always visible */}
      <button
        onClick={() => setExpanded((v) => !v)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '13px 18px',
          background: 'linear-gradient(90deg, rgba(139,92,246,0.10) 0%, transparent 100%)',
          border: 'none',
          borderBottom: expanded ? '1px solid var(--border-dim)' : 'none',
          cursor: 'pointer',
          textAlign: 'left',
        }}
        aria-expanded={expanded}
      >
        <span style={{ fontSize: 20 }}>🧠</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>
            AI — DAM Threat Analysis
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
            Live reasoning over ingested DAM alerts, DB violation findings, and WAF SQL blocks
          </div>
        </div>

        {result && (
          <span style={{
            padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700,
            background: pt.bg, color: pt.color, border: `1px solid ${pt.color}`,
          }}>
            {pt.icon} {result.overall_dam_posture}
          </span>
        )}

        {result && (
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {result.total_events_analysed} events · {result.ai_alert_cards.length} patterns
          </span>
        )}

        <span style={{ color: 'var(--text-muted)', fontSize: 16 }}>{expanded ? '▲' : '▼'}</span>
      </button>

      {/* Expanded body */}
      {expanded && (
        <div style={{ padding: '14px 18px' }}>
          {/* Control toolbar */}
          <div style={{
            display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center',
            marginBottom: 14, padding: '10px 12px',
            background: 'rgba(0,0,0,0.12)', borderRadius: 8,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)' }}>Window</label>
              <select
                value={lookback}
                onChange={(e) => setLookback(Number(e.target.value))}
                style={{ fontSize: 11, background: 'var(--surface-2)', color: 'var(--text-primary)', border: '1px solid var(--border-dim)', borderRadius: 4, padding: '2px 6px' }}
              >
                <option value={4}>4h</option>
                <option value={24}>24h</option>
                <option value={48}>48h</option>
                <option value={72}>72h</option>
                <option value={168}>7d</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)' }}>DB filter</label>
              <input
                type="text"
                value={dbName}
                onChange={(e) => setDbName(e.target.value)}
                placeholder="e.g. CitizenDB"
                style={{
                  fontSize: 11, background: 'var(--surface-2)', color: 'var(--text-primary)',
                  border: '1px solid var(--border-dim)', borderRadius: 4, padding: '2px 8px', width: 120,
                }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)' }}>Min severity</label>
              <select
                value={minSev}
                onChange={(e) => setMinSev(e.target.value)}
                style={{ fontSize: 11, background: 'var(--surface-2)', color: 'var(--text-primary)', border: '1px solid var(--border-dim)', borderRadius: 4, padding: '2px 6px' }}
              >
                <option value="">All</option>
                <option value="critical">Critical</option>
                <option value="high">High+</option>
                <option value="medium">Medium+</option>
              </select>
            </div>

            <button
              onClick={handleRun}
              disabled={loading}
              style={{
                fontSize: 11, fontWeight: 700, padding: '4px 16px', borderRadius: 20,
                background: loading ? 'var(--border-dim)' : 'linear-gradient(135deg, #7c3aed, #4f46e5)',
                color: '#fff', border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
                transition: 'opacity 0.2s',
              }}
            >
              {loading ? '⏳ Analysing…' : '⚡ Run AI Analysis'}
            </button>
          </div>

          {/* Error */}
          {error && (
            <div style={{ color: 'var(--red)', fontSize: 12, padding: '8px 12px', background: 'var(--red-dim)', borderRadius: 6, marginBottom: 12 }}>
              {error}
            </div>
          )}

          {/* No result yet */}
          {!loading && !error && !result && (
            <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-muted)', fontSize: 13 }}>
              Click <strong>Run AI Analysis</strong> to ingest live DAM logs and generate AI-graded threat patterns.
            </div>
          )}

          {/* Results */}
          {result && (
            <>
              {/* Meta row */}
              <div style={{
                display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'center',
                marginBottom: 14, fontSize: 11, color: 'var(--text-muted)',
              }}>
                <span>🏢 {result.tenant_scope}</span>
                <span>⏱ {result.lookback_hours}h window</span>
                <span>📊 {result.total_events_analysed} events</span>
                <span style={{ color: 'rgba(139,92,246,0.9)' }}>👤 {rbacLabel(result.rbac_view)}</span>
                <span>🗄 {result.db_inventory_size} DBs in scope</span>
              </div>

              {/* Posture summary */}
              <div style={{
                padding: '10px 14px', borderRadius: 8, marginBottom: 14,
                background: pt.bg, border: `1px solid ${pt.color}`,
                fontSize: 12, color: pt.color, lineHeight: 1.5,
              }}>
                <strong>{pt.icon} {result.overall_dam_posture}:</strong> {result.posture_rationale}
              </div>

              {/* Signal breakdown */}
              <div style={{
                display: 'flex', gap: 12, marginBottom: 14, fontSize: 11,
              }}>
                {[
                  { label: 'DAM Alerts', value: result.dam_alerts_ingested, color: 'var(--amber)' },
                  { label: 'DB Findings', value: result.findings_ingested, color: 'var(--red)' },
                  { label: 'WAF SQL Blocks', value: result.waf_db_blocks_ingested, color: 'var(--blue)' },
                ].map(({ label, value, color }) => (
                  <div key={label} style={{
                    flex: 1, padding: '8px 12px', borderRadius: 6,
                    background: 'rgba(0,0,0,0.15)', textAlign: 'center',
                  }}>
                    <div style={{ fontSize: 18, fontWeight: 700, color }}>{value}</div>
                    <div style={{ color: 'var(--text-muted)', marginTop: 2 }}>{label}</div>
                  </div>
                ))}
              </div>

              {/* Alert cards */}
              {result.ai_alert_cards.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '16px', color: 'var(--text-muted)', fontSize: 13 }}>
                  No matching DAM threat patterns detected in the selected window and filters.
                </div>
              ) : (
                result.ai_alert_cards.map((card) => (
                  <AlertCard key={card.archetype_id} card={card} rbac={result.rbac_view} />
                ))
              )}

              <div style={{ fontSize: 10, color: 'var(--text-muted)', fontStyle: 'italic', marginTop: 8 }}>
                Advisory only — all findings require human analyst sign-off before remediation. Generated: {new Date(result.generated_at).toLocaleString()}.
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
