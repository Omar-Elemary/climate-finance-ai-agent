import React, { useEffect, useMemo } from 'react'
import { useAppContext } from '../contexts/AppContext'
import { Link, useParams } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts'
import InteractionGraph from '../components/InteractionGraph'
import MoodToggle from '../components/MoodToggle'
import { getAgentColor } from '../components/MessageCard'

type OpinionPoint = { round: number; stance: number | null; change?: number | string | null; status: string }
type AgreementPoint = { round: number; agreement_score: number | null; status: string }

function getAgentInitials(agentId: string): string {
  const normalized = agentId.replace(/-/g, '_').replace(/\s+/g, '_')
  const parts = normalized.split('_').filter(Boolean)
  if (parts.length >= 2) {
    return ((parts[0]?.[0] || 'A') + (parts[1]?.[0] || '')).toUpperCase()
  }
  const word = parts[0] || agentId
  return word.slice(0, 2).toUpperCase()
}

function formatAgentName(agentId: string): string {
  return agentId
    .replace(/-/g, '_')
    .split('_')
    .filter(Boolean)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

const AnalyticsPage: React.FC = () => {
  const { analyticsData, loading, error, loadAnalytics, mood } = useAppContext()
  const { id } = useParams<{ id: string }>()
  const light = mood === 'light'

  useEffect(() => {
    if (id) {
      loadAnalytics(id)
    }
  }, [id, loadAnalytics])

  const opinionData = useMemo(() => {
    if (!analyticsData) return [] as Array<Record<string, number | null> & { round: number }>
    const rows = new Map<number, Record<string, number | null> & { round: number }>()
    const agents = Object.keys(analyticsData.opinion_trajectory ?? {})
    agents.forEach(agent => {
      const trajectory = (analyticsData.opinion_trajectory[agent] ?? []) as OpinionPoint[]
      trajectory.forEach(point => {
        if (typeof point.round !== 'number') return
        const existing = rows.get(point.round)
        if (existing) {
          existing[agent] = typeof point.stance === 'number' ? point.stance : null
        } else {
          rows.set(point.round, {
            round: point.round,
            [agent]: typeof point.stance === 'number' ? point.stance : null,
          })
        }
      })
    })
    return Array.from(rows.values()).sort((a, b) => a.round - b.round)
  }, [analyticsData])

  const agents = useMemo(
    () => (analyticsData ? Object.keys(analyticsData.opinion_trajectory ?? {}) : []),
    [analyticsData],
  )

  const agreementData = useMemo(() => {
    if (!analyticsData) return [] as Array<{ round: number; score: number | null }>
    return ((analyticsData.agreement ?? []) as AgreementPoint[])
      .filter(item => typeof item.round === 'number')
      .map(item => ({
        round: item.round,
        score: typeof item.agreement_score === 'number' ? item.agreement_score : null,
      }))
      .sort((a, b) => a.round - b.round)
  }, [analyticsData])

  const influenceData = useMemo(() => {
    if (!analyticsData) return [] as Array<{ agent: string; score: number | null }>
    return Object.keys(analyticsData.influence ?? {}).map(agent => ({
      agent,
      score:
        typeof analyticsData.influence[agent]?.influence_score === 'number'
          ? (analyticsData.influence[agent].influence_score as number)
          : null,
    }))
  }, [analyticsData])

  if (loading && !analyticsData) {
    return (
      <main className={`flex min-h-screen items-center justify-center ${light ? 'bg-[#F4F1E8]' : 'bg-pit'}`} aria-busy="true" aria-live="polite">
        <div className="text-center space-y-4">
          <div className="mx-auto flex items-end justify-center gap-1 text-signal">
            <span className="eq-bar eq-1" /><span className="eq-bar eq-2" /><span className="eq-bar eq-3" />
          </div>
          <p className={`font-mono2 text-xs tracking-[0.3em] ${light ? 'text-black/60' : 'text-paper/70'}`}>TALLYING STANCES…</p>
        </div>
      </main>
    )
  }

  if (error) {
    return (
      <main className="max-w-3xl mx-auto px-4 py-12">
        <div className="bg-red-50 border-l-4 border-red-500 p-6 mb-6 flex items-start space-x-4" role="alert">
          <div className="flex-shrink-0 h-12 w-12 flex items-center justify-center bg-red-50">
            <svg aria-hidden="true" className="h-6 w-6 text-red-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M7 20a10.011 10.011 0 015.302-7.197m0 0a10.011 10.011 0 0110.016-0M20 21v-2a4 4 0 00-3-3.414M5 20a10.011 10.011 0 00-5.302-7.198"></path>
            </svg>
          </div>
          <div>
            <p className="text-sm font-medium text-red-800">{error}</p>
            <p className="mt-1 text-sm text-gray-500">
              Please try again or contact support if the issue persists.
            </p>
            {id && (
              <button
                type="button"
                onClick={() => loadAnalytics(id)}
                className="mt-3 inline-flex items-center px-4 py-2 min-h-[44px] text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
              >
                Retry
              </button>
            )}
          </div>
        </div>
      </main>
    )
  }

  if (!analyticsData) {
    return (
      <main className="min-h-screen flex items-center justify-center px-4">
        <div className="text-center py-12">
          <p className="text-gray-500">No discussion data available</p>
          <p className="mt-2 text-sm text-gray-400">
            Start a discussion to generate analytics.
          </p>
          <Link
            to="/"
            className="mt-4 inline-flex items-center px-4 py-2 min-h-[44px] text-sm font-medium text-white bg-climate-blue rounded-lg hover:bg-climate-blue-dark focus:outline-none focus-visible:ring-2 focus-visible:ring-climate-blue focus-visible:ring-offset-2"
          >
            Back to topics
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main className={`min-h-screen transition-colors duration-300 ${light ? 'bg-[#F4F1E8] text-[#121A16]' : 'bg-pit text-paper'}`}>
      <div className={`border-b ${light ? 'border-black/15 bg-[#F4F1E8]/90' : 'border-white/10 bg-black/80'}`}>
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-2">
          <Link to={`/discussion/${analyticsData.discussion_id}`} className={`font-mono2 text-[11px] tracking-[0.2em] ${light ? 'text-black/60 hover:text-black' : 'text-paper/60 hover:text-paper'}`}>← FLOOR</Link>
          <span className="flex items-center gap-1.5 border border-moss/60 bg-moss/15 px-2 py-0.5 font-mono2 text-[10px] tracking-[0.25em] text-moss">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-moss" /> TALLY
          </span>
          <div className="ml-auto"><MoodToggle compact /></div>
        </div>
      </div>
      <div className="relative py-8 px-4 max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className={`font-mono2 text-[10px] tracking-[0.3em] ${light ? 'text-black/55' : 'text-paper/50'}`}>AFTER-ACTION · {light ? 'LIGHT DOSSIER' : 'DARK WAR-ROOM'}</div>
          <h1 className="font-display mt-2 text-4xl font-black uppercase tracking-tight sm:text-5xl">
            The tally.
          </h1>
          <div className="font-serif-human mt-2 text-xl">{analyticsData.topic}</div>
          <div className={`mt-4 h-1 w-full ${light ? 'bg-black/10' : 'bg-white/10'}`} role="progressbar" aria-valuenow={100} aria-valuemin={0} aria-valuemax={100} aria-label="Analytics ready">
            <div className="h-1 bg-signal" style={{ width: '100%' }}></div>
          </div>
        </div>

        {/* Analytics Cards */}
        <div className="grid gap-4 mb-8">
          {/* Opinion Trajectory */}
          <section aria-labelledby="opinion-heading" className={light ? 'border border-black/20 bg-white' : 'border border-white/10 bg-pit-2'}>
            <div className="px-8 py-6">
              <div className="flex items-center justify-between mb-4">
                <h2 id="opinion-heading" className="text-xl font-bold text-climate-blue">
                  Opinion Trajectory
                </h2>
                <p className="text-sm text-climate-blue/60">
                  Stance evolution across rounds
                </p>
              </div>
              <p className="mb-6 text-sm text-gray-600">
                Shows how each agent&apos;s stance evolved across discussion rounds
              </p>
              {!opinionData.length ? (
                <div className="text-center py-12" role="status">
                  <p className="text-gray-500">No opinion data available</p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={350}>
                  <LineChart data={opinionData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      dataKey="round"
                      type="number"
                      domain={['dataMin', 'dataMax']}
                      allowDecimals={false}
                      name="Round"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fill: '#6b7280' }}
                    />
                    <YAxis
                      domain={[-1.2, 1.2]}
                      name="Stance (-1 = Against, 0 = Neutral, +1 = In Favor)"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fill: '#6b7280' }}
                    />
                    <Tooltip
                      formatter={(value) => {
                        if (typeof value === 'number') return [value.toFixed(2), 'Stance']
                        return [String(value ?? '—'), 'Stance']
                      }}
                    />
                    <Legend
                      verticalAlign="top"
                      height={36}
                      formatter={(value: string) => formatAgentName(value)}
                    />
                    {agents.map((agent, index) => (
                      <Line
                        key={agent}
                        dataKey={agent}
                        connectNulls
                        stroke={`hsl(${(index * 360) / Math.max(agents.length, 1)}, 70%, 50%)`}
                        strokeWidth={3}
                        dot={false}
                        type="monotone"
                        isAnimationActive={true}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </section>

          {/* Agreement */}
          <section aria-labelledby="agreement-heading" className={light ? 'border border-black/20 bg-white' : 'border border-white/10 bg-pit-2'}>
            <div className="px-8 py-6">
              <div className="flex items-center justify-between mb-4">
                <h2 id="agreement-heading" className="text-xl font-bold text-climate-blue">
                  Agreement Levels
                </h2>
                <p className="text-sm text-climate-blue/60">
                  Group consensus measurement
                </p>
              </div>
              <p className="mb-6 text-sm text-gray-600">
                Measures group alignment across rounds (0 = disagreement, 1 = agreement)
              </p>
              {!agreementData.length ? (
                <div className="text-center py-12" role="status">
                  <p className="text-gray-500">No agreement data available</p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={agreementData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      dataKey="round"
                      type="number"
                      domain={['dataMin', 'dataMax']}
                      allowDecimals={false}
                      name="Round"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fill: '#6b7280' }}
                    />
                    <YAxis
                      domain={[0, 1]}
                      name="Agreement Score"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fill: '#6b7280' }}
                    />
                    <Tooltip
                      formatter={(value) => {
                        if (typeof value === 'number') return [`${(value * 100).toFixed(1)}%`, 'Agreement']
                        return ['—', 'Agreement']
                      }}
                    />
                    <Legend
                      verticalAlign="top"
                      height={36}
                    />
                    <Bar
                      dataKey="score"
                      name="Agreement"
                      fill="url(#agreementGradient)"
                      radius={[6, 6, 0, 0]}
                    />
                    <defs>
                      <linearGradient id="agreementGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" />
                        <stop offset="100%" stopColor="#059669" />
                      </linearGradient>
                    </defs>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </section>

          {/* Influence */}
          <section aria-labelledby="influence-heading" className={light ? 'border border-black/20 bg-white' : 'border border-white/10 bg-pit-2'}>
            <div className="px-8 py-6">
              <div className="flex items-center justify-between mb-4">
                <h2 id="influence-heading" className="text-xl font-bold text-climate-blue">
                  Influence Scores
                </h2>
                <p className="text-sm text-climate-blue/60">
                  Relative impact on discussion
                </p>
              </div>
              <p className="mb-6 text-sm text-gray-600">
                Shows each agent&apos;s relative influence on the discussion
              </p>
              {!influenceData.length ? (
                <div className="text-center py-12" role="status">
                  <p className="text-gray-500">No influence data available</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {influenceData.map((item) => {
                    const color = getAgentColor(item.agent)
                    const pct = item.score == null ? null : item.score * 100
                    return (
                      <div key={item.agent} className="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg">
                        <div className="flex-shrink-0 h-10 w-10" aria-hidden="true">
                          <div
                            className="h-10 w-10 rounded-lg flex items-center justify-center text-white text-sm font-medium"
                            style={{ backgroundColor: color }}
                          >
                            {getAgentInitials(item.agent)}
                          </div>
                        </div>
                        <div className="flex-1">
                          <div className="flex justify-between mb-2">
                            <span className="font-medium text-gray-900">
                              {formatAgentName(item.agent)}
                            </span>
                            <span className="text-sm font-medium text-climate-blue">
                              {pct == null ? '—' : `${pct.toFixed(1)}%`}
                            </span>
                          </div>
                          <div
                            className="w-full bg-gray-200 rounded-full h-3"
                            role="progressbar"
                            aria-valuenow={pct == null ? 0 : Math.round(pct)}
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-label={`${formatAgentName(item.agent)} influence`}
                          >
                            <div
                              className="h-3 rounded-full bg-climate-blue"
                              style={{ width: `${pct == null ? 0 : pct}%` }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </section>

          {/* Interaction Graph */}
          <section aria-labelledby="graph-heading" className={light ? 'border border-black/20 bg-white' : 'border border-white/10 bg-pit-2'}>
            <div className="px-8 py-6">
              <div className="flex items-center justify-between mb-4">
                <h2 id="graph-heading" className="text-xl font-bold text-climate-blue">
                  Interaction Graph
                </h2>
                <p className="text-sm text-climate-blue/60">
                  Agent relationships and influence
                </p>
              </div>
              <p className="mb-6 text-sm text-gray-600">
                Visualizes relationships and interaction strength between agents
              </p>
              {!analyticsData.interaction_graph.nodes.length ? (
                <div className="text-center py-12" role="status">
                  <p className="text-gray-500">No interaction data available</p>
                </div>
              ) : (
                <div className="relative">
                  <InteractionGraph
                    nodes={analyticsData.interaction_graph.nodes}
                    edges={analyticsData.interaction_graph.edges}
                  />
                </div>
              )}
            </div>
          </section>
        </div>

        {/* Metrics Status */}
        <section aria-labelledby="status-heading" className="mt-8 p-6 bg-gray-50 rounded-xl border border-gray-200">
          <h2 id="status-heading" className="text-xl font-bold text-gray-900 mb-4">
            System Status
          </h2>
          <div className="grid gap-4 mb-6">
            {Object.entries(analyticsData.metric_statuses).map(([metric, statusObj]) => (
              <div key={metric} className="flex items-center p-4 bg-white rounded-lg shadow-sm border border-gray-100">
                <div className="flex-shrink-0 h-8 w-8 flex items-center justify-center" aria-hidden="true">
                  {statusObj.status === 'ok' ? (
                    <svg className="h-5 w-5 text-green-500" fill="none" viewBox="0 0 20 20" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 20 20" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M10 6v4m0 4h.01M10 2a8 8 0 100 16 8 8 0 000-16z" />
                    </svg>
                  )}
                </div>
                <div className="ml-4">
                  <p className="font-medium text-gray-900 mb-1">
                    {metric.charAt(0).toUpperCase() + metric.slice(1).replace(/_/g, ' ')}
                  </p>
                  <p className="text-sm text-gray-500">
                    {statusObj.status === 'ok' ? 'Operational' : 'Limited Functionality'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Warnings */}
        {analyticsData.warnings.length > 0 && (
          <section aria-labelledby="warnings-heading" className="mt-8 p-6 bg-yellow-50 rounded-xl border border-yellow-200">
            <h2 id="warnings-heading" className="text-xl font-bold text-gray-900 mb-4">
              Important Notes
            </h2>
            <ul className="space-y-3">
              {analyticsData.warnings.map((warning, index) => (
                <li key={index} className="flex items-start space-x-3">
                  <div className="flex-shrink-0" aria-hidden="true">
                    <svg className="h-5 w-5 text-yellow-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 1118 0z"></path>
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm text-yellow-800">{warning}</p>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </main>
  )
}

export default AnalyticsPage
