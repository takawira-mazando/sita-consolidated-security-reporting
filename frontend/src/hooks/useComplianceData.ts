import { useApi } from './useApi';
import { fetchCompliance, fetchGaps, fetchEvidence } from '../api/compliance';
import {
  toneForSeverity,
  toneForStatus,
  gapStatusCounts,
  barHeight,
} from '../data/mappers';
import type { Tone } from '../data/mappers';

export function useComplianceData() {
  const popia = useApi(() => fetchCompliance('popia'));
  const iso = useApi(() => fetchCompliance('iso_27001'));
  const gaps = useApi(() => fetchGaps({ sort_by: 'due_date' }));
  const evidence = useApi(() => fetchEvidence());

  const loading = [popia, iso, gaps, evidence].some((h) => h.loading);
  const error = [popia, iso, gaps, evidence].find((h) => h.error)?.error || null;

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
  };
}

function barWidth(count: number, total: number): string {
  return `${Math.max(4, Math.round((count / Math.max(1, total)) * 100))}%`;
}
