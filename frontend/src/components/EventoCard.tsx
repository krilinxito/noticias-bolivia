import type { Tema } from '../types'
import { detectarCategoria, CAT_COLOR } from '../lib/categorias'

interface Props { tema: Tema }

function tiempoRelativo(fecha: string) {
  const diff = Date.now() - new Date(fecha).getTime()
  const h = Math.floor(diff / 3_600_000)
  if (h < 1) return 'hace menos de 1h'
  if (h < 24) return `hace ${h}h`
  return `hace ${Math.floor(h / 24)}d`
}

export default function EventoCard({ tema }: Props) {
  const pct = Math.round(tema.score_importancia * 100)
  const categoria = detectarCategoria(tema.keywords ?? [])
  const catColor = CAT_COLOR[categoria] ?? '#5a4a32'

  return (
    <a href={`/temas/${tema.id}`} style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}>
      <div style={{ border: '1px solid var(--border)', overflow: 'hidden' }}>
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
            {tema.titulo.length > 90 ? tema.titulo.slice(0, 87) + '…' : tema.titulo}
          </p>
        </div>
        <div style={{ padding: '0.75rem 0.875rem' }}>
          <span style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: catColor, display: 'block', marginBottom: '0.25rem' }}>
            {categoria}
          </span>
          <p style={{ fontFamily: "'Playfair Display', Georgia, serif", fontWeight: 600, fontSize: '0.92rem', lineHeight: 1.35, marginBottom: '0.4rem' }}>
            {tema.titulo}
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
            {tema.medios.join(' · ')} · {tiempoRelativo(tema.fecha_deteccion)}
          </p>
        </div>
      </div>
    </a>
  )
}
