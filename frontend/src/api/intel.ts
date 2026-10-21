import api from './client';

// ── AVP-2: Author Alert Rule ──────────────────────────────────────────────────
export interface AuthorRuleResult {
  avp: string;
  technique_id: string;
  rule_id: string;
  status: string;
  advisory_only: boolean;
  auto_merged: boolean;
  rationale: string;
  rule_definition: Record<string, unknown>;
  proposed_yaml: string;
  git_diff: string;
  governance_note: string;
}

export async function postAuthorRule(params: {
  technique_id: string;
  technique_name?: string;
  severity?: string;
  target_source?: string;
}): Promise<AuthorRuleResult> {
  const { data } = await api.post('/intel/attack/author-rule', null, { params });
  return data;
}

// ── AVP-3: Campaign Attribution ───────────────────────────────────────────────
export interface CampaignAttributionResult {
  avp: string;
  advisory_only: boolean;
  enriched_by_model: boolean;
  extracted_techniques: string[];
  extracted_cves: string[];
  sector_match_candidates: string[];
  exposure_overlap: {
    technique_id: string;
    in_estate: boolean | null;
    coverage_status: string;
  }[];
  coverage_gaps: {
    technique_id: string;
    in_estate: boolean | null;
    coverage_status: string;
  }[];
  analyst_judgement_required: string;
  governance_note: string;
}

export async function postAttributeCampaign(reportText: string): Promise<CampaignAttributionResult> {
  const { data } = await api.post('/intel/threat/attribute', reportText, {
    headers: { 'Content-Type': 'text/plain' },
  });
  return data;
}

// ── AVP-5: POPIA Dossier ──────────────────────────────────────────────────────
export interface PlaChecklistItem {
  item: string;
  statutory_test: string;
  platform_evidence: string | null;
  can_evidence: boolean;
  human_input: string | null;
}

export interface PopiaDossierResult {
  avp: string;
  advisory_only: boolean;
  draft_narrative_required: boolean;
  threshold_judgement_required: boolean;
  threshold_note: string;
  incident_anchor: { alert_id: string | null; app_name: string | null; window_days: number };
  timeline: { earliest_indicator_at: string | null; latest_indicator_at: string | null };
  compromise_indicators: {
    critical_findings: number;
    high_findings: number;
    total_findings_in_window: number;
    alert_events_in_window: number;
  };
  affected_data_subjects_estimate: string;
  supporting_findings: Record<string, unknown>[];
  popia_s22_checklist: PlaChecklistItem[];
  governance_note: string;
}

export async function postPopiaDossier(params: {
  alert_id?: string;
  app_name?: string;
  window_days?: number;
}): Promise<PopiaDossierResult> {
  const { data } = await api.post('/intel/popia/dossier', null, { params });
  return data;
}

// ── AVP-8: Risk Causal Attribution ───────────────────────────────────────────
export interface CausalResult {
  avp: string;
  advisory_only: boolean;
  delta_summary: Record<string, unknown>;
  causal_hypothesis: {
    app_name: string;
    total_risk_delta: number;
    primary_signal: string;
    mapped_technique: string | null;
    technique_found_in_threat_report: boolean | null;
    techniques_in_supplied_report: string[];
    requires_analyst_review: boolean;
    analyst_review_note: string;
    model_narration_requested: boolean;
    narration_stub: string;
  };
  governance_note: string;
}

export async function postRiskCausal(params: {
  app_name: string;
  window_days?: number;
  threat_report?: string;
}): Promise<CausalResult> {
  const { app_name, window_days, threat_report } = params;
  const { data } = await api.post(
    '/intel/risk/causal',
    threat_report ?? null,
    {
      params: { app_name, window_days },
      headers: { 'Content-Type': 'text/plain' },
    }
  );
  return data;
}

// ── AVP-11: Behaviour Sequence Explanation ───────────────────────────────────
export interface AuditCluster {
  actor_id: string;
  events: Record<string, unknown>[];
  pattern_labels: string[];
  pattern_confidence: number;
}

export interface BehaviourSequenceResult {
  avp: string;
  advisory_only: boolean;
  window_days: number;
  actors_analysed: number;
  clusters: AuditCluster[];
  anomalous_clusters: AuditCluster[];
  narration_stub: string;
  analyst_review_required: boolean;
  governance_note: string;
}

export async function postExplainBehaviour(params: {
  window_days?: number;
  actor_id?: string;
  min_confidence?: number;
}): Promise<BehaviourSequenceResult> {
  const { data } = await api.post('/intel/audit/explain', null, { params });
  return data;
}

// ── AIMI VAPT Log Interpretation Layer atop Telemetry ────────────────────────
export interface VaptVectorSummary {
  vector_key: string;
  title: string;
  severity: string;
  owasp_id: string;
  cwe_ids: string[];
  vapt_ref: string;
  event_count: number;
  percentage: number;
  blocked_count: number;
  exploit_likelihood: string;
  mitre_technique: string;
  aimi_interpretation: string;
  remediation_guidance: string;
}

export interface InterpretedLogEvent {
  id: string;
  timestamp: string;
  source: string;
  app_name: string;
  department_id: string | null;
  request_uri: string | null;
  source_ip: string | null;
  attack_vector: string;
  action_taken: string;
  vapt_cwe: string;
  mitre_technique: string;
  aimi_verdict: string;
  is_mitigated_baseline: boolean;
}

export interface VaptBaselineRemediation {
  id: string;
  title: string;
  status: string;
  control: string;
  log_signature: string;
}

export interface VaptLogInterpretationResult {
  avp: string;
  advisory_only: boolean;
  generated_at: string;
  tenant_scope: {
    scope_label: string;
    department_ids: string[];
    branch_ids: string[];
    province_ids: string[];
    is_transversal: boolean;
  };
  lookback_hours: number;
  telemetry_summary: {
    total_logs_analyzed: number;
    waf_blocks_count: number;
    vulnerability_findings_count: number;
    alerts_correlated_count: number;
    distinct_attack_vectors: number;
  };
  perimeter_resilience: {
    resilience_percentage: number;
    blocked_events_count: number;
    unmitigated_bypasses_count: number;
    defense_grade: string;
    status: string;
  };
  attacker_typology: {
    profile_name: string;
    inferred_intent: string;
    exploitability_index: number;
    dominant_attack_vector: string;
  };
  vector_breakdown: VaptVectorSummary[];
  interpreted_events: InterpretedLogEvent[];
  vapt_baseline_audit: VaptBaselineRemediation[];
  role_gated_insights: {
    soc_appsec?: {
      authorized: boolean;
      unique_attacker_ips?: number;
      top_targeted_apps?: string[];
      highest_risk_payload_type?: string;
      recommended_sigma_action?: string;
      forensic_note?: string;
      note?: string;
    };
    compliance?: {
      authorized: boolean;
      popia_s22_breach_triggered?: boolean;
      popia_rationale?: string;
      iso_27001_control_status?: string;
      auditor_attestation?: string;
      note?: string;
    };
    exec_risks?: {
      authorized: boolean;
      overall_posture?: string;
      business_impact_score?: string;
      perimeter_resilience_grade?: string;
      blast_radius_containment?: string;
      executive_synopsis?: string;
      note?: string;
    };
  };
  advisory_notes: string[];
}

export async function postInterpretVaptLogs(params?: {
  lookback_hours?: number;
  app_name?: string;
  min_severity?: string;
  limit_events?: number;
}): Promise<VaptLogInterpretationResult> {
  const { data } = await api.post('/intel/vapt/interpret-logs', null, { params });
  return data;
}

export async function getVaptBaselineStatus(): Promise<{
  status: string;
  baseline_version: string;
  remediations: VaptBaselineRemediation[];
  supported_vectors: string[];
}> {
  const { data } = await api.get('/intel/vapt/baseline-status');
  return data;
}



// -- Database Security AI Alerts ---------------------------------------------

export interface DamAlertCard {
  archetype_id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  confidence_score: number;
  confidence_label: 'HIGH' | 'MEDIUM' | 'LOW';
  evidence_count: number;
  evidence_sources: string[];
  mitre_technique: string;
  owasp_ref: string;
  popia_condition: string;
  advisory_only: boolean;
  requires_human_review?: boolean;
  // SOC/DBA (findings role)
  d3fend_countermeasure?: string;
  technical_summary?: string;
  top_rule_ids?: string[];
  top_targets?: string[];
  temporal_burst?: string;
  // Compliance role
  regulatory_impact?: string;
  breach_window_est?: string;
  data_class_at_risk?: string;
  // All roles
  business_impact: string;
  blast_radius_est: string;
  remediation_urgency: string;
  dam_resilience_grade: string;
}

export interface DbSecAiResult {
  generated_at: string;
  tenant_scope: string;
  lookback_hours: number;
  total_events_analysed: number;
  dam_alerts_ingested: number;
  findings_ingested: number;
  waf_db_blocks_ingested: number;
  db_inventory_size: number;
  overall_dam_posture: 'CRITICAL' | 'ELEVATED' | 'GUARDED' | 'NORMAL';
  posture_rationale: string;
  ai_alert_cards: DamAlertCard[];
  rbac_view: 'SOC_DBA_TECHNICAL' | 'COMPLIANCE_REGULATORY' | 'EXECUTIVE_RISK';
  advisory_only: boolean;
}

export async function postDbSecAiAlerts(params: {
  lookback_hours?: number;
  db_name?: string;
  min_severity?: string;
  limit_events?: number;
}): Promise<DbSecAiResult> {
  const { data } = await api.post('/intel/dbsec/ai-alerts', null, { params });
  return data;
}
