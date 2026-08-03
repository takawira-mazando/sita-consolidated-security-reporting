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
import { useSreData } from '../hooks/useSreData';

export default function SreDashboard() {
  const [overlay, setOverlay] = useState<null | 'explain' | 'layman'>(null);
  const d = useSreData();

  if (d.loading) {
    return <div className="dash"><DashHeader title="Service Operations" subtitle="Loading live data…" badge={{ label: 'sre', color: 'var(--text-secondary)', bg: 'var(--text-muted)' }} consolidatedTag="Infrastructure · connectors" onExplain={() => {}} onLayman={() => {}} /><div className="dash-loading"><span className="spin" />Loading live data…</div></div>;
  }

  const facts: ExplainFacts = {
    healthy: d.healthy,
    total: d.total,
    degraded: d.degraded,
    events: d.eventsTotal,
    errorRate: d.errorRate,
  };

  return (
    <div className="dash">
      <DashHeader
        title="Service Operations"
        subtitle="Agent health, connector status, and ingestion pipeline"
        badge={{ label: 'sre', color: 'var(--text-secondary)', bg: 'var(--text-muted)' }}
        consolidatedTag="Infrastructure · connectors"
        onExplain={() => setOverlay('explain')}
        onLayman={() => setOverlay('layman')}
      />
      <div className="consol-note">
        <strong>✓ Consolidation:</strong>&nbsp;
        Service Ops monitors all <OemTag source="appscan" label="ingestion" /> connectors and
        <span style={{ margin: '0 4px' }}><OemTag source="imperva" label="agent" /></span> health across the platform.
        This view is not available in any individual OEM console.
      </div>

      {d.error && <div className="dash-error">{d.error}</div>}

      <div className="stats-bar">
        <StatCard ghost={`${d.healthy} / ${d.total}`} accent="var(--green)" value={`${d.healthy} / ${d.total}`} valueColor={d.degraded > 0 ? 'var(--amber)' : 'var(--green)'} label="Connectors Online" delta={d.degraded > 0 ? `${d.degraded} degraded` : 'all nominal'} deltaColor={d.degraded > 0 ? 'var(--red)' : 'var(--green)'} />
        <StatCard ghost="DAM" accent="var(--green)" value="—" valueColor="var(--text-muted)" label="DAM Agents" delta="not tracked" deltaColor="var(--text-muted)" />
        <StatCard ghost="Uptime" accent="var(--green)" value="—" valueColor="var(--text-muted)" label="Pipeline Uptime" delta="not tracked" deltaColor="var(--text-muted)" />
        <StatCard ghost={String(d.eventsTotal)} accent="var(--blue)" value={d.eventsTotal.toLocaleString()} valueColor="var(--blue)" label="Events / h" delta="live from connectors" deltaColor="var(--green)" />
      </div>

      <div className="dash-grid cols-2">
        <Panel title="Connector Health" bodyClassName="scroll-x" bodyStyle={{ padding: 0 }}>
          <table>
            <thead><tr><th>Connector</th><th>Source</th><th>Status</th><th>Latency</th><th>Events/h</th><th>Circuit</th></tr></thead>
            <tbody>
              {d.rows.length ? d.rows.map((c) => (
                <tr key={c.name}>
                  <td><code>{c.name}</code></td>
                  <td><OemTag source={c.src} label={c.srcLabel} /></td>
                  <td><Chip tone={c.statusTone}>{c.status}</Chip></td>
                  <td style={{ fontFamily: 'var(--mono)' }}>{c.latency}</td>
                  <td>{c.events}</td>
                  <td>{c.circuit}</td>
                </tr>
              )) : <tr><td colSpan={6}><div className="panel-empty">No connectors registered yet.</div></td></tr>}
            </tbody>
          </table>
        </Panel>
        <Panel title="System Health" hint="last 24h" bodyStyle={{ paddingTop: 10 }}>
          {d.systemHealth.map((s) => (
            <BarRow key={s.label} label={s.label} width="0%" color={s.color} value={s.value} />
          ))}
          <div className="panel-empty" style={{ marginTop: 8 }}>System metrics not exposed by backend yet.</div>
        </Panel>
      </div>

      <div className="dash-grid cols-3">
        <Panel title="Connector Throughput">
          {d.eventBars.length ? <MiniBarChart bars={d.eventBars} axis={['low', 'high']} height={60} /> : <div className="panel-empty">No connector metrics yet.</div>}
        </Panel>
        <Panel title="Error Rate">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 6 }}>
            <span style={{ fontFamily: 'var(--grotesk)', fontSize: 28, color: 'var(--green)', fontWeight: 700 }}>{d.errorRate}</span>
            <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>of events (live)</span>
          </div>
        </Panel>
        <Panel title="Agent Versions">
          <div className="panel-empty">Agent inventory not tracked by backend yet.</div>
        </Panel>
      </div>

      <ExplainOverlay
        open={overlay !== null}
        title={`${ROLE_LABELS.sre} — ${overlay === 'layman' ? "Layman's Guide" : 'How This Dashboard Is Built'}`}
        body={overlay === 'layman' ? buildLayman('sre', facts) : buildExplain('sre', facts)}
        onClose={() => setOverlay(null)}
      />
    </div>
  );
}
