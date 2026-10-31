import { createSlice, type PayloadAction } from "@reduxjs/toolkit"

import { emptyRecord, newId } from "../record"
import type {
  Approval,
  Cause,
  Capa,
  FishItem,
  Gap,
  ItemCollection,
  RCARecord,
  Status,
  TeamMember,
  TrackedKey,
  WhyStep,
} from "../types"
import { loadInvestigation, saveInvestigation } from "./thunks"
import { resetWorkspace } from "./workspace"

interface InvestigationState {
  id: string | null
  record: RCARecord
  highlighted: string[]
  dirty: boolean
  saving: boolean
  saveError: string | null
  lastSavedAt: string | null
  loading: boolean
  loadError: string | null
}

const initialState = (): InvestigationState => ({
  id: null,
  record: emptyRecord(),
  highlighted: [],
  dirty: false,
  saving: false,
  saveError: null,
  lastSavedAt: null,
  loading: false,
  loadError: null,
})

const investigationSlice = createSlice({
  name: "investigation",
  initialState,
  reducers: {
    updateTracked(state, action: PayloadAction<{ path: TrackedKey; value: string }>) {
      const field = state.record[action.payload.path]
      field.value = action.payload.value
      field.origin = "user"
      field.confirmed = true
      state.highlighted = state.highlighted.filter((item) => item !== action.payload.path)
      state.dirty = true
      state.saveError = null
    },
    confirmTracked(state, action: PayloadAction<{ paths: TrackedKey[] }>) {
      let changed = false
      for (const path of action.payload.paths) {
        const field = state.record[path]
        if (field.origin === "ai" && !field.confirmed) {
          field.confirmed = true
          changed = true
        }
        state.highlighted = state.highlighted.filter((item) => item !== path)
      }
      if (changed) state.dirty = true
    },
    updateItem(
      state,
      action: PayloadAction<{ collection: ItemCollection; id: string; patch: Record<string, string | boolean> }>,
    ) {
      const list = state.record[action.payload.collection] as { id: string }[]
      const item = list.find((entry) => entry.id === action.payload.id)
      if (!item) return
      const target = item as unknown as Record<string, string | boolean>
      for (const [key, value] of Object.entries(action.payload.patch)) {
        target[key] = value
      }
      state.dirty = true
      state.saveError = null
    },
    removeItem(state, action: PayloadAction<{ collection: ItemCollection; id: string }>) {
      const drop = <T extends { id: string }>(items: T[]) => items.filter((entry) => entry.id !== action.payload.id)
      const collection = action.payload.collection
      if (collection === "whys") state.record.whys = drop(state.record.whys)
      else if (collection === "fishbone") state.record.fishbone = drop(state.record.fishbone)
      else if (collection === "root_causes") state.record.root_causes = drop(state.record.root_causes)
      else if (collection === "contributing_factors") state.record.contributing_factors = drop(state.record.contributing_factors)
      else if (collection === "gaps") state.record.gaps = drop(state.record.gaps)
      else if (collection === "capas") state.record.capas = drop(state.record.capas)
      else state.record.team = drop(state.record.team)
      state.highlighted = state.highlighted.filter((item) => !item.includes(action.payload.id))
      state.dirty = true
      state.saveError = null
    },
    addBlank(state, action: PayloadAction<{ collection: ItemCollection }>) {
      const collection = action.payload.collection
      if (collection === "whys") state.record.whys.push(blankWhy())
      else if (collection === "fishbone") state.record.fishbone.push(blankFish())
      else if (collection === "root_causes") state.record.root_causes.push(blankCause("cause"))
      else if (collection === "contributing_factors") state.record.contributing_factors.push(blankCause("factor"))
      else if (collection === "gaps") state.record.gaps.push(blankGap())
      else if (collection === "capas") state.record.capas.push(blankCapa())
      else state.record.team.push(blankTeam())
      state.dirty = true
      state.saveError = null
    },
    confirmItem(
      state,
      action: PayloadAction<{ collection: ItemCollection; id: string; confirmed: boolean; by: string }>,
    ) {
      const list = state.record[action.payload.collection] as { id: string }[]
      const item = list.find((entry) => entry.id === action.payload.id) as
        | (Cause & WhyStep & FishItem & Capa)
        | undefined
      if (!item || !("confirmed" in item)) return
      if (action.payload.confirmed && "evidence" in item && !String(item.evidence || "").trim()) return
      item.confirmed = action.payload.confirmed
      if ("confirmed_by" in item) item.confirmed_by = action.payload.confirmed ? action.payload.by : ""
      if (action.payload.confirmed && "evidence_supported" in item) item.evidence_supported = true
      state.dirty = true
      state.saveError = null
    },
    setStatus(state, action: PayloadAction<Exclude<Status, "approved">>) {
      state.record.status = action.payload
      state.dirty = true
      state.saveError = null
    },
    patchApproval(state, action: PayloadAction<Partial<Approval>>) {
      state.record.approval = { ...state.record.approval, ...action.payload }
      state.dirty = true
      state.saveError = null
    },
    markApproved(state) {
      state.record.status = "approved"
      state.record.approval.decision = "approved"
      state.dirty = true
      state.saveError = null
    },
    markReturned(state) {
      state.record.status = "under_investigation"
      state.record.approval.decision = "returned"
      state.dirty = true
      state.saveError = null
    },
    applyServerRecord(state, action: PayloadAction<{ record: RCARecord; changedPaths: string[] }>) {
      state.record = action.payload.record
      state.highlighted = action.payload.changedPaths
      state.dirty = true
      state.saveError = null
    },
    clearHighlights(state) {
      state.highlighted = []
    },
  },
  extraReducers(builder) {
    builder
      .addCase(resetWorkspace, () => initialState())
      .addCase(loadInvestigation.pending, (state) => {
        state.loading = true
        state.loadError = null
      })
      .addCase(loadInvestigation.fulfilled, (state, action) => {
        state.loading = false
        state.id = action.payload.id
        state.record = action.payload.record
        state.highlighted = []
        state.dirty = false
        state.lastSavedAt = action.payload.updated_at
        state.loadError = null
        state.saveError = null
      })
      .addCase(loadInvestigation.rejected, (state, action) => {
        state.loading = false
        state.loadError = action.payload ?? "The investigation could not be opened."
      })
      .addCase(saveInvestigation.pending, (state) => {
        state.saving = true
        state.saveError = null
      })
      .addCase(saveInvestigation.fulfilled, (state, action) => {
        state.saving = false
        state.id = action.payload.id
        state.record = action.payload.record
        state.dirty = false
        state.lastSavedAt = action.payload.updated_at
        state.saveError = null
      })
      .addCase(saveInvestigation.rejected, (state, action) => {
        state.saving = false
        state.saveError = action.payload ?? "The investigation could not be saved."
      })
  },
})

function blankWhy(): WhyStep {
  return {
    id: newId("why"),
    question: "Why?",
    answer: "",
    evidence: "",
    grounded: false,
    origin: "user",
    confirmed: false,
  }
}

function blankFish(): FishItem {
  return {
    id: newId("fish"),
    category: "Man",
    cause: "",
    evidence: "",
    plausible: true,
    grounded: false,
    origin: "user",
    confirmed: false,
  }
}

function blankCause(prefix: string): Cause {
  return {
    id: newId(prefix),
    statement: "",
    category: "Method",
    evidence: "",
    confidence: "low",
    evidence_supported: false,
    grounded: false,
    ai_suggested: false,
    confirmed: false,
    confirmed_by: "",
  }
}

function blankGap(): Gap {
  return {
    id: newId("gap"),
    topic: "",
    why_it_matters: "",
    suggested_source: "",
    origin: "user",
    resolved: false,
  }
}

function blankCapa(): Capa {
  return {
    id: newId("capa"),
    capa_type: "corrective",
    description: "",
    rationale: "",
    owner: "",
    due_date: "",
    effectiveness_check: "",
    status: "proposed",
    ai_suggested: false,
    confirmed: false,
  }
}

function blankTeam(): TeamMember {
  return {
    id: newId("team"),
    name: "",
    role: "",
    department: "",
    origin: "user",
    confirmed: false,
  }
}

export const {
  updateTracked,
  confirmTracked,
  updateItem,
  removeItem,
  addBlank,
  confirmItem,
  setStatus,
  patchApproval,
  markApproved,
  markReturned,
  applyServerRecord,
  clearHighlights,
} = investigationSlice.actions

export const investigationReducer = investigationSlice.reducer
