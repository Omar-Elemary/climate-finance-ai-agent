import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom'
import React from 'react'
import TopicSelectionPage from './pages/TopicSelectionPage'
import DiscussionPage from './pages/DiscussionPage'
import AnalyticsPage from './pages/AnalyticsPage'
import { AppContextProvider } from './contexts/AppContext'

class FloorErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { message: string | null }
> {
  state = { message: null as string | null }

  static getDerivedStateFromError(err: unknown) {
    return { message: err instanceof Error ? err.message : 'Something broke while rendering.' }
  }

  componentDidCatch() {
    /* surfaced via fallback UI */
  }

  render() {
    if (this.state.message) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-pit p-8 text-paper">
          <div className="max-w-md border border-signal/60 bg-signal/10 p-6">
            <div className="font-mono2 text-[10px] tracking-[0.3em] text-signal">■ FLOOR FEED INTERRUPTED</div>
            <p className="font-mono2 mt-2 text-sm">{this.state.message}</p>
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => window.location.reload()}
                className="bg-signal px-4 py-2 font-display text-xs font-black uppercase text-white"
              >
                ↺ Reload
              </button>
              <Link to="/" className="border border-white/25 px-4 py-2 font-mono2 text-xs text-paper">
                ← Index
              </Link>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

function App() {
  return (
    <AppContextProvider>
      <BrowserRouter>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-white focus:text-climate-blue focus:rounded-lg focus:ring-2 focus:ring-climate-blue"
        >
          Skip to main content
        </a>
        <div id="main-content">
          <FloorErrorBoundary>
            <Routes>
              <Route path="/" element={<TopicSelectionPage />} />
              <Route path="/discussion/:id" element={<DiscussionPage />} />
              <Route path="/discussion/:id/analytics" element={<AnalyticsPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </FloorErrorBoundary>
        </div>
      </BrowserRouter>
    </AppContextProvider>
  )
}

export default App