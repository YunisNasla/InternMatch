import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { load } from './lib/storage'
import Results from './pages/Results'
import Review from './pages/Review'
import Upload from './pages/Upload'

function Home() {
  const saved = load()
  // A returning student with a saved profile goes straight to their results.
  return saved.profile && saved.filters ? <Navigate to="/results" replace /> : <Upload />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/review" element={<Review />} />
        <Route path="/results" element={<Results />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
