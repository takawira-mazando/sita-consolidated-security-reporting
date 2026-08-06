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
import { useSocData } from '../hooks/useSocData';

export default function SocDashboard() {
  const [overlay, setOverlay] = useState<null | 'explain' | 'layman'>(null);
  const d = useSocData();

  if (d.loading) {
    return <div className="dash"><DashHeader title="SOC Analyst — Incident Response" subtitle="Loading live data…" badge={{ label: 'soc_analyst', color: 'var(--blue)', bg: 'var(--blue-dim)' }} consolidatedTag="Consolidated · 4 sources live" onExplain={() => {}} onLayman={() => {}} /><div className="dash-loading"><span className="spin" />Loading live data…</div></div>;
  }

  const facts: ExplainFacts = {
    incidents: d.activeIncidents,
    backlog: d.queue.length,
    findings: d.findingsTotal,
  };

  return (
    <div className="dash">
      <DashHeader
        title="SOC Analyst — Incident Response"
        subtitle="Unified alert feed from AppScan + Imperva DAM/WAF + API Security"
        badge={{ label: 'soc_analyst', color: 'var(--blue)', bg: 'var(--blue-dim)' }}
        consolidatedTag="Consolidated · 4 sources live"
        onExplain={() => setOverlay('explain')}
        onLayman={() => setOverlay('layman')}
      />
      <div className="consol-note">
        <strong>✓ Consolidation:</strong>&nbsp;
        OEM silos merged into one alert timeline, findings table, and incident queue.
        <span style={{ margin: '0 4px' }}><OemTag source="appscan" label="AppScan" /></span>
        <span style={{ margin: '0 4px' }}><OemTag source="imperva" label="Imperva DAM" /></span>
        <span style={{ margin: '0 4px' }}><OemTag source="imperva-waf" label="Imperva WAF" /></span>
        <span style={{ margin: '0 4px' }}><OemTag source="api-sec" label="API Security" /></span>
      </div>

      {d.error && <div className="dash-error">{d.error}</div>}

      <div className="stats-bar">
        <StatCard ghost={String(d.activeIncidents)} accent="var(--red)" value={String(d.activeIncidents)} valueColor="var(--red)" label={<><span>Active Incidents </span><OemTag source="imperva" label="aggregated" /></>} delta="live" deltaColor="var(--text-muted)" />
        <StatCard ghost="MTTD" accent="var(--amber)" value={d.mttd != null ? `${d.mttd}h` : '—'} valueColor={d.mttd != null ? 'var(--amber)' : 'var(--text-muted)'} label={<><span>MTTD </span><OemTag source="appscan" label="7w" /></>} delta="trending" deltaColor="var(--text-muted)" />
        <StatCard ghost="MTTR" accent="var(--amber)" value={d.mttr != null ? `${d.mttr}h` : '—'} valueColor={d.mttr != null ? 'var(--amber)' : 'var(--text-muted)'} label={<><span>MTTR </span><OemTag source="imperva" label="7w" /></>} delta="trending" deltaColor="var(--text-muted)" />
        <StatCard ghost={String(d.alertTotal)} accent="var(--red)" value={String(d.alertTotal)} valueColor="var(--red)" label={<><span>Alert Backlog </span><OemTag source="api-sec" label="unified" /></>} delta="live" deltaColor="var(--text-muted)" />
      </div>

      <div className="dash-grid cols-2-1">
        <Panel title="Unified Alert Timeline" hint="AppScan + Imperva + API Security">
          {d.timeline.length ? (
            <div className="timeline">
              {d.timeline.map((t, i) => (
                <div key={i} className={`tl-item ${t.sev}`}>
                  <div className="tl-time">{t.time} <OemTag source={t.src} label={t.srcLabel} /></div>
                  <div className="tl-title">{t.title}</div>
                  <div className="tl-desc">{t.desc}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="panel-empty">No alerts in the pipeline yet.</div>
          )}
        </Panel>
        <div className="dash-grid" style={{ gap: 10 }}>
          <Panel title="Top Alert Rules">
            {d.topRules.length ? d.topRules.map((r, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '5px 0', borderBottom: i === d.topRules.length - 1 ? 'none' : '1px solid var(--border-dim)', fontSize: 13 }}>
                <span><code>{r.rule}</code></span>
                <span><Chip tone={r.sevTone}>{r.sev}</Chip> ×{r.count}</span>
              </div>
            )) : <div className="panel-empty">No alert rules yet.</div>}
          </Panel>
          <Panel title="Backlog Age">
            {d.backlogBars.length ? (
              <div>
                {d.backlogBars.map((b) => (
                  <BarRow key={b.label} label={b.label} width={b.width} color={b.color} value={b.value} />
                ))}
                <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 8 }}>
                  {d.backlogTotal} open · oldest {d.oldestHours}h
                </div>
              </div>
            ) : <div className="panel-empty">No open alerts in backlog.</div>}
          </Panel>
        </div>
      </div>

      <div className="dash-grid cols-2">
        <Panel title="Unified Findings" hint="all sources" bodyClassName="scroll-x" bodyStyle={{ padding: 0 }}>
          <table>
            <thead><tr><th>Source</th><th>Severity</th><th>Application</th><th>Title</th><th>Status</th><th>First Seen</th></tr></thead>
            <tbody>
              {d.findings.length ? d.findings.map((f, i) => (
                <tr key={i}>
                  <td><OemTag source={f.src} label={f.srcLabel} /></td>
                  <td><Chip tone={f.sevTone}>{f.sev}</Chip></td>
                  <td>{f.app}</td>
                  <td>{f.title}</td>
                  <td><Chip tone={f.statusTone}>{f.status}</Chip></td>
                  <td style={{ color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>{f.first}</td>
                </tr>
              )) : <tr><td colSpan={6}><div className="panel-empty">No findings yet.</div></td></tr>}
            </tbody>
          </table>
        </Panel>
        <Panel title="MTTD / MTTR Trend" hint="7 weeks · hours">
          {d.trendBars.length ? (
            <MiniBarChart bars={d.trendBars} axis={['MTTD', 'MTTR']} paired height={120} />
          ) : <div className="panel-empty">No SLO history recorded yet.</div>}
        </Panel>
      </div>

      <Panel title="Alert Queue" hint="all OEMs · live" bodyClassName="scroll-x" bodyStyle={{ padding: 0 }}>
        <table>
          <thead><tr><th>Alert ID</th><th>Rule</th><th>Source</th><th>Severity</th><th>Fired At</th><th>Status</th></tr></thead>
          <tbody>
            {d.queue.length ? d.queue.map((q) => (
              <tr key={q.id}>
                <td><code>{q.id}</code></td>
                <td>{q.rule}</td>
                <td><OemTag source={q.src} label={q.srcLabel} /></td>
                <td><Chip tone={q.sevTone}>{q.sev}</Chip></td>
                <td style={{ fontFamily: 'var(--mono)' }}>{q.fired}</td>
                <td><Chip tone={q.statusTone}>{q.status}</Chip></td>
              </tr>
            )) : <tr><td colSpan={6}><div className="panel-empty">No alerts in queue.</div></td></tr>}
          </tbody>
        </table>
      </Panel>

      <ExplainOverlay
        open={overlay !== null}
        title={`${ROLE_LABELS.soc} — ${overlay === 'layman' ? "Layman's Guide" : 'How This Dashboard Is Built'}`}
        body={overlay === 'layman' ? buildLayman('soc', facts) : buildExplain('soc', facts)}
        onClose={() => setOverlay(null)}
      />
    </div>
  );
}
