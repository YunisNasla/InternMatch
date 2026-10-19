import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router'
import './index.css'
import Results from './pages/Results'
import Review from './pages/Review'
import Upload from './pages/Upload'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Upload />} />
        <Route path="/review" element={<Review />} />
        <Route path="/results" element={<Results />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
