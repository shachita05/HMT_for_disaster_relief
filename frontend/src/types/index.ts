// Mirrors backend/app/schemas/*.py -- keep these in sync by hand (no
// codegen step for a capstone-scope project; see ARCHITECTURE.md).

export type Verdict = "TRUE" | "FAKE" | "UNVERIFIED";
export type PriorityLevel = "HIGH" | "MEDIUM" | "LOW";
export type ReliabilityBand = "HIGH" | "MEDIUM" | "LOW";

export interface LocationOut {
  id: number;
  matched_text: string;
  match_level: string;
  match_type: string;
  locality: string | null;
  city: string | null;
  district: string | null;
  state: string | null;
  pin_code: string | null;
  latitude: number | null;
  longitude: number | null;
  coordinate_precision: string | null;
  is_primary: boolean;
}

export interface EvidenceOut {
  id: number;
  source: string;
  url: string | null;
  evidence_type: string;
  description: string;
  event_timestamp: string | null;
  matched_confidence: number;
  created_at: string;
}

export interface ClaimOut {
  id: number;
  text: string;
  source: string;
  source_url: string | null;
  submitted_at: string;
  disaster_type: string;
  classification: Verdict;
  confidence: number;
  reliability_score: number | null;
  reliability_band: ReliabilityBand | null;
  priority: PriorityLevel;
  priority_score: number;
  verification_status: string;
  is_historical_seed: boolean;
}

export interface ClaimDetail extends ClaimOut {
  all_disaster_types: string[];
  top_terms: [string, number][];
  priority_reasons: string[];
  reliability_reasons: string[];
  reason: string | null;
  locations: LocationOut[];
  evidence: EvidenceOut[];
  official_verification_message: string;
}

export interface ClaimListResponse {
  total: number;
  items: ClaimOut[];
}

export interface ClaimFilters {
  verdict?: string;
  disaster_type?: string;
  priority?: string;
  state?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

export interface OverviewStats {
  total_claims: number;
  true_count: number;
  fake_count: number;
  unverified_count: number;
  high_priority_count: number;
  verified_against_corpus_count: number;
  verification_rate: number;
}

export interface CountItem {
  label: string;
  count: number;
}

export interface TimelinePoint {
  date: string;
  count: number;
}

export interface MapPoint {
  claim_id: number;
  latitude: number;
  longitude: number;
  coordinate_precision: string;
  matched_text: string;
  disaster_type: string;
  classification: Verdict;
  priority: PriorityLevel;
  reliability_band: ReliabilityBand | null;
  submitted_at: string;
  is_historical_seed: boolean;
}

export interface AlertOut {
  id: number;
  claim_id: number;
  created_at: string;
  level: PriorityLevel;
  reason_text: string;
  acknowledged: boolean;
}

export interface AlertListResponse {
  total: number;
  items: AlertOut[];
}

export interface FeedHealth {
  name: string;
  status: "ok" | "error" | "not_configured" | "unknown";
  last_attempt_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
  last_event_count: number;
}
