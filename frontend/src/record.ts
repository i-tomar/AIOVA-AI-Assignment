import type { RCARecord, Tracked, TrackedKey } from "./types"

export function blankTracked(): Tracked {
  return { value: "", origin: "empty", confirmed: false }
}

export function emptyRecord(): RCARecord {
  const field = blankTracked
  return {
    deviation_number: field(),
    title: field(),
    occurred_at: field(),
    detected_at: field(),
    site: field(),
    area: field(),
    equipment: field(),
    product_name: field(),
    batch_lot: field(),
    process_stage: field(),
    description: field(),
    immediate_actions: field(),
    impact_product_quality: field(),
    impact_patient_safety: field(),
    impact_regulatory: field(),
    batch_disposition: field(),
    severity: field(),
    severity_rationale: field(),
    prepared_by: field(),
    method: field(),
    method_notes: field(),
    problem_statement: field(),
    team: [],
    whys: [],
    fishbone: [],
    root_causes: [],
    contributing_factors: [],
    gaps: [],
    capas: [],
    approval: {
      reviewer_name: "",
      reviewer_role: "Quality Assurance",
      decision: "",
      comment: "",
      acknowledged_ai_review: false,
      signed_at: "",
    },
    status: "draft",
    source: { kind: "", filename: "", subject: "", sender: "", raw_text: "" },
    ai_summary: "",
    conversation: [],
  }
}

export function newId(prefix: string): string {
  const token = crypto.randomUUID().replace(/-/g, "").slice(0, 8)
  return `${prefix}_${token}`
}

export function nowIso(): string {
  return new Date().toISOString()
}

export function hasPendingFacts(record: RCARecord, keys: TrackedKey[]): boolean {
  return keys.some((key) => record[key].origin === "ai" && !record[key].confirmed)
}
