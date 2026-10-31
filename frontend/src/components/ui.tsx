import type { ReactNode } from "react"

import type { Tracked, TrackedKey } from "../types"

export function Badge({ tone, children }: { tone: "ai" | "ok" | "warn" | "user"; children: string }) {
  return <span className={`badge ${tone}`}>{children}</span>
}

export function Section({
  id,
  index,
  title,
  lede,
  onAccept,
  children,
}: {
  id: string
  index: string
  title: string
  lede?: string
  onAccept?: () => void
  children: ReactNode
}) {
  return (
    <section className="section" id={id}>
      <header className="section-head">
        <span className="idx">{index}</span>
        <div>
          <h2>{title}</h2>
          {lede && <p>{lede}</p>}
        </div>
        {onAccept && (
          <button type="button" className="text-btn" onClick={onAccept}>
            Accept extracted facts
          </button>
        )}
      </header>
      {children}
    </section>
  )
}

export function Field({
  label,
  path,
  tracked,
  hint,
  multiline = false,
  rows = 4,
  options,
  highlighted = false,
  onChange,
  onConfirm,
}: {
  label: string
  path: TrackedKey
  tracked: Tracked
  hint?: string
  multiline?: boolean
  rows?: number
  options?: { value: string; label: string }[]
  highlighted?: boolean
  onChange: (path: TrackedKey, value: string) => void
  onConfirm: (path: TrackedKey) => void
}) {
  const id = `field-${path}`
  const pending = tracked.origin === "ai" && !tracked.confirmed
  const accepted = tracked.origin === "ai" && tracked.confirmed
  const choices =
    options && tracked.value && !options.some((option) => option.value === tracked.value)
      ? [{ value: tracked.value, label: tracked.value }, ...options]
      : options
  return (
    <div className={`field ${highlighted ? "is-fresh" : ""}`} data-ai-fresh={highlighted ? "true" : undefined}>
      <div className="field-label">
        <label htmlFor={id}>{label}</label>
        {pending && <Badge tone="ai">AI extracted</Badge>}
        {accepted && <Badge tone="ok">Accepted</Badge>}
        {pending && (
          <button type="button" className="text-btn" onClick={() => onConfirm(path)}>
            Accept
          </button>
        )}
      </div>
      {choices ? (
        <select id={id} value={tracked.value} onChange={(event) => onChange(path, event.target.value)}>
          {tracked.value === "" && <option value="">Select</option>}
          {choices.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : multiline ? (
        <textarea
          id={id}
          rows={rows}
          value={tracked.value}
          onChange={(event) => onChange(path, event.target.value)}
        />
      ) : (
        <input
          id={id}
          value={tracked.value}
          autoComplete="off"
          onChange={(event) => onChange(path, event.target.value)}
        />
      )}
      {hint && <p className="hint">{hint}</p>}
    </div>
  )
}
