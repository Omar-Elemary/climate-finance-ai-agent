import React from 'react'
import { getAgentColor } from './personaMeta'

interface StickerProps {
  agentId: string
  size?: number
  speaking?: boolean
  mood?: 'dark' | 'light'
}

/** Distinct accessory per persona family */
function Accessory({ kind, color }: { kind: string; color: string }) {
  switch (kind) {
    case 'investor':
      // tie + coin
      return (
        <g>
          <rect x="44" y="58" width="12" height="26" fill="#121A16" />
          <polygon points="44,58 56,58 50,50" fill="#121A16" />
          <circle cx="74" cy="26" r="10" fill="none" stroke="#121A16" strokeWidth="3" />
          <text x="74" y="31" textAnchor="middle" fontSize="12" fontWeight="900" fill="#121A16">$</text>
        </g>
      )
    case 'policy':
      // columns pediment + glasses
      return (
        <g>
          <polygon points="20,22 50,8 80,22" fill="#121A16" />
          <rect x="26" y="24" width="5" height="12" fill="#121A16" />
          <rect x="38" y="24" width="5" height="12" fill="#121A16" />
          <rect x="50" y="24" width="5" height="12" fill="#121A16" />
          <rect x="62" y="24" width="5" height="12" fill="#121A16" />
          <rect x="34" y="46" width="12" height="10" fill="none" stroke="#121A16" strokeWidth="2.5" />
          <rect x="54" y="46" width="12" height="10" fill="none" stroke="#121A16" strokeWidth="2.5" />
          <line x1="46" y1="50" x2="54" y2="50" stroke="#121A16" strokeWidth="2.5" />
        </g>
      )
    case 'scientist':
      // goggles + flask
      return (
        <g>
          <rect x="28" y="14" width="44" height="10" rx="5" fill="#121A16" />
          <circle cx="38" cy="50" r="9" fill="none" stroke="#121A16" strokeWidth="3" />
          <circle cx="62" cy="50" r="9" fill="none" stroke="#121A16" strokeWidth="3" />
          <line x1="47" y1="50" x2="53" y2="50" stroke="#121A16" strokeWidth="3" />
          <polygon points="72,66 84,66 80,84 76,84" fill="none" stroke="#121A16" strokeWidth="2.5" />
        </g>
      )
    case 'cfo':
      // visor + calculator
      return (
        <g>
          <rect x="24" y="20" width="52" height="12" rx="3" fill="#121A16" />
          <rect x="66" y="62" width="16" height="20" fill="#121A16" />
          <rect x="68" y="65" width="12" height="4" fill={color} />
          <circle cx="71" cy="74" r="1.6" fill={color} />
          <circle cx="77" cy="74" r="1.6" fill={color} />
        </g>
      )
    case 'env':
      // leaf sprout
      return (
        <g>
          <line x1="50" y1="22" x2="50" y2="10" stroke="#121A16" strokeWidth="3" />
          <ellipse cx="40" cy="12" rx="9" ry="5" fill="#121A16" transform="rotate(-25 40 12)" />
          <ellipse cx="60" cy="12" rx="9" ry="5" fill="#121A16" transform="rotate(25 60 12)" />
        </g>
      )
    case 'industry':
      // hard hat
      return (
        <g>
          <path d="M24 34 Q24 14 50 14 Q76 14 76 34 Z" fill="#121A16" />
          <rect x="18" y="32" width="64" height="7" rx="3" fill="#121A16" />
          <rect x="46" y="8" width="8" height="10" fill="#121A16" />
        </g>
      )
    case 'labour':
      // beanie + fist
      return (
        <g>
          <path d="M28 26 Q30 10 50 10 Q70 10 72 26 Z" fill="#121A16" />
          <rect x="28" y="24" width="44" height="8" fill="#121A16" />
          <circle cx="50" cy="8" r="4" fill="#121A16" />
        </g>
      )
    case 'compliance':
      // clipboard check
      return (
        <g>
          <rect x="64" y="58" width="20" height="24" fill="none" stroke="#121A16" strokeWidth="3" />
          <polyline points="67,70 72,75 81,63" fill="none" stroke="#121A16" strokeWidth="3" />
        </g>
      )
    default:
      // mic badge
      return (
        <g>
          <rect x="68" y="60" width="8" height="16" rx="4" fill="#121A16" />
          <path d="M64 74 Q72 82 80 74" fill="none" stroke="#121A16" strokeWidth="2.5" />
        </g>
      )
  }
}

function kindFor(agentId: unknown): string {
  const id = String(agentId ?? '').toLowerCase()
  if (id.includes('investor')) return 'investor'
  if (id.includes('policy_expert') || id.includes('policymaker') || id.includes('government')) return 'policy'
  if (id.includes('scient') || id.includes('academic')) return 'scientist'
  if (id.includes('cfo')) return 'cfo'
  if (id.includes('env_special') || id.includes('sustain') || id.includes('esg')) return 'env'
  if (id.includes('industr')) return 'industry'
  if (id.includes('labour') || id.includes('labor') || id.includes('worker') || id.includes('just_transition')) return 'labour'
  if (id.includes('compliance') || id.includes('officer') || id.includes('regulat')) return 'compliance'
  if (id.includes('fossil') || id.includes('fuel')) return 'industry'
  if (id.includes('supply')) return 'env'
  return 'default'
}

/**
 * PersonaSticker — a flat dossier-style face badge per agent.
 * speaking=true plays the talk cycle: bob + jaw + pop ring.
 */
const PersonaSticker: React.FC<StickerProps> = ({ agentId, size = 32, speaking = false }) => {
  const color = getAgentColor(agentId)
  const kind = kindFor(agentId)
  const skin = '#F2E7CF'

  return (
    <span
      className={`sticker ${speaking ? 'sticker-talking' : ''}`}
      style={{ width: size, height: size, background: color }}
      role="img"
      aria-label={`${agentId} sticker${speaking ? ', speaking' : ''}`}
    >
      <svg viewBox="0 0 100 100" width={size} height={size} aria-hidden>
        {/* face */}
        <rect x="30" y="30" width="40" height="46" rx="14" fill={skin} stroke="#121A16" strokeWidth="3" />
        {/* ears */}
        <circle cx="29" cy="55" r="5" fill={skin} stroke="#121A16" strokeWidth="2.5" />
        <circle cx="71" cy="55" r="5" fill={skin} stroke="#121A16" strokeWidth="2.5" />
        {/* eyes */}
        <g className="sticker-eyes">
          <circle cx="42" cy="52" r="3.4" fill="#121A16" />
          <circle cx="58" cy="52" r="3.4" fill="#121A16" />
        </g>
        {/* brows */}
        <line x1="37" y1="43" x2="47" y2="43" stroke="#121A16" strokeWidth="2.5" />
        <line x1="53" y1="43" x2="63" y2="43" stroke="#121A16" strokeWidth="2.5" />
        {/* mouth: jaw bar animates when talking */}
        {speaking ? (
          <rect className="sticker-jaw" x="42" y="63" width="16" height="9" rx="4" fill="#121A16" />
        ) : (
          <line x1="43" y1="66" x2="57" y2="66" stroke="#121A16" strokeWidth="3" strokeLinecap="round" />
        )}
        <Accessory kind={kind} color={color} />
      </svg>
      {speaking && <span className="sticker-ring" />}
    </span>
  )
}

export default PersonaSticker
