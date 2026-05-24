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
  const pct = Math.round(evento.score_importancia * 100)
  const categoria = detectarCategoria(evento.keywords ?? [])
  const catColor = CAT_COLOR[categoria] ?? '#5a4a32'
  const tieneImagen = !!evento.imagen_url && !imgError

  return (
    <a href={`/eventos/${evento.id}`} style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}>
      <div style={{ border: '1px solid var(--border)', overflow: 'hidden' }}>

        {tieneImagen ? (
          <div style={{ position: 'relative', borderTop: `4px solid ${catColor}` }}>
            <img
              src={evento.imagen_url!}
              alt=""
              style={{ width: '100%', height: '140px', objectFit: 'cover', display: 'block' }}
              loading="lazy"
              onError={() => setImgError(true)}
            />
            <span style={{
              position: 'absolute', bottom: '0.4rem', left: '0.5rem',
              fontFamily: "'IM Fell English', Georgia, serif",
              fontSize: '0.55rem', textTransform: 'uppercase', letterSpacing: '0.12em',
              color: 'white', background: catColor,
              padding: '0.15rem 0.45rem',
            }}>
              {categoria}
            </span>
          </div>
        ) : (
          <div style={{
            height: '130px',
            borderTop: `4px solid ${catColor}`,
            background: `color-mix(in srgb, ${catColor} 10%, var(--paper))`,
            display: 'flex', flexDirection: 'column', justifyContent: 'center',
            padding: '0.75rem 0.875rem',
            overflow: 'hidden',
          }}>
            <p style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.55rem', textTransform: 'uppercase', letterSpacing: '0.14em', color: catColor, marginBottom: '0.45rem' }}>
              {categoria}
            </p>
            <p style={{ fontFamily: "'Playfair Display', Georgia, serif", fontWeight: 700, fontSize: '1rem', lineHeight: 1.3, color: 'var(--ink)' }}>
              {evento.titulo.length > 90 ? evento.titulo.slice(0, 87) + '…' : evento.titulo}
            </p>
          </div>
        )}

        <div style={{ padding: '0.75rem 0.875rem' }}>
          {!tieneImagen && (
            <span style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: catColor, display: 'block', marginBottom: '0.25rem' }}>
              {categoria}
            </span>
          )}
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
            {(evento.medios ?? []).join(' · ')} · {tiempoRelativo(evento.fecha_deteccion)}
          </p>
        </div>

      </div>
    </a>
  )
}
