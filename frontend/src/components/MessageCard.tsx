import React from 'react'
import PersonaSticker from './PersonaSticker'
import MarkdownBody from './MarkdownBody'
import { getAgentColor, getAgentName, isFailedMessage } from './personaMeta'

export { AGENT_COLORS, getAgentColor, getAgentName, getInitials, isFailedMessage } from './personaMeta'

interface MessageCardProps {
  agentId: string
  message: string
  round: number
  isFirst?: boolean
  isLast?: boolean
  /** live playback states (optional for backwards-compat) */
  isActive?: boolean
  isPast?: boolean
  isUpcoming?: boolean
  displayText?: string
  isTyping?: boolean
  clash?: boolean
  mood?: 'dark' | 'light'
}

const MessageCard: React.FC<MessageCardProps> = ({
  agentId,
  message,
  round,
  isActive = false,
  isPast = true,
  isUpcoming = false,
  displayText,
  isTyping = false,
  clash = false,
  mood = 'dark',
}) => {
  const color = getAgentColor(agentId)
  const name = getAgentName(agentId)
  const text = displayText ?? message
  const light = mood === 'light'
  const failed = isFailedMessage(message)

  if (isUpcoming) {
    return (
      <div className="px-4 py-2 opacity-40 select-none" aria-hidden>
        <div className={`flex items-center gap-3 border border-dashed px-4 py-3 ${light ? 'border-black/20 bg-black/[0.03]' : 'border-white/15 bg-white/[0.02]'}`}>
          <div className={`font-mono2 text-[10px] tracking-[0.2em] ${light ? 'text-black/50' : 'text-white/40'}`}>
            {name} — QUEUED · R{round}
          </div>
          <div className={`h-px flex-1 ${light ? 'bg-black/10' : 'bg-white/10'}`} />
          <div className={`font-mono2 text-[10px] ${light ? 'text-black/40' : 'text-white/30'}`}>···</div>
        </div>
      </div>
    )
  }

  return (
    <article
      className={`anim-slide-in relative px-4 py-2 transition-all duration-500 ${
        isActive ? '' : isPast ? 'opacity-100' : ''
      }`}
    >
      <div
        className={`relative border transition-all duration-300 ${
          light ? 'bg-white' : 'bg-pit-2'
        } ${
          isActive
            ? 'anim-speaking-border border-2'
            : light ? 'border-black/15' : 'border-white/10'
        }`}
        style={isActive ? { borderLeft: `6px solid ${color}` } : { borderLeft: `4px solid ${color}55` }}
      >
        {/* header strip */}
        <div className={`flex items-center gap-3 border-b px-4 py-2 ${light ? 'border-black/10 bg-black/[0.04]' : 'border-white/10 bg-black/40'}`}>
          <PersonaSticker agentId={agentId} size={36} speaking={isActive} />
          <div className="min-w-0">
            <div className={`font-display text-[13px] font-800 font-extrabold uppercase tracking-wide leading-none ${light ? 'text-black' : 'text-paper'}`}>
              {name}
            </div>
            <div className={`font-mono2 mt-1 text-[10px] tracking-[0.18em] ${light ? 'text-black/55' : 'text-white/50'}`}>
              ROUND {String(round).padStart(2, '0')} · ON RECORD
            </div>
          </div>

          <div className="ml-auto flex items-center gap-3">
            {failed ? (
              <span className="anim-stamp border border-signal bg-signal/15 px-2 py-0.5 font-mono2 text-[10px] font-semibold tracking-[0.2em] text-signal">
                ■ TRANSMISSION FAILED
              </span>
            ) : (
              clash && (
                <span className="anim-stamp border border-signal bg-signal/15 px-2 py-0.5 font-mono2 text-[10px] font-semibold tracking-[0.2em] text-signal">
                  CLASH
                </span>
              )
            )}
            {isActive && !failed ? (
              <span className="flex items-end gap-[3px] text-signal" aria-label="speaking">
                <span className="eq-bar eq-1" />
                <span className="eq-bar eq-2" />
                <span className="eq-bar eq-3" />
                <span className="ml-2 flex items-center gap-1.5 font-mono2 text-[10px] tracking-[0.2em]">
                  <span className="anim-live-dot inline-block h-2 w-2 rounded-full bg-signal" />
                  SPEAKING
                </span>
              </span>
            ) : !failed ? (
              <span className={`font-mono2 text-[10px] tracking-[0.2em] ${light ? 'text-black/40' : 'text-white/35'}`}>● FILED</span>
            ) : null}
          </div>
        </div>

        {/* body */}
        <div className="px-4 py-3">
          {failed ? (
            <p className={`font-mono2 break-words text-[13px] leading-relaxed ${light ? 'text-black/60' : 'text-paper/50'}`}>
              {text}
            </p>
          ) : isTyping ? (
            <p className={`font-serif-human break-words text-[16px] leading-relaxed ${light ? 'text-black' : 'text-paper'}`}>
              {text}
              <span className="anim-blink ml-1 inline-block h-4 w-[8px] translate-y-[2px] bg-signal"> </span>
            </p>
          ) : (
            <MarkdownBody text={message} light={light} />
          )}
        </div>

        {isActive && <div className="pit-scanline pointer-events-none absolute inset-0 overflow-hidden" />}
      </div>
    </article>
  )
}

export default MessageCard
