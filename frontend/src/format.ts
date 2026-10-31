import type { Cause, Status } from "./types"

export const SEVERITY_LABEL: Record<string, string> = {
  critical: "Critical",
  major: "Major",
  minor: "Minor",
  unknown: "Unclassified",
}

export const STATUS_LABEL: Record<Status, string> = {
  draft: "Draft",
  under_investigation: "Under investigation",
  pending_qa: "Pending QA",
  approved: "Approved",
  closed: "Closed",
}

export const CONFIDENCE_LABEL: Record<string, string> = {
  low: "Low confidence",
  medium: "Medium confidence",
  high: "High confidence",
}

export const CAPA_STATUS_LABEL: Record<string, string> = {
  proposed: "Proposed",
  accepted: "Accepted",
  in_progress: "In progress",
  completed: "Completed",
  verified: "Effectiveness verified",
}

export const FISH_CATEGORIES = [
  "Man",
  "Machine",
  "Method",
  "Material",
  "Measurement",
  "Environment",
] as const

export function causeBadge(cause: Cause): { tone: "ai" | "ok" | "user"; label: string } {
  const established = cause.confirmed && cause.evidence.trim().length > 0
  if (established) return { tone: "ok", label: "Confirmed" }
  if (cause.ai_suggested) return { tone: "ai", label: "AI suggested" }
  return { tone: "user", label: "Added in review" }
}

export function formatWhen(iso: string): string {
  if (!iso) return ""
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error && error.name === "TimeoutError") {
    return "The request timed out. Try again, or use a shorter source."
  }
  if (error instanceof Error && error.message) return error.message
  return "Something went wrong."
}
