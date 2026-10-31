import { ingest, analyzeStream, sendChat } from "./api"
import { errorMessage } from "./format"
import { nowIso } from "./record"
import {
  analysisFailed,
  analysisFinished,
  analysisPhase,
  analysisStarted,
  chatFailed,
  chatFinished,
  chatStarted,
  pushMessage,
} from "./store/assistantSlice"
import type { AppDispatch } from "./store"
import { applyServerRecord } from "./store/investigationSlice"
import type { ChatMessage, RCARecord } from "./types"

interface Current {
  record: RCARecord
  messages: ChatMessage[]
}

export async function runAnalysis(
  dispatch: AppDispatch,
  current: Current,
  input: { text: string; file: File | null },
): Promise<void> {
  const label = input.file
    ? `Analyse ${input.file.name}.`
    : "Analyse the pasted incident text."
  const userMessage: ChatMessage = { role: "user", content: label, at: nowIso() }
  dispatch(analysisStarted())
  dispatch(pushMessage(userMessage))
  try {
    dispatch(analysisPhase("ingest"))
    const ingested = await ingest(input.file, input.text)
    const result = await analyzeStream(
      {
        source_text: ingested.source_text,
        source_kind: ingested.source_kind,
        filename: ingested.filename,
        subject: ingested.subject,
        sender: ingested.sender,
      },
      (node) => dispatch(analysisPhase(node)),
    )
    const assistantMessage: ChatMessage = {
      role: "assistant",
      content: result.assistant_message,
      at: nowIso(),
    }
    const record = preserveReview(current.record, result.record)
    record.conversation = [...current.messages, userMessage, assistantMessage]
    dispatch(pushMessage(assistantMessage))
    dispatch(applyServerRecord({ record, changedPaths: result.changed_paths }))
    dispatch(analysisFinished())
  } catch (error) {
    dispatch(analysisFailed(errorMessage(error)))
  }
}

export async function runChat(dispatch: AppDispatch, current: Current, message: string): Promise<void> {
  const userMessage: ChatMessage = { role: "user", content: message, at: nowIso() }
  dispatch(pushMessage(userMessage))
  dispatch(chatStarted())
  try {
    const result = await sendChat({
      message,
      history: current.messages,
      record: current.record,
    })
    const assistantMessage: ChatMessage = {
      role: "assistant",
      content: result.assistant_message,
      at: nowIso(),
    }
    const record = result.record
    record.conversation = [...current.messages, userMessage, assistantMessage]
    dispatch(pushMessage(assistantMessage))
    dispatch(applyServerRecord({ record, changedPaths: result.changed_paths }))
    dispatch(chatFinished())
  } catch (error) {
    dispatch(chatFailed(errorMessage(error)))
  }
}

function preserveReview(previous: RCARecord, incoming: RCARecord): RCARecord {
  const next: RCARecord = structuredClone(incoming)
  if (previous.prepared_by.origin === "user" && previous.prepared_by.value.trim()) {
    next.prepared_by = previous.prepared_by
  }
  const approval = previous.approval
  if (approval.reviewer_name.trim() || approval.comment.trim() || approval.acknowledged_ai_review) {
    next.approval = approval
  }
  if (previous.status === "approved" || previous.status === "pending_qa" || previous.status === "closed") {
    next.status = previous.status
  }
  return next
}
