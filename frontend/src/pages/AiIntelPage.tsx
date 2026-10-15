import { useState, useCallback, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { getTierAccess } from '../context/AuthContext';
import type { TenancyTier } from '../types';
import DashHeader from '../components/dashboard/DashHeader';
import Panel from '../components/dashboard/Panel';
import AiReportStudio from '../components/ai/AiReportStudio';
import {
  postAuthorRule,
  postAttributeCampaign,
  postPopiaDossier,
  postRiskCausal,
  postExplainBehaviour,
  postInterpretVaptLogs,
  getVaptBaselineStatus,
  type AuthorRuleResult,
  type CampaignAttributionResult,
  type PopiaDossierResult,
  type CausalResult,
  type BehaviourSequenceResult,
  type VaptLogInterpretationResult,
  type VaptVectorSummary,
  type InterpretedLogEvent,
  type VaptBaselineRemediation,
} from '../api/intel';

// ─── Role gates ───────────────────────────────────────────────────────────────
// These mirror the backend permission scopes:
//   findings  → appsec, soc, soc-ha, appsec-ha, admin, operator, transversal-admin
//   compliance → compliance, exec, deptadmin-*, branchadmin-*, admin, operator, transversal-admin
//   risks     → exec, soc, soc-ha, admin, operator, transversal-admin
const FINDINGS_ROLES = new Set([
  'appsec', 'appsec-ha', 'soc', 'soc-ha',
  'admin', 'operator', 'transversal-admin',
]);
const COMPLIANCE_ROLES = new Set([
  'compliance', 'exec',
  'deptadmin-ha', 'branchadmin-ha', 'dept-admin', 'branch-admin',
  'admin', 'operator', 'transversal-admin',
]);
const RISKS_ROLES = new Set([
  'exec', 'soc', 'soc-ha',
  'admin', 'operator', 'transversal-admin',
]);

function hasAny(roles: string[], set: Set<string>) {
  return roles.some((r) => set.has(r));
}

// ─── Shared UI primitives ─────────────────────────────────────────────────────
function AdvisoryBadge() {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      background: 'rgba(245,158,11,0.15)', color: '#f59e0b',
      border: '1px solid rgba(245,158,11,0.35)',
      borderRadius: 6, fontSize: 11, fontWeight: 700,
      padding: '2px 8px', letterSpacing: '0.05em',
    }}>
      ⚠ ADVISORY ONLY
    </span>
  );
}

function GovernanceNote({ note }: { note: string }) {
  return (
    <div style={{
      marginTop: 12, padding: '10px 14px',
      background: 'rgba(99,102,241,0.08)',
      border: '1px solid rgba(99,102,241,0.2)',
      borderRadius: 8, fontSize: 12, color: 'var(--text-muted)',
      lineHeight: 1.6,
    }}>
      🔒 {note}
    </div>
  );
}

function RunButton({ onClick, loading, label, disabled }: {
  onClick: () => void; loading: boolean; label: string; disabled?: boolean;
}) {
  return (
    <button
      id={`ai-run-${label.toLowerCase().replace(/\s+/g, '-')}`}
      onClick={onClick}
      disabled={loading || disabled}
      style={{
        padding: '9px 20px', borderRadius: 8,
        background: loading ? 'rgba(99,102,241,0.3)' : 'linear-gradient(135deg,#6366f1,#8b5cf6)',
        border: 'none', color: '#fff', fontWeight: 700, fontSize: 13,
        cursor: loading ? 'not-allowed' : 'pointer',
        display: 'flex', alignItems: 'center', gap: 8,
        transition: 'all 0.2s', boxShadow: loading ? 'none' : '0 2px 8px rgba(99,102,241,0.35)',
      }}
    >
      {loading ? <><span className="spin" style={{ width: 14, height: 14 }} /> Running…</> : `▶ ${label}`}
    </button>
  );
}

function ErrorMsg({ error }: { error: string }) {
  return (
    <div style={{
      marginTop: 12, padding: '10px 14px',
      background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
      borderRadius: 8, fontSize: 12, color: '#f87171',
    }}>
      ✗ {error}
    </div>
  );
}

function FieldRow({ label, value, mono }: { label: string; value: string | number | boolean | null | undefined; mono?: boolean }) {
  const display = value === null || value === undefined ? '—' : String(value);
  return (
    <div style={{ display: 'flex', gap: 12, padding: '5px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', alignItems: 'flex-start' }}>
      <span style={{ color: 'var(--text-muted)', fontSize: 12, minWidth: 160, flexShrink: 0 }}>{label}</span>
      <span style={{ fontSize: 13, fontFamily: mono ? 'monospace' : undefined, wordBreak: 'break-all' }}>{display}</span>
    </div>
  );
}

function TagList({ items, color }: { items: string[]; color: string }) {
  if (!items.length) return <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>none</span>;
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
      {items.map((t) => (
        <span key={t} style={{
          padding: '2px 8px', borderRadius: 12,
          background: `${color}22`, color, border: `1px solid ${color}44`,
          fontSize: 12, fontWeight: 600,
        }}>{t}</span>
      ))}
    </div>
  );
}

function SectionHeader({ avp, title, gate, icon }: { avp: string; title: string; gate: string; icon: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
      <div style={{
        width: 42, height: 42, borderRadius: 10,
        background: 'linear-gradient(135deg,#1e1b4b,#312e81)',
        border: '1px solid rgba(99,102,241,0.4)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20,
      }}>{icon}</div>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#6366f1', letterSpacing: '0.1em' }}>{avp}</span>
          <AdvisoryBadge />
        </div>
        <div style={{ fontWeight: 700, fontSize: 16 }}>{title}</div>
      </div>
      <div style={{ marginLeft: 'auto' }}>
        <span style={{
          fontSize: 10, padding: '2px 8px', borderRadius: 12,
          background: 'rgba(139,92,246,0.15)', color: '#a78bfa',
          border: '1px solid rgba(139,92,246,0.3)', fontWeight: 600,
        }}>scope: {gate}</span>
      </div>
    </div>
  );
}

// ─── AVP-2: Author Alert Rule ─────────────────────────────────────────────────
function Avp2Panel({ roles }: { roles: string[] }) {
  const canUse = hasAny(roles, FINDINGS_ROLES);
  const [techniqueId, setTechniqueId] = useState('T1190');
  const [techniqueName, setTechniqueName] = useState('');
  const [severity, setSeverity] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AuthorRuleResult | null>(null);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<'summary' | 'yaml' | 'diff'>('summary');

  const run = useCallback(async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const r = await postAuthorRule({
        technique_id: techniqueId,
        technique_name: techniqueName || undefined,
        severity: severity || undefined,
      });
      setResult(r);
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Request failed');
    } finally {
      setLoading(false);
    }
  }, [techniqueId, techniqueName, severity]);

  return (
    <Panel title={
      <SectionHeader avp="AVP-2" title="Author Alert Rule" gate="findings" icon="🎯" />
    }>
      {!canUse ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '12px 0' }}>
          🔒 Requires <code>appsec</code> or <code>soc</code> role.
        </div>
      ) : (
        <>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.6 }}>
            Given an ATT&CK technique present in received telemetry, propose an alert rule
            for the platform's <code>alert_rules.yaml</code>. The rule is <strong>never automatically merged</strong> —
            a git diff is returned for operator review.
          </p>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
            <div style={{ flex: '1 1 150px' }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Technique ID *</label>
              <input
                id="avp2-technique-id"
                value={techniqueId}
                onChange={(e) => setTechniqueId(e.target.value.toUpperCase())}
                placeholder="e.g. T1190"
                style={inputStyle}
              />
            </div>
            <div style={{ flex: '2 1 200px' }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Technique Name (optional)</label>
              <input
                id="avp2-technique-name"
                value={techniqueName}
                onChange={(e) => setTechniqueName(e.target.value)}
                placeholder="e.g. Exploit Public-Facing Application"
                style={inputStyle}
              />
            </div>
            <div style={{ flex: '1 1 130px' }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Override Severity</label>
              <select
                id="avp2-severity"
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                style={{ ...inputStyle, cursor: 'pointer' }}
              >
                <option value="">auto</option>
                <option value="critical">critical</option>
                <option value="high">high</option>
                <option value="medium">medium</option>
                <option value="low">low</option>
              </select>
            </div>
          </div>
          <RunButton onClick={run} loading={loading} label="Author Rule" />
          {error && <ErrorMsg error={error} />}
          {result && (
            <div style={{ marginTop: 20 }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                {(['summary', 'yaml', 'diff'] as const).map((t) => (
                  <button key={t} id={`avp2-tab-${t}`} onClick={() => setTab(t)}
                    style={{
                      padding: '5px 14px', borderRadius: 6, border: 'none',
                      background: tab === t ? '#6366f1' : 'rgba(255,255,255,0.07)',
                      color: tab === t ? '#fff' : 'var(--text-muted)',
                      cursor: 'pointer', fontSize: 12, fontWeight: 600,
                    }}>{t}</button>
                ))}
              </div>
              {tab === 'summary' && (
                <div>
                  <FieldRow label="Rule ID" value={result.rule_id} mono />
                  <FieldRow label="Technique" value={result.technique_id} />
                  <FieldRow label="Status" value={result.status} />
                  <FieldRow label="Auto-merged" value={String(result.auto_merged)} />
                  <FieldRow label="Rationale" value={result.rationale} />
                  <GovernanceNote note={result.governance_note} />
                </div>
              )}
              {tab === 'yaml' && (
                <pre style={codeStyle}>{result.proposed_yaml}</pre>
              )}
              {tab === 'diff' && (
                <pre style={{ ...codeStyle, fontSize: 11 }}>
                  {result.git_diff.split('\n').map((line, i) => (
                    <span key={i} style={{
                      color: line.startsWith('+') ? '#34d399'
                        : line.startsWith('-') ? '#f87171'
                        : line.startsWith('@@') ? '#60a5fa' : undefined,
                      display: 'block',
                    }}>{line}</span>
                  ))}
                </pre>
              )}
            </div>
          )}
        </>
      )}
    </Panel>
  );
}

// ─── AVP-3: Campaign Attribution ─────────────────────────────────────────────
function Avp3Panel({ roles }: { roles: string[] }) {
  const canUse = hasAny(roles, FINDINGS_ROLES);
  const [reportText, setReportText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CampaignAttributionResult | null>(null);
  const [error, setError] = useState('');

  const run = useCallback(async () => {
    if (!reportText.trim()) return;
    setLoading(true); setError(''); setResult(null);
    try {
      setResult(await postAttributeCampaign(reportText));
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Request failed');
    } finally {
      setLoading(false);
    }
  }, [reportText]);

  const coverageColor = (status: string) =>
    status === 'covered' ? '#34d399' : status === 'gap' ? '#f87171' : '#6b7280';

  return (
    <Panel title={
      <SectionHeader avp="AVP-3" title="Campaign Attribution" gate="findings" icon="🔍" />
    }>
      {!canUse ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '12px 0' }}>
          🔒 Requires <code>appsec</code> or <code>soc</code> role.
        </div>
      ) : (
        <>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.6 }}>
            Paste the text of an external threat report (OSINT, MITRE ATT&CK advisory, CTI feed entry).
            The platform extracts ATT&CK techniques and CVEs, then cross-references them against
            this estate's live exposure. Advisory only — analyst judgement required.
          </p>
          <textarea
            id="avp3-report-text"
            value={reportText}
            onChange={(e) => setReportText(e.target.value)}
            placeholder="Paste threat report text here…"
            rows={6}
            style={{ ...inputStyle, width: '100%', resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }}
          />
          <div style={{ marginTop: 10 }}>
            <RunButton onClick={run} loading={loading} label="Attribute Campaign" disabled={!reportText.trim()} />
          </div>
          {error && <ErrorMsg error={error} />}
          {result && (
            <div style={{ marginTop: 20 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>TECHNIQUES FOUND</div>
                  <TagList items={result.extracted_techniques} color="#6366f1" />
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>CVEs FOUND</div>
                  <TagList items={result.extracted_cves} color="#f59e0b" />
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>SECTOR MATCHES</div>
                  <TagList items={result.sector_match_candidates} color="#34d399" />
                </div>
              </div>
              {result.exposure_overlap.length > 0 && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, color: 'var(--text-muted)' }}>
                    ESTATE CROSS-REFERENCE ({result.coverage_gaps.length} gap{result.coverage_gaps.length !== 1 ? 's' : ''})
                  </div>
                  <div style={{ overflowX: 'auto' }}>
                    <table style={tableStyle}>
                      <thead>
                        <tr>
                          {['Technique', 'In Estate', 'Coverage Status'].map((h) => (
                            <th key={h} style={thStyle}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {result.exposure_overlap.map((row) => (
                          <tr key={row.technique_id}>
                            <td style={tdStyle}><code>{row.technique_id}</code></td>
                            <td style={tdStyle}>{row.in_estate === true ? '✓' : row.in_estate === false ? '✗' : '?'}</td>
                            <td style={tdStyle}>
                              <span style={{ color: coverageColor(row.coverage_status), fontWeight: 600, fontSize: 12 }}>
                                {row.coverage_status.replace('_', ' ')}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
              <GovernanceNote note={result.analyst_judgement_required} />
            </div>
          )}
        </>
      )}
    </Panel>
  );
}

// ─── AVP-5: POPIA s.22 Breach Dossier ─────────────────────────────────────────
function Avp5Panel({ roles }: { roles: string[] }) {
  const canUse = hasAny(roles, COMPLIANCE_ROLES);
  const [appName, setAppName] = useState('');
  const [windowDays, setWindowDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PopiaDossierResult | null>(null);
  const [error, setError] = useState('');

  const run = useCallback(async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      setResult(await postPopiaDossier({ app_name: appName || undefined, window_days: windowDays }));
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Request failed');
    } finally {
      setLoading(false);
    }
  }, [appName, windowDays]);

  return (
    <Panel title={
      <SectionHeader avp="AVP-5" title="POPIA s.22 Breach Dossier" gate="compliance" icon="⚖️" />
    }>
      {!canUse ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '12px 0' }}>
          🔒 Requires <code>compliance</code> or <code>exec</code> role.
        </div>
      ) : (
        <>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.6 }}>
            Assembles a structured evidence dossier for a potential POPIA s.22 breach-notification event.
            The <strong>statutory threshold judgement</strong> (whether notification is required) and the
            <strong> notification narrative</strong> are deliberately withheld — they require legal review.
          </p>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
            <div style={{ flex: '2 1 200px' }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Application (optional)</label>
              <input
                id="avp5-app-name"
                value={appName}
                onChange={(e) => setAppName(e.target.value)}
                placeholder="Filter to specific application"
                style={inputStyle}
              />
            </div>
            <div style={{ flex: '1 1 100px' }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Window (days)</label>
              <input
                id="avp5-window-days"
                type="number" min={1} max={180}
                value={windowDays}
                onChange={(e) => setWindowDays(Number(e.target.value))}
                style={inputStyle}
              />
            </div>
          </div>
          <RunButton onClick={run} loading={loading} label="Generate Dossier" />
          {error && <ErrorMsg error={error} />}
          {result && (
            <div style={{ marginTop: 20 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 12, marginBottom: 16 }}>
                {[
                  { label: 'Critical Findings', value: result.compromise_indicators.critical_findings, color: '#f87171' },
                  { label: 'High Findings', value: result.compromise_indicators.high_findings, color: '#f59e0b' },
                  { label: 'Total in Window', value: result.compromise_indicators.total_findings_in_window, color: '#60a5fa' },
                  { label: 'Alert Events', value: result.compromise_indicators.alert_events_in_window, color: '#c084fc' },
                ].map(({ label, value, color }) => (
                  <div key={label} style={{
                    padding: '12px 16px', borderRadius: 10,
                    background: `${color}11`, border: `1px solid ${color}33`,
                    textAlign: 'center',
                  }}>
                    <div style={{ fontSize: 24, fontWeight: 800, color }}>{value}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{label}</div>
                  </div>
                ))}
              </div>
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, color: 'var(--text-muted)' }}>POPIA s.22 CHECKLIST</div>
                {result.popia_s22_checklist.map((item) => (
                  <div key={item.item} style={{
                    padding: '10px 14px', marginBottom: 6, borderRadius: 8,
                    background: item.can_evidence ? 'rgba(52,211,153,0.07)' : 'rgba(245,158,11,0.07)',
                    border: `1px solid ${item.can_evidence ? 'rgba(52,211,153,0.2)' : 'rgba(245,158,11,0.2)'}`,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 16 }}>{item.can_evidence ? '✅' : '⚠️'}</span>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{item.item}</span>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4, marginLeft: 24 }}>
                      {item.statutory_test}
                    </div>
                    {item.human_input && (
                      <div style={{ fontSize: 11, color: '#f59e0b', marginTop: 4, marginLeft: 24, fontStyle: 'italic' }}>
                        🏛 {item.human_input}
                      </div>
                    )}
                    {item.platform_evidence && (
                      <div style={{ fontSize: 11, color: '#34d399', marginTop: 4, marginLeft: 24 }}>
                        📊 {item.platform_evidence}
                      </div>
                    )}
                  </div>
                ))}
              </div>
              <GovernanceNote note={result.governance_note} />
            </div>
          )}
        </>
      )}
    </Panel>
  );
}

// ─── AVP-8: Risk Causal Attribution ──────────────────────────────────────────
function Avp8Panel({ roles }: { roles: string[] }) {
  const canUse = hasAny(roles, RISKS_ROLES);
  const [appName, setAppName] = useState('');
  const [windowDays, setWindowDays] = useState(14);
  const [threatReport, setThreatReport] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CausalResult | null>(null);
  const [error, setError] = useState('');

  const run = useCallback(async () => {
    if (!appName.trim()) return;
    setLoading(true); setError(''); setResult(null);
    try {
      setResult(await postRiskCausal({
        app_name: appName,
        window_days: windowDays,
        threat_report: threatReport || undefined,
      }));
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Request failed');
    } finally {
      setLoading(false);
    }
  }, [appName, windowDays, threatReport]);

  const hyp = result?.causal_hypothesis;

  return (
    <Panel title={
      <SectionHeader avp="AVP-8" title="Risk-Delta Causal Attribution" gate="risks" icon="📈" />
    }>
      {!canUse ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '12px 0' }}>
          🔒 Requires <code>exec</code> or <code>soc</code> role.
        </div>
      ) : (
        <>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.6 }}>
            Explains a computed risk-score movement in terms of external threat activity.
            Maps the dominant signal to an ATT&CK technique and — if a threat report is supplied —
            checks whether that technique appears in it. Analyst confirmation required.
          </p>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
            <div style={{ flex: '2 1 200px' }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Application *</label>
              <input
                id="avp8-app-name"
                value={appName}
                onChange={(e) => setAppName(e.target.value)}
                placeholder="Application name"
                style={inputStyle}
              />
            </div>
            <div style={{ flex: '1 1 100px' }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Window (days)</label>
              <input
                id="avp8-window-days"
                type="number" min={2} max={90}
                value={windowDays}
                onChange={(e) => setWindowDays(Number(e.target.value))}
                style={inputStyle}
              />
            </div>
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
              Threat Report Text (optional — paste to cross-reference)
            </label>
            <textarea
              id="avp8-threat-report"
              value={threatReport}
              onChange={(e) => setThreatReport(e.target.value)}
              placeholder="Paste relevant threat report text (optional)…"
              rows={3}
              style={{ ...inputStyle, width: '100%', resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }}
            />
          </div>
          <RunButton onClick={run} loading={loading} label="Explain Causal" disabled={!appName.trim()} />
          {error && <ErrorMsg error={error} />}
          {hyp && (
            <div style={{ marginTop: 20 }}>
              <div style={{
                padding: '16px 20px', borderRadius: 12, marginBottom: 16,
                background: 'linear-gradient(135deg,rgba(99,102,241,0.1),rgba(139,92,246,0.1))',
                border: '1px solid rgba(99,102,241,0.25)',
              }}>
                <div style={{ fontSize: 13, lineHeight: 1.7 }}>{hyp.narration_stub}</div>
              </div>
              <FieldRow label="Application" value={hyp.app_name} />
              <FieldRow label="Total Risk Delta" value={`${hyp.total_risk_delta > 0 ? '+' : ''}${hyp.total_risk_delta?.toFixed(2)}`} />
              <FieldRow label="Primary Signal" value={hyp.primary_signal} />
              <FieldRow label="Mapped Technique" value={hyp.mapped_technique ?? 'unknown'} />
              <FieldRow
                label="In Threat Report"
                value={hyp.technique_found_in_threat_report === null ? 'n/a (no report supplied)' : String(hyp.technique_found_in_threat_report)}
              />
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>TECHNIQUES IN REPORT</div>
                <TagList items={hyp.techniques_in_supplied_report} color="#6366f1" />
              </div>
              <GovernanceNote note={result!.governance_note} />
            </div>
          )}
        </>
      )}
    </Panel>
  );
}

// ─── AVP-11: Behaviour Sequence ───────────────────────────────────────────────
function Avp11Panel({ roles }: { roles: string[] }) {
  const canUse = hasAny(roles, COMPLIANCE_ROLES);
  const [windowDays, setWindowDays] = useState(30);
  const [actorId, setActorId] = useState('');
  const [minConf, setMinConf] = useState(2);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BehaviourSequenceResult | null>(null);
  const [error, setError] = useState('');

  const run = useCallback(async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      setResult(await postExplainBehaviour({
        window_days: windowDays,
        actor_id: actorId || undefined,
        min_confidence: minConf,
      }));
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Request failed');
    } finally {
      setLoading(false);
    }
  }, [windowDays, actorId, minConf]);

  const patternColor = (label: string) => {
    const map: Record<string, string> = {
      SELF_APPROVE_CHAIN: '#f87171',
      ESCALATING_EXPORT: '#f59e0b',
      CROSS_SCOPE_PIVOT: '#c084fc',
      RAPID_AUTHORITY_SWEEP: '#fb923c',
    };
    return map[label] ?? '#6b7280';
  };

  return (
    <Panel title={
      <SectionHeader avp="AVP-11" title="Behavioural Sequence Analysis" gate="compliance" icon="🔎" />
    }>
      {!canUse ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '12px 0' }}>
          🔒 Requires <code>compliance</code> or <code>exec</code> role.
        </div>
      ) : (
        <>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.6 }}>
            Groups signed audit-trail events into temporal clusters and labels multi-step patterns
            (self-approve chains, escalating exports, cross-scope pivots, rapid authority sweeps)
            that no single per-row rule would detect. Analyst review required before action.
          </p>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
            <div style={{ flex: '1 1 100px' }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Window (days)</label>
              <input id="avp11-window-days" type="number" min={1} max={365} value={windowDays}
                onChange={(e) => setWindowDays(Number(e.target.value))} style={inputStyle} />
            </div>
            <div style={{ flex: '2 1 180px' }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Actor ID (optional)</label>
              <input id="avp11-actor-id" value={actorId} onChange={(e) => setActorId(e.target.value)}
                placeholder="Scope to specific actor" style={inputStyle} />
            </div>
            <div style={{ flex: '1 1 100px' }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Min Confidence</label>
              <input id="avp11-min-confidence" type="number" min={1} max={10} value={minConf}
                onChange={(e) => setMinConf(Number(e.target.value))} style={inputStyle} />
            </div>
          </div>
          <RunButton onClick={run} loading={loading} label="Analyse Behaviour" />
          {error && <ErrorMsg error={error} />}
          {result && (
            <div style={{ marginTop: 20 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(130px,1fr))', gap: 12, marginBottom: 16 }}>
                {[
                  { label: 'Actors', value: result.actors_analysed, color: '#60a5fa' },
                  { label: 'Clusters', value: result.clusters.length, color: '#6366f1' },
                  { label: 'Anomalous', value: result.anomalous_clusters.length, color: '#f87171' },
                ].map(({ label, value, color }) => (
                  <div key={label} style={{
                    padding: '12px 16px', borderRadius: 10,
                    background: `${color}11`, border: `1px solid ${color}33`, textAlign: 'center',
                  }}>
                    <div style={{ fontSize: 26, fontWeight: 800, color }}>{value}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{label}</div>
                  </div>
                ))}
              </div>
              <div style={{
                padding: '14px 18px', borderRadius: 10, marginBottom: 16,
                background: result.anomalous_clusters.length > 0
                  ? 'rgba(248,113,113,0.08)' : 'rgba(52,211,153,0.08)',
                border: `1px solid ${result.anomalous_clusters.length > 0 ? 'rgba(248,113,113,0.25)' : 'rgba(52,211,153,0.25)'}`,
                fontSize: 13, lineHeight: 1.7,
              }}>
                {result.narration_stub}
              </div>
              {result.anomalous_clusters.length > 0 && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, color: 'var(--text-muted)' }}>
                    ANOMALOUS CLUSTERS
                  </div>
                  {result.anomalous_clusters.slice(0, 10).map((c, i) => (
                    <div key={i} style={{
                      padding: '12px 14px', marginBottom: 8, borderRadius: 8,
                      background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                        <code style={{ fontSize: 12, color: '#60a5fa' }}>{c.actor_id || '(unknown)'}</code>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{c.events.length} events · confidence {c.pattern_confidence}</span>
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {c.pattern_labels.map((p) => (
                          <span key={p} style={{
                            padding: '2px 8px', borderRadius: 12, fontSize: 11, fontWeight: 700,
                            background: `${patternColor(p)}22`, color: patternColor(p),
                            border: `1px solid ${patternColor(p)}44`,
                          }}>{p}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <GovernanceNote note={result.governance_note} />
            </div>
          )}
        </>
      )}
    </Panel>
  );
}

// ─── AIMI VAPT Log Interpretation Layer atop Telemetry ────────────────────────
function AimiVaptLogInterpreterPanel({ roles, tier }: { roles: string[]; tier: TenancyTier }) {
  const [lookbackHours, setLookbackHours] = useState<number>(24);
  const [appName, setAppName] = useState<string>('');
  const [data, setData] = useState<VaptLogInterpretationResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'soc' | 'compliance' | 'exec' | 'stream' | 'baseline'>('soc');
  const [filterSearch, setFilterSearch] = useState<string>('');

  const runAnalysis = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await postInterpretVaptLogs({
        lookback_hours: lookbackHours,
        app_name: appName.trim() || undefined,
        limit_events: 50,
      });
      setData(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to execute AIMI VAPT log interpretation');
    } finally {
      setLoading(false);
    }
  }, [lookbackHours, appName]);

  useEffect(() => {
    runAnalysis();
  }, [runAnalysis]);

  const canSoc = hasAny(roles, FINDINGS_ROLES);
  const canComp = hasAny(roles, COMPLIANCE_ROLES);
  const canExec = hasAny(roles, RISKS_ROLES);

  // Default active tab to first authorized persona
  useEffect(() => {
    if (canSoc) setActiveTab('soc');
    else if (canComp) setActiveTab('compliance');
    else if (canExec) setActiveTab('exec');
    else setActiveTab('stream');
  }, [canSoc, canComp, canExec]);

  const filteredEvents = (data?.interpreted_events || []).filter((e) => {
    if (!filterSearch) return true;
    const term = filterSearch.toLowerCase();
    return (
      e.app_name?.toLowerCase().includes(term) ||
      e.attack_vector?.toLowerCase().includes(term) ||
      e.source_ip?.toLowerCase().includes(term) ||
      e.vapt_cwe?.toLowerCase().includes(term) ||
      e.aimi_verdict?.toLowerCase().includes(term)
    );
  });

  return (
    <Panel title={<SectionHeader avp="AIMI-VAPT" title="AIMI VAPT Log Interpretation Layer atop Telemetry" gate="tenanted-rbac" icon="🛡️" />}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#6366f1', letterSpacing: '0.1em' }}>AIMI-VAPT-LOGS</span>
            <AdvisoryBadge />
            <span style={{
              fontSize: 11, padding: '2px 8px', borderRadius: 12,
              background: 'rgba(99,102,241,0.12)', color: '#818cf8',
              border: '1px solid rgba(99,102,241,0.25)', fontWeight: 600,
            }}>
              Tier: {tier.toUpperCase()} · Multi-Tenant RBAC
            </span>
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Cognitive interpretation over multi-tenant WAF blocks, AppScan DAST/SAST findings, and database audit logs.
          </div>
        </div>

        {/* Tenant scope badge */}
        {data && (
          <div style={{
            padding: '6px 14px', borderRadius: 8,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            fontSize: 12, display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span style={{ color: 'var(--text-muted)' }}>Tenant Scope:</span>
            <strong style={{ color: '#818cf8' }}>{data.tenant_scope.scope_label}</strong>
          </div>
        )}
      </div>

      {/* Control bar */}
      <div style={{
        padding: '14px 18px', borderRadius: 10,
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 14,
        marginBottom: 20,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>Lookback:</span>
          {[
            { label: '6h', value: 6 },
            { label: '12h', value: 12 },
            { label: '24h', value: 24 },
            { label: '48h', value: 48 },
            { label: '7d', value: 168 },
          ].map((opt) => (
            <button
              key={opt.value}
              onClick={() => setLookbackHours(opt.value)}
              style={{
                padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                background: lookbackHours === opt.value ? '#6366f1' : 'rgba(255,255,255,0.05)',
                color: lookbackHours === opt.value ? '#fff' : 'inherit',
                border: '1px solid rgba(255,255,255,0.1)', cursor: 'pointer',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 200 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>Filter App:</span>
          <input
            style={{ ...inputStyle, width: '100%', padding: '5px 10px', fontSize: 12 }}
            placeholder="e.g. lp-treasury-core or all"
            value={appName}
            onChange={(e) => setAppName(e.target.value)}
          />
        </div>

        <RunButton onClick={runAnalysis} loading={loading} label="Interpret Logs with AIMI VAPT" />
      </div>

      {error && <ErrorMsg error={error} />}

      {data && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          {/* Top 4 KPI Stat Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 12 }}>
            <div style={{
              padding: '14px 16px', borderRadius: 10,
              background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.25)',
            }}>
              <div style={{ fontSize: 11, color: '#818cf8', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Total Telemetry Logs
              </div>
              <div style={{ fontSize: 26, fontWeight: 800, marginTop: 4 }}>
                {data.telemetry_summary.total_logs_analyzed}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                {data.telemetry_summary.waf_blocks_count} WAF · {data.telemetry_summary.vulnerability_findings_count} Findings · {data.telemetry_summary.alerts_correlated_count} Alerts
              </div>
            </div>

            <div style={{
              padding: '14px 16px', borderRadius: 10,
              background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.25)',
            }}>
              <div style={{ fontSize: 11, color: '#34d399', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Hostile WAF Interceptions
              </div>
              <div style={{ fontSize: 26, fontWeight: 800, color: '#34d399', marginTop: 4 }}>
                {data.perimeter_resilience.blocked_events_count}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                100% neutralized at perimeter DMZ
              </div>
            </div>

            <div style={{
              padding: '14px 16px', borderRadius: 10,
              background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.25)',
            }}>
              <div style={{ fontSize: 11, color: '#60a5fa', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Perimeter Resilience
              </div>
              <div style={{ fontSize: 26, fontWeight: 800, color: '#60a5fa', marginTop: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
                {data.perimeter_resilience.resilience_percentage}%
                <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 6, background: 'rgba(59,130,246,0.2)', fontWeight: 700 }}>
                  Grade {data.perimeter_resilience.defense_grade}
                </span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                Bypasses: {data.perimeter_resilience.unmitigated_bypasses_count} · Status: {data.perimeter_resilience.status}
              </div>
            </div>

            <div style={{
              padding: '14px 16px', borderRadius: 10,
              background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)',
            }}>
              <div style={{ fontSize: 11, color: '#f87171', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Exploitability Index
              </div>
              <div style={{ fontSize: 26, fontWeight: 800, color: '#f87171', marginTop: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
                {data.attacker_typology.exploitability_index}
                <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}>/ 10</span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                Dominant vector: <strong style={{ color: '#fff' }}>{data.attacker_typology.dominant_attack_vector}</strong>
              </div>
            </div>
          </div>

          {/* Attacker Typology & Intent Box */}
          <div style={{
            padding: '14px 18px', borderRadius: 10,
            background: 'linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.06))',
            border: '1px solid rgba(99,102,241,0.25)',
            display: 'flex', alignItems: 'flex-start', gap: 14,
          }}>
            <span style={{ fontSize: 24 }}>🎯</span>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#818cf8', textTransform: 'uppercase' }}>Inferred Attacker Profile</span>
                <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6, background: 'rgba(245,158,11,0.15)', color: '#f59e0b', fontWeight: 700 }}>
                  AIMI COGNITIVE INFERENCE
                </span>
              </div>
              <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>
                {data.attacker_typology.profile_name}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                {data.attacker_typology.inferred_intent}
              </div>
            </div>
          </div>

          {/* VAPT Attack Vectors Grid */}
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 10 }}>
              Identified VAPT Attack Vectors in Telemetry ({data.vector_breakdown.length})
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 12 }}>
              {data.vector_breakdown.map((v) => (
                <div key={v.vector_key} style={{
                  padding: '14px 16px', borderRadius: 10,
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  display: 'flex', flexDirection: 'column', gap: 8,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{
                      fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 6,
                      background: v.severity === 'critical' ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)',
                      color: v.severity === 'critical' ? '#f87171' : '#fbbf24',
                      border: `1px solid ${v.severity === 'critical' ? 'rgba(239,68,68,0.4)' : 'rgba(245,158,11,0.4)'}`,
                    }}>
                      {v.severity.toUpperCase()}
                    </span>
                    <span style={{ fontSize: 11, fontWeight: 700, color: '#818cf8' }}>
                      {v.event_count} events ({v.percentage}%)
                    </span>
                  </div>

                  <div style={{ fontWeight: 700, fontSize: 14 }}>{v.title}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    <span>{v.owasp_id}</span> ·
                    <span>{v.cwe_ids.join(', ')}</span> ·
                    <span style={{ color: '#a78bfa' }}>{v.mitre_technique}</span>
                  </div>

                  <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5, background: 'rgba(0,0,0,0.2)', padding: '8px 10px', borderRadius: 6 }}>
                    {v.aimi_interpretation}
                  </div>

                  <div style={{ fontSize: 11, color: '#34d399', display: 'flex', alignItems: 'flex-start', gap: 6, marginTop: 'auto' }}>
                    <span>🛡️</span>
                    <span><strong>Virtual Patch:</strong> {v.remediation_guidance}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* RBAC Differentiated Insights Navigation Bar */}
          <div style={{
            display: 'flex', flexWrap: 'wrap', gap: 8,
            borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: 10,
            marginTop: 8,
          }}>
            {[
              { id: 'soc', label: '🛠 SOC / AppSec Telemetry Forensics', gate: 'findings' },
              { id: 'compliance', label: '⚖️ Statutory & POPIA Impact', gate: 'compliance' },
              { id: 'exec', label: '📈 Executive Risk Posture', gate: 'risks' },
              { id: 'stream', label: `📜 Interpreted Log Telemetry (${data.interpreted_events.length})`, gate: 'all' },
              { id: 'baseline', label: '✅ VAPT Baseline Remediation Verifier', gate: 'all' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                style={{
                  padding: '7px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600,
                  background: activeTab === tab.id ? 'rgba(99,102,241,0.2)' : 'transparent',
                  color: activeTab === tab.id ? '#818cf8' : 'var(--text-muted)',
                  border: activeTab === tab.id ? '1px solid rgba(99,102,241,0.4)' : '1px solid transparent',
                  cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* TAB 1: SOC / AppSec Telemetry Forensics */}
          {activeTab === 'soc' && (
            <div style={{
              padding: '16px 18px', borderRadius: 10,
              background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)',
            }}>
              {data.role_gated_insights.soc_appsec?.authorized ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 700, fontSize: 15 }}>Technical Forensic Telemetry (AppSec / SOC)</span>
                    <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 6, background: 'rgba(99,102,241,0.2)', color: '#818cf8', fontWeight: 700 }}>
                      ROLE: FINDINGS
                    </span>
                  </div>

                  <FieldRow label="Unique Attacker Source IPs" value={data.role_gated_insights.soc_appsec.unique_attacker_ips} />
                  <FieldRow label="Top Targeted Services" value={(data.role_gated_insights.soc_appsec.top_targeted_apps || []).join(', ') || 'Estate-wide'} />
                  <FieldRow label="Dominant Hostile Payload" value={data.role_gated_insights.soc_appsec.highest_risk_payload_type} mono />
                  <FieldRow label="Recommended Sigma Action" value={data.role_gated_insights.soc_appsec.recommended_sigma_action} />
                  <FieldRow label="Perimeter Forensic Verification" value={data.role_gated_insights.soc_appsec.forensic_note} />

                  <GovernanceNote note="Forensic telemetry confirms complete containment. In accordance with zero-trust posture, source IPs remain monitored under continuous evaluation." />
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '20px 0', color: 'var(--text-muted)' }}>
                  🔒 Technical forensic insight is restricted to callers holding the <strong>findings</strong> role scope (AppSec / SOC Analyst).
                </div>
              )}
            </div>
          )}

          {/* TAB 2: Statutory & POPIA Impact */}
          {activeTab === 'compliance' && (
            <div style={{
              padding: '16px 18px', borderRadius: 10,
              background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)',
            }}>
              {data.role_gated_insights.compliance?.authorized ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 700, fontSize: 15 }}>Regulatory & Compliance Impact Assessment</span>
                    <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 6, background: 'rgba(16,185,129,0.2)', color: '#34d399', fontWeight: 700 }}>
                      ROLE: COMPLIANCE
                    </span>
                  </div>

                  <FieldRow label="POPIA Section 22 Breach Triggered" value={data.role_gated_insights.compliance.popia_s22_breach_triggered ? 'TRUE (Breach Occurred)' : 'FALSE (Zero Compromise)'} />
                  <FieldRow label="POPIA Statutory Rationale" value={data.role_gated_insights.compliance.popia_rationale} />
                  <FieldRow label="ISO/IEC 27001 Status" value={data.role_gated_insights.compliance.iso_27001_control_status} />
                  <FieldRow label="Auditor-General Attestation" value={data.role_gated_insights.compliance.auditor_attestation} />

                  <GovernanceNote note="POPIA s.22 statutory threshold is NOT triggered because telemetry demonstrates 100% deflection of exfiltration queries at perimeter controls with zero PII access." />
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '20px 0', color: 'var(--text-muted)' }}>
                  🔒 Statutory compliance insight is restricted to callers holding the <strong>compliance</strong> role scope.
                </div>
              )}
            </div>
          )}

          {/* TAB 3: Executive Risk Posture */}
          {activeTab === 'exec' && (
            <div style={{
              padding: '16px 18px', borderRadius: 10,
              background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)',
            }}>
              {data.role_gated_insights.exec_risks?.authorized ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 700, fontSize: 15 }}>Executive Risk & Business Posture</span>
                    <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 6, background: 'rgba(239,68,68,0.2)', color: '#f87171', fontWeight: 700 }}>
                      ROLE: RISKS / EXEC
                    </span>
                  </div>

                  <FieldRow label="Overall Estate Defense Posture" value={data.role_gated_insights.exec_risks.overall_posture} />
                  <FieldRow label="Business Impact Severity" value={data.role_gated_insights.exec_risks.business_impact_score} />
                  <FieldRow label="Perimeter Resilience Grade" value={data.role_gated_insights.exec_risks.perimeter_resilience_grade} />
                  <FieldRow label="Blast Radius Containment" value={data.role_gated_insights.exec_risks.blast_radius_containment} />
                  <FieldRow label="Executive Synopsis" value={data.role_gated_insights.exec_risks.executive_synopsis} />

                  <GovernanceNote note="Advisory executive synthesis. Cross-tenant boundaries and state asset confidentiality maintained with zero transversal spillage." />
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '20px 0', color: 'var(--text-muted)' }}>
                  🔒 Executive risk insights are restricted to callers holding the <strong>risks</strong> or <strong>exec</strong> role scope.
                </div>
              )}
            </div>
          )}

          {/* TAB 4: Interpreted Log Telemetry Stream */}
          {activeTab === 'stream' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
                <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                  Showing {filteredEvents.length} interpreted telemetry rows across tenant scope.
                </span>
                <input
                  style={{ ...inputStyle, width: 240, padding: '4px 10px', fontSize: 12 }}
                  placeholder="Search logs (app, vector, IP)..."
                  value={filterSearch}
                  onChange={(e) => setFilterSearch(e.target.value)}
                />
              </div>

              <div style={{ overflowX: 'auto', maxHeight: 360, overflowY: 'auto', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }}>
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={thStyle}>Timestamp</th>
                      <th style={thStyle}>App</th>
                      <th style={thStyle}>Source IP</th>
                      <th style={thStyle}>Vector</th>
                      <th style={thStyle}>CWE / ATT&CK</th>
                      <th style={thStyle}>Action</th>
                      <th style={thStyle}>AIMI Verdict</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredEvents.map((evt) => (
                      <tr key={evt.id} style={{ background: evt.is_mitigated_baseline ? 'rgba(99,102,241,0.04)' : undefined }}>
                        <td style={{ ...tdStyle, fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                          {evt.timestamp.slice(0, 19).replace('T', ' ')}
                        </td>
                        <td style={{ ...tdStyle, fontWeight: 600 }}>{evt.app_name}</td>
                        <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 11, color: '#a78bfa' }}>
                          {evt.source_ip}
                        </td>
                        <td style={tdStyle}>
                          <span style={{
                            fontSize: 10, fontWeight: 700, padding: '1px 6px', borderRadius: 4,
                            background: 'rgba(239,68,68,0.15)', color: '#f87171',
                          }}>
                            {evt.attack_vector}
                          </span>
                        </td>
                        <td style={{ ...tdStyle, fontSize: 11, color: 'var(--text-muted)' }}>
                          {evt.vapt_cwe} · {evt.mitre_technique}
                        </td>
                        <td style={tdStyle}>
                          <span style={{
                            fontSize: 10, fontWeight: 700, padding: '1px 6px', borderRadius: 4,
                            background: 'rgba(16,185,129,0.2)', color: '#34d399',
                          }}>
                            {evt.action_taken}
                          </span>
                        </td>
                        <td style={{ ...tdStyle, fontSize: 11, color: 'var(--text-muted)', maxWidth: 300 }}>
                          {evt.aimi_verdict}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 5: Baseline VAPT Remediation Verifier */}
          {activeTab === 'baseline' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 4 }}>
                Continuous empirical audit verifying that remediated VAPT baseline vulnerabilities remain actively neutralized in telemetry:
              </div>
              <div style={{ overflowX: 'auto', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }}>
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={thStyle}>VAPT ID</th>
                      <th style={thStyle}>Vulnerability Title</th>
                      <th style={thStyle}>Status</th>
                      <th style={thStyle}>Verified Control Fabric</th>
                      <th style={thStyle}>Log Signature</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.vapt_baseline_audit || []).map((b) => (
                      <tr key={b.id}>
                        <td style={{ ...tdStyle, fontWeight: 700, color: '#818cf8' }}>{b.id}</td>
                        <td style={{ ...tdStyle, fontWeight: 600 }}>{b.title}</td>
                        <td style={tdStyle}>
                          <span style={{
                            fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 6,
                            background: 'rgba(16,185,129,0.2)', color: '#34d399',
                          }}>
                            {b.status}
                          </span>
                        </td>
                        <td style={{ ...tdStyle, fontSize: 11, color: 'var(--text-muted)' }}>{b.control}</td>
                        <td style={{ ...tdStyle, fontSize: 11, fontFamily: 'monospace', color: '#a78bfa' }}>{b.log_signature}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <GovernanceNote note="AIMI VAPT Log Interpretation Layer is non-destructive, strictly read-only, and bounded by cryptographic action auditing and SITA government multi-tenancy." />
        </div>
      )}
    </Panel>
  );
}

// ─── Shared styles ────────────────────────────────────────────────────────────
const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 12px',
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: 8,
  color: 'inherit',
  fontSize: 13,
  outline: 'none',
  boxSizing: 'border-box',
};

const tableStyle: React.CSSProperties = {
  width: '100%', borderCollapse: 'collapse', fontSize: 12,
};

const thStyle: React.CSSProperties = {
  textAlign: 'left', padding: '6px 10px',
  background: 'rgba(255,255,255,0.04)',
  color: 'var(--text-muted)', fontWeight: 700, fontSize: 11,
  borderBottom: '1px solid rgba(255,255,255,0.08)',
};

const tdStyle: React.CSSProperties = {
  padding: '6px 10px',
  borderBottom: '1px solid rgba(255,255,255,0.04)',
};

const codeStyle: React.CSSProperties = {
  padding: '14px 16px', borderRadius: 8,
  background: 'rgba(0,0,0,0.3)',
  border: '1px solid rgba(255,255,255,0.08)',
  fontSize: 12, lineHeight: 1.7, overflowX: 'auto',
  fontFamily: 'monospace', whiteSpace: 'pre',
};

// ─── Capability Manifest strip ────────────────────────────────────────────────
const AVP_META = [
  { avp: 'G2-REPORT', title: 'AI Report Studio & Copilot', gate: 'two-gate-rbac', icon: '🧠', ai: true },
  { avp: 'AIMI-VAPT', title: 'VAPT Log Interpretation', gate: 'tenanted-rbac', icon: '🛡️', ai: true },
  { avp: 'AVP-2',     title: 'Author Alert Rule',       gate: 'findings',      icon: '🎯', ai: true },
  { avp: 'AVP-3',     title: 'Campaign Attribution',     gate: 'findings',      icon: '🔍', ai: true },
  { avp: 'AVP-5',     title: 'POPIA s.22 Breach Dossier',gate: 'compliance',    icon: '⚖️', ai: true },
  { avp: 'AVP-8',     title: 'Risk-Delta Causal',        gate: 'risks',         icon: '📈', ai: true },
  { avp: 'AVP-11',    title: 'Behavioural Sequence',    gate: 'compliance',    icon: '🔎', ai: true },
];

// ─── Page ─────────────────────────────────────────────────────────────────────
const TIER_CONFIG: Record<TenancyTier, { title: string; subtitle: string }> = {
  sita:     { title: 'AI Intelligence — SITA Command Center', subtitle: 'Overarching · G2 Verified Report Generation, AIMI VAPT Log Interpretation & AI capabilities across estate' },
  national: { title: 'AI Intelligence — National Estate',     subtitle: 'Strategic · G2 Verified Report Generation, AIMI VAPT log intelligence, threat attribution and compliance dossiers' },
  dept:     { title: 'AI Intelligence — Department',          subtitle: 'Tactical · G2 Verified Report Generation, VAPT telemetry analysis, detection authoring and risk explanation' },
  branch:   { title: 'AI Intelligence — Branch',              subtitle: 'Granular · G2 Local Intelligence, VAPT log interpretation and audit behaviour analysis' },
};

export default function AiIntelPage({ tier = 'dept' }: { tier?: TenancyTier }) {
  const { user } = useAuth();
  const roles = user?.roles ?? [];
  const cfg = TIER_CONFIG[tier];

  return (
    <div className="dash">
      <DashHeader
        title={cfg.title}
        subtitle={cfg.subtitle}
        badge={{ label: 'AI · Advisory Only', color: '#6366f1', bg: 'rgba(99,102,241,0.15)' }}
        consolidatedTag="AppScan · Imperva WAF · Imperva DAM · API Security"
        onExplain={() => {}}
        onLayman={() => {}}
      />

      {/* Capability strip */}
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: 10,
        padding: '0 0 24px', marginBottom: 8,
      }}>
        {AVP_META.map(({ avp, title, gate, icon }) => (
          <div key={avp} style={{
            padding: '8px 14px', borderRadius: 10,
            background: 'rgba(99,102,241,0.07)',
            border: '1px solid rgba(99,102,241,0.2)',
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span>{icon}</span>
            <div>
              <div style={{ fontSize: 10, color: '#6366f1', fontWeight: 700, letterSpacing: '0.08em' }}>{avp}</div>
              <div style={{ fontSize: 12, fontWeight: 600 }}>{title}</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>scope: {gate}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Important advisory notice */}
      <div style={{
        padding: '14px 18px', borderRadius: 12, marginBottom: 24,
        background: 'rgba(245,158,11,0.08)',
        border: '1px solid rgba(245,158,11,0.25)',
        display: 'flex', gap: 12, alignItems: 'flex-start',
      }}>
        <span style={{ fontSize: 22 }}>⚠️</span>
        <div>
          <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>All outputs are advisory only</div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>
            No result from this page is committed, dispatched, or acted upon automatically.
            Every response requires human review and approval before any operational action is taken.
            Role-based access control and government multi-tenancy are enforced by both this UI and the backend API.
          </div>
        </div>
      </div>

      {/* AVP & VAPT panels — shown per gate access */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        {/* Premier G2 AI Report Studio & Grounded Copilot */}
        <AiReportStudio roles={roles} />

        {/* AIMI VAPT Log Interpretation Layer */}
        <AimiVaptLogInterpreterPanel roles={roles} tier={tier} />

        <Avp2Panel roles={roles} />
        <Avp3Panel roles={roles} />
        <Avp5Panel roles={roles} />
        <Avp8Panel roles={roles} />
        <Avp11Panel roles={roles} />
      </div>
    </div>
  );
}

