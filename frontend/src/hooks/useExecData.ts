import { useApi } from './useApi';
import { fetchDashboardSummary } from '../api/dashboard';
import { fetchFindings } from '../api/findings';
import { fetchRisks } from '../api/risks';
import { fetchCompliance } from '../api/compliance';
import { fetchAlerts } from '../api/alerts';
import {
  severityCounts,
  findingsByAppSeverity,
  latestRiskPerApp,
  riskTrendSeries,
  groupAlertsByRule,
  toneForSeverity,
  toneForStatus,
  oemForSource,
  barHeight,
} from '../data/mappers';
import type { Tone } from '../data/mappers';

export function useExecData() {
  const summary = useApi(() => fetchDashboardSummary());
  const findings = useApi(() => fetchFindings({ size: 200 }));
  const risks = useApi(() => fetchRisks({ size: 100 }));
  const popia = useApi(() => fetchCompliance('popia'));
  const iso = useApi(() => fetchCompliance('iso_27001'));
  const alerts = useApi(() => fetchAlerts({ size: 50 }));

  const loading = [summary, findings, risks, popia, iso, alerts].some((h) => h.loading);
  const error = [summary, findings, risks, popia, iso, alerts].find((h) => h.error)?.error || null;

  const findingsItems = findings.data?.items || [];
  const risksItems = risks.data?.items || [];
  const counts = severityCounts(findingsItems);
  const appRows = findingsByAppSeverity(findingsItems);
  const topRisks = latestRiskPerApp(risksItems).slice(0, 5);
  const series = riskTrendSeries(risksItems, 30);

  const trendBars = series.map((s, i) => {
    const isLast = i === series.length - 1;
    let color = 'var(--blue-dim)';
    if (s.fused_score >= 70) color = 'var(--red-dim)';
    else if (s.fused_score >= 45) color = 'var(--amber-dim)';
    else if (s.fused_score >= 25) color = 'var(--green-dim)';
    if (isLast) {
      if (s.fused_score >= 70) color = 'var(--red)';
      else if (s.fused_score >= 45) color = 'var(--amber)';
      else if (s.fused_score >= 25) color = 'var(--green)';
      else color = 'var(--blue)';
    }
    return { height: barHeight(s.fused_score / 100), color };
  });

  const heatmapRows = appRows.slice(0, 8).map((r) => ({
    app: r.app,
    cells: [
      [String(r.critical), heatClass(r.critical)] as [string, string],
      [String(r.high), heatClass(r.high)] as [string, string],
      [String(r.medium), heatClass(r.medium)] as [string, string],
      [String(r.low), heatClass(r.low)] as [string, string],
    ],
  }));

  const donutTotal = Math.max(
    1,
    counts.critical + counts.high + counts.medium + counts.low + counts.info
  );
  const pct = (n: number) => (n / donutTotal) * 360;
  let acc = 0;
  const segs = [
    { n: counts.critical, color: 'var(--red)' },
    { n: counts.high, color: 'var(--amber)' },
    { n: counts.medium, color: 'var(--blue)' },
    { n: counts.low + counts.info, color: 'var(--text-muted)' },
  ];
  const donutCss = segs
    .filter((s) => s.n > 0)
    .map((s) => {
      const start = acc;
      const end = acc + pct(s.n);
      acc = end;
      return `${s.color} ${start}deg ${end}deg`;
    })
    .join(',');
  const donutLegend = [
    { label: `Critical — ${counts.critical}`, color: 'var(--red)' },
    { label: `High — ${counts.high}`, color: 'var(--amber)' },
    { label: `Medium — ${counts.medium}`, color: 'var(--blue)' },
    { label: `Low — ${counts.low + counts.info}`, color: 'var(--text-muted)' },
  ];

  const alertSummary = groupAlertsByRule(alerts.data?.items || []).slice(0, 8).map(([rule, items]) => {
    const first = items[0];
    const sev = first.severity;
    return {
      rule,
      app: first.target_id || '—',
      severity: sev,
      sevTone: toneForSeverity(sev) as Tone,
      src: first.source || 'fusion',
      srcLabel: oemForSource(first.source || 'fusion')[1],
      count: String(items.length),
      status: first.status,
      statusTone: toneForStatus(first.status),
    };
  });

  return {
    loading,
    error,
    hasData: findingsItems.length > 0 || risksItems.length > 0 || (alerts.data?.items || []).length > 0,
    summary: summary.data,
    findingsTotal: findings.data?.total ?? findingsItems.length,
    activeAlerts: summary.data?.active_alerts ?? alerts.data?.items?.length ?? 0,
    popiaScore: popia.data?.overall_score ?? null,
    isoScore: iso.data?.overall_score ?? null,
    counts,
    appRows,
    topRisks,
    trendBars,
    heatmapRows,
    donutCss,
    donutLegend,
    alertSummary,
  };
}

function heatClass(n: number): string {
  if (n <= 0) return 'hm-0';
  if (n < 5) return 'hm-1';
  if (n < 10) return 'hm-2';
  if (n < 20) return 'hm-3';
  return 'hm-4';
}
