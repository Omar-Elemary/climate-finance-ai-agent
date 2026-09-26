import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownBodyProps {
  text: string
  light?: boolean
}

/**
 * Debate prose renderer: headings, bold, lists and — critically —
 * GFM tables as real war-room tables instead of raw pipe text.
 */
const MarkdownBody: React.FC<MarkdownBodyProps> = ({ text, light = false }) => {
  const ink = light ? 'text-black/85' : 'text-paper/85'
  const faint = light ? 'text-black/60' : 'text-paper/60'
  const line = light ? 'border-black/15' : 'border-white/12'
  const headBg = light ? 'bg-black/[0.05]' : 'bg-white/[0.06]'
  const rowAlt = light ? 'odd:bg-black/[0.025]' : 'odd:bg-white/[0.03]'

  return (
    <div className={`md-body font-serif-human text-[16px] leading-relaxed ${ink}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
          strong: ({ children }) => <strong className="font-extrabold">{children}</strong>,
          h1: ({ children }) => <h3 className="font-display mt-4 mb-2 text-lg font-black uppercase tracking-wide">{children}</h3>,
          h2: ({ children }) => <h3 className="font-display mt-4 mb-2 text-base font-black uppercase tracking-wide">{children}</h3>,
          h3: ({ children }) => <h4 className="font-display mt-3 mb-1.5 text-[15px] font-extrabold uppercase tracking-wide">{children}</h4>,
          h4: ({ children }) => <h4 className="font-display mt-3 mb-1.5 text-sm font-extrabold uppercase tracking-wide">{children}</h4>,
          ul: ({ children }) => <ul className="mb-3 space-y-1.5 pl-0">{children}</ul>,
          ol: ({ children }) => <ol className="mb-3 list-decimal space-y-1.5 pl-5">{children}</ol>,
          li: ({ children }) => (
            <li className="flex gap-2">
              <span aria-hidden className="mt-[9px] h-1.5 w-1.5 shrink-0 bg-signal" />
              <span className="min-w-0">{children}</span>
            </li>
          ),
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noreferrer" className="text-signal underline underline-offset-2">{children}</a>
          ),
          blockquote: ({ children }) => (
            <blockquote className={`my-3 border-l-4 border-signal/70 pl-3 italic ${faint}`}>{children}</blockquote>
          ),
          hr: () => <hr className={`my-4 border-t ${line}`} />,
          code: ({ children }) => (
            <code className={`font-mono2 rounded px-1 py-0.5 text-[13px] ${light ? 'bg-black/[0.06]' : 'bg-white/[0.08]'}`}>{children}</code>
          ),
          pre: ({ children }) => (
            <pre className={`font-mono2 my-3 overflow-x-auto border p-3 text-[13px] leading-relaxed ${line} ${light ? 'bg-black/[0.03]' : 'bg-black/40'}`}>{children}</pre>
          ),
          table: ({ children }) => (
            <div className={`my-4 overflow-x-auto border ${line}`}>
              <table className="w-full border-collapse text-left font-sans text-[13.5px] leading-snug">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className={headBg}>{children}</thead>,
          th: ({ children }) => (
            <th className={`font-display border px-3 py-2 text-[11px] font-extrabold uppercase tracking-wider ${line}`}>{children}</th>
          ),
          td: ({ children }) => <td className={`border px-3 py-2 align-top ${line}`}>{children}</td>,
          tr: ({ children }) => <tr className={rowAlt}>{children}</tr>,
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  )
}

export default MarkdownBody
