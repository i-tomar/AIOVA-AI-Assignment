import { configureStore } from "@reduxjs/toolkit"

import { assistantReducer } from "./assistantSlice"
import { investigationReducer } from "./investigationSlice"
import { libraryReducer } from "./librarySlice"

export const store = configureStore({
  reducer: {
    investigation: investigationReducer,
    assistant: assistantReducer,
    library: libraryReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
