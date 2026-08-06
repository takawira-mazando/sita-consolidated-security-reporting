import { useState } from 'react';
import DashHeader from '../components/dashboard/DashHeader';
import Panel from '../components/dashboard/Panel';
import StatCard from '../components/dashboard/StatCard';
import BarRow from '../components/dashboard/BarRow';
import OemTag from '../components/dashboard/OemTag';
import Chip from '../components/dashboard/Chip';
import ExplainOverlay from '../components/dashboard/ExplainOverlay';
import { buildExplain, buildLayman, ROLE_LABELS, type ExplainFacts } from '../data/explanations';
import { useAppSecData } from '../hooks/useAppSecData';

export default function AppSecDashboard() {
  const [overlay, setOverlay] = useState<null | 'explain' | 'layman'>(null);
  const d = useAppSecData();

  if (d.loading) {
    return <div className="dash"><DashHeader title="Application Security" subtitle="Loading live data…" badge={{ label: 'appsec', color: 'var(--amber)', bg: 'var(--amber-dim)' }} consolidatedTag="AppScan · API Security · Imperva WAF" onExplain={() => {}} onLayman={() => {}} /><div className="dash-loading"><span className="spin" />Loading live data…</div></div>;
  }

  const facts: ExplainFacts = {
    findings: d.findingsTotal,
    critical: d.counts.critical,
    topCat: d.owasp[0]?.label,
    topCatCount: d.owasp[0]?.value,
    topCve: d.criticals[0]?.cve,
  };

  return (
    <div className="dash">
      <DashHeader
        title="Application Security"
        subtitle="AppScan vulnerability management — application-level findings"
        badge={{ label: 'appsec', color: 'var(--amber)', bg: 'var(--amber-dim)' }}
        consolidatedTag="AppScan · API Security · Imperva WAF"
        onExplain={() => setOverlay('explain')}
        onLayman={() => setOverlay('layman')}
      />
      <div className="consol-note">
        <strong>✓ Consolidation:</strong>&nbsp;
        AppSec view fuses <OemTag source="appscan" label="AppScan" /> vulnerability findings with
        <span style={{ margin: '0 4px' }}><OemTag source="api-sec" label="API Security" /></span> exposure data and
        <span style={{ margin: '0 4px' }}><OemTag source="imperva-waf" label="Imperva WAF" /></span> blocking telemetry.
      </div>

      {d.error && <div className="dash-error">{d.error}</div>}

      <div className="stats-bar">
        <StatCard ghost={String(d.findingsTotal)} accent="var(--amber)" value={d.findingsTotal.toLocaleString()} valueColor="var(--amber)" label={<><span>Total Findings </span><OemTag source="appscan" label="AppScan" /></>} delta="live" deltaColor="var(--text-muted)" />
        <StatCard ghost={String(d.counts.critical)} accent="var(--red)" value={String(d.counts.critical)} valueColor="var(--red)" label={<><span>Critical </span><OemTag source="appscan" label="Sev 4" /></>} delta="live" deltaColor="var(--text-muted)" />
        <StatCard ghost="Fix Rate" accent="var(--green)" value={d.fixRate != null ? `${d.fixRate}%` : '—'} valueColor={d.fixRate != null ? 'var(--green)' : 'var(--text-muted)'} label={<><span>Fix Rate (30d) </span><OemTag source="appscan" label="tracked" /></>} delta="30-day window" deltaColor="var(--green)" />
        <StatCard ghost="WAF" accent="var(--red)" value={d.wafTotal.toLocaleString()} valueColor="var(--red)" label={<><span>WAF Blocks </span><OemTag source="imperva-waf" label="30d" /></>} delta="live" deltaColor="var(--text-muted)" />
      </div>

      <div className="dash-grid cols-2">
        <Panel title={<><span>Vulnerability by Application</span> <OemTag source="appscan" label="AppScan" /></>} bodyClassName="scroll-x" bodyStyle={{ padding: 0 }}>
          <table>
            <thead><tr><th>Application</th><th>Critical</th><th>High</th><th>Medium</th><th>Low</th><th>Status</th></tr></thead>
            <tbody>
              {d.vulnByApp.length ? d.vulnByApp.map((v) => (
                <tr key={v.app}>
                  <td><strong>{v.app}</strong></td>
                  <td style={{ color: 'var(--red)', fontWeight: 700 }}>{v.crit}</td>
                  <td>{v.high}</td>
                  <td>{v.med}</td>
                  <td>{v.low}</td>
                  <td style={{ color: v.trendColor }}>{v.trend}</td>
                </tr>
              )) : <tr><td colSpan={6}><div className="panel-empty">No findings yet.</div></td></tr>}
            </tbody>
          </table>
        </Panel>
        <Panel title={<><span>Distribution by Category</span> <OemTag source="appscan" label="AppScan" /></>}>
          {d.owasp.length ? d.owasp.map((o) => (
            <BarRow key={o.label} label={o.label} width={o.width} color={o.color} value={o.value} />
          )) : <div className="panel-empty">No findings yet.</div>}
        </Panel>
      </div>

      <div className="dash-grid cols-2-1">
        <Panel title={<><span>API Exposure</span> <OemTag source="api-sec" label="API Security" /></>} bodyClassName="scroll-x" bodyStyle={{ padding: 0 }}>
          <table>
            <thead><tr><th>API Endpoint</th><th>Application</th><th>Method</th><th>Risk</th><th>Shadow</th></tr></thead>
            <tbody>
              {d.apiExposure.length ? d.apiExposure.map((e, i) => (
                <tr key={i}>
                  <td><code>{e.endpoint}</code></td>
                  <td>{e.app}</td>
                  <td>{e.method}</td>
                  <td style={{ color: Number(e.risk) >= 80 ? 'var(--red)' : Number(e.risk) >= 50 ? 'var(--amber)' : 'var(--text-primary)' }}>{e.risk}</td>
                  <td>{e.shadow === 'yes' ? <Chip tone="high">shadow</Chip> : 'no'}</td>
                </tr>
              )) : <tr><td colSpan={5}><div className="panel-empty">No API exposure records yet.</div></td></tr>}
            </tbody>
          </table>
        </Panel>
        <Panel title={<><span>WAF Block Summary</span> <OemTag source="imperva-waf" label="Imperva WAF" /></>}>
          {d.wafByType.length ? d.wafByType.map((w) => (
            <BarRow key={w.label} label={w.label} width={w.width} color={w.color} value={w.value} />
          )) : <div className="panel-empty">No WAF blocks recorded yet.</div>}
        </Panel>
      </div>

      <Panel title={<><span>Critical Findings</span> <OemTag source="appscan" label="AppScan" /></>} bodyClassName="scroll-x" bodyStyle={{ padding: 0 }}>
        <table>
          <thead><tr><th>ID</th><th>Severity</th><th>Application</th><th>Category</th><th>Discovered</th></tr></thead>
          <tbody>
            {d.criticals.length ? d.criticals.map((c) => (
              <tr key={c.cve}>
                <td><code>{c.cve}</code></td>
                <td><Chip tone={c.cvssTone}>critical</Chip></td>
                <td>{c.app}</td>
                <td>{c.comp}</td>
                <td style={{ fontFamily: 'var(--mono)' }}>{c.discovered}</td>
              </tr>
            )) : <tr><td colSpan={5}><div className="panel-empty">No critical findings yet.</div></td></tr>}
          </tbody>
        </table>
      </Panel>

      <ExplainOverlay
        open={overlay !== null}
        title={`${ROLE_LABELS.appsec} — ${overlay === 'layman' ? "Layman's Guide" : 'How This Dashboard Is Built'}`}
        body={overlay === 'layman' ? buildLayman('appsec', facts) : buildExplain('appsec', facts)}
        onClose={() => setOverlay(null)}
      />
    </div>
  );
}
