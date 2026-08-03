export const ROLE_LABELS: Record<string, string> = {
  exec: 'Executive',
  soc: 'SOC Analyst',
  appsec: 'AppSec',
  dbsec: 'DB Security',
  compliance: 'Compliance',
  sre: 'Service Ops',
};

export type ExplainFacts = Record<string, string | number | null | undefined>;

function fmt(n: string | number | null | undefined, suffix = ''): string {
  if (n === undefined || n === null || n === '') return '—';
  return `${n}${suffix}`;
}

function count(n: string | number | null | undefined): string {
  if (n === undefined || n === null || n === '') return '—';
  return Number(n).toLocaleString();
}

export function buildExplain(role: string, f: ExplainFacts): string {
  switch (role) {
    case 'exec':
      return `<h3>Executive Risk Dashboard &mdash; Consolidation Logic</h3>
<ul>
  <li><strong>Fused Risk Score (${fmt(f.fusedRisk)}):</strong> Weighted composite of AppScan severity (40%), Imperva violation volume (30%), API exposure (20%), and compliance maturity (10%). Each factor normalized 0&ndash;100 before weighting. Computed from the live risk-scoring pipeline.</li>
  <li><strong>Open Findings (${count(f.findings)}):</strong> All AppScan findings across 5 applications. Critical &amp; high severity findings are flagged for immediate remediation.</li>
  <li><strong>POPIA Compliance (${fmt(f.popia, '%')}):</strong> Aggregated from the compliance snapshots stored in the warehouse &mdash; data inventory, consent management, breach response, data subject rights, and cross-border transfer.</li>
  <li><strong>Active Alerts (${count(f.alerts)}):</strong> Alert rules evaluated against the fused data stream &mdash; includes fusion-specific rules (e.g., fused_score &gt; 71) and OEM-specific rules from each source.</li>
  <li><strong>Heatmap:</strong> AppScan findings &times; severity per application. Color intensity reflects finding count (4 levels). ${f.topApp ? `<strong>${f.topApp}</strong> currently leads the critical bucket.` : ''}</li>
  <li><strong>Top 5 by Fused Risk:</strong> Each application scored using the same weight model as the enterprise score. ${f.topApp ? `${f.topApp} leads at ${fmt(f.topAppScore)}.` : ''}</li>
</ul>
<p><em>This view does not exist in any OEM console &mdash; it is generated entirely by the consolidation pipeline.</em></p>`;

    case 'soc':
      return `<h3>SOC Analyst Dashboard &mdash; Consolidation Logic</h3>
<ul>
  <li><strong>Active Incidents (${count(f.incidents)}):</strong> Aggregated from AppScan findings (critical severities), Imperva DAM violations (sev 4), Imperva WAF blocks, and API Security shadow API detections. Deduplicated by normalized alert signature.</li>
  <li><strong>MTTD &amp; MTTR:</strong> Mean time to detect and resolve across all incident sources. Not tracked by the backend yet &mdash; will be calculated from the unified alert timeline.</li>
  <li><strong>Alert Backlog (${count(f.backlog)}):</strong> Unacknowledged alerts across all OEMs &mdash; includes findings, violations, WAF blocks, and shadow API detections.</li>
  <li><strong>Unified Timeline:</strong> Single chronological feed merging AppScan, Imperva, and API Security alerts. Each entry tagged with OEM source.</li>
  <li><strong>Alert Queue:</strong> Full list of unacknowledged alerts with source attribution. Acknowledge/investigate actions available per alert.</li>
</ul>
<p><em>No OEM provides a cross-source alert timeline &mdash; this is a fusion-only feature.</em></p>`;

    case 'appsec':
      return `<h3>Application Security Dashboard &mdash; Consolidation Logic</h3>
<ul>
  <li><strong>Total Findings (${count(f.findings)}):</strong> All AppScan vulnerabilities across 5 applications (legacy-api, payment-gateway, customer-portal, document-svc, internal-hr).</li>
  <li><strong>Critical (${count(f.critical)}):</strong> Severity-critical findings awaiting remediation.</li>
  <li><strong>Fix Rate / WAF Blocks:</strong> Not tracked by the backend yet &mdash; shown once a remediation and WAF telemetry feed is available.</li>
  <li><strong>API Exposure:</strong> API Security findings for risky endpoints. Shadow APIs flagged for immediate investigation.</li>
  <li><strong>OWASP Top 10:</strong> AppScan findings mapped to OWASP categories. ${f.topCat ? `<strong>${f.topCat}</strong> is currently the top category (${count(f.topCatCount)}).` : ''}</li>
  <li><strong>Critical CVEs:</strong> CVEs with CVSS &ge; 7.0 discovered by AppScan. ${f.topCve ? `<code>${f.topCve}</code> is the current priority.` : ''}</li>
</ul>`;

    case 'dbsec':
      return `<h3>Database Security Dashboard &mdash; Consolidation Logic</h3>
<ul>
  <li><strong>Total Violations (${count(f.violations)}):</strong> Imperva DAM policy violations across monitored database servers (DB-CUST-01, DB-PAY-01, DB-DOC-01, DB-HR-01).</li>
  <li><strong>Critical Violations (${count(f.critical)}):</strong> Severity-critical violations requiring immediate investigation.</li>
  <li><strong>Databases Monitored / Coverage:</strong> Not tracked by the backend yet &mdash; no DAM inventory feed.</li>
  <li><strong>Violation Categories:</strong> Unauthorized access, privilege abuse, SQL injection, data exfiltration, and other policy violations.</li>
  <li><strong>Active Alerts:</strong> Open DAM alerts across monitored databases, sourced from the unified alert feed.</li>
</ul>`;

    case 'compliance':
      return `<h3>Compliance Dashboard &mdash; Consolidation Logic</h3>
<ul>
  <li><strong>POPIA Readiness (${fmt(f.popia, '%')}):</strong> Self-assessed overall score stored in the compliance snapshot. Cross-border data transfer remains the largest gap.</li>
  <li><strong>ISO 27001 (${fmt(f.iso, '%')}):</strong> Progress toward ISO 27001 certification from the latest snapshot.</li>
  <li><strong>Open Audit Items (${count(f.open)}):</strong> ${fmt(f.overdue, '')} overdue items requiring attention.</li>
  <li><strong>Evidence Collection:</strong> ${fmt(f.avail)} of ${fmt(f.total)} required compliance artifacts collected. ${fmt(f.missing)} missing, ${fmt(f.expiring)} expiring within 30 days.</li>
  <li><strong>Regulatory Calendar:</strong> Key dates tracked &mdash; POPIA Review, ISO Audit, Board Report. Not populated by the backend yet.</li>
</ul>`;

    case 'sre':
      return `<h3>Service Operations Dashboard</h3>
<ul>
  <li><strong>Connectors Online (${fmt(f.healthy)}/${fmt(f.total)}):</strong> ${fmt(f.total)} total OEM connectors &mdash; ${fmt(f.healthy)} healthy, ${fmt(f.degraded)} degraded. Status and latency come from the connector health feed.</li>
  <li><strong>DAM Agents / Pipeline Uptime:</strong> Not tracked by the backend yet.</li>
  <li><strong>Events / Hour:</strong> ${count(f.events)} events per hour across all connectors &mdash; nominal volume.</li>
  <li><strong>Error Rate (${fmt(f.errorRate, '%')}):</strong> Proportion of connector events with errors.</li>
  <li><strong>System Health:</strong> CPU, memory, disk, and queue metrics are not tracked by the backend yet.</li>
</ul>`;

    default:
      return '';
  }
}

export function buildLayman(role: string, f: ExplainFacts): string {
  switch (role) {
    case 'exec':
      return `<h3>Executive Dashboard &mdash; Plain English</h3>
<ul>
  <li><strong>Fused Risk Score (${fmt(f.fusedRisk)}):</strong> One number out of 100 that combines AppScan bugs, Imperva violations, API exposure, and compliance gaps. Computed live from the pipeline.</li>
  <li><strong>Open Findings (${count(f.findings)}):</strong> Total unfixed security bugs. Critical ones are flagged in red.</li>
  <li><strong>POPIA Compliance (${fmt(f.popia, '%')}):</strong> Readiness for SA's privacy law, from the latest compliance snapshot.</li>
  <li><strong>Active Alerts (${count(f.alerts)}):</strong> Automated rules currently firing. The custom rule "fused_score &gt; 71" catches apps crossing the danger line.</li>
  <li><strong>Heatmap:</strong> Color grid showing which apps have the worst bugs. ${f.topApp ? `<strong>${f.topApp}</strong> (darkest red) needs fixing first.` : ''}</li>
  <li><strong>Top 5 by Fused Risk:</strong> Each app gets a score. ${f.topApp ? `${f.topApp} at ${fmt(f.topAppScore)} leads.` : ''}</li>
</ul>`;

    case 'soc':
      return `<h3>SOC Dashboard &mdash; Plain English</h3>
<ul>
  <li><strong>Active Incidents (${count(f.incidents)}):</strong> Things a human needs to investigate.</li>
  <li><strong>MTTD / MTTR:</strong> Average time to notice and fix. Not tracked by the backend yet.</li>
  <li><strong>Alert Backlog (${count(f.backlog)}):</strong> Alerts nobody has looked at yet.</li>
  <li><strong>Unified Timeline:</strong> Every alert from every tool in one feed, sorted by time. No more alt-tabbing between consoles.</li>
  <li><strong>Alert Queue:</strong> A to-do list with "Acknowledge" and "Investigate" buttons. No spreadsheets needed.</li>
</ul>`;

    case 'appsec':
      return `<h3>AppSec Dashboard &mdash; Plain English</h3>
<ul>
  <li><strong>Total Findings (${count(f.findings)}):</strong> Bugs found by AppScan across 5 apps. ${count(f.critical)} are critical (most dangerous).</li>
  <li><strong>Vulns by Application:</strong> Table showing each app with its bug count by severity.</li>
  <li><strong>OWASP Top 10:</strong> Types of bugs found. ${f.topCat ? `<strong>${f.topCat}</strong> tops the list (${count(f.topCatCount)}).` : ''}</li>
  <li><strong>API Exposure:</strong> Risky API endpoints. Shadow APIs without rate limiting are a data-leak risk.</li>
  <li><strong>WAF Blocks:</strong> Not tracked by the backend yet.</li>
  <li><strong>Critical CVEs:</strong> The scariest known vulnerabilities. ${f.topCve ? `<code>${f.topCve}</code> is the current priority.` : ''}</li>
</ul>`;

    case 'dbsec':
      return `<h3>DB Security Dashboard &mdash; Plain English</h3>
<ul>
  <li><strong>Total Violations (${count(f.violations)}):</strong> Suspicious database actions from Imperva DAM.</li>
  <li><strong>Critical Violations (${count(f.critical)}):</strong> Most-serious violations &mdash; on your most sensitive databases.</li>
  <li><strong>Violations by Database:</strong> Table showing which DB servers have the most problems.</li>
  <li><strong>Violation Categories:</strong> What happened? Unauthorized access, data exfiltration, SQL injection, privilege abuse.</li>
  <li><strong>Active Alerts:</strong> Open DAM alerts from the unified feed.</li>
</ul>`;

    case 'compliance':
      return `<h3>Compliance Dashboard &mdash; Plain English</h3>
<ul>
  <li><strong>POPIA Readiness (${fmt(f.popia, '%')}):</strong> Score for SA privacy law compliance. Cross-border data transfer is the biggest legal gap.</li>
  <li><strong>ISO 27001 (${fmt(f.iso, '%')}):</strong> Progress toward certification from the latest snapshot.</li>
  <li><strong>Open Audit Items (${count(f.open)}):</strong> Things auditors said must be fixed. ${fmt(f.overdue, '')} are overdue.</li>
  <li><strong>Evidence Collection:</strong> ${fmt(f.avail)} of ${fmt(f.total)} required proof-documents exist. ${fmt(f.missing)} missing &mdash; if a regulator asks, you can't prove compliance.</li>
  <li><strong>Regulatory Calendar:</strong> POPIA review, ISO audit, board report deadlines. Not populated by the backend yet.</li>
</ul>`;

    case 'sre':
      return `<h3>Service Ops Dashboard &mdash; Plain English</h3>
<ul>
  <li><strong>Connectors Online (${fmt(f.healthy)}/${fmt(f.total)}):</strong> ${fmt(f.total)} data pipelines, ${fmt(f.healthy)} healthy, ${fmt(f.degraded)} degraded.</li>
  <li><strong>DAM Agents / Pipeline Uptime:</strong> Not tracked by the backend yet.</li>
  <li><strong>Events / Hour (${count(f.events)}):</strong> Security events processed per hour. A sudden drop would mean something broke.</li>
  <li><strong>Error Rate (${fmt(f.errorRate, '%')}):</strong> Share of events with errors. Worth looking at but not an emergency at low levels.</li>
  <li><strong>System Health:</strong> CPU, memory, disk, queue &mdash; not tracked by the backend yet.</li>
</ul>`;

    default:
      return '';
  }
}
