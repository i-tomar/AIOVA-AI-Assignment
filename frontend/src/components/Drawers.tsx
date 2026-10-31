import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"

import { deleteInvestigation, getAudit } from "../api"
import { errorMessage, formatWhen, SEVERITY_LABEL, STATUS_LABEL } from "../format"
import { useAppDispatch, useAppSelector } from "../store/hooks"
import { fetchLibrary } from "../store/thunks"
import type { AuditEvent, Status } from "../types"

export function LibraryDrawer({
  open,
  dirty,
  onClose,
}: {
  open: boolean
  dirty: boolean
  onClose: () => void
}) {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const items = useAppSelector((state) => state.library.items)
  const loading = useAppSelector((state) => state.library.loading)
  const error = useAppSelector((state) => state.library.error)
  const [localError, setLocalError] = useState<string | null>(null)

  useEffect(() => {
    if (open) void dispatch(fetchLibrary())
  }, [open, dispatch])

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-label="Saved investigations" onClick={(event) => event.stopPropagation()}>
        <header className="drawer-head">
          <h2>Saved investigations</h2>
          <button type="button" className="text-btn" onClick={onClose}>
            Close
          </button>
        </header>
        {loading && <p className="hint">Loading the library…</p>}
        {(error || localError) && (
          <p className="banner error">
            {error || localError}
            <button type="button" className="text-btn" onClick={() => void dispatch(fetchLibrary())}>
              Retry
            </button>
          </p>
        )}
        {!loading && !error && items.length === 0 && (
          <p className="empty-form">
            No investigations saved yet. Analyse a source, review the record, and save it. It will reopen here with the
            same suggestion and confirmation flags.
          </p>
        )}
        <ul className="lib-list">
          {items.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className="lib-item"
                onClick={() => {
                  if (dirty && !window.confirm("Discard unsaved changes and open this investigation?")) return
                  navigate(`/i/${item.id}`)
                  onClose()
                }}
              >
                <strong>{item.deviation_number || "Unassigned"}</strong>
                <span>{item.title || "Untitled deviation"}</span>
                <span className="muted">
                  {[item.product_name, item.batch_lot].filter(Boolean).join(" · ") || "Product not recorded"}
                </span>
                <span className="lib-meta">
                  <span className="stamp" data-severity={item.severity || "unknown"}>
                    {SEVERITY_LABEL[item.severity] ?? item.severity}
                  </span>
                  <span>{STATUS_LABEL[item.status as Status] ?? item.status}</span>
                  <time>{formatWhen(item.updated_at)}</time>
                </span>
              </button>
              <button
                type="button"
                className="text-btn danger"
                onClick={() => {
                  if (!window.confirm("Delete this investigation and its history?")) return
                  void deleteInvestigation(item.id)
                    .then(() => dispatch(fetchLibrary()))
                    .catch((reason: unknown) => setLocalError(errorMessage(reason)))
                }}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  )
}

export function AuditDrawer({
  open,
  investigationId,
  onClose,
}: {
  open: boolean
  investigationId: string | null
  onClose: () => void
}) {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open || !investigationId) return
    let cancel = false
    setLoading(true)
    setError(null)
    getAudit(investigationId)
      .then((rows) => {
        if (!cancel) setEvents(rows)
      })
      .catch((reason: unknown) => {
        if (!cancel) setError(errorMessage(reason))
      })
      .finally(() => {
        if (!cancel) setLoading(false)
      })
    return () => {
      cancel = true
    }
  }, [open, investigationId])

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-label="Change history" onClick={(event) => event.stopPropagation()}>
        <header className="drawer-head">
          <h2>Change history</h2>
          <button type="button" className="text-btn" onClick={onClose}>
            Close
          </button>
        </header>
        <p className="hint">Each save is recorded. Edits made before the first save appear as the created document.</p>
        {loading && <p className="hint">Loading history…</p>}
        {error && <p className="banner error">{error}</p>}
        {!loading && events.length === 0 && <p className="empty-form">No history yet.</p>}
        <ol className="audit-list">
          {events.map((event) => (
            <li key={event.id}>
              <header>
                <strong>{event.summary}</strong>
                <span>
                  {event.actor} · {formatWhen(event.created_at)}
                </span>
              </header>
              {event.changes.length > 0 && (
                <ul>
                  {event.changes.slice(0, 8).map((change) => (
                    <li key={change.path}>
                      <code>{change.path}</code>
                    </li>
                  ))}
                  {event.changes.length > 8 && <li>{event.changes.length - 8} more fields</li>}
                </ul>
              )}
            </li>
          ))}
        </ol>
      </aside>
    </div>
  )
}
