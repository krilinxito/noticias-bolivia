import { useState } from 'react'
import type { Evento } from '../types'
import { detectarCategoria, CAT_COLOR } from '../lib/categorias'
import EventoCard from './EventoCard'

interface EventoEnriquecido extends Evento {
  categoria: string
}

interface Props {
  eventos: EventoEnriquecido[]
}

function tiempoRelativo(fecha: string) {
  const diff = Date.now() - new Date(fecha).getTime()
  const h = Math.floor(diff / 3_600_000)
  if (h < 1) return 'hace menos de 1h'
  if (h < 24) return `hace ${h}h`
  return `hace ${Math.floor(h / 24)}d`
}

export default function PortadaContenido({ eventos }: Props) {
  const [categoriaActiva, setCategoriaActiva] = useState<string | null>(null)
  const [imgDestacadoError, setImgDestacadoError] = useState(false)

  const categorias = [...new Set(eventos.map(e => e.categoria))].sort((a, b) => {
    const na = eventos.filter(e => e.categoria === a).length
    const nb = eventos.filter(e => e.categoria === b).length
    return nb - na
  })

  const eventosFiltrados = categoriaActiva
    ? eventos.filter(e => e.categoria === categoriaActiva)
    : eventos

  const destacado = eventosFiltrados[0]
  const resto = eventosFiltrados.slice(1)

  return (
    <div style={{ maxWidth: '60rem', margin: '0 auto', padding: '1.5rem 2rem' }}>

      {/* Filtro de categorías */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '1.5rem', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border)' }}>
        <button
          onClick={() => setCategoriaActiva(null)}
          style={{
            fontFamily: "'IM Fell English', Georgia, serif",
            fontSize: '0.72rem',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            padding: '0.25rem 0.75rem',
            border: '1px solid var(--border-dark)',
            cursor: 'pointer',
            background: !categoriaActiva ? 'var(--ink)' : 'transparent',
            color: !categoriaActiva ? 'var(--paper)' : 'var(--ink)',
          }}
        >
          Todas
        </button>
        {categorias.map(cat => {
          const color = CAT_COLOR[cat] ?? '#5a4a32'
          const activa = categoriaActiva === cat
          return (
            <button
              key={cat}
              onClick={() => setCategoriaActiva(activa ? null : cat)}
              style={{
                fontFamily: "'IM Fell English', Georgia, serif",
                fontSize: '0.72rem',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                padding: '0.25rem 0.75rem',
                border: `1px solid ${color}`,
                cursor: 'pointer',
                background: activa ? color : 'transparent',
                color: activa ? 'var(--paper)' : color,
              }}
            >
              {cat}
            </button>
          )
        })}
      </div>

      {eventosFiltrados.length === 0 && (
        <p style={{ fontFamily: "'IM Fell English', Georgia, serif", fontStyle: 'italic', color: 'var(--ink-light)' }}>
          Sin eventos disponibles.
        </p>
      )}

      {/* Evento destacado */}
      {destacado && (
        <a href={`/eventos/${destacado.id}`} style={{ textDecoration: 'none', color: 'inherit', display: 'block', marginBottom: '1.5rem' }}>
          <div style={{ border: '1px solid var(--border)', borderTop: `4px solid ${CAT_COLOR[destacado.categoria] ?? '#5a4a32'}`, display: 'grid', gridTemplateColumns: destacado.imagen_url && !imgDestacadoError ? '38% 1fr' : '1fr', overflow: 'hidden' }}>
            {destacado.imagen_url && !imgDestacadoError && (
              <img
                src={destacado.imagen_url}
                alt=""
                style={{ width: '100%', height: '220px', objectFit: 'cover', display: 'block' }}
                loading="eager"
                onError={() => setImgDestacadoError(true)}
              />
            )}
            <div style={{ padding: '1.25rem 1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <span style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: CAT_COLOR[destacado.categoria] ?? '#5a4a32', marginBottom: '0.4rem', display: 'block' }}>
                {destacado.categoria} · Evento principal
              </span>
              <h2 style={{ fontFamily: "'Playfair Display', Georgia, serif", fontSize: '1.5rem', fontWeight: 700, lineHeight: 1.2, marginBottom: '0.6rem' }}>
                {destacado.titulo}
              </h2>
              <p style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.78rem', color: 'var(--ink-light)' }}>
                {destacado.medios.join(' · ')} · {Math.round(destacado.score_importancia * 100)}% importancia · {tiempoRelativo(destacado.fecha_deteccion)}
              </p>
            </div>
          </div>
        </a>
      )}

      {/* Grid de eventos */}
      {resto.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(16rem, 1fr))', gap: '1rem' }}>
          {resto.map(t => (
            <EventoCard key={t.id} evento={t} />
          ))}
        </div>
      )}

    </div>
  )
}
