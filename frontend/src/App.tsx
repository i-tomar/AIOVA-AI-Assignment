import { Route, Routes } from "react-router-dom"

import { Workspace } from "./components/Workspace"

export default function App() {
  return (
    <Routes>
      <Route element={<Workspace />}>
        <Route path="/" element={<Nothing />} />
        <Route path="/i/:id" element={<Nothing />} />
      </Route>
    </Routes>
  )
}

function Nothing() {
  return null
}
