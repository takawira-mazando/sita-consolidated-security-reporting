import { useState } from 'react';
import DashHeader from '../components/dashboard/DashHeader';
import Panel from '../components/dashboard/Panel';
import StatCard from '../components/dashboard/StatCard';
import MiniBarChart from '../components/dashboard/MiniBarChart';
import Gauge from '../components/dashboard/Gauge';
import OemTag from '../components/dashboard/OemTag';
import Chip from '../components/dashboard/Chip';
import ExplainOverlay from '../components/dashboard/ExplainOverlay';
import { buildExplain, buildLayman, ROLE_LABELS, type ExplainFacts } from '../data/explanations';
import { useExecData } from '../hooks/useExecData';
import { toneForBucket, colorForBucket, oemForSource } from '../data/mappers';

export default function ExecDashboard() {
  const [overlay, setOverlay] = useState<null | 'explain' | 'layman'>(null);
  const d = useExecData();

  if (d.loading) {
    return <div className="dash"><DashHeader title="Executive Risk Overview" subtitle="Loading live data…" badge={{ label: 'executive', color: 'var(--red)', bg: 'var(--red-dim)' }} consolidatedTag="Consolidated · 4 sources live" onExplain={() => {}} onLayman={() => {}} /><div className="dash-loading"><span className="spin" />Loading live data…</div></div>;
  }

  const topRisks = d.topRisks.map((r) => ({
    app: r.app_name,
    score: r.fused_score.toFixed(1),
    color: colorForBucket(r.bucket),
    bucket: r.bucket,
    tone: toneForBucket(r.bucket),
    trend: 'latest',
    trendColor: 'var(--text-muted)',
  }));

  const heatmapHasData = d.heatmapRows.length > 0;

  const facts: ExplainFacts = {
    fusedRisk: d.summary?.current_risk_score ?? d.topRisks[0]?.fused_score,
    findings: d.findingsTotal,
    popia: d.popiaScore,
    alerts: d.activeAlerts,
    topApp: d.topRisks[0]?.app_name,
    topAppScore: d.topRisks[0]?.fused_score,
  };

  return (
    <div className="dash">
      <DashHeader
        title="Executive Risk Overview"
        subtitle="Consolidated from 4 OEM sources — live from API"
        badge={{ label: 'executive', color: 'var(--red)', bg: 'var(--red-dim)' }}
        consolidatedTag="Consolidated · 4 sources live"
        onExplain={() => setOverlay('explain')}
        onLayman={() => setOverlay('layman')}
      />
      <div className="consol-note">
        <strong>✓ Consolidation:</strong>&nbsp;
        This dashboard fuses
        <span style={{ margin: '0 4px' }}><OemTag source="appscan" label="AppScan" /></span>
        vulnerabilities,
        <span style={{ margin: '0 4px' }}><OemTag source="imperva" label="Imperva DAM" /></span>
        threats,
        <span style={{ margin: '0 4px' }}><OemTag source="imperva-waf" label="Imperva WAF" /></span>
        blocks,
        <span style={{ margin: '0 4px' }}><OemTag source="api-sec" label="API Security" /></span>
        exposure, and
        <span style={{ margin: '0 4px' }}><OemTag source="compliance" label="Compliance" /></span>
        into a single fused risk score. No OEM provides this view natively.
      </div>

      {d.error && <div className="dash-error">{d.error}</div>}

      <div className="stats-bar">
        <StatCard ghost={d.summary ? String(d.summary.current_risk_score) : '—'} accent="var(--red)" value={d.summary ? String(d.summary.current_risk_score) : '—'} valueColor="var(--red)" label={<><span>Fused Risk Score </span><OemTag source="appscan" label="fusion" /></>} delta="live" deltaColor="var(--text-muted)" />
        <StatCard ghost={String(d.findingsTotal)} accent="var(--amber)" value={d.findingsTotal.toLocaleString()} valueColor="var(--amber)" label={<><span>Open Findings </span><OemTag source="appscan" label="AppScan" /></>} delta="live" deltaColor="var(--text-muted)" />
        <StatCard ghost={d.popiaScore != null ? `${d.popiaScore}%` : '—'} accent="var(--green)" value={d.popiaScore != null ? `${d.popiaScore}%` : '—'} valueColor="var(--green)" label={<><span>POPIA Compliance </span><OemTag source="compliance" label="internal" /></>} delta="live" deltaColor="var(--text-muted)" />
        <StatCard ghost={String(d.activeAlerts)} accent="var(--red)" value={String(d.activeAlerts)} valueColor="var(--red)" label={<><span>Active Alerts </span><OemTag source="imperva" label="all sources" /></>} delta="live" deltaColor="var(--text-muted)" />
      </div>

      <div className="dash-grid cols-2-1">
        <Panel title="Fused Risk Score — 30 Day Trend" hint="consolidated">
          {d.trendBars.length ? (
            <MiniBarChart bars={d.trendBars} axis={d.trendBars.length > 4 ? [d.trendBars[0].height ? 'start' : '', 'now'] : undefined} />
          ) : (
            <div className="panel-empty">No risk scores recorded yet. Ingestion will populate this trend.</div>
          )}
        </Panel>
        <div className="dash-grid" style={{ gap: 10 }}>
          <Panel title={<><span>Compliance Gauges</span> <OemTag source="compliance" label="internal" /></>}>
            <div style={{ display: 'flex', gap: 16, justifyContent: 'center', alignItems: 'center' }}>
              <Gauge pct={d.popiaScore ?? 0} label="POPIA" color="var(--green)" />
              <Gauge pct={d.isoScore ?? 0} label="ISO 27001" color="var(--amber)" />
            </div>
          </Panel>
          <Panel title={<><span>Severity Distribution</span> <OemTag source="appscan" label="AppScan" /></>}>
            <div className="donut-wrap">
              {d.donutCss ? (
                <>
                  <div className="donut-ring" style={{ background: `conic-gradient(${d.donutCss})` }} />
                  <div className="donut-legend">
                    {d.donutLegend.map((l) => (
                      <div key={l.label} className="l"><span className="sw" style={{ background: l.color }}></span><span>{l.label}</span></div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="panel-empty">No findings yet.</div>
              )}
            </div>
          </Panel>
        </div>
      </div>

      <div className="dash-grid cols-2">
        <Panel title="Application Risk Heatmap" hint="findings × severity">
          {heatmapHasData ? (
            <div className="scroll-x">
              <div className="heatmap">
                <div className="hm-label" style={{ fontWeight: 600, color: 'var(--text-muted)', fontSize: 10 }}>Application</div>
                <div className="hm-label" style={{ color: 'var(--red)', fontSize: 10 }}>CRIT</div>
                <div className="hm-label" style={{ color: 'var(--amber)', fontSize: 10 }}>HIGH</div>
                <div className="hm-label" style={{ color: 'var(--blue)', fontSize: 10 }}>MED</div>
                <div className="hm-label" style={{ color: 'var(--text-muted)', fontSize: 10 }}>LOW</div>
                {d.heatmapRows.map((row) => (
                  <div key={row.app} style={{ display: 'contents' }}>
                    <div className="hm-label">{row.app}</div>
                    {row.cells.map(([val, cls], i) => (
                      <div key={i} className={`hm-cell ${cls}`}>{val}</div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="panel-empty">No findings yet to build the heatmap.</div>
          )}
        </Panel>
        <Panel title="Top 5 Applications by Fused Risk" bodyClassName="scroll-x" bodyStyle={{ padding: 0 }}>
          <table>
            <thead><tr><th>Application</th><th>Score</th><th>Bucket</th><th>7d Trend</th></tr></thead>
            <tbody>
              {topRisks.length ? topRisks.map((r) => (
                <tr key={r.app}>
                  <td><strong>{r.app}</strong></td>
                  <td style={{ color: r.color, fontFamily: 'var(--grotesk)', fontWeight: 700 }}>{r.score}</td>
                  <td><Chip tone={r.tone}>{r.bucket}</Chip></td>
                  <td style={{ color: r.trendColor, fontFamily: 'var(--mono)' }}>{r.trend}</td>
                </tr>
              )) : <tr><td colSpan={4}><div className="panel-empty">No risk scores yet.</div></td></tr>}
            </tbody>
          </table>
        </Panel>
      </div>

      <Panel title="Alert Summary — Live" hint="consolidated from all OEMs" bodyClassName="scroll-x" bodyStyle={{ padding: 0 }}>
        <table>
          <thead><tr><th>Alert Rule</th><th>Application</th><th>Severity</th><th>Source</th><th>Count</th><th>Status</th></tr></thead>
          <tbody>
            {d.alertSummary.length ? d.alertSummary.map((a, i) => {
              const [src] = oemForSource(a.src);
              return (
                <tr key={i}>
                  <td><code>{a.rule}</code></td>
                  <td>{a.app}</td>
                  <td><Chip tone={a.sevTone}>{a.severity}</Chip></td>
                  <td><OemTag source={src} label={a.srcLabel} /></td>
                  <td>{a.count}</td>
                  <td><Chip tone={a.statusTone}>{a.status}</Chip></td>
                </tr>
              );
            }) : <tr><td colSpan={6}><div className="panel-empty">No alerts yet.</div></td></tr>}
          </tbody>
        </table>
      </Panel>

      <ExplainOverlay
        open={overlay !== null}
        title={`${ROLE_LABELS.exec} — ${overlay === 'layman' ? "Layman's Guide" : 'How This Dashboard Is Built'}`}
        body={overlay === 'layman' ? buildLayman('exec', facts) : buildExplain('exec', facts)}
        onClose={() => setOverlay(null)}
      />
    </div>
  );
}
