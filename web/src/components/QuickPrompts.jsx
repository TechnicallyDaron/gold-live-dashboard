import { useState } from 'react'
import { api } from '../lib/api.js'
import './QuickPrompts.css'

const PROMPTS = [
  'Explain this in simple terms',
  'Is now a good entry?',
  'What flips this setup?',
  'Risk for a beginner',
]

export default function QuickPrompts({ asset }) {
  const [question, setQuestion] = useState('')
  const [state, setState] = useState({ status: 'idle' })

  const ask = async (q) => {
    const trimmed = q.trim()
    if (!trimmed || !asset || state.status === 'loading') return
    setState({ status: 'loading' })
    try {
      const res = await api.ask(asset, trimmed)
      setState({ status: 'success', answer: res.answer, usage: res.usage })
    } catch (err) {
      setState({ status: 'error', detail: err.message })
    }
  }

  return (
    <section className="quick-prompts">
      <span className="qp-title">Quick Prompts</span>

      <div className="qp-pills">
        {PROMPTS.map((p) => (
          <button
            key={p}
            type="button"
            className="qp-pill"
            onClick={() => {
              setQuestion(p)
              ask(p)
            }}
          >
            {p}
          </button>
        ))}
      </div>

      <div className="qp-input-row">
        <input
          className="qp-input"
          placeholder="Ask about this setup…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') ask(question)
          }}
        />
        <button
          type="button"
          className="qp-ask-btn"
          onClick={() => ask(question)}
          disabled={state.status === 'loading'}
          aria-label="Ask"
        >
          ⚡
        </button>
      </div>

      {state.status === 'loading' && <div className="skeleton qp-answer-skeleton" />}

      {state.status === 'error' && (
        <div className="qp-error-notice">{state.detail}</div>
      )}

      {state.status === 'success' && (
        <div className="qp-answer-card">
          <p className="qp-answer-text">{state.answer}</p>
          <span className="qp-usage">
            {state.usage.count}/{state.usage.limit} AI calls today
          </span>
        </div>
      )}
    </section>
  )
}
