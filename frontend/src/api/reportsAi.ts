import api from './client';

export interface ReportMeta {
  report_type: string;
  name?: string;
  title?: string;
  target_audience?: string;
  description?: string;
  classification?: string;
  claim_class?: string;
  cadence?: string;
  icon?: string;
  allowed_roles?: string[];
}

export interface VerificationResult {
  passed: boolean;
  fidelity_score: number;
  discrepancies: string[];
  zero_hallucination_guaranteed: boolean;
}

export interface ReportRecommendation {
  priority?: string;
  action?: string;
  target?: string;
  [key: string]: unknown;
}

export interface GeneratedReport {
  report_id: string;
  report_type: string;
  title: string;
  generated_at: string;
  scope_summary: string;
  scope_hash: string;
  summary: string;
  key_findings: Array<string | { text?: string; finding?: string; [key: string]: unknown }>;
  risk_analysis: string;
  recommendations: Array<string | ReportRecommendation>;
  facts: {
    report_type: string;
    as_of_date: string;
    total_findings: number;
    critical_findings: number;
    high_findings: number;
    medium_findings: number;
    low_findings: number;
    total_apps: number;
    avg_risk_score: number;
    max_risk_score: number;
    risk_safe_count: number;
    risk_monitored_count: number;
    risk_critical_count: number;
    total_alerts: number;
    open_alerts: number;
    compliance_posture_index: number;
    top_categories: Array<{ category: string; count: number }>;
    top_cwes: Array<{ cwe_id: string; count: number }>;
    fact_pack_hash: string;
    [key: string]: unknown;
  };
  verification: VerificationResult;
  fallback_used: boolean;
}

export async function getAvailableAiReports(): Promise<ReportMeta[]> {
  const res = await api.get<ReportMeta[]>('/reports-ai/available');
  return res.data;
}

export async function getAiReportCatalog(): Promise<ReportMeta[]> {
  const res = await api.get<ReportMeta[]>('/reports-ai/catalog');
  return res.data;
}

export async function generateAiReport(reportType: string, focusArea?: string): Promise<GeneratedReport> {
  const res = await api.post<GeneratedReport>('/reports-ai/generate', {
    report_type: reportType,
    focus_area: focusArea || undefined,
  });
  return res.data;
}
