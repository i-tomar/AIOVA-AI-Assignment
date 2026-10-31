import { createAsyncThunk } from "@reduxjs/toolkit"

import {
  createInvestigation,
  getInvestigation,
  listInvestigations,
  updateInvestigation,
  ApiError,
} from "../api"
import type { ChatMessage, InvestigationEnvelope, InvestigationSummary, RCARecord } from "../types"

interface SaveShape {
  investigation: { id: string | null; record: RCARecord }
  assistant: { messages: ChatMessage[] }
}

export const loadInvestigation = createAsyncThunk<InvestigationEnvelope, string, { rejectValue: string }>(
  "investigation/load",
  async (id, { rejectWithValue }) => {
    try {
      return await getInvestigation(id)
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "The investigation could not be opened."
      return rejectWithValue(message)
    }
  },
)

export const saveInvestigation = createAsyncThunk<InvestigationEnvelope, void, { rejectValue: string }>(
  "investigation/save",
  async (_, { getState, rejectWithValue }) => {
    const state = getState() as SaveShape
    const actor = state.investigation.record.prepared_by.value.trim() || "investigator"
    const record: RCARecord = {
      ...state.investigation.record,
      conversation: state.assistant.messages,
    }
    try {
      if (state.investigation.id) {
        return await updateInvestigation(state.investigation.id, record, actor)
      }
      return await createInvestigation(record, actor)
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "The investigation could not be saved."
      return rejectWithValue(message)
    }
  },
)

export const fetchLibrary = createAsyncThunk<InvestigationSummary[], void, { rejectValue: string }>(
  "library/fetch",
  async (_, { rejectWithValue }) => {
    try {
      return await listInvestigations()
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "The library could not be loaded."
      return rejectWithValue(message)
    }
  },
)
