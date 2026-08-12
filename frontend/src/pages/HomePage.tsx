import { useEffect, useState } from 'react';
import LoginPage from './LoginPage';
import { useAuth } from '../hooks/useAuth';
import '../styles/home.css';

const MATRIX_ROWS = [
  { role: 'Executive', tag: 'exec@', alerts: true, vulns: false, logs: false, compliance: true, infra: false },
  { role: 'SOC Analyst', tag: 'soc@', alerts: true, vulns: true, logs: true, compliance: false, infra: false },
  { role: 'AppSec', tag: 'appsec@', alerts: false, vulns: true, logs: false, compliance: false, infra: false },
  { role: 'DB Security', tag: 'dbsec@', alerts: false, vulns: true, logs: true, compliance: false, infra: false },
  { role: 'Compliance', tag: 'compliance@', alerts: false, vulns: false, logs: true, compliance: true, infra: false },
  { role: 'SRE', tag: 'sre@', alerts: false, vulns: false, logs: false, compliance: false, infra: true },
];

const MATRIX_COLUMNS = ['Alerts', 'Vulns', 'Access Logs', 'Compliance', 'Infra'];
const MATRIX_KEYS: (keyof (typeof MATRIX_ROWS)[number])[] = ['alerts', 'vulns', 'logs', 'compliance', 'infra'];

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
    body: 'New accounts inherit the narrowest view for their role. Broader access is requested and logged, never assumed.',
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
  { app: 'payments-api', score: 82, bucket: 'critical', trend: '+6' },
  { app: 'customer-portal', score: 57, bucket: 'monitored', trend: '−3' },
  { app: 'identity-svc', score: 44, bucket: 'monitored', trend: '−11' },
  { app: 'retail-web', score: 19, bucket: 'safe', trend: '−2' },
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
                <span className="preview-live"><span className="dot"></span>Live · demo feed</span>
                <span className="preview-mono">executive view</span>
              </div>
              <div className="preview-body">
                <div className="preview-score">
                  <div className="gauge-ring" style={{ background: 'conic-gradient(var(--flare-1) 0deg 295deg, var(--line) 295deg 360deg)' }}>
                    <div className="inner">
                      <span className="pct">82</span>
                      <span className="lbl">/ 100</span>
                    </div>
                  </div>
                  <div>
                    <div className="preview-score-l">Fused Risk Score</div>
                    <div className="preview-score-bucket">critical · 4 sources</div>
                    <div className="preview-score-note">recomputed every 5 min</div>
                  </div>
                </div>
                <div className="preview-panel">
                  <div className="preview-panel-t">30-day trend</div>
                  <PreviewTrend values={PREVIEW_TREND} />
                </div>
                <div className="preview-panel">
                  <div className="preview-panel-t">Top applications</div>
                  {PREVIEW_APPS.map((r) => (
                    <div key={r.app} className="preview-row">
                      <code>{r.app}</code>
                      <span className={`preview-bucket b-${r.bucket}`}>{r.bucket}</span>
                      <strong style={{ color: 'var(--flare-1)' }}>{r.score}</strong>
                      <span className="preview-trend">{r.trend}</span>
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
              <div className="fusion-bucket"><span className="b-chip b-critical">Critical</span><span>0–100 · needs attention now</span></div>
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
          <div className="metric"><strong>4</strong><span>OEM sources fused</span></div>
          <div className="metric"><strong>1</strong><span>risk score per app</span></div>
          <div className="metric"><strong>5 min</strong><span>recompute cadence</span></div>
          <div className="metric"><strong>3</strong><span>dispatch channels</span></div>
        </div>
      </section>

      <section className="matrix-section" id="matrix">
        <div className="container">
          <div className="section-head">
            <div className="eyebrow"><span className="dot"></span>Role-based access control</div>
            <h2>Every role sees a different slice of the same truth</h2>
            <p>No dashboard shows a role more than it's cleared for. This is the actual access matrix behind every login — not a marketing chart.</p>
          </div>
          <div className="matrix-wrap">
            <table className="matrix">
              <thead>
                <tr>
                  <th style={{ textAlign: 'left' }}>Role</th>
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
          <p className="matrix-note">Admin accounts see every column. Everyone else sees exactly their row — nothing scoped in, nothing leaked out.</p>
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
          <p>Every role — from executive and compliance to delegated department and branch admins — is provisioned with live demo data. Sign in to explore your persona's dashboard — or talk to us about connecting your OEMs.</p>
          <div className="cta-row" style={{ justifyContent: 'center' }}>
            <button className="btn btn-flare" onClick={openModal}>Explore Live Dashboards</button>
            <a href="#preview" className="btn btn-outline">Why the score moves</a>
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
