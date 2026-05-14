import { useState, useRef, useEffect } from 'react'
import type { ChatMessage } from '../types'
import { chat } from '../lib/api'

export default function ChatWidget() {
  const [historial, setHistorial] = useState<ChatMessage[]>([
    { rol: 'asistente', texto: 'Bienvenido. Soy el analista de El Observador Digital. Puede preguntarme sobre cobertura noticiosa, sesgo editorial o comparar cómo los medios bolivianos abordan un tema.' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [historial, loading])

  const enviar = async () => {
    const msg = input.trim()
    if (!msg || loading) return
    setHistorial(h => [...h, { rol: 'usuario', texto: msg }])
    setInput('')
    setLoading(true)
    try {
      const res = await chat(msg, historial)
      setHistorial(h => [...h, { rol: 'asistente', texto: res.respuesta }])
    } catch {
      setHistorial(h => [...h, { rol: 'asistente', texto: 'Error al conectar con la API.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', border: '1px solid var(--border)', fontFamily: 'Georgia, serif' }}>
      <div style={{ borderBottom: '1px solid var(--border)', padding: '0.6rem 0.875rem' }}>
        <p style={{ fontFamily: "'Playfair Display', Georgia, serif", fontWeight: 700, fontSize: '0.85rem', color: 'var(--ink)' }}>Analista IA</p>
        <p style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.7rem', color: 'var(--ink-light)', fontStyle: 'italic' }}>Gemini · consulta datos reales</p>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '0.875rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', minHeight: 0 }}>
        {historial.map((m, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: m.rol === 'usuario' ? 'flex-end' : 'flex-start' }}>
            <div style={{
              maxWidth: '88%',
              padding: '0.5rem 0.75rem',
              fontSize: '0.82rem',
              lineHeight: 1.55,
              whiteSpace: 'pre-wrap',
              background: m.rol === 'usuario' ? 'var(--ink)' : 'transparent',
              color: m.rol === 'usuario' ? 'var(--paper)' : 'var(--ink)',
              borderLeft: m.rol === 'asistente' ? '2px solid var(--border-dark)' : 'none',
              paddingLeft: m.rol === 'asistente' ? '0.75rem' : '0.75rem',
            }}>
              {m.texto}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ fontFamily: "'IM Fell English', Georgia, serif", fontStyle: 'italic', fontSize: '0.78rem', color: 'var(--ink-light)' }}>
            Consultando…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div style={{ borderTop: '1px solid var(--border)', padding: '0.6rem', display: 'flex', gap: '0.5rem' }}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && enviar()}
          placeholder="¿Qué pasó hoy en Bolivia?"
          style={{
            flex: 1,
            background: 'transparent',
            border: '1px solid var(--border)',
            padding: '0.4rem 0.6rem',
            fontSize: '0.8rem',
            fontFamily: 'Georgia, serif',
            color: 'var(--ink)',
            outline: 'none',
          }}
        />
        <button
          onClick={enviar}
          disabled={loading || !input.trim()}
          style={{
            background: 'var(--ink)',
            color: 'var(--paper)',
            border: 'none',
            padding: '0.4rem 0.75rem',
            fontSize: '0.78rem',
            fontFamily: "'IM Fell English', Georgia, serif",
            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
            opacity: loading || !input.trim() ? 0.5 : 1,
          }}
        >
          Enviar
        </button>
      </div>
    </div>
  )
}
