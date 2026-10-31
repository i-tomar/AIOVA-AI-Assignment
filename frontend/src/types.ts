export type Origin = "empty" | "ai" | "user"
export type Severity = "critical" | "major" | "minor" | "unknown"
export type Status = "draft" | "under_investigation" | "pending_qa" | "approved" | "closed"
export type Confidence = "low" | "medium" | "high"
export type CapaType = "corrective" | "preventive"
export type CapaStatus = "proposed" | "accepted" | "in_progress" | "completed" | "verified"

export interface Tracked {
  value: string
  origin: Origin
  confirmed: boolean
}

export interface TeamMember {
  id: string
  name: string
  role: string
  department: string
  origin: "ai" | "user"
  confirmed: boolean
}

export interface WhyStep {
  id: string
  question: string
  answer: string
  evidence: string
  grounded: boolean
  origin: "ai" | "user"
  confirmed: boolean
}

export interface FishItem {
  id: string
  category: string
  cause: string
  evidence: string
  plausible: boolean
  grounded: boolean
  origin: "ai" | "user"
  confirmed: boolean
}

export interface Cause {
  id: string
  statement: string
  category: string
  evidence: string
  confidence: Confidence | string
  evidence_supported: boolean
  grounded: boolean
  ai_suggested: boolean
  confirmed: boolean
  confirmed_by: string
}

export interface Gap {
  id: string
  topic: string
  why_it_matters: string
  suggested_source: string
  origin: "ai" | "user"
  resolved: boolean
}

export interface Capa {
  id: string
  capa_type: CapaType | string
  description: string
  rationale: string
  owner: string
  due_date: string
  effectiveness_check: string
  status: CapaStatus | string
  ai_suggested: boolean
  confirmed: boolean
}

export interface Approval {
  reviewer_name: string
  reviewer_role: string
  decision: string
  comment: string
  acknowledged_ai_review: boolean
  signed_at: string
}

export interface SourceInfo {
  kind: string
  filename: string
  subject: string
  sender: string
  raw_text: string
}

export interface ChatMessage {
  role: "user" | "assistant" | "system"
  content: string
  at: string
}

export interface RCARecord {
  deviation_number: Tracked
  title: Tracked
  occurred_at: Tracked
  detected_at: Tracked
  site: Tracked
  area: Tracked
  equipment: Tracked
  product_name: Tracked
  batch_lot: Tracked
  process_stage: Tracked
  description: Tracked
  immediate_actions: Tracked
  impact_product_quality: Tracked
  impact_patient_safety: Tracked
  impact_regulatory: Tracked
  batch_disposition: Tracked
  severity: Tracked
  severity_rationale: Tracked
  prepared_by: Tracked
  method: Tracked
  method_notes: Tracked
  problem_statement: Tracked
  team: TeamMember[]
  whys: WhyStep[]
  fishbone: FishItem[]
  root_causes: Cause[]
  contributing_factors: Cause[]
  gaps: Gap[]
  capas: Capa[]
  approval: Approval
  status: Status
  source: SourceInfo
  ai_summary: string
  conversation: ChatMessage[]
}

export const TRACKED_KEYS = [
  "deviation_number",
  "title",
  "occurred_at",
  "detected_at",
  "site",
  "area",
  "equipment",
  "product_name",
  "batch_lot",
  "process_stage",
  "description",
  "immediate_actions",
  "impact_product_quality",
  "impact_patient_safety",
  "impact_regulatory",
  "batch_disposition",
  "severity",
  "severity_rationale",
  "prepared_by",
  "method",
  "method_notes",
  "problem_statement",
] as const

export type TrackedKey = (typeof TRACKED_KEYS)[number]

export type ItemCollection =
  | "team"
  | "whys"
  | "fishbone"
  | "root_causes"
  | "contributing_factors"
  | "gaps"
  | "capas"

export interface IngestResult {
  source_text: string
  source_kind: string
  filename: string
  subject: string
  sender: string
  characters: number
}

export interface AnalyzeResult {
  record: RCARecord
  changed_paths: string[]
  assistant_message: string
}

export interface InvestigationEnvelope {
  id: string
  record: RCARecord
  created_at: string
  updated_at: string
}

export interface InvestigationSummary {
  id: string
  deviation_number: string
  title: string
  product_name: string
  batch_lot: string
  severity: string
  status: string
  updated_at: string
}

export interface AuditEvent {
  id: number
  investigation_id: string
  created_at: string
  actor: string
  action: string
  summary: string
  changes: { path: string; before: string; after: string }[]
}

export interface Health {
  status: string
  database: string
  model: string
  llm_configured: boolean
}

export interface SampleInfo {
  filename: string
  title: string
  blurb: string
  media_type: string
}
