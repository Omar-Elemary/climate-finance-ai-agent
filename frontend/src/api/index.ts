import axios, { AxiosError } from 'axios'

const rawBaseUrl = import.meta.env.VITE_API_URL as string | undefined
// Dev default uses the Vite proxy (/api -> http://127.0.0.1:8000).
// Prod default hits the backend directly (no /api prefix on the backend).
const baseURL = rawBaseUrl && rawBaseUrl.trim() !== '' ? rawBaseUrl : '/api'

const api = axios.create({
  baseURL,
  timeout: 120000, // LLM-backed POST /discussions can take a while
})

// Add a request interceptor to show loading states if needed
api.interceptors.request.use(config => {
  // You could set a global loading state here if desired
  return config
})

// Add a response interceptor for error handling
api.interceptors.response.use(
  response => response,
  error => {
    // You could handle common errors here
    return Promise.reject(error)
  }
)

export interface Topic {
  id: string
  title: string
  domain: string
  description: string
  suggested_personas: string[]
}

export interface DiscussionMessage {
  message_id: string
  discussion_id: string
  agent_id: string
  agent_name: string
  content: string
  timestamp: string
  in_response_to: string | null
  metadata: Record<string, unknown>
  round: number
}

export interface DiscussionResponse {
  discussion_id: string
  topic: string
  domain?: string | null
  participants: string[]
  rounds_completed: number
  total_rounds: number
  status: string
  rounds: Array<{ round: number; messages: DiscussionMessage[] }>
  messages: DiscussionMessage[]
  opinions: Record<string, unknown[]>
}

export function getApiErrorMessage(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const axiosErr = err as AxiosError<{ error?: { message?: string; code?: string } }>
    const apiMessage = axiosErr.response?.data?.error?.message
    if (apiMessage && apiMessage.trim() !== '') return apiMessage
    if (axiosErr.code === 'ECONNABORTED') return 'Request timed out. The discussion may still be running — please try again.'
    if (!axiosErr.response) return 'Cannot reach the API. Is the backend running on http://localhost:8000?'
    const status = axiosErr.response.status
    if (status === 404) return 'Not found.'
    if (status === 503) return 'Service temporarily unavailable. Check LLM / retrieval configuration.'
  }
  if (err instanceof Error && err.message) return err.message
  return fallback
}

export const getTopics = async (): Promise<Topic[]> => {
  const response = await api.get('/topics')
  return response.data as Topic[]
}

export const createDiscussion = async (
  topic: string,
  numRounds: number,
  personas: string[],
  enableRetrieval: boolean,
  domain?: string | null,
): Promise<DiscussionResponse> => {
  const response = await api.post('/discussions', {
    topic,
    // Backend treats domain as an optional grouping tag; omit when empty.
    ...(domain && domain.trim() !== '' ? { domain: domain.trim() } : {}),
    num_rounds: numRounds,
    personas,
    enable_retrieval: enableRetrieval,
  }, {
    // A real multi-round LLM debate takes minutes, not seconds.
    timeout: 600000,
  })
  return response.data as DiscussionResponse
}

export const getDiscussion = async (id: string): Promise<DiscussionResponse> => {
  const response = await api.get(`/discussions/${id}`)
  return response.data as DiscussionResponse
}

export const getAnalytics = async (id: string) => {
  const response = await api.get(`/discussions/${id}/analytics`)
  return response.data
}
