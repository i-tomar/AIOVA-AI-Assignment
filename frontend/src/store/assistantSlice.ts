import { createSlice, type PayloadAction } from "@reduxjs/toolkit"

import type { ChatMessage } from "../types"
import { loadInvestigation, saveInvestigation } from "./thunks"
import { resetWorkspace } from "./workspace"

type Phase = "idle" | "running" | "chatting"

interface AssistantState {
  messages: ChatMessage[]
  phase: Phase
  activeNode: string | null
  phaseLog: string[]
  error: string | null
}

const initial = (): AssistantState => ({
  messages: [],
  phase: "idle",
  activeNode: null,
  phaseLog: [],
  error: null,
})

const assistantSlice = createSlice({
  name: "assistant",
  initialState: initial,
  reducers: {
    analysisStarted(state) {
      state.phase = "running"
      state.error = null
      state.phaseLog = []
      state.activeNode = "ingest"
    },
    analysisPhase(state, action: PayloadAction<string>) {
      state.activeNode = action.payload
      state.phaseLog.push(action.payload)
    },
    analysisFinished(state) {
      state.phase = "idle"
      state.activeNode = null
    },
    analysisFailed(state, action: PayloadAction<string>) {
      state.phase = "idle"
      state.activeNode = null
      state.error = action.payload
    },
    chatStarted(state) {
      state.phase = "chatting"
      state.error = null
    },
    chatFinished(state) {
      state.phase = "idle"
    },
    chatFailed(state, action: PayloadAction<string>) {
      state.phase = "idle"
      state.error = action.payload
    },
    pushMessage(state, action: PayloadAction<ChatMessage>) {
      state.messages.push(action.payload)
    },
    clearAssistantError(state) {
      state.error = null
    },
  },
  extraReducers(builder) {
    builder
      .addCase(resetWorkspace, () => initial())
      .addCase(loadInvestigation.fulfilled, (state, action) => {
        state.messages = action.payload.record.conversation ?? []
        state.phase = "idle"
        state.activeNode = null
        state.phaseLog = []
        state.error = null
      })
      .addCase(saveInvestigation.fulfilled, (state, action) => {
        state.messages = action.payload.record.conversation ?? []
      })
  },
})

export const {
  analysisStarted,
  analysisPhase,
  analysisFinished,
  analysisFailed,
  chatStarted,
  chatFinished,
  chatFailed,
  pushMessage,
  clearAssistantError,
} = assistantSlice.actions

export const assistantReducer = assistantSlice.reducer
