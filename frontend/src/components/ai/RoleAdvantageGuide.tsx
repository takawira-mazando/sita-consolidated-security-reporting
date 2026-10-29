import React, { useState } from 'react';

export interface RoleTag {
  id: string;
  label: string;
  color: string;
  bg: string;
}

export interface RoleGuidanceItem {
  key: string;
  engineName: string;
  icon: string;
  badge: string;
  targetRoles: RoleTag[];
  headline: string;
  roleHelpSummary: string;
  laymanAnalogy: string;
  whatItHelpsWithDetailed: string[];
  deterministicBaseline: string;
  cognitiveAiAdvantage: string;
  whyCodeFails: string;
  operationalGain: string;
  governingOutcome: string;
}

export const ROLE_GUIDANCE_MAP: Record<string, RoleGuidanceItem> = {
  all: {
    key: 'all',
    engineName: 'Unified View — All AI Engines & Telemetry',
    icon: '🌟',
    badge: 'UNIFIED SUITE',
    targetRoles: [
      { id: 'exec', label: 'Executive Leadership / DG', color: '#f87171', bg: 'rgba(239,68,68,0.15)' },
      { id: 'soc', label: 'SOC Analyst / Threat Hunter', color: '#60a5fa', bg: 'rgba(59,130,246,0.15)' },
      { id: 'appsec', label: 'AppSec Engineer', color: '#fbbf24', bg: 'rgba(245,158,11,0.15)' },
      { id: 'compliance', label: 'Compliance & Legal', color: '#c084fc', bg: 'rgba(192,132,252,0.15)' },
      { id: 'admin', label: 'Internal Audit & Admin', color: '#34d399', bg: 'rgba(52,211,153,0.15)' },
      { id: 'sre', label: 'SRE / Systems Ops', color: '#94a3b8', bg: 'rgba(148,163,184,0.15)' },
    ],
    headline: 'Transversal Whole-Estate Situational Awareness & Defense Synchronization',
    roleHelpSummary: 'Eliminates departmental silos by uniting perimeter WAF blocks, AppScan vulnerabilities, DAM database queries, and compliance filings into one synchronized tactical command center.',
    laymanAnalogy: "Like a Joint Operations Command Center that monitors naval radar, air defenses, infantry movements, and legal rules of engagement simultaneously on a single unified tactical board, ensuring no unit operates in the dark.",
    whatItHelpsWithDetailed: [
      'Allows CISOs and Transversal Administrators to oversee all 7 cognitive engines in real time.',
      'Correlates perimeter defenses (WAF) directly with application defects (AppScan) and database access (DAM).',
      'Provides instantaneous cross-department risk posture across National, Provincial, Departmental, and Branch tiers.',
      'Maintains 100% tenant isolation with zero cross-tenant leakage between organs of state.'
    ],
    deterministicBaseline: 'Separate disjointed dashboards for AppScan, Imperva WAF, Imperva DAM, and static audit spreadsheets.',
    cognitiveAiAdvantage: 'Unified real-time reasoning and correlation connecting raw vulnerability counts to active adversarial threat campaigns.',
    whyCodeFails: 'Relational databases store tables in silos. Code cannot semantically link an unpatched web defect to an active adversary campaign without human-like cognitive inference.',
    operationalGain: 'Replaces 4 fragmented vendor consoles with a single command screen; speeds transversal triaging from days to minutes.',
    governingOutcome: 'D0 Outcomes 1–7 (Consolidated Security Reporting Mandate)'
  },
  'g2-report': {
    key: 'g2-report',
    engineName: 'G2 AI Report Studio & Grounded Copilot',
    icon: '🧠',
    badge: 'STAGE 4 / G2 VERIFIED',
    targetRoles: [
      { id: 'exec', label: 'Executive Leadership / DG', color: '#f87171', bg: 'rgba(239,68,68,0.15)' },
      { id: 'admin', label: 'Transversal Admin / CISO', color: '#34d399', bg: 'rgba(52,211,153,0.15)' },
      { id: 'compliance', label: 'Audit & Compliance', color: '#c084fc', bg: 'rgba(192,132,252,0.15)' },
    ],
    headline: 'Instant Cabinet-Ready Executive Briefings with Zero-Hallucination Numeral Verifier',
    roleHelpSummary: 'Helps Ministers, Director-Generals, and CISOs instantly understand their exact cyber risk posture and author board-defensible briefings in 8 seconds with 100% verified numbers.',
    laymanAnalogy: "Like a Minister having a veteran Chief of Staff who reviews 500 pages of technical scan logs every morning and delivers a 1-page briefing explaining: 'Our risk rose by 14% because a global ransomware campaign is actively targeting state health systems, and our hospital servers have an unpatched Apache defect matching their exact playbook.'",
    whatItHelpsWithDetailed: [
      'Generates plain-language executive narratives explaining complex technical findings to non-technical leaders.',
      'Enforces Gate 1 & Gate 2 multi-tenant data pruning so no department ever sees another department\'s confidential data.',
      'Automated Numeral Verifier checks every digit against the SQL warehouse; discards any hallucinated claims.',
      'Provides an interactive Grounded Copilot for rapid Q&A during parliamentary and board oversight sessions.',
      'Enables 1-click export to branded DOCX and PDF briefings signed with ECDSA cryptographic hashes.'
    ],
    deterministicBaseline: 'Calculates composite risk score formula (e.g. 58 - 42 = +16); displays mathematical line charts and counts.',
    cognitiveAiAdvantage: 'Reads external intelligence, correlates it with estate defects, and authors persuasive, executive-grade briefs in under 8 seconds.',
    whyCodeFails: 'Traditional code can compute score differences, but code cannot read English intelligence bulletins, understand adversary motivations, or author executive prose.',
    operationalGain: 'Cuts executive briefing preparation from 3 days to 8 seconds; guarantees 100% audit defensibility.',
    governingOutcome: 'AI-01 to AI-05 (Outcome 1 - Plain Language Security Narratives)'
  },
  'aimi-vapt': {
    key: 'aimi-vapt',
    engineName: 'AIMI Blue-Team Telemetry & VAPT Interpreter',
    icon: '🛡️',
    badge: 'BLUE-TEAM DEFENSE',
    targetRoles: [
      { id: 'soc', label: 'SOC Lead / Threat Hunter', color: '#60a5fa', bg: 'rgba(59,130,246,0.15)' },
      { id: 'appsec', label: 'AppSec Engineer', color: '#fbbf24', bg: 'rgba(245,158,11,0.15)' },
      { id: 'sre', label: 'Site Reliability / Ops', color: '#94a3b8', bg: 'rgba(148,163,184,0.15)' },
      { id: 'compliance', label: 'Compliance Officer', color: '#c084fc', bg: 'rgba(192,132,252,0.15)' },
    ],
    headline: 'Real-Time Perimeter DMZ Resilience, Containment Verification & Exploit Forensics',
    roleHelpSummary: 'Helps SOC and AppSec engineers verify that perimeter WAF blocks successfully shielded internal databases from VAPT exploit vectors, providing empirical proof of zero compromise.',
    laymanAnalogy: "Like an automated naval defense grid that intercepts incoming ballistic missiles at the perimeter DMZ while verifying that internal bulkhead blast doors remain sealed and undamaged.",
    whatItHelpsWithDetailed: [
      'Correlates live WAF block events, AppScan vulnerabilities, and DAM database logs against VAPT test vectors.',
      'Computes Perimeter Resilience Grade (e.g., Grade A 100%) and Exploitability Index (/10) in real time.',
      'Infers attacker typology, profiling whether traffic stems from automated scrapers or coordinated APT syndicates.',
      'Provides role-differentiated forensic tabs: technical payloads for SOC, ISO 27001 proof for Compliance, and blast radius for Executives.',
      'Verifies continuous neutralization of remediated baseline vulnerabilities via live signature tracking.'
    ],
    deterministicBaseline: 'Collects raw WAF event logs, HTTP error codes, and static AppScan CWE tables in isolation.',
    cognitiveAiAdvantage: 'Semantically matches attack payloads against VAPT baseline test vectors, infers attacker intent/typology, and synthesizes virtual patching instructions.',
    whyCodeFails: 'Ordinary firewalls log raw IP addresses and ports. Code cannot infer attacker intent or assess whether a WAF block successfully shielded an underlying unpatched database procedure.',
    operationalGain: 'Proves 100% perimeter containment; prevents false-alarm panic; saves SOC analysts 15 hours per week of manual log correlation.',
    governingOutcome: 'Outcome 4 (Guaranteed Resilience) & AIR-R4 (Data Privacy Safeguards)'
  },
  'avp-2': {
    key: 'avp-2',
    engineName: 'AVP-2 Autonomous Alert Rule Authoring Engine',
    icon: '🎯',
    badge: 'DETECTION ENG',
    targetRoles: [
      { id: 'appsec', label: 'AppSec Engineer', color: '#fbbf24', bg: 'rgba(245,158,11,0.15)' },
      { id: 'soc', label: 'SOC Detection Engineer', color: '#60a5fa', bg: 'rgba(59,130,246,0.15)' },
    ],
    headline: 'Synthesizing Schema-Compliant Alert Rules from MITRE ATT&CK Techniques',
    roleHelpSummary: 'Helps AppSec and SOC engineers convert newly published attacker techniques into valid, reviewable YAML detection rules matching SITA\'s schema in under 2 minutes.',
    laymanAnalogy: "Like an expert locksmith who, upon hearing that burglars designed a new master key, instantly fabricates custom deadbolts for every government building that fit the doors perfectly without jamming the locks.",
    whatItHelpsWithDetailed: [
      'Ingests MITRE ATT&CK technique IDs (e.g. T1190) and maps them to SITA\'s internal log sources.',
      'Selects appropriate normalized field predicates, thresholds, and severity ratings.',
      'Outputs syntactically valid YAML rules directly adhering to alert_rules.yaml standards.',
      'Presents a color-coded side-by-side Git diff for operator review and verification.',
      'Strictly enforces human-in-the-loop governance: rules are never automatically merged without sign-off.'
    ],
    deterministicBaseline: 'Runs HCL AppScan DAST and SAST scanners; produces static spreadsheets with 69 CWE defect rows.',
    cognitiveAiAdvantage: 'Translates external MITRE techniques into custom YAML alert rules matching SITA\'s database schema with diff viewers.',
    whyCodeFails: 'External Sigma or Splunk rules use foreign taxonomies. Traditional code cannot infer semantic equivalence between foreign rule parameters and SITA\'s custom database schema without generating syntax errors.',
    operationalGain: 'Rule deployment drops from 48 hours to 2 minutes; zero schema syntax errors; zero risk of untested autonomous commits.',
    governingOutcome: 'AIR-R2 (Automated Alert Rule Authoring)'
  },
  'avp-3': {
    key: 'avp-3',
    engineName: 'AVP-3 Threat Campaign Attribution Engine',
    icon: '🔍',
    badge: 'THREAT INTEL',
    targetRoles: [
      { id: 'soc', label: 'SOC Analyst / Threat Hunter', color: '#60a5fa', bg: 'rgba(59,130,246,0.15)' },
      { id: 'appsec', label: 'AppSec Engineer', color: '#fbbf24', bg: 'rgba(245,158,11,0.15)' },
    ],
    headline: 'Semantic Mapping of Adversary Advisories to Live Estate Vulnerabilities',
    roleHelpSummary: 'Helps SOC threat hunters paste raw external advisories (CISA, CERT, OSINT) and instantly identify which government departments and applications are exposed to that exact adversary.',
    laymanAnalogy: "Like an air traffic controller equipped with radar that not only detects an unidentified aircraft, but instantly recognizes the flight formation, identifies the hostile squadron, and predicts which airfield they are attempting to bomb.",
    whatItHelpsWithDetailed: [
      'Accepts raw, unstructured threat reports and CTI feeds via simple text paste.',
      'Extracts MITRE ATT&CK techniques, CVE numbers, and targeted industry sectors using semantic reasoning.',
      'Cross-references extracted techniques against SITA\'s live estate exposure tables.',
      'Generates a comprehensive gap analysis highlighting covered versus uncovered attack vectors.',
      'Token-only egress ensures no department names, internal IP addresses, or citizen data leave the secure enclave.'
    ],
    deterministicBaseline: 'Ingests 15,000 WAF and scanner events daily; manual filtering by IP, port, and timestamp.',
    cognitiveAiAdvantage: 'Ingests unstructured threat bulletins, matches attacker tactics to live vulnerabilities, and synthesizes 1-click hunting queries.',
    whyCodeFails: 'Attributing an attack requires semantically parsing narrative threat reports and mapping those concepts to internal CWE categories.',
    operationalGain: 'Reduces threat campaign investigation time from 6 hours to 45 seconds; pinpoints high-risk estate gaps immediately.',
    governingOutcome: 'AI-23 to AI-26 (Outcome 6 - Threat Attribution & User Steering)'
  },
  'avp-5': {
    key: 'avp-5',
    engineName: 'AVP-5 POPIA s.22 Statutory Breach Notification Dossier',
    icon: '⚖️',
    badge: 'COMPLIANCE & LEGAL',
    targetRoles: [
      { id: 'compliance', label: 'Compliance & Legal Officer', color: '#c084fc', bg: 'rgba(192,132,252,0.15)' },
      { id: 'exec', label: 'Information Officer / DG', color: '#f87171', bg: 'rgba(239,68,68,0.15)' },
    ],
    headline: 'Legal Threshold Evaluation & Mandatory Regulator Notification Assembly',
    roleHelpSummary: 'Helps Compliance and Legal Counsel assemble structured breach evidence dossiers and assess statutory disclosure duties under POPIA Section 22 to prevent R10M regulatory fines.',
    laymanAnalogy: "Like having a Senior Advocate specializing in cyber law standing beside the IT team during a suspected data leak, immediately reviewing technical evidence and drafting a legally binding notice to the Information Regulator before deadlines expire.",
    whatItHelpsWithDetailed: [
      'Gathers all compromise indicators (critical findings, high findings, alert counts) across a customizable investigation window.',
      'Structures a rigorous POPIA Section 22 statutory checklist mapped to South African privacy jurisprudence.',
      'Differentiates between technical anomalies and legally reportable breaches involving unauthorized citizen personal information access.',
      'Deliberately withholds the final statutory legal verdict for human legal counsel sign-off.',
      'Pre-populates statutory notification templates ready for Information Regulator filing within the 72-hour window.'
    ],
    deterministicBaseline: 'Evaluates 8 POPIA conditions against available telemetry; generates mathematical compliance scores (0-100).',
    cognitiveAiAdvantage: 'Applies the statutory legal threshold (\'reasonable grounds to believe personal information has been accessed\') to technical facts.',
    whyCodeFails: 'A database cannot interpret statutory legal thresholds. Legal evaluation requires cognitive reasoning over data sensitivity, encryption status, and exfiltration likelihood.',
    operationalGain: 'Guarantees statutory reporting within the regulatory window; prevents R10,000,000 administrative fines from the Information Regulator.',
    governingOutcome: 'Outcome 7 (POPIA Section 22 Statutory Breach Dossier)'
  },
  'avp-8': {
    key: 'avp-8',
    engineName: 'AVP-8 Risk-Delta Causal Attribution Engine',
    icon: '📈',
    badge: 'RISK ANALYTICS',
    targetRoles: [
      { id: 'exec', label: 'Executive Leadership / DG', color: '#f87171', bg: 'rgba(239,68,68,0.15)' },
      { id: 'soc', label: 'Risk Manager / SOC Lead', color: '#60a5fa', bg: 'rgba(59,130,246,0.15)' },
    ],
    headline: 'Root-Cause Explanation of Mathematical Risk-Score Shifts',
    roleHelpSummary: 'Helps Executives and Risk Managers explain the underlying systemic "Why" behind security posture shifts (e.g. Why risk rose by +16) by correlating external threat activity with estate defects.',
    laymanAnalogy: "Like a financial portfolio manager who doesn't just state that the fund lost 3%, but explains that an unexpected central bank interest rate hike in Asia triggered an automated bond sell-off affecting specific state holdings.",
    whatItHelpsWithDetailed: [
      'Analyzes score shifts over 2 to 90-day windows across specific state applications.',
      'Identifies the primary contributing telemetry signal driving the mathematical delta.',
      'Maps the root cause to specific MITRE ATT&CK techniques and correlates with external threat bulletins.',
      'Produces an explainable narrative stub ready for inclusion in ministerial briefings.',
      'Helps leadership prioritize remediation budget on defects that adversaries are actively weaponizing.'
    ],
    deterministicBaseline: 'Calculates composite risk score formula (e.g. 58 - 42 = +16); displays mathematical line charts.',
    cognitiveAiAdvantage: 'Explains the \'Why\' behind a mathematical score shift by correlating external threat activity with internal vulnerabilities.',
    whyCodeFails: 'Traditional code computes the arithmetic difference (+16), but code cannot read threat bulletins, understand adversary motivations, or author executive narratives.',
    operationalGain: 'Transforms raw numbers into actionable business intelligence; eliminates days of manual post-mortem investigation.',
    governingOutcome: 'AI-01 to AI-05 (Outcome 1 - Causal Attribution & Risk Explanation)'
  },
  'avp-11': {
    key: 'avp-11',
    engineName: 'AVP-11 Behavioral Sequence & Privilege Analysis',
    icon: '🔎',
    badge: 'BEHAVIORAL AI',
    targetRoles: [
      { id: 'admin', label: 'Internal Audit & Forensics', color: '#34d399', bg: 'rgba(52,211,153,0.15)' },
      { id: 'compliance', label: 'Compliance Officer', color: '#c084fc', bg: 'rgba(192,132,252,0.15)' },
      { id: 'exec', label: 'Executive Leadership', color: '#f87171', bg: 'rgba(239,68,68,0.15)' },
    ],
    headline: 'Multi-Day Temporal Pattern Detection Across Signed Audit Logs',
    roleHelpSummary: 'Helps Internal Auditors and Platform Admins identify non-linear insider threat patterns (self-approval, escalating exports, privilege creep) that bypass standard single-event rules.',
    laymanAnalogy: "Like an expert forensic investigator who reviews an employee's actions over 60 days, recognizing that while each single action seemed normal on paper, the combined sequence proves they were preparing to embezzle state funds.",
    whatItHelpsWithDetailed: [
      'Clusters signed audit events (audit.action_audit) into chronological multi-day chains.',
      'Detects complex insider abuse patterns: SELF_APPROVE_CHAIN, ESCALATING_EXPORT, CROSS_SCOPE_PIVOT, and RAPID_AUTHORITY_SWEEP.',
      'Computes statistical confidence scores for each detected anomalous cluster.',
      'Generates explainable narration stubs to support formal disciplinary or forensic inquests.',
      'Provides verifiable cryptographic evidence for the Auditor-General.'
    ],
    deterministicBaseline: 'Cryptographically logs every administrative API request with ECDSA signatures; checks single-event authorization against RBAC.',
    cognitiveAiAdvantage: 'Interprets multi-day non-linear event sequences in signed audit logs to recognize insider intent and privilege abuse.',
    whyCodeFails: 'Rule-based security only evaluates single isolated events (\'was user authorized to export?\'). It cannot synthesize a 20-step chronological narrative to recognize coordinated insider malice.',
    operationalGain: 'Catches slow, low-and-slow insider threats before catastrophic data exfiltration occurs; ensures a clean Auditor-General audit.',
    governingOutcome: 'Outcome 5 (Auditability, Model Hashing & Privilege Integrity)'
  },
};

export function RoleExplanationModal({
  guidance,
  open,
  onClose,
}: {
  guidance: RoleGuidanceItem;
  open: boolean;
  onClose: () => void;
}) {
  if (!open) return null;

  return (
    <div
      className="overlay open"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      style={{
        zIndex: 10000,
        backdropFilter: 'blur(10px)',
        background: 'rgba(10, 15, 30, 0.85)',
      }}
    >
      <div
        className="overlay-content"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 820,
          maxWidth: '94vw',
          maxHeight: '88vh',
          background: 'var(--ai-modal-bg)',
          border: '1px solid var(--ai-card-border)',
          boxShadow: '0 25px 70px rgba(0, 0, 0, 0.4), var(--ai-card-shadow)',
          borderRadius: 18,
          padding: '28px 32px',
          color: 'var(--text-primary)',
        }}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="overlay-close"
          style={{
            background: 'var(--surface-2)',
            border: '1px solid var(--border-dim)',
            color: 'var(--text-secondary)',
          }}
        >
          ✕
        </button>

        {/* Modal Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16 }}>
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: 14,
              background: 'linear-gradient(135deg, #312e81, #4338ca)',
              border: '1px solid rgba(129, 140, 248, 0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 26,
              boxShadow: '0 4px 16px rgba(99,102,241,0.3)',
            }}
          >
            {guidance.icon}
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 800,
                  color: '#818cf8',
                  letterSpacing: '0.08em',
                  background: 'rgba(99,102,241,0.15)',
                  padding: '2px 8px',
                  borderRadius: 6,
                  border: '1px solid rgba(99,102,241,0.3)',
                }}
              >
                {guidance.badge}
              </span>
              <span style={{ fontSize: 11, color: '#34d399', fontWeight: 600 }}>• Role Advantage Playbook</span>
            </div>
            <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--text-primary)' }}>{guidance.engineName}</div>
          </div>
        </div>

        {/* Target Roles Badges Bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            flexWrap: 'wrap',
            marginBottom: 20,
            padding: '10px 14px',
            borderRadius: 10,
            background: 'var(--ai-subcard-bg)',
            border: '1px solid var(--ai-subcard-border)',
          }}
        >
          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)' }}>Target Roles Supported:</span>
          {guidance.targetRoles.map((role) => (
            <span
              key={role.id}
              style={{
                fontSize: 11,
                fontWeight: 700,
                padding: '3px 10px',
                borderRadius: 20,
                color: role.color,
                background: role.bg,
                border: `1px solid ${role.color}44`,
              }}
            >
              {role.label}
            </span>
          ))}
        </div>

        {/* Layman Analogy Callout (Official SITA Matrix) */}
        <div
          style={{
            padding: '16px 20px',
            borderRadius: 12,
            marginBottom: 20,
            background: 'var(--amber-dim)',
            border: '1px solid var(--amber)',
            boxShadow: '0 4px 20px rgba(0,0,0,0.06)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <span style={{ fontSize: 16 }}>💡</span>
            <span style={{ fontSize: 11, fontWeight: 800, color: 'var(--amber)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Layman&apos;s Real-World Analogy
            </span>
          </div>
          <div style={{ fontSize: 13.5, color: 'var(--text-primary)', lineHeight: 1.6, fontStyle: 'italic' }}>
            &ldquo;{guidance.laymanAnalogy}&rdquo;
          </div>
        </div>

        {/* What it Helps That Role With Section */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--blue)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
            🎯 What this engine specifically helps that role with:
          </div>
          <div style={{ fontSize: 14, color: 'var(--text-primary)', fontWeight: 600, marginBottom: 10, lineHeight: 1.5 }}>
            {guidance.headline}
          </div>
          <ul style={{ paddingLeft: 20, margin: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {guidance.whatItHelpsWithDetailed.map((item, idx) => (
              <li key={idx} style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                {item}
              </li>
            ))}
          </ul>
        </div>

        {/* Two-Column Comparison: Deterministic Baseline vs Cognitive Advantage */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: 14,
            marginBottom: 20,
          }}
        >
          <div
            style={{
              padding: '14px 16px',
              borderRadius: 10,
              background: 'var(--ai-subcard-bg)',
              border: '1px solid var(--ai-subcard-border)',
            }}
          >
            <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
              ⚙️ Deterministic Foundation (Ordinary Code)
            </div>
            <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {guidance.deterministicBaseline}
            </div>
          </div>

          <div
            style={{
              padding: '14px 16px',
              borderRadius: 10,
              background: 'var(--blue-dim)',
              border: '1px solid var(--blue)',
            }}
          >
            <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--blue)', textTransform: 'uppercase', marginBottom: 6 }}>
              🧠 Cognitive AI Advantage (AIMI Residue)
            </div>
            <div style={{ fontSize: 12.5, color: 'var(--text-primary)', lineHeight: 1.5 }}>
              {guidance.cognitiveAiAdvantage}
            </div>
          </div>
        </div>

        {/* Why Code Alone Fails */}
        <div
          style={{
            padding: '12px 16px',
            borderRadius: 10,
            background: 'var(--red-dim)',
            border: '1px solid var(--red)',
            marginBottom: 20,
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--red)', textTransform: 'uppercase', marginBottom: 4 }}>
            ⚠️ Why Traditional Code Alone Fails:
          </div>
          <div style={{ fontSize: 12.5, color: 'var(--text-primary)', lineHeight: 1.5 }}>
            {guidance.whyCodeFails}
          </div>
        </div>

        {/* Operational Gain & Mandate Footer */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 12,
            paddingTop: 16,
            borderTop: '1px solid var(--border-dim)',
          }}
        >
          <div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Operational Gain: </span>
            <strong style={{ fontSize: 12, color: 'var(--green)' }}>{guidance.operationalGain}</strong>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 11, color: 'var(--blue)', fontWeight: 600 }}>{guidance.governingOutcome}</span>
            <button
              onClick={onClose}
              style={{
                padding: '6px 18px',
                borderRadius: 8,
                background: 'linear-gradient(135deg, #4f46e5, #6366f1)',
                border: 'none',
                color: '#fff',
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              Done &rarr;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function RoleExplanationFootlink({
  viewKey,
  onOpenModal,
}: {
  viewKey: string;
  onOpenModal: () => void;
}) {
  const [inlineExpanded, setInlineExpanded] = useState(false);
  const guidance = ROLE_GUIDANCE_MAP[viewKey] || ROLE_GUIDANCE_MAP.all;

  return (
    <div
      className="role-explanation-footlink"
      style={{
        borderRadius: 12,
        background: 'var(--ai-footlink-bg)',
        border: '1px solid var(--ai-card-border)',
        boxShadow: 'var(--ai-card-shadow)',
        padding: '12px 18px',
        marginTop: 14,
        marginBottom: 16,
        transition: 'all 0.2s ease',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: '1 1 360px' }}>
          <span style={{ fontSize: 22 }}>💡</span>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 800,
                  color: 'var(--blue)',
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                }}
              >
                ROLE ADVANTAGE GUIDANCE
              </span>
              <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>• Target Roles:</span>
              <div style={{ display: 'inline-flex', gap: 4, flexWrap: 'wrap' }}>
                {guidance.targetRoles.slice(0, 3).map((r) => (
                  <span
                    key={r.id}
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      padding: '1px 6px',
                      borderRadius: 12,
                      color: r.color,
                      background: r.bg,
                    }}
                  >
                    {r.label}
                  </span>
                ))}
                {guidance.targetRoles.length > 3 && (
                  <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                    +{guidance.targetRoles.length - 3} more
                  </span>
                )}
              </div>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-primary)', marginTop: 2, lineHeight: 1.4 }}>
              <strong>What it helps this role with:</strong> {guidance.roleHelpSummary}
            </div>
          </div>
        </div>

        {/* Action Footlinks */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <button
            onClick={() => setInlineExpanded(!inlineExpanded)}
            style={{
              padding: '6px 12px',
              borderRadius: 8,
              background: 'var(--surface-2)',
              border: '1px solid var(--border-dim)',
              color: 'var(--text-secondary)',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <span>{inlineExpanded ? '▴ Hide Quick Guide' : '▾ Quick Guide'}</span>
          </button>

          <button
            id={`footlink-role-guide-${viewKey}`}
            onClick={onOpenModal}
            style={{
              padding: '6px 14px',
              borderRadius: 8,
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.25), rgba(139, 92, 246, 0.35))',
              border: '1px solid rgba(99, 102, 241, 0.5)',
              color: 'var(--blue)',
              fontSize: 11,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'linear-gradient(135deg, #4f46e5, #6366f1)';
              e.currentTarget.style.color = '#fff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background =
                'linear-gradient(135deg, rgba(99, 102, 241, 0.25), rgba(139, 92, 246, 0.35))';
              e.currentTarget.style.color = 'var(--blue)';
            }}
          >
            <span>📖</span>
            <span>View Role Playbook &amp; Layman Analogy &rarr;</span>
          </button>
        </div>
      </div>

      {/* Inline Quick Guide (collapsible) */}
      {inlineExpanded && (
        <div
          style={{
            marginTop: 12,
            paddingTop: 12,
            borderTop: '1px solid var(--border-dim)',
            animation: 'aiFlashFadeIn 0.2s ease',
          }}
        >
          <div
            style={{
              padding: '10px 14px',
              borderRadius: 8,
              background: 'var(--amber-dim)',
              border: '1px solid var(--amber)',
              fontSize: 12,
              color: 'var(--text-primary)',
              marginBottom: 10,
              lineHeight: 1.5,
            }}
          >
            <strong style={{ color: 'var(--amber)' }}>Layman&apos;s Analogy:</strong> &ldquo;{guidance.laymanAnalogy}&rdquo;
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 10 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5 }}>
              <strong style={{ color: 'var(--text-secondary)' }}>Deterministic Code Limit:</strong> {guidance.deterministicBaseline}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-primary)', lineHeight: 1.5 }}>
              <strong style={{ color: 'var(--blue)' }}>AI Cognitive Elevation:</strong> {guidance.cognitiveAiAdvantage}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
