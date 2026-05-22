import { useState, useRef, useEffect, useCallback } from 'react'
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

const MEDIOS = ['Red Uno', 'El Deber', 'Brújula Digital', 'Los Tiempos', 'Erbol', 'La Razón']

const PREGUNTAS_INICIALES = [
  '¿Qué eventos importantes hay esta semana?',
  '¿Qué medio tiene más sesgo editorial?',
  '¿Cómo cubren los medios la política boliviana?',
  '¿Cuál es la noticia más cubierta?',
]

const SEGUIMIENTOS = [
  'Dame más detalles',
  '¿Qué otros medios lo cubrieron?',
  '¿Cuál es el sesgo de este evento?',
  '¿Y qué dice la oposición?',
  '¿Hay más eventos relacionados?',
  '¿Cómo comparan los medios este tema?',
]

function renderTexto(texto: string) {
  const partes: JSX.Element[] = []
  const lineas = texto.split('\n')
  let listItems: JSX.Element[] = []
  let listKey = 0

  const flushList = () => {
    if (listItems.length > 0) {
      partes.push(<ul key={`ul-${listKey++}`} style={{ paddingLeft: '1.1rem', margin: '0.25rem 0' }}>{listItems}</ul>)
      listItems = []
    }
  }

  const renderNegrita = (texto: string, key: number) => {
    const partes: (string | JSX.Element)[] = []
    const regex = /\*\*([^*]+)\*\*/g
    let last = 0, m: RegExpExecArray | null, i = 0
    while ((m = regex.exec(texto)) !== null) {
      if (m.index > last) partes.push(texto.slice(last, m.index))
      partes.push(<strong key={i++}>{m[1]}</strong>)
      last = m.index + m[0].length
    }
    if (last < texto.length) partes.push(texto.slice(last))
    return <span key={key}>{partes}</span>
  }

  lineas.forEach((linea, i) => {
    const esItem = linea.match(/^[-•*]\s+(.+)/)
    if (esItem) {
      listItems.push(<li key={i} style={{ fontSize: '0.82rem', lineHeight: 1.5 }}>{renderNegrita(esItem[1], i)}</li>)
    } else {
      flushList()
      if (linea.trim()) {
        partes.push(<p key={i} style={{ margin: '0.2rem 0', fontSize: '0.82rem', lineHeight: 1.55 }}>{renderNegrita(linea, i)}</p>)
      }
    }
  })
  flushList()
  return partes
}

function MiniEventoCard({ card }: { card: Extract<CardChat, { tipo: 'evento' }> }) {
  const color = '#5a4a32'
  return (
    <a href={`/eventos/${card.id}`} style={{ display: 'block', textDecoration: 'none', color: 'inherit', border: '1px solid var(--border)', borderTop: `3px solid ${color}`, marginTop: '0.5rem', overflow: 'hidden' }}>
      <div style={{ padding: '0.5rem 0.6rem' }}>
        <p style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.08em', color, marginBottom: '0.2rem' }}>
          Evento · {card.medios.length} medios
        </p>
        <p style={{ fontFamily: "'Playfair Display', Georgia, serif", fontWeight: 600, fontSize: '0.8rem', lineHeight: 1.3, marginBottom: '0.2rem' }}>
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
  const [medioCtx, setMedioCtx] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs, loading, open])

  const enviarTexto = useCallback(async (texto: string) => {
    const msg = texto.trim()
    if (!msg || loading) return
    const historial: ChatMessage[] = msgs.map(m => ({ rol: m.rol, texto: m.texto }))
    const msgFinal = medioCtx ? `(Habla específicamente sobre ${medioCtx}): ${msg}` : msg
    setMsgs(h => [...h, { rol: 'usuario', texto: msg }])
    setInput('')
    setLoading(true)
    try {
      const res = await chat(msgFinal, historial)
      setMsgs(h => [...h, { rol: 'asistente', texto: res.respuesta, cards: res.cards ?? [] }])
    } catch {
      setMsgs(h => [...h, { rol: 'asistente', texto: 'Error al conectar con la API.' }])
    } finally {
      setLoading(false)
    }
  }, [msgs, loading, medioCtx])

  const enviar = () => enviarTexto(input)

  const seguimientosPara = (idx: number) => {
    const offset = idx % SEGUIMIENTOS.length
    return [SEGUIMIENTOS[offset], SEGUIMIENTOS[(offset + 1) % SEGUIMIENTOS.length]]
  }

  return (
    <>
      {open && (
        <div style={{
          position: 'fixed', bottom: '4.25rem', right: '1.5rem',
          width: 'min(92vw, 32rem)', height: 'min(88vh, 46rem)',
          border: '1px solid var(--border-dark)',
          background: 'var(--paper)',
          display: 'flex', flexDirection: 'column',
          zIndex: 99,
          boxShadow: '0 4px 32px rgba(0,0,0,0.15)',
          fontFamily: 'Georgia, serif',
        }}>

          {/* Header */}
          <div style={{ borderBottom: '1px solid var(--border)', padding: '0.6rem 0.875rem' }}>
            <p style={{ fontFamily: "'Playfair Display', Georgia, serif", fontWeight: 700, fontSize: '0.85rem' }}>Analista IA</p>
            <p style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.68rem', color: 'var(--ink-light)', fontStyle: 'italic' }}>Gemini · consulta datos reales</p>
          </div>

          {/* Mensajes */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '0.875rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', minHeight: 0 }}>
              {msgs.map((m, i) => (
                <div key={i}>
                  <div style={{ display: 'flex', justifyContent: m.rol === 'usuario' ? 'flex-end' : 'flex-start' }}>
                    <div style={{
                      maxWidth: '92%',
                      padding: '0.5rem 0.75rem',
                      lineHeight: 1.55,
                      whiteSpace: m.rol === 'usuario' ? 'pre-wrap' : undefined,
                      background: m.rol === 'usuario' ? 'var(--ink)' : 'transparent',
                      color: m.rol === 'usuario' ? 'var(--paper)' : 'var(--ink)',
                      borderLeft: m.rol === 'asistente' ? '2px solid var(--border-dark)' : 'none',
                    }}>
                      {m.rol === 'usuario' ? m.texto : renderTexto(m.texto)}
                    </div>
                  </div>

                  {/* Cards de eventos/artículos */}
                  {m.rol === 'asistente' && (m as MsgAsistente).cards && (m as MsgAsistente).cards!.length > 0 && (
                    <div style={{ marginTop: '0.25rem' }}>
                      {(m as MsgAsistente).cards!.map((card, ci) =>
                        card.tipo === 'evento'
                          ? <MiniEventoCard key={ci} card={card} />
                          : <MiniArticuloCard key={ci} card={card} />
                      )}
                    </div>
                  )}

                  {/* Chips de preguntas iniciales (solo en el primer mensaje) */}
                  {m.rol === 'asistente' && i === 0 && msgs.length === 1 && (
                    <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                      {PREGUNTAS_INICIALES.map(p => (
                        <button key={p} onClick={() => enviarTexto(p)} disabled={loading}
                          style={{ textAlign: 'left', background: 'transparent', border: '1px solid var(--border-dark)', padding: '0.35rem 0.6rem', cursor: 'pointer', fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.72rem', color: 'var(--ink)', lineHeight: 1.3 }}
                          onMouseEnter={e => { e.currentTarget.style.background = 'var(--ink)'; e.currentTarget.style.color = 'var(--paper)' }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--ink)' }}
                        >
                          {p}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Chips de seguimiento (después de cada respuesta del asistente, excepto la primera) */}
                  {m.rol === 'asistente' && i > 0 && i === msgs.length - 1 && !loading && (
                    <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                      {seguimientosPara(i).map(s => (
                        <button key={s} onClick={() => enviarTexto(s)} disabled={loading}
                          style={{ background: 'transparent', border: 'none', borderBottom: '1px dotted var(--border-dark)', padding: '0.15rem 0', cursor: 'pointer', fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.68rem', color: 'var(--ink-light)' }}
                          onMouseEnter={e => (e.currentTarget.style.color = 'var(--ink)')}
                          onMouseLeave={e => (e.currentTarget.style.color = 'var(--ink-light)')}
                        >
                          {s}
                        </button>
                      ))}
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

          {/* Selector de medio */}
          <div style={{ borderTop: '1px solid var(--border)', padding: '0.4rem 0.6rem', display: 'flex', gap: '0.35rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--ink-light)', marginRight: '0.1rem' }}>Medio:</span>
            {MEDIOS.map(m => {
              const activo = medioCtx === m
              return (
                <button key={m} onClick={() => setMedioCtx(activo ? null : m)}
                  style={{ background: activo ? 'var(--ink)' : 'transparent', color: activo ? 'var(--paper)' : 'var(--ink-light)', border: '1px solid var(--border)', padding: '0.15rem 0.45rem', cursor: 'pointer', fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.62rem', whiteSpace: 'nowrap' }}
                >
                  {m}{activo ? ' ×' : ''}
                </button>
              )
            })}
          </div>

          {/* Input */}
          <div style={{ borderTop: '1px solid var(--border)', padding: '0.6rem', display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && enviar()}
                placeholder={medioCtx ? `Pregunta sobre ${medioCtx}…` : '¿Qué pasó hoy en Bolivia?'}
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
