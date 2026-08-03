import { useApi } from './useApi';
import { fetchAlerts, acknowledgeAlert, resolveAlert } from '../api/alerts';
import { fetchFindings } from '../api/findings';
import { fetchDashboardSummary } from '../api/dashboard';
import {
  toneForSeverity,
  toneForStatus,
  oemForSource,
  formatIsoDateTime,
  formatIsoDate,
  sevLabel,
  groupAlertsByRule,
} from '../data/mappers';
import type { Tone } from '../data/mappers';

export function useSocData() {
  const summary = useApi(() => fetchDashboardSummary());
  const alerts = useApi(() => fetchAlerts({ size: 50 }));
  const findings = useApi(() => fetchFindings({ size: 200 }));

  const loading = [summary, alerts, findings].some((h) => h.loading);
  const error = [summary, alerts, findings].find((h) => h.error)?.error || null;

  const alertItems = alerts.data?.items || [];
  const findingsItems = findings.data?.items || [];

  const timeline = alertItems.map((a) => {
    const [src, srcLabel] = oemForSource(a.source);
    return {
      sev: a.severity === 'critical' ? 'tl-severe' : a.severity === 'high' ? 'tl-high' : 'tl-med',
      time: formatIsoDateTime(a.last_triggered),
      src,
      srcLabel,
      title: `${a.rule_id} — ${a.target_id || a.title}`,
      desc: a.description || a.title,
    };
  });

  const queue = alertItems
    .filter((a) => a.status !== 'resolved' && a.status !== 'closed')
    .map((a) => {
      const [src, srcLabel] = oemForSource(a.source);
      return {
        id: a.id,
        rule: a.rule_id,
        src,
        srcLabel,
        sev: a.severity,
        sevTone: toneForSeverity(a.severity) as Tone,
        fired: formatIsoDateTime(a.last_triggered),
        status: a.status,
        statusTone: toneForStatus(a.status),
        acknowledged: a.status === 'acknowledged',
      };
    });

  const findingsRows = findingsItems.map((f) => {
    const [src, srcLabel] = oemForSource(f.source);
    return {
      src,
      srcLabel,
      sev: sevLabel(f.severity),
      sevTone: toneForSeverity(f.severity) as Tone,
      app: f.app_name,
      title: f.title,
      status: f.status,
      statusTone: toneForStatus(f.status),
      first: formatIsoDate(f.first_seen),
    };
  });

  const grouped = groupAlertsByRule(alertItems);
  const topRules = grouped
    .map(([rule, items]) => ({
      rule,
      count: items.length,
      sev: items[0].severity,
      sevTone: toneForSeverity(items[0].severity) as Tone,
      src: items[0].source || 'fusion',
      srcLabel: oemForSource(items[0].source || 'fusion')[1],
      status: items[0].status,
      statusTone: toneForStatus(items[0].status),
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6);

  return {
    loading,
    error,
    hasData: alertItems.length > 0 || findingsItems.length > 0,
    activeIncidents: summary.data?.active_alerts ?? alertItems.filter((a) => a.status === 'new').length,
    alertTotal: alerts.data?.total ?? alertItems.length,
    findingsTotal: findings.data?.total ?? findingsItems.length,
    timeline,
    queue,
    findings: findingsRows,
    topRules,
    refresh: () => {
      summary.refresh();
      alerts.refresh();
      findings.refresh();
    },
    acknowledge: async (id: string) => {
      await acknowledgeAlert(id);
      alerts.refresh();
    },
    resolve: async (id: string) => {
      await resolveAlert(id);
      alerts.refresh();
    },
  };
}
