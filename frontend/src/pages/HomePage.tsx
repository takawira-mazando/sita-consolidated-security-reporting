import { useEffect, useState } from 'react';
import LoginPage from './LoginPage';
import { useAuth } from '../hooks/useAuth';
import { fetchSummary, PublicSummary } from '../api/auth';
import '../styles/home.css';

const MATRIX_ROWS = [
  { role: 'Executive', tag: 'exec@', scope: 'National · whole estate', alerts: true, vulns: false, logs: false, compliance: true, infra: false },
  { role: 'SOC Analyst', tag: 'soc@', scope: 'Assigned departments/branches', alerts: true, vulns: true, logs: true, compliance: false, infra: false },
  { role: 'AppSec', tag: 'appsec@', scope: 'Assigned departments/branches', alerts: false, vulns: true, logs: false, compliance: false, infra: false },
  { role: 'DB Security', tag: 'dbsec@', scope: 'Assigned departments/branches', alerts: false, vulns: true, logs: true, compliance: false, infra: false },
  { role: 'Compliance', tag: 'compliance@', scope: 'National · whole estate', alerts: false, vulns: false, logs: true, compliance: true, infra: false },
  { role: 'Service Ops', tag: 'sre@', scope: 'National · whole estate', alerts: false, vulns: false, logs: false, compliance: false, infra: true },
  { role: 'Transversal Admin', tag: 'transversal@', scope: 'Depts or whole estate', alerts: true, vulns: true, logs: true, compliance: true, infra: true },
  { role: 'Department Admin', tag: 'deptadmin@', scope: 'One department', alerts: true, vulns: true, logs: true, compliance: true, infra: false },
  { role: 'Branch Admin', tag: 'branchadmin@', scope: 'Department branch', alerts: true, vulns: true, logs: true, compliance: true, infra: false },
  { role: 'Provincial SOC Lead', tag: 'provincesoc@', scope: 'One province', alerts: true, vulns: true, logs: true, compliance: false, infra: false },
  { role: 'Provincial Dept Admin', tag: 'provdeptadmin@', scope: 'Province dept', alerts: true, vulns: true, logs: true, compliance: true, infra: false },
  { role: 'Local AppSec', tag: 'localappsec@', scope: 'Province dept', alerts: false, vulns: true, logs: false, compliance: false, infra: false },
  { role: 'Admin', tag: 'admin@', scope: 'Whole estate', alerts: true, vulns: true, logs: true, compliance: true, infra: true },
];

const MATRIX_COLUMNS = ['Alerts', 'Vulns', 'Access Logs', 'Compliance', 'Infra'];
const MATRIX_KEYS: (keyof (typeof MATRIX_ROWS)[number])[] = ['alerts', 'vulns', 'logs', 'compliance', 'infra'];

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info'];

const FEATURES = [
  {
    icon: '◈',
    title: 'One fused risk score',
    body: 'AppScan, Imperva DAM, Imperva WAF, API exposure, and compliance controls are blended into a single transparent 0–100 score per application — no more reconciling four OEM consoles before a meeting.',
  },
  {
    icon: '▤',
    title: 'Action-level accountability',
    body: 'Every acknowledge, resolve, and dead-letter reprocess is recorded with who and when — giving compliance a verifiable trail without a ticket.',
  },
  {
    icon: '◔',
    title: 'Least-privilege by default',
    body: 'New accounts inherit the narrowest view for their role. Broader access is requested and logged, never assumed — down to department, branch, or province.',
  },
  {
    icon: '⚙',
    title: 'Config-driven, not code-driven',
    body: 'New sources and detection rules are added through YAML field mappers and alert rules — onboarding a connector never requires a redeploy.',
  },
  {
    icon: '⇄',
    title: 'Built to never miss a signal',
    body: 'Circuit breakers, token-bucket rate limiting, retry with backoff, and a dead-letter queue with one-click reprocess keep the pipeline resilient.',
  },
  {
    icon: '↯',
    title: 'Dispatch where your team works',
    body: 'High and critical alerts route automatically to email, Microsoft Teams, and PagerDuty — enriched with app owner, team, and priority.',
  },
];

const PIPELINE_STAGES = [
  { n: '01', title: 'Ingest', body: 'OEM connectors poll AppScan, Imperva DAM, Imperva WAF, API Security, and compliance sources — with rate limiting and circuit breakers.' },
  { n: '02', title: 'Normalise', body: 'Vendor-speak becomes one schema: canonical severity, UTC timestamps, typed fields, and de-duplication across every source.' },
  { n: '03', title: 'Correlate', body: 'YAML rules fire on records and aggregates — critical spikes, shadow APIs, compliance drops, and 3-sigma anomalies.' },
  { n: '04', title: 'Score', body: 'A weighted 0–100 fused risk score per application, bucketed safe / monitored / critical, recomputed every 5 minutes.' },
  { n: '05', title: 'Dispatch', body: 'Severity-gated routing to email, Teams, and PagerDuty — each alert enriched with app ownership and priority.' },
];

const FUSION_WEIGHTS = [
  { label: 'AppScan findings', pct: 35, color: 'var(--flare-1)' },
  { label: 'Imperva violations', pct: 25, color: 'var(--flare-2)' },
  { label: 'API exposure', pct: 20, color: 'var(--link)' },
  { label: 'Compliance penalty', pct: 20, color: 'var(--ok)' },
];

const SOURCES = [
  { name: 'HCL AppScan', kind: 'AppSec · SAST/DAST' },
  { name: 'Imperva DAM', kind: 'Database activity' },
  { name: 'Imperva WAF', kind: 'Web application firewall' },
  { name: 'API Security', kind: 'Shadow API discovery' },
  { name: 'POPIA', kind: 'Compliance control data' },
  { name: 'ISO 27001', kind: 'Compliance control data' },
];

const PREVIEW_APPS = [
  { app: 'payments-api', score: 82, bucket: 'critical' },
  { app: 'customer-portal', score: 57, bucket: 'monitored' },
  { app: 'identity-svc', score: 44, bucket: 'monitored' },
  { app: 'retail-web', score: 19, bucket: 'safe' },
];

const PREVIEW_TREND = [34, 41, 38, 52, 48, 61, 58, 66, 62, 71, 68, 74];

function PreviewTrend({ values }: { values: number[] }) {
  const max = Math.max(...values);
  return (
    <div className="preview-chart">
      {values.map((v, i) => (
        <div key={i} className="preview-bar" style={{ height: `${(v / max) * 100}%`, background: i === values.length - 1 ? 'var(--flare-1)' : 'var(--line)' }} />
      ))}
    </div>
  );
}

export default function HomePage() {
  const { loginDemo, demoAccounts } = useAuth();
  const [modalOpen, setModalOpen] = useState(false);
  const [isDark, setIsDark] = useState(() => document.body.dataset.theme !== 'light');
  const [summary, setSummary] = useState<PublicSummary | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchSummary()
      .then((s) => {
        if (!cancelled) setSummary(s);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const toggleTheme = () => {
    const next = isDark ? 'light' : 'dark';
    document.body.dataset.theme = next;
    localStorage.setItem('sita_theme', next);
    setIsDark(!isDark);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeModal();
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, []);

  const openModal = () => {
    setModalOpen(true);
    document.body.style.overflow = 'hidden';
  };

  const closeModal = () => {
    setModalOpen(false);
    document.body.style.overflow = '';
  };

  const loginAsRole = async (role: string) => {
    if (!demoAccounts.some((a) => a.role === role)) return;
    document.body.style.overflow = '';
    await loginDemo(role);
  };

  const heroApps = summary
    ? summary.top_risky_apps.slice(0, 4).map((a) => ({
        app: a.app_name,
        score: Math.round(a.score),
        bucket: a.bucket,
      }))
    : PREVIEW_APPS;
  const heroTrend = summary && summary.risk.trend.length ? summary.risk.trend : PREVIEW_TREND;
  const gaugeScore = summary && summary.risk.trend.length ? Math.round(summary.risk.trend[summary.risk.trend.length - 1].avg_score) : 82;
  const gaugeBucket = summary?.top_risky_apps[0]?.bucket || 'critical';
  const connectorText = summary
    ? `${summary.connectors.healthy}/${summary.connectors.total} connectors healthy`
    : '4 sources fused';
  const severityList = summary
    ? SEVERITY_ORDER.filter((s) => summary.findings.by_severity[s]).map((s) => ({
        sev: s,
        count: summary.findings.by_severity[s],
      }))
    : [];

  return (
    <div className="home-page">
      <header className="site">
        <div className="container">
          <a href="#" className="logo">
            <img className="home-logo-img" src="/sita-logo.gif" alt="SITA" />
          </a>
          <nav className="primary">
            <a href="#problem">The Problem</a>
            <a href="#preview">Live Preview</a>
            <a href="#pipeline">How It Works</a>
            <a href="#estate">Live Estate</a>
            <a href="#matrix">Role Matrix</a>
            <a href="#security">Security</a>
          </nav>
          <div className="home-actions">
            <button className="theme-toggle" onClick={toggleTheme}>
              {isDark ? '☀ Light' : '🌙 Dark'}
            </button>
            <button className="btn btn-outline" onClick={openModal}>Sign In</button>
          </div>
        </div>
      </header>

      <section className="hero">
        <div className="container hero-grid">
          <div>
            <div className="eyebrow"><span className="dot"></span>All security signals, one login</div>
            <h1>Stop reconciling four OEM consoles.<br />See the whole posture <span className="gradient-text">as one number.</span></h1>
            <p className="lede">SITA Security ingests AppScan, Imperva DAM, Imperva WAF, API exposure, and compliance controls into a single normalised feed — then fuses them into one risk score per application, scoped to who's looking.</p>
            <div className="cta-row">
              <button className="btn btn-flare" onClick={openModal}>Explore Live Dashboards</button>
              <a href="#pipeline" className="btn btn-outline">See how it works ↓</a>
            </div>
            <div className="role-strip">
              {demoAccounts.map((account) => (
                <button
                  key={account.role}
                  className="role-chip"
                  title={`Sign in as ${account.label}`}
                  onClick={() => loginAsRole(account.role)}
                >
                  <b>{account.email.split('@')[0]}@</b>
                  <span className="role-chip-cap">— {account.label.toLowerCase()} view</span>
                </button>
              ))}
            </div>
          </div>

          <div className="hero-preview" aria-hidden="true">
            <div className="preview-card">
              <div className="preview-card-h">
                <span className="preview-live"><span className="dot"></span>Live · estate-wide</span>
                <span className="preview-mono">executive view</span>
              </div>
              <div className="preview-body">
                <div className="preview-score">
                  <div className="gauge-ring" style={{ background: `conic-gradient(var(--flare-1) 0deg ${(gaugeScore / 100) * 360}deg, var(--line) ${(gaugeScore / 100) * 360}deg 360deg)` }}>
                    <div className="inner">
                      <span className="pct">{gaugeScore}</span>
                      <span className="lbl">/ 100</span>
                    </div>
                  </div>
                  <div>
                    <div className="preview-score-l">Estate avg risk score</div>
                    <div className={`preview-score-bucket ${gaugeBucket ? `b-${gaugeBucket}` : ''}`}>{gaugeBucket || '—'} · {connectorText}</div>
                    <div className="preview-score-note">
                      {summary?.risk.latest_score_date ? `latest scoring ${summary.risk.latest_score_date}` : 'recomputed every 5 min'}
                    </div>
                  </div>
                </div>
                <div className="preview-panel">
                  <div className="preview-panel-t">14-day average trend</div>
                  <PreviewTrend values={heroTrend.map((t) => (typeof t === 'number' ? t : t.avg_score))} />
                </div>
                <div className="preview-panel">
                  <div className="preview-panel-t">Top applications at risk</div>
                  {heroApps.map((r) => (
                    <div key={r.app} className="preview-row">
                      <code>{r.app}</code>
                      <span className={`preview-bucket b-${r.bucket}`}>{r.bucket}</span>
                      <strong style={{ color: 'var(--flare-1)' }}>{r.score}</strong>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="problem-section" id="problem">
        <div className="container">
          <div className="section-head">
            <div className="eyebrow"><span className="dot"></span>Why teams buy this</div>
            <h2>Security teams are drowning in tools — not in signals</h2>
            <p>Four OEM consoles, four logins, four opinions of the same incident. Someone reconciles them all before every meeting. SITA is that reconciliation, automated.</p>
          </div>
          <div className="problem-grid">
            <div className="problem-card">
              <div className="problem-n">Alert fatigue</div>
              <p>SOC analysts triage the same event differently in each console. SITA normalises severity and de-duplicates before an analyst ever sees it.</p>
            </div>
            <div className="problem-card">
              <div className="problem-n">Tool sprawl</div>
              <p>AppSec, DBsec, WAF, and API tools each report in isolation. SITA consolidates them into one schema and one dashboard per stakeholder.</p>
            </div>
            <div className="problem-card">
              <div className="problem-n">Manual board prep</div>
              <p>Executives get a posture summary pulled together by hand. SITA fuses a transparent risk score computed automatically every 5 minutes.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="preview-section" id="preview">
        <div className="container">
          <div className="section-head">
            <div className="eyebrow"><span className="dot"></span>Real product, real data</div>
            <h2>One number. Every domain, every role.</h2>
            <p>Four OEM sources become a single fused risk score with a transparent breakdown — so anyone can explain why a score moved.</p>
          </div>
          <div className="fusion-wrap">
            <div className="fusion-main">
              <div className="fusion-score-head">
                <span>How the score is built</span>
                <span className="preview-mono">weighted · 0–100</span>
              </div>
              {FUSION_WEIGHTS.map((w) => (
                <div key={w.label} className="fusion-row">
                  <span className="fusion-label">{w.label}</span>
                  <div className="bar-track"><div className="bar-fill" style={{ width: `${w.pct}%`, background: w.color }} /></div>
                  <span className="fusion-pct">{w.pct}%</span>
                </div>
              ))}
              <p className="fusion-note">AppScan severity counts drive 35% of the score, Imperva violations 25%, API exposure 20%, and compliance penalties 20%. Every component is visible and exportable — nothing black-boxed.</p>
            </div>
            <div className="fusion-side">
              <div className="fusion-side-t">Score buckets</div>
              <div className="fusion-bucket"><span className="b-chip b-critical">Critical</span><span>needs attention now</span></div>
              <div className="fusion-bucket"><span className="b-chip b-monitored">Monitored</span><span>elevated but being watched</span></div>
              <div className="fusion-bucket"><span className="b-chip b-safe">Safe</span><span>within acceptable posture</span></div>
              <div className="fusion-side-t" style={{ marginTop: 22 }}>Sources feeding the score</div>
              <div className="fusion-src-list">
                {SOURCES.map((s) => (
                  <div key={s.name} className="fusion-src">
                    <span className="fusion-src-dot" />
                    <div>
                      <div className="fusion-src-name">{s.name}</div>
                      <div className="fusion-src-kind">{s.kind}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="pipeline-section" id="pipeline">
        <div className="container">
          <div className="section-head">
            <div className="eyebrow"><span className="dot"></span>Under the hood</div>
            <h2>From raw OEM signals to a decision in five stages</h2>
            <p>An event-driven pipeline — ingestion, normalisation, correlation, scoring, and dispatch — running as independently scalable services.</p>
          </div>
          <div className="pipeline-grid">
            {PIPELINE_STAGES.map((stage) => (
              <div className="pipeline-card" key={stage.n}>
                <div className="pipeline-n">{stage.n}</div>
                <h3>{stage.title}</h3>
                <p>{stage.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="metrics-band">
        <div className="container metrics-grid">
          <div className="metric"><strong>{summary ? summary.assets.apps : 4}</strong><span>{summary ? 'applications scored' : 'OEM sources fused'}</span></div>
          <div className="metric"><strong>{summary ? summary.assets.monitored_databases : 1}</strong><span>{summary ? 'databases monitored' : 'risk score per app'}</span></div>
          <div className="metric"><strong>{summary ? summary.findings.open : 5}</strong><span>{summary ? 'open findings' : 'min recompute cadence'}</span></div>
          <div className="metric"><strong>{summary ? `${summary.connectors.healthy}/${summary.connectors.total}` : 3}</strong><span>{summary ? 'connectors healthy' : 'dispatch channels'}</span></div>
        </div>
      </section>

      <section className="estate-section" id="estate">
        <div className="container">
          <div className="section-head">
            <div className="eyebrow"><span className="dot"></span>The whole estate, live</div>
            <h2>One window into every tenant's posture</h2>
            <p>Aggregates computed from the live warehouse — open findings by severity, risk distribution, connector health, and the three-tier government tenancy model (national → department → branch, provincial included).</p>
          </div>
          <div className="estate-grid">
            <div className="estate-card">
              <div className="estate-card-t">Open findings</div>
              <div className="estate-big">{summary ? summary.findings.open.toLocaleString() : '—'}</div>
              <div className="estate-chips">
                {summary && severityList.length
                  ? severityList.map((s) => (
                      <span key={s.sev} className={`estate-sev s-${s.sev}`}>{s.count} {s.sev}</span>
                    ))
                  : <span className="estate-sub">all severities from every connected source</span>}
              </div>
            </div>
            <div className="estate-card">
              <div className="estate-card-t">Risk distribution</div>
              <div className="estate-rows">
                <div className="estate-row"><span className="estate-row-l"><span className="b-chip b-critical">Critical</span></span><strong>{summary?.risk.distribution.critical ?? '—'}</strong></div>
                <div className="estate-row"><span className="estate-row-l"><span className="b-chip b-monitored">Monitored</span></span><strong>{summary?.risk.distribution.monitored ?? '—'}</strong></div>
                <div className="estate-row"><span className="estate-row-l"><span className="b-chip b-safe">Safe</span></span><strong>{summary?.risk.distribution.safe ?? '—'}</strong></div>
              </div>
              <div className="estate-sub">{summary?.risk.latest_score_date ? `as scored ${summary.risk.latest_score_date}` : 'latest daily scoring snapshot'}</div>
            </div>
            <div className="estate-card">
              <div className="estate-card-t">Connector health</div>
              <div className="estate-rows">
                <div className="estate-row"><span className="estate-row-l"><span className="b-sev healthy">Healthy</span></span><strong>{summary?.connectors.healthy ?? '—'}</strong></div>
                <div className="estate-row"><span className="estate-row-l"><span className="b-sev degraded">Degraded</span></span><strong>{summary?.connectors.degraded ?? '—'}</strong></div>
                <div className="estate-row"><span className="estate-row-l"><span className="b-sev down">Down</span></span><strong>{summary?.connectors.down ?? '—'}</strong></div>
              </div>
              <div className="estate-sub">{summary ? `of ${summary.connectors.total} connectors · last ingest ${new Date(summary.latest_ingest || '').toLocaleString()}` : 'ingestion pipeline status'}</div>
            </div>
            <div className="estate-card">
              <div className="estate-card-t">Assets under management</div>
              <div className="estate-rows">
                <div className="estate-row"><span className="estate-row-l">Applications</span><strong>{summary?.assets.apps ?? '—'}</strong></div>
                <div className="estate-row"><span className="estate-row-l">Databases (monitored)</span><strong>{summary ? `${summary.assets.monitored_databases}/${summary.assets.databases}` : '—'}</strong></div>
                <div className="estate-row"><span className="estate-row-l">API endpoints</span><strong>{summary?.assets.api_endpoints ?? '—'}</strong></div>
                <div className="estate-row"><span className="estate-row-l">Agents / WAF blocks</span><strong>{summary ? `${summary.assets.agents} / ${summary.assets.waf_blocks}` : '—'}</strong></div>
              </div>
            </div>
            <div className="estate-card estate-card-wide">
              <div className="estate-card-t">Three-tier government tenancy</div>
              <div className="estate-mandate">
                <div><strong>{summary?.tenancy.departments ?? '—'}</strong><span>departments ({summary?.tenancy.provincial_departments ?? '—'} provincial)</span></div>
                <div><strong>{summary?.tenancy.branches ?? '—'}</strong><span>organisational branches</span></div>
                <div><strong>{summary?.tenancy.provinces ?? '—'}</strong><span>provinces</span></div>
              </div>
              <div className="estate-sub">
                Every application and database is denormalised to its department and branch at write time, so a department-scoped login literally cannot see outside its assigned tenants.
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="matrix-section" id="matrix">
        <div className="container">
          <div className="section-head">
            <div className="eyebrow"><span className="dot"></span>Role-based access control</div>
            <h2>Every role sees a different slice of the same truth</h2>
            <p>No dashboard shows a role more than it's cleared for. This is the actual access matrix behind every login, including the full delegated-admin and provincial personas — not a marketing chart.</p>
          </div>
          <div className="matrix-wrap">
            <table className="matrix">
              <thead>
                <tr>
                  <th style={{ textAlign: 'left' }}>Role</th>
                  <th style={{ textAlign: 'left' }}>Tenant scope</th>
                  {MATRIX_COLUMNS.map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {MATRIX_ROWS.map((row) => (
                  <tr key={row.tag}>
                    <td className="rolecell">
                      {row.role}
                      <span>{row.tag}</span>
                    </td>
                    <td className="matrix-scope">{row.scope}</td>
                    {MATRIX_KEYS.map((key) => (
                      <td key={key}>
                        <span className={row[key] ? 'dot-on' : 'dot-off'}></span>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="matrix-note">Admin accounts see every column. Everyone else sees exactly their row — nothing scoped in, nothing leaked out. Sign in as any persona above to see its scoped view.</p>
        </div>
      </section>

      <section className="features" id="security">
        <div className="container">
          <div className="section-head">
            <div className="eyebrow"><span className="dot"></span>Platform</div>
            <h2>Built for the people who actually get paged</h2>
          </div>
          <div className="feat-grid">
            {FEATURES.map((feature) => (
              <div className="feat-card" key={feature.title}>
                <div className="fico">{feature.icon}</div>
                <h3>{feature.title}</h3>
                <p>{feature.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="cta-band">
        <div className="container">
          <h2>See your own view before rolling this out.</h2>
          <p>Every role — from executive and compliance to delegated department, branch, and provincial admins — is provisioned with live demo data. Sign in to explore your persona's dashboard — or talk to us about connecting your OEMs.</p>
          <div className="cta-row" style={{ justifyContent: 'center' }}>
            <button className="btn btn-flare" onClick={openModal}>Explore Live Dashboards</button>
            <a href="#estate" className="btn btn-outline">View the live estate</a>
          </div>
        </div>
      </section>

      <footer>
        <div className="container">
          <span>© 2026 SITA · Security</span>
          <span className="status"><span className="dot"></span>All systems operational</span>
        </div>
      </footer>

      {modalOpen && <LoginPage onClose={closeModal} />}
    </div>
  );
}