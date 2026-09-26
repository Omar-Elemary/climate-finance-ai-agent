import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { getTopics, createDiscussion as apiCreateDiscussion, getDiscussion, getAnalytics, getApiErrorMessage } from '../api'
import type { Topic, DiscussionMessage } from '../api'

interface DiscussionData {
  discussion_id: string
  topic: string
  domain?: string | null
  participants: string[]
  rounds_completed: number
  total_rounds: number
  status: string
  rounds: Array<{
    round: number
    messages: DiscussionMessage[]
  }>
  messages: DiscussionMessage[]
  opinions: Record<string, unknown[]>
  conclusion?: string | null
}

interface AnalyticsData {
  discussion_id: string
  topic: string
  generated_at: string
  schema_version: string
  summary: Record<string, unknown>
  opinion_trajectory: Record<string, Array<{ round: number; stance: number | null; change: number | string | null; status: string }>>
  agreement: Array<{ round: number; agreement_score: number | null; status: string }>
  influence: Record<string, { influence_score: number | null; messages_sent: number; status: string }>
  sentiment: Array<Record<string, unknown>>
  interaction_graph: {
    nodes: Array<{ agent_id: string; message_count: number; influence_score: number | null }>
    edges: Array<{ source: string; target: string; weight: number; kind: string }>
  }
  metric_statuses: Record<string, { status: string }>
  warnings: string[]
}

interface AppContextType {
  topics: Topic[]
  currentTopic: string | null
  currentDiscussionId: string | null
  discussionData: DiscussionData | null
  analyticsData: AnalyticsData | null
  loading: boolean
  error: string | null
  mood: 'dark' | 'light'
  toggleMood: () => void
  setMood: (m: 'dark' | 'light') => void
  clearError: () => void
  setTopic: (topic: string) => void
  createDiscussion: (topic: string, numRounds: number, personas: string[], enableRetrieval: boolean) => Promise<void>
  loadDiscussion: (id: string, opts?: { quiet?: boolean }) => Promise<void>
  loadAnalytics: (id: string, opts?: { quiet?: boolean }) => Promise<void>
}

const AppContext = createContext<AppContextType | undefined>(undefined)

export const AppContextProvider = ({ children }: { children: React.ReactNode }) => {
  const [topics, setTopics] = useState<Topic[]>([])
  const [currentTopic, setCurrentTopic] = useState<string | null>(null)
  const [currentDiscussionId, setCurrentDiscussionId] = useState<string | null>(null)
  const [discussionData, setDiscussionData] = useState<DiscussionData | null>(null)
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [mood, setMoodState] = useState<'dark' | 'light'>(() => {
    try {
      const saved = localStorage.getItem('qf-mood')
      return saved === 'light' ? 'light' : 'dark'
    } catch {
      return 'dark'
    }
  })

  const setMood = useCallback((m: 'dark' | 'light') => {
    setMoodState(m)
    try {
      localStorage.setItem('qf-mood', m)
    } catch { /* ignore */ }
    document.documentElement.dataset.mood = m
    document.documentElement.classList.toggle('mood-light', m === 'light')
  }, [])

  const toggleMood = useCallback(() => {
    setMoodState((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark'
      try {
        localStorage.setItem('qf-mood', next)
      } catch { /* ignore */ }
      document.documentElement.dataset.mood = next
      document.documentElement.classList.toggle('mood-light', next === 'light')
      return next
    })
  }, [])

  useEffect(() => {
    document.documentElement.dataset.mood = mood
    document.documentElement.classList.toggle('mood-light', mood === 'light')
  }, [])

  const loadDiscussion = useCallback(async (id: string, opts?: { quiet?: boolean }) => {
    const quiet = opts?.quiet === true
    try {
      if (!quiet) {
        setLoading(true)
        setError(null)
      }
      const data = await getDiscussion(id)
      setDiscussionData(data)
      if (!quiet) setError(null)
    } catch (err: unknown) {
      // Quiet polls (live streaming) swallow transient failures: a torn
      // mid-write read or a busy store resolves on the next tick.
      if (!quiet) setError(getApiErrorMessage(err, 'Failed to load discussion'))
    } finally {
      if (!quiet) setLoading(false)
    }
  }, [])

  const loadAnalytics = useCallback(async (id: string, opts?: { quiet?: boolean }) => {
    const quiet = opts?.quiet === true
    try {
      if (!quiet) {
        setLoading(true)
        setError(null)
      }
      const data = await getAnalytics(id)
      setAnalyticsData(data)
      if (!quiet) setError(null)
    } catch (err: unknown) {
      if (!quiet) setError(getApiErrorMessage(err, 'Failed to load analytics'))
    } finally {
      if (!quiet) setLoading(false)
    }
  }, [])

  const handleCreateDiscussion = useCallback(async (topic: string, numRounds: number, personas: string[], enableRetrieval: boolean) => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiCreateDiscussion(topic, numRounds, personas, enableRetrieval)
      setCurrentDiscussionId(response.discussion_id)
      setCurrentTopic(topic)
      // Don't await loadDiscussion here - let DiscussionPage handle it
      // await loadDiscussion(response.discussion_id)
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Failed to create discussion'))
    } finally {
      setLoading(false)
    }
  }, []) // Removed loadDiscussion from dependencies

  const clearError = useCallback(() => setError(null), [])

  useEffect(() => {
    const fetchTopics = async () => {
      try {
        setLoading(true)
        setError(null) // FIX: Clear error on success
        const data = await getTopics()
        setTopics(data)
      } catch (err: unknown) {
        setError(getApiErrorMessage(err, 'Failed to load topics'))
      } finally {
        setLoading(false)
      }
    }

    fetchTopics()
  }, [])

  return (
    <AppContext.Provider value={{
      topics,
      currentTopic,
      currentDiscussionId,
      discussionData,
      analyticsData,
      loading,
      error,
      mood,
      toggleMood,
      setMood,
      clearError,
      setTopic: setCurrentTopic,
      createDiscussion: handleCreateDiscussion,
      loadDiscussion,
      loadAnalytics
    }}>
      {children}
    </AppContext.Provider>
  )
}

export const useAppContext = () => {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useAppContext must be used within AppContextProvider')
  }
  return context
}