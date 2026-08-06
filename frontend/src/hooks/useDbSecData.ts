import { useApi } from './useApi';
import { fetchFindings } from '../api/findings';
import { fetchAlerts } from '../api/alerts';
import { fetchDbInventory } from '../api/metrics';
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
  const findings = useApi(() => fetchFindings({ size: 200 }));
  const alerts = useApi(() => fetchAlerts({ size: 50 }));
  const inventory = useApi(() => fetchDbInventory());

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

  const timelineBars = alertItems.slice(0, 24).map((a, i) => ({
    height: `${Math.max(10, (24 - i) * 4)}%`,
    color: a.severity === 'critical' ? 'var(--red-dim)' : a.severity === 'high' ? 'var(--amber-dim)' : 'var(--blue-dim)',
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
    activeAlerts,
    dbMonitored: monitored,
    dbCoverage: coverage,
    formatIsoDate,
  };
}
