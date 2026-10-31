import { useEffect, useRef } from "react"

import { useAppDispatch, useAppSelector } from "../store/hooks"
import { clearHighlights } from "../store/investigationSlice"
import { FindingsSections } from "./FindingsSection"
import { IdentitySections } from "./IdentitySection"
import { InvestigationSection } from "./InvestigationSection"

const NAV = [
  ["identity", "Identity"],
  ["product", "Product"],
  ["narrative", "Event"],
  ["impact", "Impact"],
  ["investigation", "Investigation"],
  ["causes", "Causes"],
  ["gaps", "Gaps"],
  ["capa", "CAPA"],
  ["approval", "QA review"],
] as const

export function FormPane() {
  const dispatch = useAppDispatch()
  const record = useAppSelector((state) => state.investigation.record)
  const highlighted = useAppSelector((state) => state.investigation.highlighted)
  const loading = useAppSelector((state) => state.investigation.loading)
  const loadError = useAppSelector((state) => state.investigation.loadError)
  const pane = useRef<HTMLDivElement>(null)
  const seen = useRef<string[]>([])

  useEffect(() => {
    const added = highlighted.some((path) => !seen.current.includes(path))
    seen.current = highlighted
    if (!added || highlighted.length === 0) return
    const node = pane.current?.querySelector("[data-ai-fresh='true']")
    node?.scrollIntoView({ behavior: "smooth", block: "nearest" })
  }, [highlighted])

  const source = record.source
  const empty = !source.raw_text && !record.title.value && !record.description.value

  return (
    <div className="form-pane" ref={pane}>
      <div className="form-layout">
        <nav className="section-nav" aria-label="Record sections">
          {NAV.map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" })}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className="form-body">
          {loading && <p className="banner">Opening the investigation…</p>}
          {loadError && <p className="banner error">{loadError}</p>}
          {source.raw_text && (
            <p className="source-line">
              Source {source.kind || "text"}
              {source.filename ? ` · ${source.filename}` : ""}
              {source.sender ? ` · ${source.sender}` : ""} · {source.raw_text.length.toLocaleString()} characters
            </p>
          )}
          {highlighted.length > 0 && (
            <p className="source-line fresh-note">
              Fields just filled by the assistant are marked.
              <button type="button" className="text-btn" onClick={() => dispatch(clearHighlights())}>
                Dismiss highlights
              </button>
            </p>
          )}
          {empty && (
            <p className="empty-form">
              The record is empty. Bring a deviation report, a shift note, or an email into the assistant. The form
              fills from that source; edit it only to review.
            </p>
          )}
          <IdentitySections />
          <InvestigationSection />
          <FindingsSections />
          <p className="legal">
            The assistant is an investigation aid. Saving a record does not make an AI suggestion an established root
            cause. A qualified person confirms causes against evidence.
          </p>
        </div>
      </div>
    </div>
  )
}
