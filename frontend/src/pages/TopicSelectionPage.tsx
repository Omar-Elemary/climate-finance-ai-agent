import React, { useState } from 'react'
import { useAppContext } from '../contexts/AppContext'
import { useNavigate } from 'react-router-dom'
import MoodToggle from '../components/MoodToggle'
import PersonaSticker from '../components/PersonaSticker'
import { getAgentColor, getAgentName } from '../components/MessageCard'

const FALLBACK_PERSONAS = ['investor', 'policy_expert', 'scientist', 'cfo_agent', 'env_specialist', 'industry_representative']

const TopicSelectionPage: React.FC = () => {
  const { topics, loading, error, createDiscussion, currentDiscussionId, mood } = useAppContext()
  const navigate = useNavigate()
  const light = mood === 'light'
  const [question, setQuestion] = useState<string>('')
  const [numRounds, setNumRounds] = useState<number>(3)
  const [selectedPersonas, setSelectedPersonas] = useState<string[]>(['investor', 'policy_expert', 'scientist'])
  const [enableRetrieval, setEnableRetrieval] = useState<boolean>(true)
  const [starting, setStarting] = useState(false)

  const allPersonas = React.useMemo(() => {
    const set = new Set<string>(FALLBACK_PERSONAS)
    topics.forEach((t) => t.suggested_personas?.forEach((p) => set.add(p)))
    return Array.from(set).sort()
  }, [topics])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim() || selectedPersonas.length === 0 || starting) return
    setStarting(true)
    try {
      await createDiscussion(question.trim(), numRounds, selectedPersonas, enableRetrieval)
    } finally {
      setStarting(false)
    }
  }

  React.useEffect(() => {
    if (currentDiscussionId) navigate(`/discussion/${currentDiscussionId}`)
  }, [currentDiscussionId, navigate])

  const togglePersona = (p: string) => {
    setSelectedPersonas((prev) => (prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]))
  }

  return (
    <div className={`min-h-screen overflow-x-clip transition-colors duration-300 ${light ? 'bg-[#F4F1E8] text-[#121A16]' : 'bg-pit text-paper'}`}>
      <div className={`border-b ${light ? 'border-black/15 bg-[#F4F1E8]/90' : 'border-white/10 bg-black/80'}`}>
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2">
          <span className="font-mono2 text-[11px] tracking-[0.3em] opacity-60">QUBETERRA · FLOOR BRIEF</span>
          <span className="flex items-center gap-1.5 border border-moss/60 bg-moss/15 px-2 py-0.5 font-mono2 text-[10px] tracking-[0.25em] text-moss">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-moss" /> STANDBY
          </span>
          <div className="ml-auto"><MoodToggle compact /></div>
        </div>
      </div>

      <main className="mx-auto max-w-6xl px-4 pb-20 pt-8">
        <header className={`border p-6 ${light ? 'border-black/20 bg-white' : 'border-white/10 bg-pit-2'}`}>
          <div className="font-mono2 text-[10px] tracking-[0.35em] opacity-60">CLIMATE FINANCE · MULTI-AGENT DEBATE · {light ? 'LIGHT DOSSIER' : 'DARK WAR-ROOM'}</div>
          <h1 className="font-display mt-2 text-4xl font-black uppercase leading-[0.95] tracking-tight sm:text-6xl">
            Table<br />the motion.
          </h1>
          <p className={`font-serif-human mt-3 max-w-2xl text-lg leading-snug ${light ? 'text-black/75' : 'text-paper/75'}`}>
            Write one hard question. Pick the agents. They argue on record — you read the clash, not a summary.
          </p>
        </header>

        {error && (
          <div className="mt-4 border border-signal/60 bg-signal/10 p-3 font-mono2 text-xs text-signal" role="alert">{error}</div>
        )}

        <div className="mt-4 grid min-w-0 gap-4 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
          {/* order slip */}
          <form onSubmit={handleSubmit} className={`min-w-0 border p-5 ${light ? 'border-black/20 bg-white' : 'border-white/10 bg-pit-2'}`}>
            <div className="font-mono2 text-[10px] tracking-[0.3em] opacity-60">01 · YOUR MOTION</div>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Should developed nations double public adaptation grants without private co-financing?"
              className={`font-serif-human mt-2 block min-h-[120px] w-full min-w-0 resize-y break-words border p-4 text-xl leading-snug outline-none transition-colors ${
                light
                  ? 'border-black/25 bg-[#F4F1E8] text-black placeholder:text-black/35 focus:border-black'
                  : 'border-white/20 bg-black/50 text-paper placeholder:text-paper/30 focus:border-signal'
              }`}
            />
            {!question.trim() && <div className="mt-1 font-mono2 text-[11px] text-signal">REQUIRED — ONE MOTION TO OPEN THE FLOOR</div>}

            <div className="mt-5 grid min-w-0 gap-4 min-[560px]:grid-cols-2">
              <div className="min-w-0">
                <div className="font-mono2 text-[10px] tracking-[0.3em] opacity-60">02 · ROUNDS</div>
                <div className="mt-2 grid grid-cols-5 gap-1">
                  {[1, 2, 3, 4, 5].map((r) => (
                    <button
                      type="button"
                      key={r}
                      onClick={() => setNumRounds(r)}
                      className={`flex-1 border py-2 font-display text-sm font-black transition-all ${
                        numRounds === r
                          ? 'border-signal bg-signal text-white'
                          : light
                            ? 'border-black/20 text-black/60 hover:border-black'
                            : 'border-white/15 text-paper/60 hover:border-paper'
                      }`}
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </div>
              <div className="min-w-0">
                <div className="font-mono2 text-[10px] tracking-[0.3em] opacity-60">03 · EVIDENCE FEED</div>
                <button
                  type="button"
                  onClick={() => setEnableRetrieval(!enableRetrieval)}
                  className={`mt-2 flex w-full min-w-0 items-center justify-between gap-2 border px-3 py-2 font-mono2 text-[11px] tracking-[0.15em] ${
                    light ? 'border-black/20' : 'border-white/15'
                  }`}
                >
                  <span className="min-w-0 truncate">{enableRetrieval ? '● RAG GROUNDED' : '○ FREE DEBATE'}</span>
                  <span className={`inline-block h-4 w-8 shrink-0 border p-[2px] ${enableRetrieval ? 'border-moss' : light ? 'border-black/30' : 'border-white/25'}`}>
                    <span className={`block h-full transition-all ${enableRetrieval ? 'ml-auto w-1/2 bg-moss' : 'w-1/2 bg-current opacity-30'}`} />
                  </span>
                </button>
              </div>
            </div>

            <div className="mt-5">
              <div className="flex items-baseline justify-between">
                <div className="font-mono2 text-[10px] tracking-[0.3em] opacity-60">04 · SEAT THE AGENTS ({selectedPersonas.length})</div>
                <div className="font-mono2 text-[10px] opacity-50">MIN 2 TO CLASH</div>
              </div>
              <div className="mt-2 grid gap-2 grid-cols-1 min-[520px]:grid-cols-2">
                {allPersonas.map((p) => {
                  const color = getAgentColor(p)
                  const on = selectedPersonas.includes(p)
                  return (
                    <button
                      type="button"
                      key={p}
                      title={getAgentName(p)}
                      onClick={() => togglePersona(p)}
                      className={`flex min-w-0 w-full items-center gap-3 overflow-hidden border px-3 py-2.5 text-left transition-all duration-200 ${
                        on
                          ? light
                            ? 'border-black/30 text-black'
                            : 'border-white/25 bg-pit-3 text-paper'
                          : light
                            ? 'border-black/15 bg-transparent opacity-75 hover:border-black/40 hover:opacity-100'
                            : 'border-white/10 bg-transparent opacity-65 hover:border-white/30 hover:opacity-100'
                      }`}
                      style={on ? { borderLeft: `6px solid ${color}`, backgroundColor: light ? `${color}1A` : undefined } : { borderLeft: `3px solid ${color}55` }}
                    >
                      <PersonaSticker agentId={p} size={36} speaking={false} />
                      <span className="min-w-0 flex-1">
                        <span className="block break-words font-display text-[12px] font-extrabold uppercase leading-[1.15]">{getAgentName(p)}</span>
                        {on ? (
                          <span className="mt-1.5 inline-block px-1.5 py-0.5 font-mono2 text-[9px] font-bold tracking-[0.2em] text-black" style={{ backgroundColor: color }}>
                            ■ SEATED
                          </span>
                        ) : (
                          <span className="mt-1 block font-mono2 text-[9px] tracking-[0.2em] opacity-60">
                            ○ BENCH
                          </span>
                        )}
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>

            <button
              type="submit"
              disabled={!question.trim() || selectedPersonas.length < 2 || starting || loading}
              className="anim-slide-in mt-6 w-full bg-signal py-4 font-display text-lg font-black uppercase tracking-widest text-white transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {starting || loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="flex items-end gap-[3px]"><span className="eq-bar eq-1" /><span className="eq-bar eq-2" /><span className="eq-bar eq-3" /></span>
                  Opening floor…
                </span>
              ) : (
                '▶ Open the floor'
              )}
            </button>
            {selectedPersonas.length < 2 && (
              <div className="mt-2 text-center font-mono2 text-[11px] text-signal">SEAT AT LEAST 2 AGENTS — A DEBATE NEEDS FRICTION</div>
            )}
          </form>

          {/* preset motions */}
          <aside className={`h-fit min-w-0 border p-5 transition-colors duration-300 ${light ? 'border-black/20 bg-white text-black' : 'border-white/10 bg-pit-2 text-paper'}`}>
            <div className="font-mono2 text-[10px] tracking-[0.3em] opacity-60">PRESET MOTIONS · FROM /TOPICS</div>
            <div className="mt-3 min-w-0 space-y-2">
              {topics.length === 0 && (
                <div className="font-mono2 text-[11px] opacity-60">
                  {loading ? 'LOADING MOTIONS…' : 'NO PRESETS — WRITE YOUR OWN MOTION.'}
                </div>
              )}
              {topics.slice(0, 6).map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setQuestion(t.title)}
                  className={`group w-full min-w-0 overflow-hidden border p-3 text-left transition-colors ${light ? 'border-black/15 hover:border-signal' : 'border-white/15 hover:border-signal'}`}
                >
                  <div className="break-words font-display text-[13px] font-extrabold uppercase leading-snug">{t.title}</div>
                  <div className="mt-1 whitespace-normal break-words font-mono2 text-[10px] leading-relaxed tracking-[0.08em] opacity-60">
                    {(t.domain || 'OPEN').toUpperCase()} · {(t.suggested_personas || []).slice(0, 3).join(' / ') || 'OPEN FLOOR'}
                  </div>
                </button>
              ))}
            </div>
            <div className={`ticker-mask ticker-pause mt-4 overflow-hidden border-t pt-3 ${light ? 'border-black/10' : 'border-white/10'}`}>
              <div className="anim-ticker flex w-max whitespace-nowrap font-mono2 text-[10px] tracking-[0.25em] opacity-60">
                {[0, 1, 2, 3].map((k) => (
                  <span key={k} aria-hidden={k > 0} className="shrink-0 pr-8">
                    IPCC · UNFCCC · IRENA · IEA · DISAGREEMENT IS DATA ·
                  </span>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  )
}

export default TopicSelectionPage
