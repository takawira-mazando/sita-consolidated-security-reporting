import { useApi } from './useApi';
import { fetchConnectors } from '../api/admin';
import { fetchAgents, fetchSystemMetrics } from '../api/metrics';
import {
  oemForSource,
  barHeight,
} from '../data/mappers';
import type { Tone } from '../data/mappers';

const METRIC_LABELS: Record<string, string> = {
  cpu: 'CPU',
  memory: 'Memory',
  disk_io: 'Disk I/O',
  queue_depth: 'Queue Depth',
};

function toneForValue(value: number): string {
  return value >= 80 ? 'var(--red)' : value >= 60 ? 'var(--amber)' : 'var(--green)';
}

export function useSreData() {
  const connectors = useApi(() => fetchConnectors());
  const system = useApi(() => fetchSystemMetrics());
  const agents = useApi(() => fetchAgents());

  const loading = [connectors, system, agents].some((h) => h.loading);
  const error = [connectors, system, agents].find((h) => h.error)?.error || null;

  const items = connectors.data?.items || [];

  const healthy = items.filter((c) => c.status === 'healthy' || c.status === 'ok').length;
  const degraded = items.filter((c) => c.status === 'degraded' || c.status === 'warning').length;
  const total = items.length;

  const rows = items.map((c) => {
    const [src, srcLabel] = oemForSource(c.source);
    const events = c.events_per_hour != null ? c.events_per_hour.toLocaleString() : '—';
    const latency = c.latency_ms != null ? `${(c.latency_ms / 1000).toFixed(1)} s` : '—';
    return {
      name: c.name,
      src,
      srcLabel,
      status: c.status,
      statusTone: (c.status === 'degraded' || c.status === 'warning' ? 'half' : c.status === 'healthy' || c.status === 'ok' ? 'ok' : 'high') as Tone,
      latency,
      events,
      errorCount: c.error_count,
      circuit: c.circuit_state,
    };
  });

  const eventsTotal = items.reduce((a, c) => a + (c.events_per_hour || 0), 0);

  const eventBars = items.slice(0, 7).map((c, i) => {
    const ratio = (c.events_per_hour || 0) / Math.max(1, items.reduce((a, x) => Math.max(a, x.events_per_hour || 0), 0));
    return {
      height: barHeight(ratio),
      color: i === items.slice(0, 7).length - 1 ? 'var(--blue)' : 'var(--blue-dim)',
    };
  });

  const errorTotal = items.reduce((a, c) => a + (c.error_count || 0), 0);
  const errorRate = eventsTotal > 0 ? ((errorTotal / eventsTotal) * 100).toFixed(1) : '—';

  const sysMap = new Map((system.data?.items || []).map((m) => [m.metric, m.value]));
  const systemHealth = (['cpu', 'memory', 'disk_io', 'queue_depth'] as const).map((key) => {
    const raw = sysMap.get(key);
    const label = METRIC_LABELS[key] || key;
    if (raw == null) {
      return { label, width: '0%', color: 'var(--green)', value: '—' };
    }
    return { label, width: `${Math.min(100, raw)}%`, color: toneForValue(raw), value: `${raw}%` };
  });

  const uptime = system.data?.uptime != null ? `${system.data.uptime}%` : '—';

  const agentItems = agents.data?.items || [];
  const damRole = agents.data?.by_role.find((r) => r.role === 'dam');
  const damAgents = damRole?.count ?? null;
  const agentTotal = agents.data?.total ?? agentItems.length;
  const agentOnline = agents.data?.online ?? 0;
  const agentDegraded = agents.data?.degraded ?? 0;

  const maxVersion = Math.max(1, ...(agents.data?.versions || []).map((v) => v.count));
  const agentVersions = (agents.data?.versions || []).map((v) => ({
    label: v.version,
    width: `${Math.round((v.count / maxVersion) * 100)}%`,
    color: 'var(--blue)',
    value: String(v.count),
  }));

  return {
    loading,
    error,
    hasData: items.length > 0,
    rows,
    healthy,
    degraded,
    total,
    eventsTotal,
    eventBars,
    errorRate,
    systemHealth,
    uptime,
    damAgents,
    agentTotal,
    agentOnline,
    agentDegraded,
    agentVersions,
    refresh: () => {
      connectors.refresh();
      system.refresh();
      agents.refresh();
    },
  };
}
