import type {
  AnalyzeResult,
  AuditEvent,
  Health,
  IngestResult,
  InvestigationEnvelope,
  InvestigationSummary,
  RCARecord,
  SampleInfo,
  ChatMessage,
} from "./types"

export class ApiError extends Error {
  code: string

  constructor(message: string, code = "error") {
    super(message)
    this.name = "ApiError"
    this.code = code
  }
}

async function readError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as { detail?: unknown; code?: string }
    return new ApiError(detailText(body.detail) || response.statusText || "Request failed", body.code || "http")
  } catch {
    return new ApiError(response.statusText || "Request failed", "http")
  }
}

function detailText(detail: unknown): string {
  if (typeof detail === "string") return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) return String(item.msg)
        return String(item)
      })
      .join(" ")
  }
  return ""
}

export async function fetchHealth(): Promise<Health> {
  let response: Response
  try {
    response = await fetch("/api/health")
  } catch {
    throw new ApiError("The API is not reachable. Start the FastAPI server on port 8077.", "offline")
  }
  const body = (await response.json()) as Health
  if (!response.ok && !body.database) {
    throw new ApiError("The API is not reachable. Start the FastAPI server on port 8077.", "offline")
  }
  return body
}

export async function ingest(file: File | null, text: string): Promise<IngestResult> {
  const form = new FormData()
  if (file) form.append("file", file)
  form.append("text", text)
  const response = await fetch("/api/ingest", {
    method: "POST",
    body: form,
    signal: AbortSignal.timeout(60_000),
  })
  if (!response.ok) throw await readError(response)
  return (await response.json()) as IngestResult
}

export async function analyzeStream(
  body: {
    source_text: string
    source_kind: string
    filename: string
    subject: string
    sender: string
  },
  onPhase: (node: string) => void,
): Promise<AnalyzeResult> {
  const response = await fetch("/api/ai/analyze/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(180_000),
  })
  if (!response.ok) throw await readError(response)
  if (!response.body) throw new ApiError("The analysis stream was empty.", "empty_stream")

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  let result: AnalyzeResult | null = null
  const take = (event: string, data: string) => {
    const payload = JSON.parse(data) as {
      node?: string
      detail?: string
      code?: string
      record?: AnalyzeResult["record"]
      changed_paths?: string[]
      assistant_message?: string
    }
    if (event === "phase" && payload.node) onPhase(payload.node)
    if (event === "error") {
      throw new ApiError(payload.detail || "Analysis failed.", payload.code || "analyze_failed")
    }
    if (event === "result" && payload.record && payload.changed_paths && payload.assistant_message) {
      result = {
        record: payload.record,
        changed_paths: payload.changed_paths,
        assistant_message: payload.assistant_message,
      }
    }
  }
  while (true) {
    const chunk = await reader.read()
    if (chunk.done) break
    buffer += decoder.decode(chunk.value, { stream: true })
    buffer = consumeSse(buffer, take)
  }
  buffer = consumeSse(`${buffer}\n\n`, take)
  if (!result) throw new ApiError("Analysis ended without a record.", "analyze_failed")
  return result
}

export async function sendChat(body: {
  message: string
  history: ChatMessage[]
  record: RCARecord
}): Promise<AnalyzeResult> {
  const response = await fetch("/api/ai/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(180_000),
  })
  if (!response.ok) throw await readError(response)
  return (await response.json()) as AnalyzeResult
}

export async function createInvestigation(record: RCARecord, actor: string): Promise<InvestigationEnvelope> {
  return save("/api/investigations", "POST", record, actor)
}

export async function updateInvestigation(
  id: string,
  record: RCARecord,
  actor: string,
): Promise<InvestigationEnvelope> {
  return save(`/api/investigations/${id}`, "PUT", record, actor)
}

async function save(url: string, method: string, record: RCARecord, actor: string): Promise<InvestigationEnvelope> {
  const response = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ record, actor }),
  })
  if (!response.ok) throw await readError(response)
  return (await response.json()) as InvestigationEnvelope
}

export async function listInvestigations(): Promise<InvestigationSummary[]> {
  const response = await fetch("/api/investigations")
  if (!response.ok) throw await readError(response)
  const body = (await response.json()) as { investigations: InvestigationSummary[] }
  return body.investigations
}

export async function getInvestigation(id: string): Promise<InvestigationEnvelope> {
  const response = await fetch(`/api/investigations/${id}`)
  if (!response.ok) throw await readError(response)
  return (await response.json()) as InvestigationEnvelope
}

export async function deleteInvestigation(id: string): Promise<void> {
  const response = await fetch(`/api/investigations/${id}`, { method: "DELETE" })
  if (!response.ok) throw await readError(response)
}

export async function getAudit(id: string): Promise<AuditEvent[]> {
  const response = await fetch(`/api/investigations/${id}/audit`)
  if (!response.ok) throw await readError(response)
  const body = (await response.json()) as { events: AuditEvent[] }
  return body.events
}

export async function listSamples(): Promise<SampleInfo[]> {
  const response = await fetch("/api/samples")
  if (!response.ok) throw await readError(response)
  const body = (await response.json()) as { samples: SampleInfo[] }
  return body.samples
}

export async function fetchSampleBlob(filename: string): Promise<Blob> {
  const response = await fetch(`/api/samples/${encodeURIComponent(filename)}`)
  if (!response.ok) throw await readError(response)
  return response.blob()
}

function consumeSse(buffer: string, onEvent: (event: string, data: string) => void): string {
  const parts = buffer.split("\n\n")
  const rest = parts.pop() ?? ""
  for (const part of parts) {
    if (!part.trim()) continue
    let event = "message"
    const data: string[] = []
    for (const line of part.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim()
      else if (line.startsWith("data:")) data.push(line.slice(5).trim())
    }
    if (data.length) onEvent(event, data.join("\n"))
  }
  return rest
}
