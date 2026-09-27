import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useAppContext } from '../contexts/AppContext'
import { Link, useParams } from 'react-router-dom'
import MessageCard, { getAgentColor, getAgentName, isFailedMessage } from '../components/MessageCard'
import PersonaSticker from '../components/PersonaSticker'
import MoodToggle from '../components/MoodToggle'

type FlatMsg = {
  flatIndex: number
  round: number
  message_id: string
  agent_id: string
  content: string
}

const SPEEDS = [1, 2, 4] as const
const CLASH_RE = /(disagree|oppose|wrong|reject|risky|no evidence|flawed|cannot|against|clash|bottleneck)/i

const DiscussionPage: React.FC = () => {
  const { discussionData, loading, error, loadDiscussion, loadAnalytics, mood } = useAppContext()
  const { id } = useParams<{ id: string }>()
  const light = mood === 'light'

  const [visibleCount, setVisibleCount] = useState(0)
  const [charCount, setCharCount] = useState(0)
  const [isPlaying, setIsPlaying] = useState(true)
  const [speedIdx, setSpeedIdx] = useState(1)
  const [roundFlash, setRoundFlash] = useState<number | null>(null)
  const [mode, setMode] = useState<'live' | 'full'>('live')
  const timer = useRef<number | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const speed = SPEEDS[speedIdx]

  useEffect(() => {
    if (id) {
      loadDiscussion(id)
      loadAnalytics(id)
    }
  }, [id, loadDiscussion, loadAnalytics])

  // Live stream: while the backend is still debating, re-read the
  // persisted state quietly. New turns extend `flat` and the replay
  // engine picks them up without resetting what already played.
  const liveStatus = discussionData?.status
  useEffect(() => {
    if (liveStatus !== 'running' || !id) return
    const t = window.setInterval(() => {
      loadDiscussion(id, { quiet: true })
    }, 3000)
    return () => window.clearInterval(t)
  }, [liveStatus, id, loadDiscussion])

  const flat: FlatMsg[] = useMemo(() => {
    if (!discussionData) return []
    const out: FlatMsg[] = []
    const rounds = [...(discussionData.rounds || [])].sort((a, b) => (a?.round ?? 0) - (b?.round ?? 0))
    rounds.forEach((r) => {
      ;(r?.messages || []).forEach((m: any, i: number) => {
        const rawContent = m?.content
        out.push({
          flatIndex: out.length,
          round: m?.round ?? r?.round ?? 0,
          message_id: m?.message_id || `r${r?.round ?? 0}-${i}`,
          agent_id: m?.agent_id ?? 'unknown_agent',
          content: typeof rawContent === 'string' ? rawContent : String(rawContent ?? ''),
        })
      })
    })
    return out
  }, [discussionData])

  const participants: string[] = discussionData?.participants || []

  const spokenCounts = useMemo(() => {
    const m: Record<string, number> = {}
    flat.slice(0, mode === 'full' ? flat.length : visibleCount).forEach((f) => {
      m[f.agent_id] = (m[f.agent_id] || 0) + 1
    })
    return m
  }, [flat, visibleCount, mode])

  useEffect(() => {
    setVisibleCount(0)
    setCharCount(0)
    setIsPlaying(true)
    setMode('live')
    setRoundFlash(null)
  }, [discussionData?.discussion_id])

  useEffect(() => {
    if (roundFlash === null) return
    const t = window.setTimeout(() => setRoundFlash(null), 1250)
    return () => window.clearTimeout(t)
  }, [roundFlash])

  useEffect(() => {
    if (!flat.length || mode === 'full' || !isPlaying || roundFlash !== null) return
    if (visibleCount >= flat.length) return
    if (visibleCount === 0) {
      const firstRound = flat[0]?.round
      setRoundFlash(firstRound ?? 1)
      setVisibleCount(1)
      setCharCount(0)
      return
    }
    const active = flat[visibleCount - 1]
    if (!active) return
    if (isFailedMessage(active.content)) {
      // Dead air reads instantly — no typing theater for failed transmissions.
      if (charCount < active.content.length) setCharCount(active.content.length)
      timer.current = window.setTimeout(() => {
        const next = flat[visibleCount]
        if (next && next.round !== active.round) setRoundFlash(next.round)
        setVisibleCount((v) => Math.min(flat.length, v + 1))
        setCharCount(0)
      }, Math.max(250, 600 / speed))
      return () => {
        if (timer.current) window.clearTimeout(timer.current)
      }
    }
    if (charCount < active.content.length) {
      timer.current = window.setTimeout(() => {
        setCharCount((c) => Math.min(active.content.length, c + 3 * speed))
      }, 24)
    } else {
      timer.current = window.setTimeout(() => {
        if (visibleCount >= flat.length) {
          setIsPlaying(false)
          return
        }
        const next = flat[visibleCount]
        if (next && next.round !== active.round) setRoundFlash(next.round)
        setVisibleCount((v) => Math.min(flat.length, v + 1))
        setCharCount(0)
      }, Math.max(350, 1100 / speed))
    }
    return () => {
      if (timer.current) window.clearTimeout(timer.current)
    }
  }, [flat, visibleCount, charCount, isPlaying, speed, roundFlash, mode])

  useEffect(() => {
    if (mode !== 'live') return
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [visibleCount, charCount, mode])

  if (loading && !discussionData) {
    return (
      <div className={`flex min-h-screen items-center justify-center ${light ? 'bg-[#F4F1E8]' : 'bg-pit'}`}>
        <div className="text-center">
          <div className="mx-auto mb-4 flex items-end justify-center gap-1 text-signal">
            <span className="eq-bar eq-1" /><span className="eq-bar eq-2" /><span className="eq-bar eq-3" />
          </div>
          <p className={`font-mono2 text-xs tracking-[0.3em] ${light ? 'text-black/60' : 'text-paper/70'}`}>TUNING FLOOR FEED…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`min-h-screen p-8 ${light ? 'bg-[#F4F1E8]' : 'bg-pit'}`}>
        <div className="border border-signal/50 bg-signal/10 p-4 font-mono2 text-sm text-red-800">{error}</div>
        <Link to="/" className="mt-4 inline-block font-mono2 text-xs underline">← Back</Link>
      </div>
    )
  }

  if (!discussionData) {
    return (
      <div className={`flex min-h-screen items-center justify-center ${light ? 'bg-[#F4F1E8]' : 'bg-pit'}`}>
        <p className="font-mono2 text-sm opacity-60">No discussion data available</p>
      </div>
    )
  }

  const total = flat.length
  const done = mode === 'full' ? total : Math.min(visibleCount, total)
  const activeMsg = mode === 'live' && visibleCount > 0 && visibleCount <= total ? flat[visibleCount - 1] : null
  const activeDone = activeMsg ? charCount >= activeMsg.content.length : true
  const progress = total ? Math.round((done / total) * 100) : 0
  const currentRound = activeMsg?.round ?? discussionData.rounds_completed ?? 1

  const replay = () => {
    if (timer.current) window.clearTimeout(timer.current)
    setVisibleCount(0)
    setCharCount(0)
    setMode('live')
    setIsPlaying(true)
  }
  const stepNext = () => {
    if (mode === 'full' || visibleCount >= total) return
    setCharCount(flat[visibleCount - 1]?.content.length ?? 0)
    window.setTimeout(() => {
      const cur = flat[visibleCount - 1]
      const nxt = flat[visibleCount]
      if (nxt && cur && nxt.round !== cur.round) setRoundFlash(nxt.round)
      setVisibleCount((v) => Math.min(total, v + 1))
      setCharCount(0)
    }, 60)
  }

  return (
    <div className={`min-h-screen transition-colors duration-300 ${light ? 'bg-[#F4F1E8] text-[#121A16]' : 'bg-pit text-paper'}`}>
      {/* top status bar */}
      <div className={`sticky top-0 z-30 border-b backdrop-blur ${light ? 'border-black/15 bg-[#F4F1E8]/90' : 'border-white/10 bg-black/80'}`}>
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2">
          <Link to="/" className={`font-mono2 text-[11px] tracking-[0.2em] ${light ? 'text-black/60 hover:text-black' : 'text-paper/60 hover:text-paper'}`}>← INDEX</Link>
          <span className="flex items-center gap-1.5 border border-signal/60 bg-signal/15 px-2 py-0.5 font-mono2 text-[10px] font-semibold tracking-[0.25em] text-signal">
            <span className="anim-live-dot inline-block h-1.5 w-1.5 rounded-full bg-signal" /> LIVE REPLAY
          </span>
          <span className={`hidden font-mono2 text-[10px] tracking-[0.2em] sm:inline ${light ? 'text-black/45' : 'text-paper/40'}`}>
            {discussionData.discussion_id.slice(0, 8).toUpperCase()} · R{String(currentRound).padStart(2, '0')}/{String(discussionData.total_rounds).padStart(2, '0')} · {done}/{total} STATEMENTS
          </span>
          <div className="ml-auto flex items-center gap-2">
            <MoodToggle compact />
            <button
              onClick={() => setMode(mode === 'live' ? 'full' : 'live')}
              className={`border px-2 py-1 font-mono2 text-[10px] tracking-[0.2em] ${light ? 'border-black/25 text-black/70 hover:border-black' : 'border-white/20 text-paper/70 hover:border-paper hover:text-paper'}`}
            >
              {mode === 'live' ? 'FULL FILE' : 'REPLAY'}
            </button>
            <Link
              to={`/discussion/${discussionData.discussion_id}/analytics`}
              className={`px-3 py-1 font-display text-[11px] font-extrabold uppercase tracking-wider ${light ? 'bg-black text-[#F4F1E8] hover:bg-black/85' : 'bg-paper text-black hover:bg-white'}`}
            >
              Analytics →
            </Link>
          </div>
        </div>
        <div className={`h-1 w-full ${light ? 'bg-black/10' : 'bg-white/10'}`}>
          <div className="h-1 bg-signal transition-all duration-500" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-4 pb-24 pt-6">
        <header className={`border p-5 ${light ? 'border-black/20 bg-white' : 'border-white/10 bg-pit-2'}`}>
          <div className={`font-mono2 text-[10px] tracking-[0.3em] ${light ? 'text-black/55' : 'text-paper/50'}`}>
            {light ? 'FIELD DOSSIER · FLOOR DEBATE' : 'CLIMATE FINANCE · FLOOR DEBATE'} · {progress}% FILED · {light ? 'LIGHT MOOD' : 'DARK MOOD'}
          </div>
          <h1 className="font-display mt-2 break-words text-3xl font-black uppercase leading-[1.02] tracking-tight sm:text-5xl">
            {discussionData.topic}
          </h1>
          <div className={`mt-3 flex flex-wrap items-center gap-2 font-mono2 text-[11px] ${light ? 'text-black/60' : 'text-paper/60'}`}>
            <span>{participants.length} AGENTS</span>
            <span className="opacity-40">/</span>
            <span>{discussionData.rounds_completed}/{discussionData.total_rounds} ROUNDS</span>
            <span className="opacity-40">/</span>
            <span className={activeDone ? 'text-moss' : 'text-signal'}>
              {mode === 'full' ? '■ COMPLETE FILE' : activeMsg ? (activeDone ? '■ BEAT' : '● DELIVERING') : '○ STANDBY'}
            </span>
          </div>
        </header>

        {/* roster */}
        <div className="mt-4 grid grid-cols-1 gap-2 min-[520px]:grid-cols-2 lg:grid-cols-4">
          {participants.map((p) => {
            const color = getAgentColor(p)
            const isSpeaking = mode === 'live' && activeMsg?.agent_id === p && !activeDone
            const hasSpoken = (spokenCounts[p] || 0) > 0
            return (
              <div
                key={p}
                title={getAgentName(p)}
                className={`min-w-0 overflow-hidden border px-3 py-2 transition-all duration-300 ${isSpeaking ? `anim-speaking-border border-2 ${light ? 'bg-white' : 'bg-pit-3'}` : light ? 'border-black/15 bg-white' : 'border-white/10 bg-pit-2'}`}
                style={isSpeaking ? { borderLeft: `5px solid ${color}` } : { borderLeft: `3px solid ${color}66` }}
              >
                <div className="flex min-w-0 items-center gap-2">
                  <PersonaSticker agentId={p} size={34} speaking={isSpeaking} />
                  <div className="min-w-0 flex-1">
                    <div className={`truncate font-display text-[11px] font-extrabold uppercase leading-tight ${light ? 'text-black' : 'text-paper'}`}>{getAgentName(p)}</div>
                    <div className={`mt-0.5 font-mono2 text-[9px] tracking-[0.2em] ${light ? 'text-black/50' : 'text-paper/45'}`}>
                      {isSpeaking ? '● ON MIC' : hasSpoken ? `■ ${spokenCounts[p]} FILED` : '○ QUEUED'}
                    </div>
                  </div>
                  {isSpeaking && (
                    <span className="ml-auto flex items-end gap-[2px] text-signal">
                      <span className="eq-bar eq-1" /><span className="eq-bar eq-2" /><span className="eq-bar eq-3" />
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* transport */}
        <div className={`mt-4 flex flex-wrap items-center gap-2 border px-3 py-2 ${light ? 'border-black/20 bg-white' : 'border-white/10 bg-black/50'}`}>
          {mode === 'live' ? (
            <>
              <button onClick={() => setIsPlaying(!isPlaying)} className="bg-signal px-4 py-1.5 font-display text-[12px] font-black uppercase tracking-wider text-white hover:brightness-110">
                {isPlaying ? '❚❚ Hold' : '▶ Resume'}
              </button>
              <button onClick={stepNext} className={`border px-3 py-1.5 font-mono2 text-[11px] ${light ? 'border-black/25 text-black/75 hover:border-black' : 'border-white/20 text-paper/80 hover:border-paper'}`}>STEP →</button>
              <button onClick={replay} className={`border px-3 py-1.5 font-mono2 text-[11px] ${light ? 'border-black/25 text-black/75 hover:border-black' : 'border-white/20 text-paper/80 hover:border-paper'}`}>↺ REPLAY</button>
              <button onClick={() => setSpeedIdx((speedIdx + 1) % SPEEDS.length)} className="border border-amberx/60 px-3 py-1.5 font-mono2 text-[11px] text-amberx">
                {speed}× SPEED
              </button>
            </>
          ) : (
            <button onClick={replay} className={`px-4 py-1.5 font-display text-[12px] font-black uppercase ${light ? 'bg-black text-white' : 'bg-paper text-black'}`}>▶ Replay live</button>
          )}
          <span className={`ml-auto font-mono2 text-[10px] tracking-[0.2em] ${light ? 'text-black/50' : 'text-paper/45'}`}>
            {mode === 'live' ? 'AUTO-FEED · TYPED AS SPOKEN' : 'FULL TRANSCRIPT · ALL ROUNDS OPEN'}
          </span>
        </div>

        {/* floor */}
        <div className={`relative mt-4 border ${light ? 'border-black/20 bg-white/60' : 'border-white/10 bg-pit-2/60'}`}>
          {!light && <div className="pit-noise pointer-events-none absolute inset-0 opacity-40" />}
          <div className={`relative border-b px-4 py-2 font-mono2 text-[10px] tracking-[0.3em] ${light ? 'border-black/10 bg-black/[0.05] text-black/60' : 'border-white/10 bg-black/60 text-paper/55'}`}>
            FLOOR FEED {mode === 'live' ? '— PLAYING BACK IN ORDER' : '— COMPLETE FILE, NEWEST LAST'}
          </div>

          <div className="relative space-y-1 py-3">
            {mode === 'full'
              ? discussionData.rounds.map((r: any) => (
                  <React.Fragment key={r.round}>
                    <div className="px-4 pt-3">
                      <div className={`font-display text-sm font-black uppercase tracking-widest ${light ? 'text-black/70' : 'text-paper/70'}`}>— Round {String(r.round).padStart(2, '0')} —</div>
                    </div>
                    {r.messages.map((m: any, i: number) => (
                      <MessageCard key={m.message_id || `${r.round}-${i}`} agentId={m.agent_id} message={m.content} round={m.round ?? r.round} clash={CLASH_RE.test(m.content)} mood={mood} />
                    ))}
                  </React.Fragment>
                ))
              : flat.map((f, i) => {
                  if (i >= visibleCount) {
                    return <MessageCard key={f.message_id} agentId={f.agent_id} message={f.content} round={f.round} isUpcoming mood={mood} />
                  }
                  const isActiveMsg = i === visibleCount - 1
                  const msg = flat[i]
                  const typed = isActiveMsg ? msg.content.slice(0, charCount) : msg.content
                  return (
                    <MessageCard
                      key={f.message_id}
                      agentId={f.agent_id}
                      message={f.content}
                      round={f.round}
                      isActive={isActiveMsg && !activeDone}
                      isPast={!isActiveMsg || activeDone}
                      displayText={typed}
                      isTyping={isActiveMsg && !activeDone}
                      clash={CLASH_RE.test(f.content)}
                      mood={mood}
                    />
                  )
                })}
            <div ref={bottomRef} />
          </div>

          {done >= total && (
            <div className={`relative border-t px-4 py-4 ${light ? 'border-moss/40 bg-moss/10' : 'border-moss/40 bg-moss/10'}`}>
              <div className="anim-stamp inline-block border-2 border-moss px-3 py-1 font-display text-sm font-black uppercase tracking-[0.2em] text-moss">
                ■ Floor closed — {total} statements
              </div>
              <div className={`mt-2 font-mono2 text-[11px] ${light ? 'text-black/60' : 'text-paper/60'}`}>
                Full file open. <Link className="underline" to={`/discussion/${discussionData.discussion_id}/analytics`}>Open analytics →</Link>
              </div>
            </div>
          )}

          {/* final conclusion — the debate's closing synthesis */}
          {(mode === 'full' || done >= total) && discussionData.conclusion && (
            <div className={`relative border-t px-4 py-5 ${light ? 'border-black/20 bg-white' : 'border-white/10 bg-black/60'}`}>
              <div className={`font-mono2 text-[10px] tracking-[0.3em] ${light ? 'text-black/55' : 'text-paper/50'}`}>
                FINAL CONCLUSION — RAPPORTEUR'S SYNTHESIS
              </div>
              <div className={`mt-2 whitespace-pre-line font-mono2 text-[13px] leading-relaxed ${light ? 'text-black/85' : 'text-paper/85'}`}>
                {discussionData.conclusion}
              </div>
            </div>
          )}
        </div>

        {/* ticker */}
        <div className={`ticker-mask ticker-pause mt-4 overflow-hidden border ${light ? 'border-black/20 bg-black text-[#F4F1E8]' : 'border-white/10 bg-black'}`}>
          <div className="anim-ticker flex w-max whitespace-nowrap px-0 py-2 font-mono2 text-[10px] tracking-[0.25em] opacity-70">
            {[0, 1, 2, 3].map((k) => (
              <span key={k} aria-hidden={k > 0} className="shrink-0 pr-8">
                {participants.map((p) => getAgentName(p).toUpperCase()).join(' /// ')} /// SOURCES: IPCC · UNFCCC · IRENA · IEA /// {light ? 'LIGHT DOSSIER' : 'DARK WAR-ROOM'} /// DISAGREEMENT IS DATA ///
              </span>
            ))}
          </div>
        </div>
      </div>

      {roundFlash !== null && mode === 'live' && (
        <div className={`pointer-events-none fixed inset-0 z-40 flex items-center justify-center ${light ? 'bg-[#F4F1E8]/85' : 'bg-black/70'}`}>
          <div className="text-center">
            <div className={`anim-slam font-display text-7xl font-black uppercase sm:text-8xl ${light ? 'text-black' : 'text-paper'}`}>
              Round {String(roundFlash).padStart(2, '0')}
            </div>
            <div className="anim-slam mx-auto mt-3 h-1 w-56 bg-signal" />
            <div className={`mt-2 font-mono2 text-[11px] tracking-[0.4em] ${light ? 'text-black/60' : 'text-paper/60'}`}>MIC OPEN — SPEAK IN ORDER</div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DiscussionPage
