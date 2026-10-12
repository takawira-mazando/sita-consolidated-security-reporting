import { useState } from 'react';
import DashHeader from '../components/dashboard/DashHeader';
import Panel from '../components/dashboard/Panel';
import StatCard from '../components/dashboard/StatCard';
import BarRow from '../components/dashboard/BarRow';
import OemTag from '../components/dashboard/OemTag';
import Chip from '../components/dashboard/Chip';
import ExplainOverlay from '../components/dashboard/ExplainOverlay';
import { buildExplain, buildLayman, ROLE_LABELS, type ExplainFacts } from '../data/explanations';
import { useDbSecData } from '../hooks/useDbSecData';
import { useNarrativeFacts } from '../hooks/useNarrativeFacts';
import type { TenancyTier } from '../types';

const TIER_CONFIG: Record<TenancyTier, { title: string; subtitle: string }> = {
  sita: {
    title: 'Database Security — SITA Command Center',
    subtitle: 'Overarching · Transversal DAM across all national & provincial databases, privileged access monitoring',
  },
  national: {
    title: 'Database Security — National Estate',
    subtitle: 'Strategic · Estate-wide DAM — anomaly patterns and database policy compliance',
  },
  dept: {
    title: 'Database Security — Department',
    subtitle: 'Tactical · Department DAM alerts, database session anomalies and violation categories',
  },
  branch: {
    title: 'Database Security — Branch',
    subtitle: 'Granular · Branch DB sessions, local database policies and active violations',
  },
};

export default function DbSecDashboard({ tier = 'dept' }: { tier?: TenancyTier }) {
  const cfg = TIER_CONFIG[tier];
  const [overlay, setOverlay] = useState<null | 'explain' | 'layman'>(null);
  const d = useDbSecData();
  const narrative = useNarrativeFacts();

  if (d.loading) {
    return <div className="dash"><DashHeader title={cfg.title} subtitle="Loading live data…" badge={{ label: 'db_sec', color: 'var(--green)', bg: 'var(--green-dim)' }} consolidatedTag="Imperva DAM · database audit" onExplain={() => {}} onLayman={() => {}} /><div className="dash-loading"><span className="spin" />Loading live data…</div></div>;
  }

  const facts: ExplainFacts = {
    violations: d.totalViolations,
    critical: d.criticalViolations,
    alerts: d.activeAlerts.length,
    coverage: d.coverage,
    monitored: d.monitored,
    dbTotal: d.dbTotal,
    topCat: d.categories[0]?.label,
    topCatCount: d.categories[0]?.value,
  };
  const narrativeInput = { facts, model: narrative.facts };

  return (
    <div className="dash">
      <DashHeader
        title={cfg.title}
        subtitle={cfg.subtitle}
        badge={{ label: 'db_sec', color: 'var(--green)', bg: 'var(--green-dim)' }}
        consolidatedTag="Imperva DAM · Thales DAM · Database Audit"
        onExplain={() => setOverlay('explain')}
        onLayman={() => setOverlay('layman')}
      />
      <div className="consol-note">
        <strong>✓ Consolidation:</strong>&nbsp;
        DB Security view consolidates <OemTag source="imperva" label="Imperva DAM" /> and <OemTag source="thales" label="Thales DAM" /> database activity across all relational and Cassandra clusters.
        Database-specific policy violations, privileged DDL/DML, and baseline deviations are unified here.
      </div>

      {d.error && <div className="dash-error">{d.error}</div>}

      <div className="stats-bar">
        <StatCard ghost={String(d.totalViolations)} accent="var(--amber)" value={String(d.totalViolations)} valueColor="var(--amber)" label={<><span>Total Violations </span><OemTag source="imperva" label="24h" /></>} delta="live" deltaColor="var(--text-muted)" />
        <StatCard ghost={String(d.criticalViolations)} accent="var(--red)" value={String(d.criticalViolations)} valueColor="var(--red)" label={<><span>Critical Violations </span><OemTag source="imperva" label="Sev 4" /></>} delta="live" deltaColor="var(--text-muted)" />
        <StatCard ghost={String(d.dbMonitored)} accent="var(--green)" value={String(d.dbMonitored)} valueColor="var(--green)" label={<><span>Databases Monitored </span><OemTag source="imperva" label="DAM inventory" /></>} delta="live" deltaColor="var(--text-muted)" />
        <StatCard ghost={`${d.dbCoverage}%`} accent="var(--green)" value={`${d.dbCoverage}%`} valueColor={d.dbCoverage >= 80 ? 'var(--green)' : 'var(--amber)'} label={<><span>Coverage </span><OemTag source="imperva" label="DAM agents" /></>} delta="monitored estate" deltaColor="var(--text-muted)" />
      </div>

      <div className="dash-grid cols-2">
        <Panel title={<><span>Violations by Application</span> <OemTag source="imperva" label="Imperva DAM" /></>} bodyClassName="scroll-x" bodyStyle={{ padding: 0 }}>
          <table>
            <thead><tr><th>Application</th><th>Engine</th><th>Critical</th><th>High</th><th>Medium</th><th>Low</th></tr></thead>
            <tbody>
              {d.dbRows.length ? d.dbRows.map((v) => (
                <tr key={v.db}>
                  <td><strong>{v.db}</strong></td>
                  <td>{v.engine}</td>
                  <td style={{ color: 'var(--red)', fontWeight: 700 }}>{v.crit}</td>
                  <td>{v.high}</td>
                  <td>{v.med}</td>
                  <td>{v.low}</td>
                </tr>
              )) : <tr><td colSpan={6}><div className="panel-empty">No violation findings yet.</div></td></tr>}
            </tbody>
          </table>
        </Panel>
        <Panel title={<><span>Violation Categories</span> <OemTag source="imperva" label="Imperva DAM" /></>}>
          {d.categories.length ? d.categories.map((c) => (
            <BarRow key={c.label} label={c.label} width={c.width} color={c.color} value={c.value} />
          )) : <div className="panel-empty">No violation categories yet.</div>}
        </Panel>
      </div>

      <div className="dash-grid cols-2-1">
        <Panel title={<><span>Alert Activity by Age</span> <OemTag source="imperva" label="Imperva DAM" /></>}>
          {d.timelineBars.some((b) => b.value !== '0') ? (
            d.timelineBars.map((b) => (
              <BarRow key={b.label} label={b.label} width={b.width} color="var(--blue)" value={b.value} />
            ))
          ) : (
            <div className="panel-empty">No alert activity yet.</div>
          )}
        </Panel>
        <Panel title="Top Applications by Alerts">
          {d.topByAlerts.length ? d.topByAlerts.map((a) => (
            <BarRow key={a.db} label={<code>{a.db}</code>} width={a.width} color={a.sev === 'critical' ? 'var(--red)' : a.sev === 'high' ? 'var(--amber)' : 'var(--blue)'} value={a.value} />
          )) : <div className="panel-empty">No alert activity yet.</div>}
        </Panel>
      </div>

      <Panel title={<><span>Active Database Alerts</span> <OemTag source="imperva" label="Imperva DAM" /></>} bodyClassName="scroll-x" bodyStyle={{ padding: 0 }}>
        <table>
          <thead><tr><th>Alert</th><th>Application</th><th>Severity</th><th>Rule</th><th>Fired</th><th>Status</th></tr></thead>
          <tbody>
            {d.activeAlerts.length ? d.activeAlerts.map((a) => (
              <tr key={a.alert}>
                <td><code>{a.alert}</code></td>
                <td>{a.db}</td>
                <td><Chip tone={a.sevTone}>{a.sev}</Chip></td>
                <td>{a.rule}</td>
                <td style={{ fontFamily: 'var(--mono)' }}>{a.fired}</td>
                <td><Chip tone={a.statusTone}>{a.status}</Chip></td>
              </tr>
            )) : <tr><td colSpan={6}><div className="panel-empty">No active database alerts.</div></td></tr>}
          </tbody>
        </table>
      </Panel>

      <ExplainOverlay
        open={overlay !== null}
        title={`${ROLE_LABELS.dbsec} — ${overlay === 'layman' ? "Layman's Guide" : 'How This Dashboard Is Built'}`}
        body={overlay === 'layman' ? buildLayman('dbsec', narrativeInput) : buildExplain('dbsec', narrativeInput)}
        onClose={() => setOverlay(null)}
      />
    </div>
  );
}
