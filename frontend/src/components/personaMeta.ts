export const AGENT_COLORS: Record<string, string> = {
  investor: '#d98e32',
  policy_expert: '#3d8b5f',
  scientist: '#7fb4c5',
  cfo_agent: '#e5484d',
  env_specialist: '#8fce62',
  industry_representative: '#ef4444',
  default: '#8a94a0',
}

export function getAgentColor(agentId: unknown): string {
  const key = String(agentId ?? 'agent').toLowerCase().replace(/[\s-]+/g, '_')
  return AGENT_COLORS[key as keyof typeof AGENT_COLORS] || AGENT_COLORS.default
}

export function getAgentName(agentId: unknown): string {
  return String(agentId ?? 'agent')
    .split('_')
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ') || 'Agent'
}

export function getInitials(agentId: unknown): string {
  const parts = String(agentId ?? '')
    .split(/[_ ]+/)
    .filter((p) => /^[a-z]/i.test(p))
  if (parts.length >= 2) {
    return ((parts[0]?.[0] || 'A') + (parts[1]?.[0] || '')).toUpperCase()
  }
  const word = parts[0] || 'AG'
  return word.slice(0, 2).toUpperCase()
}

export function isFailedMessage(t: unknown): boolean {
  return /^\[Agent error/i.test(String(t ?? ''))
}
