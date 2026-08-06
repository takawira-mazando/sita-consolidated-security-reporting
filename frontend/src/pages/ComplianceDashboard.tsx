import { useState } from 'react';
import DashHeader from '../components/dashboard/DashHeader';
import Panel from '../components/dashboard/Panel';
import StatCard from '../components/dashboard/StatCard';
import MiniBarChart from '../components/dashboard/MiniBarChart';
import BarRow from '../components/dashboard/BarRow';
import OemTag from '../components/dashboard/OemTag';
import Chip from '../components/dashboard/Chip';
import ExplainOverlay from '../components/dashboard/ExplainOverlay';
import { buildExplain, buildLayman, ROLE_LABELS, type ExplainFacts } from '../data/explanations';
import { useComplianceData } from '../hooks/useComplianceData';

export default function ComplianceDashboard() {
  const [overlay, setOverlay] = useState<null | 'explain' | 'layman'>(null);
  const d = useComplianceData();

  if (d.loading) {
    return <div className="dash"><DashHeader title="Compliance & Audit" subtitle="Loading live data…" badge={{ label: 'compliance', color: 'var(--violet)', bg: 'var(--violet-dim)' }} consolidatedTag="Internal · compliance tracking" onExplain={() => {}} onLayman={() => {}} /><div className="dash-loading"><span className="spin" />Loading live data…</div></div>;
  }

  const ev = d.evidence;
  const facts: ExplainFacts = {
    popia: d.popiaScore,
    iso: d.isoScore,
    open: d.openItems,
    overdue: d.overdue,
    avail: ev?.available,
    missing: ev?.missing,
    expiring: ev?.expiring,
    total: ev?.total,
  };

  return (
    <div className="dash">
      <DashHeader
        title="Compliance & Audit"
        subtitle="POPIA · ISO 27001 · internal audit tracking"
        badge={{ label: 'compliance', color: 'var(--violet)', bg: 'var(--violet-dim)' }}
        consolidatedTag="Internal · compliance tracking"
        onExplain={() => setOverlay('explain')}
        onLayman={() => setOverlay('layman')}
      />
      <div className="consol-note">
        <strong>✓ Consolidation:</strong>&nbsp;
        Compliance consolidates <OemTag source="compliance" label="internal" /> audit data with
        <span style={{ margin: '0 4px' }}><OemTag source="appscan" label="AppScan" /></span> vulnerability findings and
        <span style={{ margin: '0 4px' }}><OemTag source="imperva" label="Imperva DAM" /></span> violation categories
        to map security posture against regulatory frameworks.
      </div>

      {d.error && <div className="dash-error">{d.error}</div>}

      <div className="stats-bar">
        <StatCard ghost={d.popiaScore != null ? `${d.popiaScore}%` : '—'} accent="var(--green)" value={d.popiaScore != null ? `${d.popiaScore}%` : '—'} valueColor={d.popiaScore != null ? 'var(--green)' : 'var(--text-muted)'} label="POPIA Readiness" delta="live" deltaColor="var(--text-muted)" />
        <StatCard ghost={d.isoScore != null ? `${d.isoScore}%` : '—'} accent="var(--amber)" value={d.isoScore != null ? `${d.isoScore}%` : '—'} valueColor={d.isoScore != null ? 'var(--amber)' : 'var(--text-muted)'} label="ISO 27001" delta="live" deltaColor="var(--text-muted)" />
        <StatCard ghost={String(d.openItems)} accent="var(--red)" value={String(d.openItems)} valueColor="var(--red)" label="Open Audit Items" delta="live" deltaColor="var(--text-muted)" />
        <StatCard ghost={String(d.overdue)} accent="var(--amber)" value={String(d.overdue)} valueColor="var(--amber)" label="Overdue" delta="live" deltaColor="var(--text-muted)" />
      </div>

      <div className="dash-grid cols-2">
        <Panel title="Compliance by Framework" bodyClassName="scroll-x" bodyStyle={{ padding: 0 }}>
          <table>
            <thead><tr><th>Framework / Domain</th><th>Score</th><th>Status</th><th>Gap</th><th>Target</th></tr></thead>
            <tbody>
              {d.popiaByDomain.length ? d.popiaByDomain.map((x) => (
                <tr key={x.domain}>
                  <td><strong>{x.domain}</strong></td>
                  <td>{x.score}</td>
                  <td><Chip tone={x.statusTone}>{x.status}</Chip></td>
                  <td>{x.gap}</td>
                  <td>{x.target}</td>
                </tr>
              )) : (
                <>
                  <tr><td><strong>POPIA</strong></td><td>{d.popiaScore != null ? `${d.popiaScore}%` : '—'}</td><td><Chip tone={d.popiaScore != null ? 'ok' : 'half'}>{d.popiaScore != null ? 'on track' : 'no data'}</Chip></td><td>{d.popiaScore != null ? `${100 - d.popiaScore}%` : '—'}</td><td>100%</td></tr>
                  <tr><td><strong>ISO 27001</strong></td><td>{d.isoScore != null ? `${d.isoScore}%` : '—'}</td><td><Chip tone={d.isoScore != null ? 'half' : 'half'}>{d.isoScore != null ? 'needs work' : 'no data'}</Chip></td><td>{d.isoScore != null ? `${100 - d.isoScore}%` : '—'}</td><td>100%</td></tr>
                </>
              )}
            </tbody>
          </table>
        </Panel>
        <Panel title="Audit Item Status" bodyStyle={{ paddingTop: 10 }}>
          {gapBarTotal(d.auditStatus) > 0 ? d.auditStatus.map((s) => (
            <BarRow key={s.label} label={s.label} width={s.width} color={s.color} value={s.value} />
          )) : <div className="panel-empty">No audit gaps recorded yet.</div>}
        </Panel>
      </div>

      <div className="dash-grid cols-3">
        <Panel title="Evidence Collection" hint="artifacts">
          {ev ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 20px', fontSize: 13 }}>
              <div style={{ display: 'contents' }}><span style={{ color: 'var(--text-muted)' }}>Available</span><span style={{ fontFamily: 'var(--grotesk)', fontWeight: 700, color: 'var(--green)' }}>{ev.available}</span></div>
              <div style={{ display: 'contents' }}><span style={{ color: 'var(--text-muted)' }}>Missing</span><span style={{ fontFamily: 'var(--grotesk)', fontWeight: 700, color: 'var(--red)' }}>{ev.missing}</span></div>
              <div style={{ display: 'contents' }}><span style={{ color: 'var(--text-muted)' }}>Expiring (30d)</span><span style={{ fontFamily: 'var(--grotesk)', fontWeight: 700, color: 'var(--amber)' }}>{ev.expiring}</span></div>
              <div style={{ display: 'contents' }}><span style={{ color: 'var(--text-muted)' }}>Total Required</span><span style={{ fontFamily: 'var(--grotesk)', fontWeight: 700, color: 'var(--text-primary)' }}>{ev.total}</span></div>
            </div>
          ) : <div className="panel-empty">No evidence stats yet.</div>}
        </Panel>
        <Panel title="Regulatory Calendar" hint="upcoming">
          {d.calendarItems.length ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {d.calendarItems.map((c) => (
                <div key={c.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, padding: '4px 0', borderBottom: '1px solid var(--border-dim)', fontSize: 13 }}>
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <span style={{ fontFamily: 'var(--mono)', color: 'var(--text-muted)' }}>{c.due}</span>
                    &nbsp;<strong>{c.control}</strong>
                    <span style={{ color: 'var(--text-muted)' }}> · {c.owner}</span>
                  </span>
                  <Chip tone={c.sevTone}>{c.severity}</Chip>
                </div>
              ))}
            </div>
          ) : <div className="panel-empty">No upcoming regulatory dates yet.</div>}
        </Panel>
        <Panel title="Compliance Trend" hint="weekly · %">
          {d.trendBars.length ? (
            <MiniBarChart bars={d.trendBars} axis={['POPIA', 'ISO 27001']} paired height={120} />
          ) : <div className="panel-empty">No compliance history recorded yet.</div>}
        </Panel>
      </div>

      <Panel title={<><span>Audit Gaps</span> <OemTag source="compliance" label="internal" /></>} bodyClassName="scroll-x" bodyStyle={{ padding: 0 }}>
        <table>
          <thead><tr><th>Finding</th><th>Framework</th><th>Owner</th><th>Severity</th><th>Due</th><th>Status</th></tr></thead>
          <tbody>
            {d.auditFindings.length ? d.auditFindings.map((f, i) => (
              <tr key={i}>
                <td>{f.finding}</td>
                <td>{f.framework}</td>
                <td>{f.owner}</td>
                <td><Chip tone={f.sevTone}>{f.sev}</Chip></td>
                <td style={{ color: f.dueColor, fontFamily: 'var(--mono)' }}>{f.due}</td>
                <td><Chip tone={f.statusTone}>{f.status}</Chip></td>
              </tr>
            )) : <tr><td colSpan={6}><div className="panel-empty">No compliance gaps yet.</div></td></tr>}
          </tbody>
        </table>
      </Panel>

      <ExplainOverlay
        open={overlay !== null}
        title={`${ROLE_LABELS.compliance} — ${overlay === 'layman' ? "Layman's Guide" : 'How This Dashboard Is Built'}`}
        body={overlay === 'layman' ? buildLayman('compliance', facts) : buildExplain('compliance', facts)}
        onClose={() => setOverlay(null)}
      />
    </div>
  );
}

function gapBarTotal(items: { value: string }[]): number {
  return items.reduce((a, b) => a + (parseInt(b.value, 10) || 0), 0);
}
