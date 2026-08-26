// Mirrors the backend Pydantic schemas in app/models/*.py — kept in sync by
// hand (a small enough surface that a generated-client step would be
// overhead for this project's size).

export type CorrelationClass = "causally_supported" | "correlated" | "insufficient_evidence";

export type EvidenceMethod =
  | "trend_seasonality_decomposition"
  | "forecast_band_deviation"
  | "driver_tree_decomposition"
  | "lag_correlation_test"
  | "lexicon_sentiment_scoring"
  | "rule_based_nlp_event_extraction"
  | "confidence_scoring"
  | "rule_based_action_lookup"
  | "llm_narrative_phrasing";

export interface DriverContribution {
  driver: string;
  description: string;
  contribution_value: number;
  contribution_pct: number;
  direction: "increase" | "decrease";
  method: EvidenceMethod;
}

export interface CorrelationSignal {
  signal_name: string;
  source_kpi_id: string;
  lag_weeks: number;
  correlation_coefficient: number;
  p_value: number;
  classification: CorrelationClass;
  rationale: string;
  method: EvidenceMethod;
}

export interface DataCompleteness {
  weeks_of_history: number;
  weeks_required_for_high_confidence: number;
  missing_periods: number;
  source_freshness_days: number;
}

export interface Hypothesis {
  id: string;
  label: string;
  summary: string;
  drivers: DriverContribution[];
  correlations: CorrelationSignal[];
  statistical_strength: number;
  evidence_agreement: number;
  data_completeness_score: number;
  confidence: number;
}

export interface KpiMovement {
  kpi_id: string;
  kpi_name: string;
  dimension_label: string;
  period_start: string;
  period_end: string;
  actual_value: number;
  expected_value: number;
  forecast_band_low: number;
  forecast_band_high: number;
  absolute_change: number;
  relative_change_pct: number;
  is_material: boolean;
  method: EvidenceMethod;
}

export interface TrendPoint {
  week_start: string;
  actual: number;
  expected: number;
  band_low: number;
  band_high: number;
  is_material: boolean;
}

export interface EvidencePacket {
  insight_id: string;
  movement: KpiMovement;
  trend: TrendPoint[];
  hypotheses: Hypothesis[];
  top_hypothesis_id: string | null;
  confidence_margin: number | null;
  abstained: boolean;
  abstention_reason: string | null;
  data_completeness: DataCompleteness;
  lineage: string[];
  generated_at: string;
}

export interface ActionRecommendation {
  driver: string;
  controllable_lever: string;
  action: string;
  expected_impact: string;
  owner: string;
  confidence: number;
  monitoring_plan: string;
  llm_phrased_summary: string | null;
}

export interface GroundingCheckResult {
  passed: boolean;
  checked_numbers: string[];
  ungrounded_numbers: string[];
}

export interface LlmTelemetry {
  provider: string;
  model: string;
  tier: "cheap" | "strong";
  tokens_in: number;
  tokens_out: number;
  latency_ms: number;
  estimated_cost_usd: number;
  cache_hit: boolean;
  called_at: string;
}

export interface PersonaNarrative {
  persona_id: string;
  persona_role: string;
  headline: string;
  narrative: string;
  recommended_actions: ActionRecommendation[];
  grounding: GroundingCheckResult;
  llm_telemetry: LlmTelemetry | null;
}

export interface Insight {
  insight_id: string;
  kpi_id: string;
  evidence: EvidencePacket;
  narratives: Record<string, PersonaNarrative>;
}

export interface PersonaOut {
  id: string;
  display_name: string;
  role: string;
  region_scope: string[];
}

export interface ScenarioDef {
  id: string;
  kpi_id: string;
  label: string;
  description: string;
  region: string | null;
  category: string | null;
  sub_category: string | null;
}

export interface MaterialityThresholds {
  min_absolute_change_usd?: number | null;
  min_absolute_change_pp?: number | null;
  min_absolute_change_count?: number | null;
  min_absolute_change?: number | null;
  min_relative_change_pct: number;
  note?: string | null;
}

export interface KpiDefinition {
  id: string;
  name: string;
  definition: string;
  formula: string;
  grain: string;
  dimensions: string[];
  source: string;
  refresh_cadence: string;
  owner: string;
  materiality: MaterialityThresholds;
  drivers: string[];
  access_restrictions: { row_level: string; column_level: string };
  lineage: string[];
}

export interface KpiContract {
  kpis: KpiDefinition[];
  personas: { id: string; role: string; region_scope: string[] }[];
}

export type FeedbackVerdict = "agree" | "disagree" | "partially_agree";

export interface FeedbackEntry {
  kpi_id: string;
  insight_id: string;
  hypothesis_id: string;
  persona_id: string;
  verdict: FeedbackVerdict;
  correction_note?: string | null;
  submitted_at: string;
}

export interface TelemetrySummary {
  total_calls: number;
  cache_hits: number;
  cache_hit_rate: number;
  total_tokens_in: number;
  total_tokens_out: number;
  total_estimated_cost_usd: number;
  avg_latency_ms: number;
  tier_breakdown: Record<string, number>;
  model_breakdown: Record<string, number>;
  cache_size: number;
  cache_lookup_hit_rate: number;
}

export interface SampleRecord {
  order_date: string;
  region: string;
  category: string;
  sub_category: string;
  product_name: string;
  sales: number;
  quantity: number;
  discount: number;
  profit: number;
  customer_id?: string;
  customer_name?: string;
  [key: string]: unknown;
}
