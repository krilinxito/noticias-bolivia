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
  const medios = Object.keys(evento.articulos_por_medio)
  const pct = Math.round(evento.score_importancia * 100)
  const categoria = detectarCategoria(evento.temas ?? [])
  const catColor = CAT_COLOR[categoria]

  return (
    <a href={`/eventos/${evento.id}`} style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}>
      <div style={{ borderLeft: `3px solid ${catColor}`, paddingLeft: '0.875rem' }}>

        {/* Etiqueta de categoría */}
        <span style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: catColor, display: 'block', marginBottom: '0.2rem' }}>
          {categoria}
        </span>

        <p style={{ fontFamily: "'Playfair Display', Georgia, serif", fontWeight: 600, fontSize: '0.95rem', lineHeight: 1.35, marginBottom: '0.4rem' }}>
          {evento.titulo}
        </p>

        {/* Barra de importancia */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
          <div style={{ flex: 1, maxWidth: '100px', height: '3px', background: 'var(--border)' }}>
            <div style={{ height: '100%', background: catColor, width: `${pct}%`, opacity: 0.7 }} />
          </div>
          <span style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.68rem', color: 'var(--ink-light)' }}>
            {pct}%
          </span>
        </div>

        <p style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.72rem', color: 'var(--ink-light)' }}>
          {medios.join(' · ')} · {tiempoRelativo(evento.fecha_deteccion)}
        </p>
      </div>
    </a>
  )
}
