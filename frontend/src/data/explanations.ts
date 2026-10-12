import type { NarrativeFacts } from '../types';

export const ROLE_LABELS: Record<string, string> = {
  exec: 'Executive',
  soc: 'SOC Analyst',
  appsec: 'AppSec',
  dbsec: 'DB Security',
  compliance: 'Compliance',
  sre: 'Service Ops',
};

export type ExplainFacts = Record<string, string | number | null | undefined>;

export interface NarrativeInput {
  /** Live, per-screen figures. */
  facts: ExplainFacts;
  /** Platform model constants served by `GET /api/v1/meta/narrative-facts`. */
  model: NarrativeFacts;
}

/**
 * Authoring rules for this file. They exist because the previous hand-authored
 * version of this narrative drifted: it asserted weights of 40/30/20/10 while
 * the engine used 35/25/20/20, "60 departments" against a catalogue of 173, and
 * seven "not tracked by the backend yet" notices for metrics that had live
 * endpoints and were rendered on the same screen.
 *
 * 1. No numeric literal. Every figure comes from `facts` or `model`.
 * 2. No capability claim unless the panel it describes is on this screen.
 * 3. No "not tracked" notice unless the fetch actually failed -- when a value is
 *    absent, say so, but never assert the platform lacks the capability.
 * 4. If `model` did not load, omit model-derived detail rather than guessing it.
 */

function fmt(n: string | number | null | undefined, suffix = ''): string {
  if (n === undefined || n === null || n === '') return '—';
  return `${n}${suffix}`;
}

function count(n: string | number | null | undefined): string {
  if (n === undefined || n === null || n === '') return '—';
  return Number(n).toLocaleString();
}

function list(items: string[] | undefined, joiner = ', '): string {
  if (!items || items.length === 0) return '';
  if (items.length === 1) return items[0];
  return `${items.slice(0, -1).join(joiner)} and ${items[items.length - 1]}`;
}

export function buildExplain(role: string, input: NarrativeInput): string {
  const f = input.facts;
  const m = input.model;
  switch (role) {
    case 'exec':
      return `<h3>Executive Risk Dashboard &mdash; Consolidation Logic</h3>
<ul>
  <li><strong>Fused Risk Score (${fmt(f.fusedRisk)}):</strong> Weighted composite of ${m.riskWeightSummary ?? 'the four component signals'}. Each component is normalised to 0&ndash;100 before weighting, then the result is banded: ${m.bandSummary ?? 'safe / monitored / critical'}.</li>
  <li><strong>Open Findings (${count(f.findings)}):</strong> Findings across the ${count(m.departments)} departments and ${count(m.branches)} operational branches in scope for this account. Severity is normalised during ingestion from each OEM's own scale before storage.</li>
  <li><strong>POPIA Compliance (${fmt(f.popia, '%')}):</strong> Latest stored snapshot. The scoring model weights ${list(m.popiaDomainLabels)}. <em>This score is seeded rather than computed &mdash; see the Compliance dashboard note.</em></li>
  <li><strong>Active Alerts (${count(f.alerts)}):</strong> Produced by ${m.alertRuleCount ?? '—'} rules evaluated against the fused warehouse &mdash; covering AppScan findings, Imperva DAM violations and WAF blocks, API Security shadow-API detections, compliance score movement and connector health.${m.alertRules ? ` Rules in force: ${list(m.alertRules.map((r) => r.id))}.` : ''}</li>
  <li><strong>Severity Distribution:</strong> Findings split across the normalised severity bands${f.topCat ? `, with <strong>${f.topCat}</strong> the largest category` : ''}.</li>
  <li><strong>Application Risk Heatmap:</strong> The eight applications with the most findings, coloured by finding volume.${f.topApp ? ` <strong>${f.topApp}</strong> currently leads the critical bucket.` : ''}</li>
  <li><strong>Top 5 by Fused Risk:</strong> Ranked by the same composite as the headline score.${f.topApp && f.topAppScore != null ? ` <strong>${f.topApp}</strong> leads at ${fmt(f.topAppScore)}.` : ''}</li>
</ul>
<p><em>This view does not exist in any OEM console &mdash; it is generated entirely by the consolidation pipeline.</em></p>`;

    case 'soc':
      return `<h3>SOC Analyst Dashboard &mdash; Consolidation Logic</h3>
<ul>
  <li><strong>Active Incidents (${count(f.incidents)}):</strong> Alerts in an open state, aggregated from AppScan findings, Imperva DAM violations, Imperva WAF blocks and API Security shadow-API detections, then deduplicated on a normalised signature.</li>
  <li><strong>MTTD / MTTR:</strong> Mean time to detect and mean time to resolve, recorded weekly in the SLO metrics table${f.mttd != null || f.mttr != null ? ` (currently ${fmt(f.mttd, 'h')} and ${fmt(f.mttr, 'h')})` : ''}. The trend panel plots both series side by side.</li>
  <li><strong>Alert Backlog (${count(f.backlog)}):</strong> Open alerts that have not reached a terminal state, bucketed by age so the oldest work is visible separately from the newest.</li>
  <li><strong>Unified Timeline:</strong> A single feed across every OEM, each entry tagged with its source so the originating console is identifiable.</li>
  <li><strong>Alert Queue:</strong> The current open-alert list with rule, source, severity, owning team and state. Alert state changes are exposed by the platform API; this dashboard is a read-only view.</li>
</ul>
<p><em>No OEM provides a cross-source alert timeline &mdash; this is a fusion-only feature.</em></p>`;

    case 'appsec':
      return `<h3>Application Security Dashboard &mdash; Consolidation Logic</h3>
<ul>
  <li><strong>Total Findings (${count(f.findings)}):</strong> AppScan vulnerabilities across the ${count(m.departments)} departments in scope.</li>
  <li><strong>Critical (${count(f.critical)}):</strong> Findings at the highest normalised severity, awaiting remediation.</li>
  <li><strong>Fix Rate (${fmt(f.fixRate, '%')}):</strong> Share of findings last seen in the remediation window that have reached a remediated state.${f.fixTotal != null ? ` Computed over ${count(f.fixTotal)} findings.` : ''}</li>
  <li><strong>WAF Blocks (${count(f.wafTotal)}):</strong> Imperva WAF block events in the observed window, grouped by attack type.</li>
  <li><strong>Distribution by Source Category:</strong> Findings grouped by the <code>category</code> field recorded at normalisation &mdash; each vendor's own taxonomy.${f.topCat ? ` <strong>${f.topCat}</strong> is currently the largest at ${count(f.topCatCount)}.` : ''}</li>
  <li><strong>OWASP Top 10 Posture:</strong> Every finding classified onto ${m.owaspTaxonomy || 'OWASP Top 10 2021'} regardless of which tool reported it${m.owaspClassifiedPct != null ? ` &mdash; ${fmt(m.owaspClassifiedPct, '%')} of mappable findings are classified` : ''}. ${m.owaspUnmapped ? `${count(m.owaspUnmapped)} findings carry a vendor value with no mapping yet and are shown separately rather than guessed at.` : ''}${m.owaspNotApplicable ? ` ${count(m.owaspNotApplicable)} compliance findings are marked not applicable, because a privacy-law control gap is not a software vulnerability class.` : ''}</li>
  <li><strong>API Exposure:</strong> Endpoints ranked by exposure score with shadow-API status.${f.shadowTotal != null ? ` ${count(f.shadowTotal)} shadow endpoints are currently flagged.` : ''}</li>
  <li><strong>Critical Findings:</strong> Identifier, application, category and discovery date. <em>The platform does not ingest a CVSS base score, so no CVSS column is shown &mdash; treat severity as the vendor-assigned rating.</em></li>
</ul>`;

    case 'dbsec':
      return `<h3>Database Security Dashboard &mdash; Consolidation Logic</h3>
<ul>
  <li><strong>Total Violations (${count(f.violations)}):</strong> Imperva DAM policy violations across monitored database servers.</li>
  <li><strong>Critical Violations (${count(f.critical)}):</strong> Violations at the highest normalised severity, requiring investigation.</li>
  <li><strong>Databases Monitored / Coverage (${fmt(f.coverage, '%')}):</strong> From the database inventory feed.${f.monitored != null ? ` ${count(f.monitored)} of ${count(f.dbTotal)} known databases are under monitoring.` : ''}</li>
  <li><strong>Violation Categories:</strong> Grouped by the <code>category</code> recorded at normalisation${f.topCat ? `, with <strong>${f.topCat}</strong> the largest group` : ''}.</li>
  <li><strong>Active Database Alerts:</strong> Open DAM alerts with rule, severity, owning application and state.</li>
</ul>`;

    case 'compliance':
      return `<h3>Compliance Dashboard &mdash; Consolidation Logic</h3>
<ul>
  <li><strong>POPIA Readiness (${fmt(f.popia, '%')}):</strong> Latest stored snapshot. The scoring model weights ${list(m.popiaDomainLabels)}.</li>
  <li><strong>ISO 27001 (${fmt(f.iso, '%')}):</strong> Progress against ${m.isoDomainCount ?? '—'} Annex A themes.</li>
  <li><strong>Open Audit Items (${count(f.open)}):</strong> ${fmt(f.overdue, '')} overdue items requiring attention.</li>
  <li><strong>Evidence Collection:</strong> ${fmt(f.avail)} of ${fmt(f.total)} gaps carry at least one evidence record. ${fmt(f.missing)} have none; ${fmt(f.expiring)} fall due within ${m.evidenceExpiryDays ?? 'the reporting window'}. <em>This counts gaps and their evidence records &mdash; it is not an artefact-level evidence inventory.</em></li>
  <li><strong>Regulatory Calendar:</strong> The next due gaps ordered by due date, with control identifier, owner and severity.</li>
  <li><strong>Framework applicability:</strong>${m.applicabilitySummary ? ` ${m.applicabilitySummary}` : ''}</li>
</ul>
<p><em>Scores in this dashboard are seeded values held in <code>warehouse.compliance_snapshots</code>. The weighted scoring functions in <code>app.processing.compliance</code> exist but have no callers, so no score here is currently derived from measured control evidence.</em></p>`;

    case 'sre':
      return `<h3>Service Operations Dashboard</h3>
<ul>
  <li><strong>Connectors Online (${fmt(f.healthy)}/${fmt(f.total)}):</strong> Ingestion pipelines and their most recent poll outcome, including latency and circuit state.</li>
  <li><strong>DAM Agents (${fmt(f.agentOnline)}/${fmt(f.agentTotal)}):</strong> Database-audience agents reporting in, broken down by role, with version distribution.</li>
  <li><strong>Pipeline Uptime (${fmt(f.uptime, '%')}):</strong> From the system metrics feed.</li>
  <li><strong>Events / Hour (${count(f.events)}):</strong> Current ingestion rate summed across all connectors.</li>
  <li><strong>System Health:</strong> CPU, memory, disk I/O and queue depth as last recorded.</li>
</ul>
<p><em>Connector health, agent inventory and system metrics are all served live by the platform API.</em></p>`;

    default:
      return '';
  }
}

export function buildLayman(role: string, input: NarrativeInput): string {
  const f = input.facts;
  const m = input.model;
  switch (role) {
    case 'exec':
      return `<h3>Executive Dashboard &mdash; Plain English</h3>
<ul>
  <li><strong>Fused Risk Score (${fmt(f.fusedRisk)}):</strong> One number out of 100 that blends four kinds of security signal${m.riskWeightSummary ? `: ${m.riskWeightSummary}` : ''}. A higher number means more concern.</li>
  <li><strong>Open Findings (${count(f.findings)}):</strong> Total unfixed security issues. Critical ones are flagged in red.</li>
  <li><strong>POPIA Compliance (${fmt(f.popia, '%')}):</strong> Readiness against South Africa's privacy law, from the latest stored assessment.</li>
  <li><strong>Active Alerts (${count(f.alerts)}):</strong> Automated rules currently firing across every connected security tool.${m.alertRuleCount ? ` There are ${m.alertRuleCount} rules in force.` : ''}</li>
  <li><strong>Severity Distribution:</strong> How the issues split across the four severity levels.</li>
  <li><strong>Application Risk Heatmap:</strong> Colour grid showing which applications have the most issues.${f.topApp ? ` <strong>${f.topApp}</strong> (darkest red) needs fixing first.` : ''}</li>
  <li><strong>Top 5 by Fused Risk:</strong> The five applications scoring highest.${f.topApp && f.topAppScore != null ? ` <strong>${f.topApp}</strong> at ${fmt(f.topAppScore)} leads.` : ''}</li>
</ul>`;

    case 'soc':
      return `<h3>SOC Dashboard &mdash; Plain English</h3>
<ul>
  <li><strong>Active Incidents (${count(f.incidents)}):</strong> Things a human needs to investigate.</li>
  <li><strong>MTTD / MTTR:</strong> Average time to notice a problem, and average time to finish dealing with it.</li>
  <li><strong>Alert Backlog (${count(f.backlog)}):</strong> Alerts nobody has closed out yet.</li>
  <li><strong>Unified Timeline:</strong> Every alert from every tool in one feed, sorted by time. No more alt-tabbing between consoles.</li>
  <li><strong>Alert Queue:</strong> The current to-do list, with the team responsible shown against each entry.</li>
</ul>`;

    case 'appsec':
      return `<h3>AppSec Dashboard &mdash; Plain English</h3>
<ul>
  <li><strong>Total Findings (${count(f.findings)}):</strong> Bugs found by the application scanner across ${count(m.departments)} departments. ${count(f.critical)} are critical.</li>
  <li><strong>Vulnerabilities by Application:</strong> Which applications have how many bugs, by severity.</li>
  <li><strong>Fix Rate (${fmt(f.fixRate, '%')}):</strong> The share of issues that have actually been fixed in the recent window.</li>
  <li><strong>Distribution by Source Category:</strong> What <em>kinds</em> of bug these are, using each scanner's own categories.${f.topCat ? ` <strong>${f.topCat}</strong> tops the list (${count(f.topCatCount)}).` : ''}</li>
  <li><strong>OWASP Top 10 Posture:</strong> The same findings sorted into the industry-standard OWASP categories${m.owaspTaxonomy ? ` (${m.owaspTaxonomy})` : ''}, so the AppScan, API Security and WAF numbers can be added up into one picture. <em>This is the view none of the individual tools can give you on its own.</em></li>
  <li><strong>API Exposure:</strong> The risky web-service entry points. Shadow APIs are ones nobody has formally registered.</li>
  <li><strong>WAF Blocks (${count(f.wafTotal)}):</strong> Malicious requests the web application firewall stopped.</li>
</ul>`;

    case 'dbsec':
      return `<h3>DB Security Dashboard &mdash; Plain English</h3>
<ul>
  <li><strong>Total Violations (${count(f.violations)}):</strong> Suspicious database actions caught by the database activity monitor.</li>
  <li><strong>Critical Violations (${count(f.critical)}):</strong> The most serious ones, on your most sensitive databases.</li>
  <li><strong>Databases Monitored (${fmt(f.coverage, '%')} coverage):</strong> How much of the estate the monitor is actually watching.</li>
  <li><strong>Violations by Application:</strong> Which database servers have the most problems.</li>
  <li><strong>Violation Categories:</strong> What happened.${f.topCat ? ` Currently <strong>${f.topCat}</strong> is the most common.` : ''}</li>
  <li><strong>Active Database Alerts:</strong> Open alerts on databases that still need a human decision.</li>
</ul>`;

    case 'compliance':
      return `<h3>Compliance Dashboard &mdash; Plain English</h3>
<ul>
  <li><strong>POPIA Readiness (${fmt(f.popia, '%')}):</strong> A score against South Africa's privacy law.</li>
  <li><strong>ISO 27001 (${fmt(f.iso, '%')}):</strong> Progress toward the international security certification.</li>
  <li><strong>Open Audit Items (${count(f.open)}):</strong> Things that must be fixed. ${fmt(f.overdue, '')} are already overdue.</li>
  <li><strong>Evidence Collection:</strong> ${fmt(f.avail)} of ${fmt(f.total)} items have supporting proof recorded. ${fmt(f.missing)} have none &mdash; if a regulator asks, those cannot be evidenced.</li>
  <li><strong>Regulatory Calendar:</strong> Upcoming due dates, so nothing is missed.</li>
</ul>
<p><em>Important: these scores are stored assessments, not measurements the platform calculates. Treat them as a record of a judgement made elsewhere.</em></p>`;

    case 'sre':
      return `<h3>Service Ops Dashboard &mdash; Plain English</h3>
<ul>
  <li><strong>Connectors Online (${fmt(f.healthy)}/${fmt(f.total)}):</strong> The data pipelines pulling information in from the security tools.</li>
  <li><strong>DAM Agents (${fmt(f.agentOnline)}/${fmt(f.agentTotal)}):</strong> The little pieces of software watching each database.</li>
  <li><strong>Pipeline Uptime (${fmt(f.uptime, '%')}):</strong> How reliably the data is arriving.</li>
  <li><strong>Events / Hour (${count(f.events)}):</strong> Security events processed each hour. A sudden drop would mean something broke.</li>
  <li><strong>System Health:</strong> CPU, memory, disk and queue depth &mdash; whether the platform itself is under strain.</li>
</ul>`;

    default:
      return '';
  }
}