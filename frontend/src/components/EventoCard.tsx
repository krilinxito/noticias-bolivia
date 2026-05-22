import { useState } from 'react'
import type { Evento } from '../types'
import { detectarCategoria, CAT_COLOR } from '../lib/categorias'

interface Props { evento: Evento }

function tiempoRelativo(fecha: string) {
  const diff = Date.now() - new Date(fecha).getTime()
  const h = Math.floor(diff / 3_600_000)
  if (h < 1) return 'hace menos de 1h'
  if (h < 24) return `hace ${h}h`
  return `hace ${Math.floor(h / 24)}d`
}

export default function EventoCard({ evento }: Props) {
  const [imgError, setImgError] = useState(false)
  const medios = Object.keys(evento.articulos_por_medio)
  const pct = Math.round(evento.score_importancia * 100)
  const categoria = detectarCategoria(evento.temas ?? [])
  const catColor = CAT_COLOR[categoria] ?? '#5a4a32'
  const imagen = evento.imagen_url

  return (
    <a href={`/eventos/${evento.id}`} style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}>
      <div style={{ border: '1px solid var(--border)', overflow: 'hidden' }}>
        {imagen && !imgError ? (
          <img
            src={imagen}
            alt=""
            style={{ width: '100%', height: '140px', objectFit: 'cover', display: 'block' }}
            loading="lazy"
            onError={() => setImgError(true)}
          />
        ) : (
          <div style={{ height: '6px', background: catColor, opacity: 0.7 }} />
        )}
        <div style={{ padding: '0.75rem 0.875rem' }}>
          <span style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: catColor, display: 'block', marginBottom: '0.25rem' }}>
            {categoria}
          </span>
          <p style={{ fontFamily: "'Playfair Display', Georgia, serif", fontWeight: 600, fontSize: '0.92rem', lineHeight: 1.35, marginBottom: '0.4rem' }}>
            {evento.titulo}
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
            <div style={{ flex: 1, maxWidth: '80px', height: '3px', background: 'var(--border)' }}>
              <div style={{ height: '100%', background: catColor, width: `${pct}%`, opacity: 0.7 }} />
            </div>
            <span style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.65rem', color: 'var(--ink-light)' }}>
              {pct}%
            </span>
          </div>
          <p style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.7rem', color: 'var(--ink-light)' }}>
            {medios.join(' · ')} · {tiempoRelativo(evento.fecha_deteccion)}
          </p>
        </div>
      </div>
    </a>
  )
}
