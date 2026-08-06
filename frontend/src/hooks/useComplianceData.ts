import { useApi } from './useApi';
import { fetchCompliance, fetchGaps, fetchEvidence } from '../api/compliance';
import { fetchComplianceTrend, fetchRegulatoryCalendar } from '../api/metrics';
import {
  toneForSeverity,
  toneForStatus,
  gapStatusCounts,
} from '../data/mappers';
import type { Tone } from '../data/mappers';

export function useComplianceData() {
  const popia = useApi(() => fetchCompliance('popia'));
  const iso = useApi(() => fetchCompliance('iso_27001'));
  const gaps = useApi(() => fetchGaps({ sort_by: 'due_date' }));
  const evidence = useApi(() => fetchEvidence());
  const trend = useApi(() => fetchComplianceTrend());
  const calendar = useApi(() => fetchRegulatoryCalendar());

  const loading = [popia, iso, gaps, evidence, trend, calendar].some((h) => h.loading);
  const error = [popia, iso, gaps, evidence, trend, calendar].find((h) => h.error)?.error || null;

  const gapItems = gaps.data?.items || [];

  const today = new Date().toISOString().slice(0, 10);
  const openGaps = gapItems.filter((g) => g.status !== 'closed' && g.status !== 'remediated');
  const overdue = gapItems.filter((g) => g.due_date && g.due_date < today && g.status !== 'closed' && g.status !== 'remediated');

  const statusCounts = gapStatusCounts(gapItems);
  const auditStatus = [
    { label: 'Open', width: barWidth(statusCounts.open || 0, gapItems.length), color: 'var(--red)', value: String(statusCounts.open || 0) },
    { label: 'In Progress', width: barWidth(statusCounts.in_progress || 0, gapItems.length), color: 'var(--amber)', value: String(statusCounts.in_progress || 0) },
    { label: 'Remediated', width: barWidth(statusCounts.remediated || 0, gapItems.length), color: 'var(--blue)', value: String(statusCounts.remediated || 0) },
    { label: 'Closed', width: barWidth(statusCounts.closed || 0, gapItems.length), color: 'var(--green)', value: String(statusCounts.closed || 0) },
  ];

  const byDomain = new Map<string, { domain: string; score: string; status: string; statusTone: Tone; gap: string; target: string }>();
  for (const g of gapItems) {
    const domain = g.domain || g.framework || 'General';
    if (!byDomain.has(domain)) {
      byDomain.set(domain, { domain, score: '—', status: 'needs work', statusTone: 'half', gap: '—', target: '100%' });
    }
  }
  const popiaByDomain = [...byDomain.values()];

  const auditFindings = gapItems.slice(0, 20).map((g) => ({
    finding: g.description,
    framework: g.control_id || g.framework,
    owner: g.owner || '—',
    sev: g.severity,
    sevTone: toneForSeverity(g.severity) as Tone,
    due: g.due_date || '—',
    dueColor: g.due_date && g.due_date < today ? 'var(--red)' : 'var(--amber)',
    status: g.status,
    statusTone: toneForStatus(g.status),
  }));

  const trendItems = trend.data?.items || [];
  const popiaTrend = trendItems.filter((t) => t.framework === 'popia');
  const isoTrend = trendItems.filter((t) => t.framework === 'iso_27001');
  const maxScore = 100;
  const trendBars: { height: string; color: string }[] = [];
  const trendDates = Array.from(new Set(trendItems.map((t) => t.snapshot_date))).sort();
  for (const date of trendDates) {
    const p = popiaTrend.find((t) => t.snapshot_date === date);
    const i = isoTrend.find((t) => t.snapshot_date === date);
    if (p) trendBars.push({ height: `${Math.round((p.overall_score / maxScore) * 100)}%`, color: 'var(--green)' });
    if (i) trendBars.push({ height: `${Math.round((i.overall_score / maxScore) * 100)}%`, color: 'var(--amber)' });
  }

  const calendarItems = (calendar.data?.items || []).map((c) => ({
    id: c.id,
    control: c.control_id,
    framework: c.framework,
    description: c.description,
    owner: c.owner || '—',
    due: c.due_date || '—',
    overdue: !!c.due_date && c.due_date < today,
    severity: c.severity,
    sevTone: toneForSeverity(c.severity) as Tone,
  }));

  return {
    loading,
    error,
    hasData: gapItems.length > 0 || popia.data?.overall_score != null || iso.data?.overall_score != null,
    popiaScore: popia.data?.overall_score ?? null,
    isoScore: iso.data?.overall_score ?? null,
    openItems: openGaps.length,
    overdue: overdue.length,
    popiaByDomain,
    auditStatus,
    auditFindings,
    evidence: evidence.data,
    trendBars,
    calendarItems,
  };
}

function barWidth(count: number, total: number): string {
  return `${Math.max(4, Math.round((count / Math.max(1, total)) * 100))}%`;
}
