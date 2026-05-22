import { useState, useRef, useEffect } from 'react'
import type { ChatMessage, CardChat } from '../types'
import { chat } from '../lib/api'

interface MsgAsistente extends ChatMessage {
  rol: 'asistente'
  cards?: CardChat[]
}
type Msg = { rol: 'usuario'; texto: string } | MsgAsistente

const TONO_COLOR: Record<string, string> = {
  positivo: '#1a4a1a',
  negativo: '#8b1a1a',
  neutral: '#8a7a62',
}

function MiniEventoCard({ card }: { card: Extract<CardChat, { tipo: 'evento' }> }) {
  const [imgError, setImgError] = useState(false)
  const color = '#5a4a32'
  return (
    <a href={`/eventos/${card.id}`} style={{ display: 'block', textDecoration: 'none', color: 'inherit', border: '1px solid var(--border)', marginTop: '0.5rem', overflow: 'hidden' }}>
      {card.imagen_url && !imgError && (
        <img src={card.imagen_url} alt="" style={{ width: '100%', height: '80px', objectFit: 'cover', display: 'block' }} loading="lazy" onError={() => setImgError(true)} />
      )}
      <div style={{ padding: '0.5rem 0.6rem', borderLeft: `3px solid ${color}` }}>
        <p style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.08em', color, marginBottom: '0.2rem' }}>
          Evento · {card.medios.length} medios
        </p>
        <p style={{ fontFamily: 'Georgia, serif', fontSize: '0.8rem', lineHeight: 1.3, marginBottom: '0.2rem' }}>
          {card.titulo}
        </p>
        <p style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.62rem', color: 'var(--ink-light)' }}>
          {card.medios.slice(0, 3).join(' · ')}{card.medios.length > 3 ? ` +${card.medios.length - 3}` : ''}
        </p>
      </div>
    </a>
  )
}

function MiniArticuloCard({ card }: { card: Extract<CardChat, { tipo: 'articulo' }> }) {
  const tonoColor = card.tono ? (TONO_COLOR[card.tono] ?? 'var(--ink-light)') : 'var(--ink-light)'
  return (
    <a href={card.url} target="_blank" rel="noreferrer" style={{ display: 'block', textDecoration: 'none', color: 'inherit', border: '1px solid var(--border)', borderLeft: `3px solid ${tonoColor}`, padding: '0.5rem 0.6rem', marginTop: '0.5rem' }}>
      <p style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: tonoColor, marginBottom: '0.2rem' }}>
        {card.medio}{card.tono ? ` · ${card.tono}` : ''}
      </p>
      <p style={{ fontFamily: 'Georgia, serif', fontSize: '0.8rem', lineHeight: 1.3 }}>
        {card.titulo}
      </p>
    </a>
  )
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [msgs, setMsgs] = useState<Msg[]>([
    { rol: 'asistente', texto: 'Bienvenido. Soy el analista de El Observador Digital. Puede preguntarme sobre cobertura noticiosa, sesgo editorial o comparar cómo los medios bolivianos abordan un tema.' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs, loading, open])

  const enviar = async () => {
    const msg = input.trim()
    if (!msg || loading) return
    const historial: ChatMessage[] = msgs.map(m => ({ rol: m.rol, texto: m.texto }))
    setMsgs(h => [...h, { rol: 'usuario', texto: msg }])
    setInput('')
    setLoading(true)
    try {
      const res = await chat(msg, historial)
      setMsgs(h => [...h, { rol: 'asistente', texto: res.respuesta, cards: res.cards ?? [] }])
    } catch {
      setMsgs(h => [...h, { rol: 'asistente', texto: 'Error al conectar con la API.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* Panel flotante */}
      {open && (
        <div style={{
          position: 'fixed', bottom: '3.75rem', right: '1.5rem',
          width: '22rem', height: '30rem',
          border: '1px solid var(--border-dark)',
          background: 'var(--paper)',
          display: 'flex', flexDirection: 'column',
          zIndex: 99,
          boxShadow: '0 4px 24px rgba(0,0,0,0.12)',
          fontFamily: 'Georgia, serif',
        }}>
          <div style={{ borderBottom: '1px solid var(--border)', padding: '0.6rem 0.875rem' }}>
            <p style={{ fontFamily: "'Playfair Display', Georgia, serif", fontWeight: 700, fontSize: '0.85rem' }}>Analista IA</p>
            <p style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.68rem', color: 'var(--ink-light)', fontStyle: 'italic' }}>Gemini · consulta datos reales</p>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '0.875rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', minHeight: 0 }}>
            {msgs.map((m, i) => (
              <div key={i}>
                <div style={{ display: 'flex', justifyContent: m.rol === 'usuario' ? 'flex-end' : 'flex-start' }}>
                  <div style={{
                    maxWidth: '90%',
                    padding: '0.5rem 0.75rem',
                    fontSize: '0.82rem',
                    lineHeight: 1.55,
                    whiteSpace: 'pre-wrap',
                    background: m.rol === 'usuario' ? 'var(--ink)' : 'transparent',
                    color: m.rol === 'usuario' ? 'var(--paper)' : 'var(--ink)',
                    borderLeft: m.rol === 'asistente' ? '2px solid var(--border-dark)' : 'none',
                  }}>
                    {m.texto}
                  </div>
                </div>
                {m.rol === 'asistente' && (m as MsgAsistente).cards && (m as MsgAsistente).cards!.length > 0 && (
                  <div style={{ marginTop: '0.25rem' }}>
                    {(m as MsgAsistente).cards!.map((card, ci) =>
                      card.tipo === 'evento'
                        ? <MiniEventoCard key={ci} card={card} />
                        : <MiniArticuloCard key={ci} card={card} />
                    )}
                  </div>
                )}
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
                flex: 1, background: 'transparent',
                border: '1px solid var(--border)',
                padding: '0.4rem 0.6rem',
                fontSize: '0.8rem', fontFamily: 'Georgia, serif',
                color: 'var(--ink)', outline: 'none',
              }}
            />
            <button
              onClick={enviar}
              disabled={loading || !input.trim()}
              style={{
                background: 'var(--ink)', color: 'var(--paper)',
                border: 'none', padding: '0.4rem 0.75rem',
                fontSize: '0.78rem', fontFamily: "'IM Fell English', Georgia, serif",
                cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
                opacity: loading || !input.trim() ? 0.5 : 1,
              }}
            >
              Enviar
            </button>
          </div>
        </div>
      )}

      {/* Botón flotante */}
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          position: 'fixed', bottom: '1.5rem', right: '1.5rem',
          background: 'var(--ink)', color: 'var(--paper)',
          fontFamily: "'IM Fell English', Georgia, serif",
          fontSize: '0.78rem', letterSpacing: '0.06em',
          border: '1px solid var(--border-dark)',
          padding: '0.5rem 1.1rem',
          cursor: 'pointer', zIndex: 100,
        }}
      >
        {open ? '× Cerrar' : '✦ Analista IA'}
      </button>
    </>
  )
}
