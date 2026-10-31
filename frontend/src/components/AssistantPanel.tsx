import { useEffect, useState, type FormEvent } from "react"

import { fetchSampleBlob, listSamples } from "../api"
import { errorMessage, formatWhen } from "../format"
import { ANALYZE_PHASES } from "../phases"
import { useAppDispatch, useAppSelector } from "../store/hooks"
import { clearAssistantError } from "../store/assistantSlice"
import type { SampleInfo } from "../types"
import { runAnalysis, runChat } from "../workflows"

export function AssistantPanel() {
  const dispatch = useAppDispatch()
  const messages = useAppSelector((state) => state.assistant.messages)
  const phase = useAppSelector((state) => state.assistant.phase)
  const activeNode = useAppSelector((state) => state.assistant.activeNode)
  const phaseLog = useAppSelector((state) => state.assistant.phaseLog)
  const error = useAppSelector((state) => state.assistant.error)
  const record = useAppSelector((state) => state.investigation.record)
  const status = useAppSelector((state) => state.investigation.record.status)

  const [draft, setDraft] = useState("")
  const [chat, setChat] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [samples, setSamples] = useState<SampleInfo[]>([])
  const [sampleError, setSampleError] = useState<string | null>(null)
  const busy = phase !== "idle"
  const canAnalyse = !busy && (file !== null || draft.trim().length >= 40)

  useEffect(() => {
    let cancel = false
    listSamples()
      .then((items) => {
        if (!cancel) setSamples(items)
      })
      .catch((reason: unknown) => {
        if (!cancel) setSampleError(errorMessage(reason))
      })
    return () => {
      cancel = true
    }
  }, [])

  async function onAnalyse() {
    if (!canAnalyse) return
    if (
      (status === "approved" || status === "pending_qa") &&
      !window.confirm("This replaces the drafted investigation with a new analysis. Reviewer comments are kept. Continue?")
    ) {
      return
    }
    dispatch(clearAssistantError())
    await runAnalysis(dispatch, { record, messages }, { text: draft, file })
  }

  async function onChat(event: FormEvent) {
    event.preventDefault()
    const message = chat.trim()
    if (!message || busy) return
    setChat("")
    await runChat(dispatch, { record, messages }, message)
  }

  async function loadSample(sample: SampleInfo) {
    setSampleError(null)
    try {
      const blob = await fetchSampleBlob(sample.filename)
      if (sample.filename.endsWith(".txt")) {
        setDraft(await blob.text())
        setFile(null)
        return
      }
      const type = sample.filename.endsWith(".pdf") ? "application/pdf" : "message/rfc822"
      setFile(new File([blob], sample.filename, { type }))
      setDraft("")
    } catch (reason) {
      setSampleError(errorMessage(reason))
    }
  }

  return (
    <aside className="assistant">
      <header className="assistant-head">
        <p className="eyebrow">Investigation assistant</p>
        <h2>Read the incident</h2>
        <p>
          Drop a deviation report, a shift note, or an email. The record, the 5 Whys, the fishbone, the cause
          hypotheses, the gaps, and the CAPA proposals are filled from that source.
        </p>
      </header>

      {(error || sampleError) && <p className="banner error">{error || sampleError}</p>}

      {phaseLog.length > 0 && (
        <ol className="stepper" aria-label="Analysis progress">
          {ANALYZE_PHASES.map((step) => {
            const count = phaseLog.filter((item) => item === step.id).length
            const active = activeNode === step.id
            const done = count > 0 && !active
            const state = active ? "active" : done ? "done" : "wait"
            return (
              <li key={step.id} data-state={state}>
                {step.label}
                {count > 1 && <em> retried</em>}
              </li>
            )
          })}
        </ol>
      )}

      <div className="thread" aria-live="polite">
        {messages.length === 0 && (
          <p className="thread-empty">
            Nothing has been read yet. The thread keeps the assistant’s summary and any later edits you ask for.
          </p>
        )}
        {messages.map((message, index) => (
          <article key={`${message.at}-${index}`} className={`msg ${message.role}`}>
            <header>
              <span>{message.role === "user" ? "You" : "Assistant"}</span>
              <time>{formatWhen(message.at)}</time>
            </header>
            <p>{message.content}</p>
          </article>
        ))}
        {busy && <p className="thread-empty">{phase === "chatting" ? "Updating the record…" : "Working through the source…"}</p>}
      </div>

      <div className="composer">
        <div
          className={`drop ${file ? "has-file" : ""}`}
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault()
            const next = event.dataTransfer.files[0]
            if (next) setFile(next)
          }}
        >
          {file ? (
            <span className="file-chip">
              {file.name}
              <button type="button" onClick={() => setFile(null)} aria-label="Remove file">
                Remove
              </button>
            </span>
          ) : (
            <span>Drop a PDF or .eml here</span>
          )}
          <label className="text-btn file-btn">
            Attach
            <input
              type="file"
              accept=".pdf,.eml,.txt,.md,application/pdf,message/rfc822,text/plain"
              onChange={(event) => {
                const next = event.target.files?.[0]
                if (next) setFile(next)
                event.target.value = ""
              }}
            />
          </label>
        </div>
        <label className="sub dark">
          Incident text
          <textarea
            rows={5}
            value={draft}
            placeholder="Paste a shift note or an email. A PDF can be attached without pasting."
            onChange={(event) => setDraft(event.target.value)}
          />
        </label>
        <div className="samples">
          {samples.map((sample) => (
            <button key={sample.filename} type="button" className="sample" onClick={() => void loadSample(sample)} disabled={busy}>
              <strong>{sample.title}</strong>
              <span>{sample.blurb}</span>
            </button>
          ))}
        </div>
        <button type="button" className="primary wide" disabled={!canAnalyse} onClick={() => void onAnalyse()}>
          {phase === "running" ? "Analysing…" : "Analyse source"}
        </button>
        {!file && draft.trim().length > 0 && draft.trim().length < 40 && (
          <p className="hint light">Paste a fuller note before analysis. A short fragment is not enough to investigate.</p>
        )}

        <form onSubmit={(event) => void onChat(event)} className="chat-row">
          <label className="sub dark grow">
            Ask for a change
            <input
              value={chat}
              placeholder='Try "add a why about the alarm" or "set the batch to ATV-CA-26-0142"'
              onChange={(event) => setChat(event.target.value)}
            />
          </label>
          <button type="submit" className="quiet" disabled={busy || chat.trim().length === 0}>
            {phase === "chatting" ? "Sending…" : "Send"}
          </button>
        </form>
      </div>
    </aside>
  )
}
