export type Role = "customer" | "provider" | "support" | "admin";

export interface Me {
  id: string; email: string; full_name: string; role: Role;
  mfa_enabled: boolean; email_verified: boolean; mfa_verified?: boolean; mfa_required?: boolean;
}
export interface Service {
  id: string; code: string; name: string; summary: string; description: string;
  inclusions: string[]; exclusions: string[]; requirements: string;
  indicative_min_minor?: number | null; indicative_max_minor?: number | null; currency?: string;
  required_consent_scope?: string; is_active?: boolean;
}
export interface Authorisation {
  id: string; parent_id: string; status: "pending" | "active" | "revoked";
  can_request_services: boolean; can_receive_updates: boolean; can_approve_costs: boolean; can_view_evidence: boolean;
  relationship_to_parent?: string;
}
export interface Consent {
  id: string; scopes: string[]; given_by: string; captured_via: string; captured_at: string;
  valid_until: string | null; revoked_at: string | null; evidence_ref?: string | null;
}
export interface Parent {
  id: string; full_name: string; phone?: string | null; preferred_language?: string | null; contact_preferences?: string | null;
  address_line?: string | null; city: string; area?: string | null; location_notes?: string | null;
  emergency_contact_name?: string | null; emergency_contact_phone?: string | null;
  authorisation?: Authorisation | null; consent_status?: "active" | "none"; consents?: Consent[];
}
export interface TimelineEvent {
  id: string; event_type: string; from_status?: string | null; to_status?: string | null; message?: string | null;
  created_at: string; visible_to_customer?: boolean;
}
export interface RequestSummary {
  id: string; reference: string; parent_id: string; parent_name: string; service_id: string; service_name: string;
  status: string; priority: string; task_details: string; location_text?: string | null;
  requested_start?: string | null; requested_end?: string | null; budget_cap_minor?: number | null; currency: string;
  created_at: string; completed_at?: string | null; cancel_reason?: string | null;
  timeline?: TimelineEvent[];
}
export interface Quote {
  id: string; version: number; scope_summary: string; provider_cost_minor: number; coordination_fee_minor: number;
  tax_minor: number; total_minor: number; currency: string; exceeds_budget_cap: boolean; valid_until?: string | null;
  cancellation_terms: string; status: "pending" | "approved" | "rejected" | "superseded" | "expired"; decided_at?: string | null;
}
export interface Invoice {
  id: string; number: string; request_id: string; status: string; total_minor: number; provider_cost_minor: number;
  coordination_fee_minor: number; tax_minor: number; currency: string; issued_at?: string | null; due_at?: string | null; paid_at?: string | null;
  checkout_url?: string | null; created_at: string;
  payments?: { id: string; amount_minor: number; status: string; created_at: string }[];
  refunds?: { id: string; amount_minor: number; status: string; reason: string }[];
}
export interface EvidenceItem { id: string; filename: string; content_type: string; purpose: string; access_scope: string; caption?: string | null; created_at: string }
export interface JobView {
  id: string; reference: string; role: string; status: string; service: string; window_start?: string | null; window_end?: string | null;
  request_status: string; area?: string | null; instructions?: string | null; task_details?: string | null;
  payout_minor: number; currency: string; checked_in_at?: string | null; checked_out_at?: string | null;
  parent_first_name?: string | null; location?: string | null; contact_phone?: string | null;
  checklist?: { items: { key: string; label: string; required?: boolean }[]; responses: Record<string, { done: boolean; note?: string }>; completed_at?: string | null };
  evidence?: EvidenceItem[];
}
