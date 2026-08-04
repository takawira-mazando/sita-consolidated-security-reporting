import { useApi } from './useApi';
import { fetchConnectors } from '../api/admin';
import {
  oemForSource,
  barHeight,
} from '../data/mappers';
import type { Tone } from '../data/mappers';

export function useSreData() {
  const connectors = useApi(() => fetchConnectors());

  const loading = connectors.loading;
  const error = connectors.error;

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

  const systemHealth = [
    { label: 'CPU', width: '—', color: 'var(--green)', value: '—' },
    { label: 'Memory', width: '—', color: 'var(--blue)', value: '—' },
    { label: 'Disk I/O', width: '—', color: 'var(--green)', value: '—' },
    { label: 'Queue Depth', width: '—', color: 'var(--green)', value: '—' },
  ];

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
    refresh: connectors.refresh,
  };
}
