import React from 'react'
import { useAppContext } from '../contexts/AppContext'

const MoodToggle: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
  const { mood, toggleMood } = useAppContext()
  const isDark = mood === 'dark'
  return (
    <button
      onClick={toggleMood}
      title={isDark ? 'Switch to light dossier mood' : 'Switch to dark war-room mood'}
      aria-label={isDark ? 'Switch to light mood' : 'Switch to dark mood'}
      className={`flex items-center gap-2 border font-mono2 transition-all duration-300 ${
        compact ? 'px-2 py-1 text-[10px]' : 'px-3 py-1.5 text-[11px]'
      } tracking-[0.2em] ${
        isDark
          ? 'border-paper/30 bg-transparent text-paper/80 hover:border-paper hover:text-paper'
          : 'border-black/25 bg-transparent text-black/70 hover:border-black hover:text-black'
      }`}
    >
      <span className={`inline-block h-2 w-2 rounded-full ${isDark ? 'bg-amberx' : 'bg-pit'}`} />
      {isDark ? '○ LIGHT' : '● DARK'}
    </button>
  )
}

export default MoodToggle
