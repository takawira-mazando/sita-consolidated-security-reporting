import type { Finding, PaginatedResponse } from '../types';

// Home Affairs branches
const DHA_BRANCHES = [
  { id: 'dha-civic', name: 'Civic Services' },
  { id: 'dha-digital', name: 'Information Services (CIO)' },
  { id: 'dha-immigration', name: 'Immigration Services' },
  { id: 'dha-operations', name: 'Operations' },
  { id: 'dha-hrmd', name: 'Human Resource Management and Development' },
  { id: 'dha-ccss', name: 'Counter Corruption and Security Services' },
  { id: 'dha-finance', name: 'Finance and Supply Chain Management' },
  { id: 'dha-planning', name: 'Institutional Planning and Support' },
] as const;

// Branch-specific apps for Home Affairs
const DHA_BRANCH_APPS: Record<string, string[]> = {
  'dha-civic': [
    'Civic Services Portal',
    'National Population Register',
    'Identity Document System',
    'Birth Registration System',
  ],
  'dha-digital': [
    'eHomeAffairs Portal',
    'SITA API Gateway',
    'Digital Identity Platform',
    'Online Services Gateway',
  ],
  'dha-immigration': [
    'Movement Control System',
    'Visa Processing System',
    'Refugee Management System',
    'Border Control System',
  ],
  'dha-operations': [
    'Operations Management System',
    'Service Delivery Platform',
    'Queue Management System',
    'Document Tracking System',
  ],
  'dha-hrmd': [
    'HR Management System',
    'Payroll System',
    'Learning Management System',
    'Performance Management',
  ],
  'dha-ccss': [
    'Security Incident System',
    'Counter Corruption Portal',
    'Vetting System',
    'Compliance Tracker',
  ],
  'dha-finance': [
    'Finance Management System',
    'Supply Chain Portal',
    'Asset Management System',
    'Revenue Collection System',
  ],
  'dha-planning': [
    'Strategic Planning System',
    'Monitoring & Evaluation',
    'Reporting Dashboard',
    'Policy Management System',
  ],
};

// Fallback apps for nationwide or unknown branches
const DEMO_APPS = [
  'XYZ Application',
  'FlorenceCassandraCluster',
  'sita-portal',
  'sita-api-gateway',
  'sita-hr-system',
  'sita-finance',
  'sita-procurement',
  'sita-reporting',
  'demo.testfire.net',
];

function getAppsForBranch(branchId?: string): string[] {
  if (branchId && DHA_BRANCH_APPS[branchId]) {
    return DHA_BRANCH_APPS[branchId];
  }
  return DEMO_APPS;
}

// Seeded Thales DAM SonarG & Database Security findings (from Thales generator)
const THALES_DAM_FINDINGS: Finding[] = [
  {
    id: 'thales-dam-001',
    source: 'thales',
    external_id: 'THALES-SONAR-90f6-001',
    app_name: 'FlorenceCassandraCluster',
    severity: 'critical',
    title: 'Unauthorized TRUNCATE on keyspace select_keyspace',
    description: 'Thales DAM detected unauthorized TRUNCATE TABLE execution on FlorenceCassandraCluster (IP 172.31.82.207) by user florence_node1.',
    category: 'Database Security',
    first_seen: '2026-08-25T11:15:00.000Z',
    last_seen: '2026-08-25T11:15:22.000Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 9.2,
  },
  {
    id: 'thales-dam-002',
    source: 'thales',
    external_id: 'THALES-SONAR-90f6-002',
    app_name: 'FlorenceCassandraCluster',
    severity: 'high',
    title: 'Excessive Failed CQL Queries from 172.16.4.89',
    description: 'Thales DAM SonarG alert: Over 45 failed CQL authentication & query attempts within 60s window on CassandraVer401.',
    category: 'Database Security',
    first_seen: '2026-08-25T10:30:00.000Z',
    last_seen: '2026-08-25T10:45:00.000Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 7.8,
  },
  {
    id: 'thales-dam-003',
    source: 'thales',
    external_id: 'THALES-SONAR-90f6-003',
    app_name: 'FlorenceCassandraCluster',
    severity: 'high',
    title: 'Privileged Schema Modification (DDL) during Non-Maintenance Window',
    description: 'Cassandra DDL ALTER KEYSPACE executed on user_keyspace outside change freeze window by DB user florence_node1.',
    category: 'Database Policy Violation',
    first_seen: '2026-08-24T18:22:00.000Z',
    last_seen: '2026-08-24T18:22:05.000Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 7.4,
  },
  {
    id: 'thales-dam-004',
    source: 'thales',
    external_id: 'THALES-SONAR-90f6-004',
    app_name: 'FlorenceCassandraCluster',
    severity: 'medium',
    title: 'Unindexed Full Table Scan on audit_keyspace',
    description: 'Thales DAM baseline anomaly: SELECT statement without partition key filtering detected on CassandraVer401 node.',
    category: 'Database Security',
    first_seen: '2026-08-24T14:10:00.000Z',
    last_seen: '2026-08-24T14:12:00.000Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 5.5,
  },
];

const DEMO_CATEGORIES = [
  'Injection',
  'Broken Access Control',
  'Cryptographic Failures',
  'Insecure Design',
  'Security Misconfiguration',
  'Vulnerable Components',
  'Authentication Failures',
  'Software Integrity Failures',
  'Logging Failures',
  'SSRF',
];

const DEMO_SEVERITIES = ['critical', 'high', 'medium', 'low'] as const;

const DEMO_STATUSES = ['Open', 'Open', 'Open', 'Fixed', 'In Progress', 'Not a Finding'];

function seededRandom(seed: number) {
  let x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

// Real AppScan findings from demo.testfire.net scan (2026-08-24)
const REAL_APPSACN_FINDINGS: Finding[] = [
  {
    id: 'appscan-sql-1',
    source: 'appscan',
    external_id: 'APPSACN-SQL-001',
    app_name: 'demo.testfire.net',
    severity: 'critical',
    title: 'SQL Injection in /bank/showtransactions',
    description: 'SQL Injection vulnerability in the transaction history endpoint allows attackers to execute arbitrary SQL commands via the account parameter.',
    category: 'Injection',
    first_seen: '2026-08-24T09:28:00.283Z',
    last_seen: '2026-08-25T07:06:34.209Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 9.8,
  },
  {
    id: 'appscan-sql-2',
    source: 'appscan',
    external_id: 'APPSACN-SQL-002',
    app_name: 'demo.testfire.net',
    severity: 'critical',
    title: 'SQL Injection in /bank/showtransactions (variant)',
    description: 'Second SQL Injection variant in the same endpoint with different payload delivery.',
    category: 'Injection',
    first_seen: '2026-08-24T09:28:00.283Z',
    last_seen: '2026-08-25T07:06:34.209Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 9.5,
  },
  {
    id: 'appscan-xss-1',
    source: 'appscan',
    external_id: 'APPSACN-XSS-001',
    app_name: 'demo.testfire.net',
    severity: 'high',
    title: 'Reflected XSS in /search.jsp',
    description: 'Reflected Cross-Site Scripting in search parameter allows execution of arbitrary JavaScript in victim\'s browser.',
    category: 'Injection',
    first_seen: '2026-08-24T09:28:00.283Z',
    last_seen: '2026-08-25T07:06:34.209Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 7.1,
  },
  {
    id: 'appscan-xss-2',
    source: 'appscan',
    external_id: 'APPSACN-XSS-002',
    app_name: 'demo.testfire.net',
    severity: 'high',
    title: 'Reflected XSS in /index.jsp',
    description: 'Reflected XSS in the homepage via query parameter.',
    category: 'Injection',
    first_seen: '2026-08-24T09:28:00.283Z',
    last_seen: '2026-08-25T07:06:34.209Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 7.1,
  },
  {
    id: 'appscan-xss-3',
    source: 'appscan',
    external_id: 'APPSACN-XSS-003',
    app_name: 'demo.testfire.net',
    severity: 'high',
    title: 'Reflected XSS in /sendfeedback',
    description: 'Reflected XSS in feedback form submission.',
    category: 'Injection',
    first_seen: '2026-08-24T09:28:00.283Z',
    last_seen: '2026-08-25T07:06:34.209Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 7.1,
  },
  {
    id: 'appscan-xss-4',
    source: 'appscan',
    external_id: 'APPSACN-XSS-004',
    app_name: 'demo.testfire.net',
    severity: 'high',
    title: 'Reflected XSS in /sendfeedback (variant)',
    description: 'Second XSS variant in feedback form.',
    category: 'Injection',
    first_seen: '2026-08-24T09:28:00.283Z',
    last_seen: '2026-08-25T07:06:34.209Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 7.1,
  },
  {
    id: 'appscan-xss-5',
    source: 'appscan',
    external_id: 'APPSACN-XSS-005',
    app_name: 'demo.testfire.net',
    severity: 'high',
    title: 'Reflected XSS in /util/serverstatuscheckservice.jsp',
    description: 'Reflected XSS in server status check service.',
    category: 'Injection',
    first_seen: '2026-08-24T09:28:00.283Z',
    last_seen: '2026-08-25T07:06:34.209Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 7.1,
  },
  {
    id: 'appscan-xss-6',
    source: 'appscan',
    external_id: 'APPSACN-XSS-006',
    app_name: 'demo.testfire.net',
    severity: 'high',
    title: 'Reflected XSS in /bank/queryxpath.jsp',
    description: 'Reflected XSS in XPath query endpoint.',
    category: 'Injection',
    first_seen: '2026-08-24T09:28:00.283Z',
    last_seen: '2026-08-25T07:06:34.209Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 7.1,
  },
  {
    id: 'appscan-xss-7',
    source: 'appscan',
    external_id: 'APPSACN-XSS-007',
    app_name: 'demo.testfire.net',
    severity: 'high',
    title: 'Reflected XSS in /bank/queryxpath.jsp (variant)',
    description: 'Second XSS variant in XPath query endpoint.',
    category: 'Injection',
    first_seen: '2026-08-24T09:28:00.283Z',
    last_seen: '2026-08-25T07:06:34.209Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 7.1,
  },
  {
    id: 'appscan-xss-8',
    source: 'appscan',
    external_id: 'APPSACN-XSS-008',
    app_name: 'demo.testfire.net',
    severity: 'high',
    title: 'Reflected XSS in /bank/customize.jsp',
    description: 'Reflected XSS in customize profile endpoint.',
    category: 'Injection',
    first_seen: '2026-08-24T09:28:00.283Z',
    last_seen: '2026-08-25T07:06:34.209Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 7.1,
  },
  {
    id: 'appscan-xss-9',
    source: 'appscan',
    external_id: 'APPSACN-XSS-009',
    app_name: 'demo.testfire.net',
    severity: 'high',
    title: 'Reflected XSS in /bank/customize.jsp (variant)',
    description: 'Second XSS variant in customize profile endpoint.',
    category: 'Injection',
    first_seen: '2026-08-24T09:28:00.283Z',
    last_seen: '2026-08-25T07:06:34.209Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 7.1,
  },
  {
    id: 'appscan-overflow-1',
    source: 'appscan',
    external_id: 'APPSACN-OVF-001',
    app_name: 'demo.testfire.net',
    severity: 'high',
    title: 'Integer Overflow in /bank/showaccount',
    description: 'Integer overflow in account balance calculation allows manipulation of financial values.',
    category: 'Insecure Design',
    first_seen: '2026-08-24T09:28:00.283Z',
    last_seen: '2026-08-25T07:06:34.209Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 7.5,
  },
  {
    id: 'appscan-overflow-2',
    source: 'appscan',
    external_id: 'APPSACN-OVF-002',
    app_name: 'demo.testfire.net',
    severity: 'high',
    title: 'Integer Overflow in /bank/dotransfer',
    description: 'Integer overflow in fund transfer allows bypassing balance checks.',
    category: 'Insecure Design',
    first_seen: '2026-08-24T09:28:00.283Z',
    last_seen: '2026-08-25T07:06:34.209Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 7.5,
  },
  {
    id: 'appscan-redirect-1',
    source: 'appscan',
    external_id: 'APPSACN-REDIR-001',
    app_name: 'demo.testfire.net',
    severity: 'high',
    title: 'Phishing Through URL Redirection in /bank/customize.jsp',
    description: 'Open redirect vulnerability allows phishing attacks via crafted redirect URLs.',
    category: 'Insecure Design',
    first_seen: '2026-08-24T09:28:00.283Z',
    last_seen: '2026-08-25T07:06:34.209Z',
    status: 'Open',
    version: 1,
    cve: undefined,
    cvss_score: 6.1,
  },
];

function generateDemoFindings(count: number = 108, branchId?: string): Finding[] {
  const findings: Finding[] = [];
  const baseDate = new Date('2026-06-01T00:00:00Z');
  const apps = getAppsForBranch(branchId);

  for (let i = 0; i < count; i++) {
    const appIdx = i % apps.length;
    const app = apps[appIdx];
    const severity = DEMO_SEVERITIES[i % 4];
    const category = DEMO_CATEGORIES[i % DEMO_CATEGORIES.length];
    const status = DEMO_STATUSES[i % DEMO_STATUSES.length];
    const daysAgo = Math.floor(seededRandom(i * 7) * 60);
    const firstSeen = new Date(baseDate.getTime() + daysAgo * 86400000);
    const lastSeen = new Date(firstSeen.getTime() + Math.floor(seededRandom(i * 11) * 5) * 86400000);

    const cve = severity === 'critical' || (severity === 'high' && seededRandom(i * 13) < 0.7)
      ? `CVE-2026-${1000 + (i % 9000)}`
      : undefined;

    findings.push({
      id: `demo-finding-${branchId ? branchId + '-' : ''}${i}`,
      source: 'appscan',
      external_id: `APPSCAN-${app.toUpperCase().replace(/-/g, '')}-${i.toString().padStart(4, '0')}`,
      app_name: app,
      severity,
      title: `${category} in ${app}`,
      description: `[Demo] ${category} vulnerability discovered in ${app}. Allows attacker to ${
        severity === 'critical' ? 'execute arbitrary code'
        : severity === 'high' ? 'access sensitive data'
        : severity === 'medium' ? 'bypass controls'
        : 'enumerate information'
      }.`,
      category,
      first_seen: firstSeen.toISOString(),
      last_seen: lastSeen.toISOString(),
      status,
      version: 1,
      cve,
      cvss_score: severity === 'critical' ? 9.0 + seededRandom(i) * 0.5
        : severity === 'high' ? 7.0 + seededRandom(i) * 1.5
        : severity === 'medium' ? 4.0 + seededRandom(i) * 2.0
        : 1.0 + seededRandom(i) * 1.5,
    });
  }
  return findings;
}

// Combine real AppScan findings with Thales DAM findings and generated demo findings
const GENERATED_DEMO_FINDINGS = generateDemoFindings(108);
const ALL_DEMO_FINDINGS = [...REAL_APPSACN_FINDINGS, ...THALES_DAM_FINDINGS, ...GENERATED_DEMO_FINDINGS];

// Cache for branch-specific findings
const branchFindingsCache: Record<string, Finding[]> = {};

function getBranchFindings(branchId?: string): Finding[] {
  if (!branchId) return ALL_DEMO_FINDINGS;
  
  if (!branchFindingsCache[branchId]) {
    const branchApps = getAppsForBranch(branchId);
    const branchGenerated = generateDemoFindings(108, branchId);
    // Include Thales DAM findings for FlorenceCassandraCluster (shared across branches)
    // Include AppScan findings for demo.testfire.net (shared)
    branchFindingsCache[branchId] = [...REAL_APPSACN_FINDINGS, ...THALES_DAM_FINDINGS, ...branchGenerated];
  }
  return branchFindingsCache[branchId];
}

export function getDemoFindings(params?: {
  app?: string;
  severity?: string;
  category?: string;
  source?: string;
  status?: string;
  since?: string;
  page?: number;
  size?: number;
  branch_id?: string;
}): PaginatedResponse<Finding> {
  const branchId = params?.branch_id;
  let filtered = getBranchFindings(branchId);

  if (params?.app) filtered = filtered.filter(f => f.app_name === params.app);
  if (params?.severity) filtered = filtered.filter(f => f.severity === params.severity);
  if (params?.category) filtered = filtered.filter(f => f.category === params.category);
  if (params?.source) filtered = filtered.filter(f => f.source === params.source);
  if (params?.status) filtered = filtered.filter(f => f.status === params.status);
  if (params?.since) {
    const sinceDate = new Date(params.since);
    filtered = filtered.filter(f => new Date(f.last_seen) >= sinceDate);
  }

  // Sort by last_seen desc
  filtered.sort((a, b) => new Date(b.last_seen).getTime() - new Date(a.last_seen).getTime());

  const page = params?.page || 1;
  const size = params?.size || 50;
  const start = (page - 1) * size;
  const items = filtered.slice(start, start + size);

  return {
    items,
    total: filtered.length,
    page,
    size,
    pages: Math.ceil(filtered.length / size),
  };
}

export function getDemoFinding(id: string, branchId?: string): Finding | undefined {
  const findings = getBranchFindings(branchId);
  return findings.find(f => f.id === id || f.external_id === id);
}

export function getDemoFixRate(branchId?: string): { fix_rate: number } {
  const findings = getBranchFindings(branchId);
  const total = findings.length;
  const fixed = findings.filter(f => f.status === 'Fixed').length;
  return { fix_rate: total > 0 ? Math.round((fixed / total) * 100) : 0 };
}

export function getDemoWafSummary(branchId?: string): { total: number; by_type: Array<{ type: string; count: number }> } {
  const wafTypes = ['SQL Injection', 'XSS', 'Path Traversal', 'Command Injection', 'LDAP Injection', 'RFI/LFI'];
  // Vary counts slightly per branch for realism
  const seed = branchId ? branchId.split('-').reduce((a, c) => a + c.charCodeAt(0), 0) : 0;
  return {
    total: 1247 + (seed % 50),
    by_type: wafTypes.map((type, i) => ({
      type,
      count: Math.floor(100 + (seed + i * 17) % 300 * (6 - i) / 6),
    })).sort((a, b) => b.count - a.count),
  };
}

export function getDemoApiExposure(branchId?: string): { total: number; shadow_total: number; items: Array<{
  endpoint: string;
  app_name: string;
  method: string;
  exposure_score: number;
  is_shadow: boolean;
}> } {
  const endpoints = [
    '/api/v1/users',
    '/api/v1/admin/config',
    '/api/v1/auth/token',
    '/api/v1/reports/export',
    '/api/v1/data/pii',
    '/api/v1/internal/debug',
    '/api/v1/payments/process',
    '/api/v1/files/upload',
    '/api/v1/webhooks/github',
    '/api/v1/metrics/prometheus',
    '/api/v1/audit/logs',
    '/api/v1/secrets/vault',
  ];

  const apps = branchId ? getAppsForBranch(branchId) : DEMO_APPS;
  return {
    total: endpoints.length,
    shadow_total: 4,
    items: endpoints.map((endpoint, i) => ({
      endpoint,
      app_name: apps[i % apps.length],
      method: ['GET', 'POST', 'PUT', 'DELETE'][i % 4],
      exposure_score: Math.floor(30 + Math.random() * 70),
      is_shadow: i >= 8,
    })),
  };
}

export function getDemoPublicSummary(branchId?: string) {
  const findings = getBranchFindings(branchId);
  const apps = branchId ? getAppsForBranch(branchId) : DEMO_APPS;
  const bySeverity: Record<string, number> = {};
  let open = 0;
  for (const f of findings) {
    bySeverity[f.severity] = (bySeverity[f.severity] || 0) + 1;
    if (f.status === 'Open') open++;
  }
  return {
    findings: {
      total: findings.length,
      open,
      by_severity: bySeverity,
    },
    apps: { total: apps.length },
    scans: { total: 24, completed: 22, failed: 2 },
    connectors: {
      appscan: { status: 'healthy', last_poll: new Date().toISOString() },
      imperva_waf: { status: 'healthy', last_poll: new Date().toISOString() },
      apisec: { status: 'healthy', last_poll: new Date().toISOString() },
    },
  };
}

export function getDemoRiskScores(branchId?: string) {
  const apps = branchId ? getAppsForBranch(branchId) : DEMO_APPS;
  const findings = getBranchFindings(branchId);
  return apps.map(app => {
    const appFindings = findings.filter(f => f.app_name === app);
    const critical = appFindings.filter(f => f.severity === 'critical').length;
    const high = appFindings.filter(f => f.severity === 'high').length;
    const medium = appFindings.filter(f => f.severity === 'medium').length;
    const low = appFindings.filter(f => f.severity === 'low').length;
    const score = Math.min(100, Math.round(critical * 10 + high * 5 + medium * 2 + low * 0.5));
    return {
      app_name: app,
      fused_score: score,
      signal_appscan: Math.min(100, critical * 8 + high * 4),
      signal_imperva: Math.floor(Math.random() * 30),
      signal_api_exposure: Math.floor(Math.random() * 25),
      signal_compliance_penalty: Math.floor(Math.random() * 15),
      bucket: score >= 70 ? 'critical' : score >= 40 ? 'high' : score >= 20 ? 'medium' : 'low',
    };
  });
}

export const getDemoRisks = getDemoRiskScores;

export function getDemoCompliance(branchId?: string) {
  // Vary compliance scores slightly per branch for realism
  const seed = branchId ? branchId.split('-').reduce((a, c) => a + c.charCodeAt(0), 0) : 0;
  return {
    frameworks: [
      { name: 'POPIA', score: 72 + (seed % 10), total: 45, passed: 32 + (seed % 5) },
      { name: 'ISO27001', score: 68 + (seed % 8), total: 114, passed: 78 + (seed % 6) },
      { name: 'PCI-DSS', score: 55 + (seed % 12), total: 280, passed: 154 + (seed % 10) },
    ],
    gaps: [
      { framework: 'POPIA', control_id: 'POPIA-5.1', domain: 'Data Processing', description: 'Lawful basis for processing not documented', severity: 'high' },
      { framework: 'ISO27001', control_id: 'A.12.6.1', domain: 'Technical Vulnerabilities', description: 'Vulnerability management process incomplete', severity: 'critical' },
      { framework: 'PCI-DSS', control_id: '6.5.6', domain: 'Injection', description: 'SQL injection protection not validated', severity: 'high' },
    ],
  };
}

export const DEMO_APPS_LIST = DEMO_APPS;
export const DEMO_CATEGORIES_LIST = DEMO_CATEGORIES;
export const DHA_BRANCHES_LIST = DHA_BRANCHES;