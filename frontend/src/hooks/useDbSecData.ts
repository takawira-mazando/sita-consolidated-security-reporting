import { useApi } from './useApi';
import { useDemoAwareFetcher } from '../api/demoApi';
import { fetchFindings } from '../api/findings';
import { fetchAlerts } from '../api/alerts';
import { fetchDbInventory } from '../api/metrics';
import { fetchDemoFindings } from '../api/demoApi';
import {
  severityCounts,
  toneForSeverity,
  toneForStatus,
  oemForSource,
  formatIsoDateTime,
  formatIsoDate,
  barHeight,
} from '../data/mappers';
import type { Tone } from '../data/mappers';

export function useDbSecData() {
  const findings = useApi(useDemoAwareFetcher(
    () => fetchFindings({ size: 200 }),
    (branchId) => fetchDemoFindings({ size: 200, branch_id: branchId })
  ));
  const alerts = useApi(() => fetchAlerts({ size: 50 })); // No demo alerts
  const inventory = useApi(() => fetchDbInventory()); // No demo inventory

  const loading = findings.loading || alerts.loading || inventory.loading;
  const error = findings.error || alerts.error || inventory.error;

  const findingsItems = findings.data?.items || [];
  const alertItems = alerts.data?.items || [];

  const engineByDb = new Map(
    (inventory.data?.items || []).map((d) => [d.name, d.engine || '—'])
  );

  const violationsByDb = new Map<string, { db: string; engine: string; crit: number; high: number; med: number; low: number }>();
  for (const f of findingsItems) {
    if (!violationsByDb.has(f.app_name)) {
      violationsByDb.set(f.app_name, { db: f.app_name, engine: engineByDb.get(f.app_name) || '—', crit: 0, high: 0, med: 0, low: 0 });
    }
    const row = violationsByDb.get(f.app_name)!;
    const sev = f.severity.toLowerCase();
    if (sev === 'critical') row.crit += 1;
    else if (sev === 'high') row.high += 1;
    else if (sev === 'medium') row.med += 1;
    else if (sev === 'low') row.low += 1;
  }
  const dbRows = [...violationsByDb.values()].sort((a, b) => b.crit + b.high - (a.crit + a.high));

  const counts = severityCounts(findingsItems);
  const monitored = inventory.data?.monitored ?? 0;
  const coverage = inventory.data?.coverage_pct ?? 0;

  const byCategory = new Map<string, number>();
  for (const f of findingsItems) {
    const key = f.category || 'other';
    byCategory.set(key, (byCategory.get(key) || 0) + 1);
  }
  const categories = [...byCategory.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([label, value]) => ({
      label: label.replace(/_/g, ' '),
      width: barHeight(value / Math.max(1, [...byCategory.values()].reduce((a, b) => Math.max(a, b), 0))),
      color: value >= 20 ? 'var(--red)' : value >= 10 ? 'var(--amber)' : 'var(--blue)',
      value: String(value),
    }));

  const activeAlerts = alertItems.map((a) => {
    const [src, srcLabel] = oemForSource(a.source);
    return {
      alert: a.id,
      db: a.target_id || a.title,
      sev: a.severity,
      sevTone: toneForSeverity(a.severity) as Tone,
      rule: a.rule_id,
      fired: formatIsoDateTime(a.last_triggered),
      status: a.status,
      statusTone: toneForStatus(a.status),
      src,
      srcLabel,
    };
  });

  // Alert volume by age, computed from `first_triggered`. The previous bar
  // heights were a function of array position rather than any measurement,
  // which made the panel decorative and made the narrative describing it a lie.
  const nowMs = Date.now();
  const ageHours = (iso: string) => (nowMs - new Date(iso).getTime()) / 3_600_000;
  const AGE_BUCKETS = [
    { label: '0–6h', min: 0, max: 6 },
    { label: '6–24h', min: 6, max: 24 },
    { label: '1–3d', min: 24, max: 72 },
    { label: '3d+', min: 72, max: Infinity },
  ];
  const ageMax = Math.max(
    1,
    ...AGE_BUCKETS.map(
      (b) => alertItems.filter((a) => {
        const h = ageHours(a.first_triggered);
        return Number.isFinite(h) && h >= b.min && h < b.max;
      }).length
    )
  );
  const timelineBars = AGE_BUCKETS.map((b) => {
    const n = alertItems.filter((a) => {
      const h = ageHours(a.first_triggered);
      return Number.isFinite(h) && h >= b.min && h < b.max;
    }).length;
    return { label: b.label, value: String(n), width: barHeight(n / ageMax) };
  });

  // Alert count per target application, proportional to the observed maximum.
  const alertsPerTarget = new Map<string, number>();
  for (const a of alertItems) {
    const key = a.target_id || a.title;
    alertsPerTarget.set(key, (alertsPerTarget.get(key) || 0) + 1);
  }
  const topByAlerts = [...alertsPerTarget.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([db, n]) => ({
      db,
      sev: alertItems.find((a) => (a.target_id || a.title) === db)?.severity || 'info',
      value: String(n),
      width: barHeight(n / Math.max(1, ...alertsPerTarget.values())),
    }));

  return {
    loading,
    error,
    hasData: findingsItems.length > 0 || alertItems.length > 0,
    dbRows,
    totalViolations: findingsItems.length,
    criticalViolations: counts.critical,
    categories,
    timelineBars,
    topByAlerts,
    activeAlerts,
    monitored,
    dbTotal: inventory.data?.total ?? 0,
    coverage,
    dbMonitored: monitored,
    dbCoverage: coverage,
    formatIsoDate,
  };
}
