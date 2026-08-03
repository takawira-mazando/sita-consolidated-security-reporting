import { Finding, Alert, RiskScore, ComplianceGap } from '../types';

export type Tone = 'severe' | 'high' | 'med' | 'ok' | 'closed' | 'open' | 'half';

export const SEVERITY_TONE: Record<string, Tone> = {
  critical: 'severe',
  high: 'high',
  medium: 'med',
  low: 'ok',
  info: 'ok',
};

export const SEVERITY_COLOR: Record<string, string> = {
  critical: 'var(--red)',
  high: 'var(--amber)',
  medium: 'var(--blue)',
  low: 'var(--green)',
  info: 'var(--text-muted)',
};

export const BUCKET_TONE: Record<string, Tone> = {
  critical: 'severe',
  monitored: 'high',
  elevated: 'med',
  safe: 'ok',
};

export const BUCKET_COLOR: Record<string, string> = {
  critical: 'var(--red)',
  monitored: 'var(--amber)',
  elevated: 'var(--blue)',
  safe: 'var(--green)',
};

export const STATUS_TONE: Record<string, Tone> = {
  open: 'open',
  new: 'open',
  acknowledged: 'closed',
  ack: 'closed',
  resolved: 'closed',
  closed: 'closed',
  investigating: 'half',
  in_review: 'half',
  triaging: 'half',
  in_progress: 'half',
};

export function toneForSeverity(sev: string): Tone {
  return SEVERITY_TONE[sev.toLowerCase()] || 'med';
}

export function colorForSeverity(sev: string): string {
  return SEVERITY_COLOR[sev.toLowerCase()] || 'var(--text-muted)';
}

export function toneForBucket(bucket: string): Tone {
  return BUCKET_TONE[bucket.toLowerCase()] || 'med';
}

export function colorForBucket(bucket: string): string {
  return BUCKET_COLOR[bucket.toLowerCase()] || 'var(--text-muted)';
}

export function toneForStatus(status: string): Tone {
  return STATUS_TONE[status.toLowerCase()] || 'half';
}

export function oemForSource(source?: string | null): [string, string] {
  const s = (source || '').toLowerCase();
  if (s.includes('imperva') && s.includes('waf')) return ['imperva-waf', 'Imperva WAF'];
  if (s.includes('imperva')) return ['imperva', 'Imperva DAM'];
  if (s.includes('api')) return ['api-sec', 'API Security'];
  if (s.includes('compliance')) return ['compliance', 'internal'];
  if (s === 'fusion') return ['appscan', 'fusion'];
  if (s === 'internal') return ['compliance', 'internal'];
  if (s.includes('ingestion')) return ['appscan', 'ingestion'];
  return ['appscan', 'AppScan'];
}

export function sevLabel(sev: string): string {
  const map: Record<string, string> = {
    critical: 'Sev 4',
    high: 'Sev 3',
    medium: 'Sev 2',
    low: 'Sev 1',
    info: 'Info',
  };
  return map[sev.toLowerCase()] || sev;
}

export function formatIsoTime(iso?: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' });
}

export function formatIsoDateTime(iso?: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString('en-ZA', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

export function formatIsoDate(iso?: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toISOString().slice(0, 10);
}

export function barHeight(ratio: number): string {
  return `${Math.max(6, Math.min(100, Math.round(ratio * 100)))}%`;
}

export function severityCounts(findings: Finding[]) {
  const counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
  for (const f of findings) {
    const key = f.severity.toLowerCase() as keyof typeof counts;
    if (key in counts) counts[key] += 1;
    else counts.info += 1;
  }
  return counts;
}

export function findingsByAppSeverity(findings: Finding[]) {
  const map = new Map<string, { critical: number; high: number; medium: number; low: number }>();
  for (const f of findings) {
    if (!map.has(f.app_name)) {
      map.set(f.app_name, { critical: 0, high: 0, medium: 0, low: 0 });
    }
    const row = map.get(f.app_name)!;
    const sev = f.severity.toLowerCase();
    if (sev === 'critical') row.critical += 1;
    else if (sev === 'high') row.high += 1;
    else if (sev === 'medium') row.medium += 1;
    else if (sev === 'low') row.low += 1;
  }
  return [...map.entries()].map(([app, c]) => ({ app, ...c }));
}

export function latestRiskPerApp(risks: RiskScore[]) {
  const map = new Map<string, RiskScore>();
  for (const r of risks) {
    const prev = map.get(r.app_name);
    if (!prev || r.score_date > prev.score_date) map.set(r.app_name, r);
  }
  return [...map.values()].sort((a, b) => b.fused_score - a.fused_score);
}

export function riskTrendSeries(risks: RiskScore[], days = 30): RiskScore[] {
  const series: RiskScore[] = [];
  const byDate = new Map<string, number[]>();
  for (const r of risks) {
    const d = r.score_date;
    if (!byDate.has(d)) byDate.set(d, []);
    byDate.get(d)!.push(r.fused_score);
  }
  const dates = [...byDate.keys()].sort().slice(-days);
  for (const d of dates) {
    const vals = byDate.get(d)!;
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
    series.push({
      app_name: '',
      score_date: d,
      fused_score: Math.round(avg * 10) / 10,
      bucket: '',
      computed_at: '',
    });
  }
  return series;
}

export function gapStatusCounts(gaps: ComplianceGap[]) {
  const counts: Record<string, number> = {};
  for (const g of gaps) {
    counts[g.status] = (counts[g.status] || 0) + 1;
  }
  return counts;
}

export function groupAlertsByRule(alerts: Alert[]) {
  const map = new Map<string, Alert[]>();
  for (const a of alerts) {
    const key = a.rule_id || a.title;
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(a);
  }
  return [...map.entries()];
}
