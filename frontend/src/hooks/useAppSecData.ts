import { useApi } from './useApi';
import { fetchFindings } from '../api/findings';
import {
  severityCounts,
  findingsByAppSeverity,
  toneForSeverity,
  oemForSource,
  formatIsoDate,
  barHeight,
} from '../data/mappers';
import type { Tone } from '../data/mappers';

export function useAppSecData() {
  const findings = useApi(() => fetchFindings({ size: 200 }));

  const loading = findings.loading;
  const error = findings.error;

  const findingsItems = findings.data?.items || [];
  const counts = severityCounts(findingsItems);
  const appRows = findingsByAppSeverity(findingsItems);

  const vulnByApp = appRows.slice(0, 10).map((r) => ({
    app: r.app,
    crit: String(r.critical),
    high: String(r.high),
    med: String(r.medium),
    low: String(r.low),
    trend: 'live',
    trendColor: 'var(--text-muted)',
  }));

  const byCategory = new Map<string, number>();
  for (const f of findingsItems) {
    const key = f.category || 'other';
    byCategory.set(key, (byCategory.get(key) || 0) + 1);
  }
  const owasp = [...byCategory.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([label, value]) => ({
      label: label.replace(/_/g, ' '),
      width: barHeight(value / Math.max(1, [...byCategory.values()].reduce((a, b) => Math.max(a, b), 0))),
      color: value >= 100 ? 'var(--red)' : value >= 50 ? 'var(--amber)' : 'var(--blue)',
      value: String(value),
    }));

  const criticals = findingsItems
    .filter((f) => f.severity.toLowerCase() === 'critical')
    .slice(0, 8)
    .map((f) => ({
      cve: f.external_id || f.title,
      cvss: '—',
      cvssTone: 'severe' as Tone,
      app: f.app_name,
      comp: f.category || '—',
      discovered: formatIsoDate(f.first_seen),
      title: f.title,
    }));

  const catColor = (sev: string) =>
    sev === 'critical' ? 'var(--red)' : sev === 'high' ? 'var(--amber)' : 'var(--blue)';

  return {
    loading,
    error,
    hasData: findingsItems.length > 0,
    findingsTotal: findings.data?.total ?? findingsItems.length,
    counts,
    vulnByApp,
    owasp,
    criticals,
    catColor,
    toneForSeverity,
    oemForSource,
  };
}
