import { createSlice } from "@reduxjs/toolkit"

import type { InvestigationSummary } from "../types"
import { fetchLibrary } from "./thunks"

interface LibraryState {
  items: InvestigationSummary[]
  loading: boolean
  error: string | null
}

const librarySlice = createSlice({
  name: "library",
  initialState: { items: [], loading: false, error: null } as LibraryState,
  reducers: {},
  extraReducers(builder) {
    builder
      .addCase(fetchLibrary.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchLibrary.fulfilled, (state, action) => {
        state.loading = false
        state.items = action.payload
      })
      .addCase(fetchLibrary.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload ?? "The library could not be loaded."
      })
  },
})

export const libraryReducer = librarySlice.reducer
