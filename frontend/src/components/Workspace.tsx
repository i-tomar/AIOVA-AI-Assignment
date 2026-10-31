import { useCallback, useEffect, useRef, useState } from "react"
import { Outlet, useNavigate, useParams } from "react-router-dom"

import { fetchHealth } from "../api"
import { errorMessage, SEVERITY_LABEL } from "../format"
import { useAppDispatch, useAppSelector } from "../store/hooks"
import { setStatus, updateTracked } from "../store/investigationSlice"
import { loadInvestigation, saveInvestigation } from "../store/thunks"
import { resetWorkspace } from "../store/workspace"
import type { Health, Status } from "../types"
import { AssistantPanel } from "./AssistantPanel"
import { AuditDrawer, LibraryDrawer } from "./Drawers"
import { FormPane } from "./FormPane"

export function Workspace() {
  const { id } = useParams()
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const record = useAppSelector((state) => state.investigation.record)
  const investigationId = useAppSelector((state) => state.investigation.id)
  const dirty = useAppSelector((state) => state.investigation.dirty)
  const saving = useAppSelector((state) => state.investigation.saving)
  const saveError = useAppSelector((state) => state.investigation.saveError)
  const lastSavedAt = useAppSelector((state) => state.investigation.lastSavedAt)
  const [tab, setTab] = useState<"form" | "assistant">("assistant")
  const [libraryOpen, setLibraryOpen] = useState(false)
  const [auditOpen, setAuditOpen] = useState(false)
  const [health, setHealth] = useState<Health | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)

  useEffect(() => {
    let cancel = false
    fetchHealth()
      .then((body) => {
        if (!cancel) setHealth(body)
      })
      .catch((reason: unknown) => {
        if (!cancel) setHealthError(errorMessage(reason))
      })
    return () => {
      cancel = true
    }
  }, [])

  const routeId = useRef<string | undefined>(undefined)
  useEffect(() => {
    const previous = routeId.current
    routeId.current = id
    if (previous && !id) {
      dispatch(resetWorkspace())
      return
    }
    if (!id || investigationId === id) return
    void dispatch(loadInvestigation(id))
  }, [id, investigationId, dispatch])

  useEffect(() => {
    const number = record.deviation_number.value.trim()
    document.title = number ? `${number} · Northline RCA` : "Northline RCA"
  }, [record.deviation_number.value])

  useEffect(() => {
    const onBefore = (event: BeforeUnloadEvent) => {
      if (!dirty) return
      event.preventDefault()
      event.returnValue = ""
    }
    window.addEventListener("beforeunload", onBefore)
    return () => window.removeEventListener("beforeunload", onBefore)
  }, [dirty])

  const onSave = useCallback(async () => {
    const result = await dispatch(saveInvestigation())
    if (saveInvestigation.fulfilled.match(result) && !id) {
      navigate(`/i/${result.payload.id}`)
    }
  }, [dispatch, id, navigate])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
        event.preventDefault()
        void onSave()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onSave])

  const openSuggestions = record.root_causes.filter((cause) => !(cause.confirmed && cause.evidence.trim())).length
  const severity = record.severity.value || "unknown"

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="mark" aria-hidden="true">
            N
          </span>
          <div>
            <strong>Northline</strong>
            <span>Root cause analysis</span>
          </div>
        </div>
        <div className="case">
          <span className="devno">{record.deviation_number.value.trim() || "Unassigned"}</span>
          <span className="stamp" data-severity={severity}>
            {SEVERITY_LABEL[severity] ?? severity}
          </span>
          <label className="status-select">
            <span className="sr">Status</span>
            <select
              value={record.status}
              onChange={(event) => {
                const value = event.target.value as Status
                if (value === "approved") return
                dispatch(setStatus(value))
              }}
            >
              {record.status === "approved" && <option value="approved">Approved</option>}
              <option value="draft">Draft</option>
              <option value="under_investigation">Under investigation</option>
              <option value="pending_qa">Pending QA</option>
              <option value="closed">Closed</option>
            </select>
          </label>
          {openSuggestions > 0 && record.root_causes.length > 0 && (
            <span className="open-count">
              {openSuggestions} open {openSuggestions === 1 ? "suggestion" : "suggestions"}
            </span>
          )}
        </div>
        <div className="top-actions">
          <label className="name-field">
            <span>Investigator</span>
            <input
              value={record.prepared_by.value}
              placeholder="Your name"
              onChange={(event) => dispatch(updateTracked({ path: "prepared_by", value: event.target.value }))}
            />
          </label>
          <button type="button" className="quiet" onClick={() => setLibraryOpen(true)}>
            Library
          </button>
          <button type="button" className="quiet" disabled={!investigationId} onClick={() => setAuditOpen(true)}>
            History
          </button>
          <button
            type="button"
            className="quiet"
            onClick={() => {
              if (dirty && !window.confirm("Discard unsaved changes?")) return
              dispatch(resetWorkspace())
              navigate("/")
            }}
          >
            New
          </button>
          <button type="button" className="primary" disabled={saving || (!dirty && Boolean(investigationId))} onClick={() => void onSave()}>
            {saving ? "Saving…" : !investigationId ? "Save draft" : dirty ? "Save" : "Saved"}
          </button>
        </div>
      </header>

      {(healthError || (health && !health.llm_configured) || (health && health.database !== "ok")) && (
        <p className={`banner ${healthError || health?.database !== "ok" ? "error" : "warn"}`}>
          {healthError && healthError}
          {!healthError && health && health.database !== "ok" && "The database is not reachable. Check Postgres and DATABASE_URL. "}
          {!healthError && health && !health.llm_configured && "No Groq API key is loaded. You can still edit and save records. Analysis and chat need GROQ_API_KEY in the root .env file."}
          {health?.model && !healthError && ` Model configured: ${health.model}.`}
        </p>
      )}
      {saveError && <p className="banner error">{saveError}</p>}
      {lastSavedAt && !dirty && !saveError && (
        <p className="save-note">Saved {new Date(lastSavedAt).toLocaleTimeString()}</p>
      )}

      <div className="tabbar">
        <button type="button" data-active={tab === "assistant"} onClick={() => setTab("assistant")}>
          Assistant
        </button>
        <button type="button" data-active={tab === "form"} onClick={() => setTab("form")}>
          RCA record
        </button>
      </div>

      <div className="workspace" data-tab={tab}>
        <FormPane />
        <AssistantPanel />
      </div>
      <Outlet />
      <LibraryDrawer open={libraryOpen} dirty={dirty} onClose={() => setLibraryOpen(false)} />
      <AuditDrawer open={auditOpen} investigationId={investigationId} onClose={() => setAuditOpen(false)} />
    </div>
  )
}
