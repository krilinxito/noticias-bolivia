import { useState } from 'react'
import { CAT_COLOR } from '../lib/categorias'

interface EventoSerie {
  id: number
  titulo: string
  fecha_deteccion: string
  score_importancia: number
  categoria: string
  mediosCount: number
  mediosNombres: string[]
}

interface Props {
  eventos: EventoSerie[]
  densidad: Record<string, number>  // YYYY-MM-DD → count
  categorias: string[]
  minFecha: string  // ISO
  maxFecha: string  // ISO
}

const ML = 80   // margin left
const MR = 20   // margin right
const MT = 16   // margin top
const DH = 70   // density chart height
const GAP = 12  // gap between density and swimlanes
const SH = 64   // swimlane height per category
const XH = 36   // x-axis height
const W = 900   // total viewBox width

function formatTick(d: Date) {
  return d.toLocaleDateString('es-BO', { day: 'numeric', month: 'short' })
}

// Beeswarm: coloca cada punto evitando colisiones, desplazando verticalmente
function beeswarm(
  items: { cx: number; r: number }[],
  yCenter: number,
  maxOffset: number
): number[] {
  const sorted = items.map((it, i) => ({ ...it, i })).sort((a, b) => a.cx - b.cx)
  const cy: number[] = new Array(items.length).fill(yCenter)

  for (let k = 0; k < sorted.length; k++) {
    const { cx, r, i } = sorted[k]
    let placed = false
    for (let step = 0; step <= maxOffset; step += 2) {
      const candidates = step === 0 ? [yCenter] : [yCenter - step, yCenter + step]
      for (const tryY of candidates) {
        const ok = sorted.slice(0, k).every(prev => {
          const dx = cx - prev.cx
          const dy = tryY - cy[prev.i]
          return Math.sqrt(dx * dx + dy * dy) >= r + prev.r + 1.5
        })
        if (ok) { cy[i] = tryY; placed = true; break }
      }
      if (placed) break
    }
    if (!placed) cy[i] = yCenter  // fallback: centro
  }
  return cy
}

export default function SerieTemporalChart({ eventos, densidad, categorias, minFecha, maxFecha }: Props) {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; ev: EventoSerie } | null>(null)

  const t0 = new Date(minFecha).getTime()
  const t1 = new Date(maxFecha).getTime()
  const chartW = W - ML - MR


  const H = MT + DH + GAP + categorias.length * SH + XH

  function xOf(isoDate: string) {
    const t = new Date(isoDate).getTime()
    return ML + ((t - t0) / (t1 - t0)) * chartW
  }

  // Density bars
  const days: string[] = []
  const cur = new Date(minFecha)
  const end = new Date(maxFecha)
  while (cur <= end) {
    days.push(cur.toISOString().slice(0, 10))
    cur.setDate(cur.getDate() + 1)
  }
  const maxDens = Math.max(...days.map(d => densidad[d] ?? 0), 1)
  const dayPx = days.length > 1 ? chartW / (days.length - 1) : chartW
  const barW = Math.max(dayPx * 0.6, 2)

  // Ticks: cuántos caben sin solaparse (~65px por etiqueta en viewBox de 900)
  const maxTicks = Math.max(2, Math.floor(chartW / 65))
  const tickStep = Math.max(1, Math.ceil(days.length / maxTicks))
  const ticks = days.filter((_, i) => i % tickStep === 0)

  const swimlaneTop = (catIdx: number) => MT + DH + GAP + catIdx * SH + SH / 2

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: '100%', height: 'auto', fontFamily: "'IM Fell English', Georgia, serif", overflow: 'visible' }}
      >
        {/* ── Density chart ── */}
        <text x={ML} y={MT - 4} fontSize="9" fill="var(--ink-light)" textAnchor="start" letterSpacing="1.5">
          ARTÍCULOS / DÍA
        </text>
        {days.map((day, i) => {
          const count = densidad[day] ?? 0
          const bh = (count / maxDens) * DH
          const bx = xOf(day + 'T12:00:00') - barW / 2
          return (
            <rect
              key={day}
              x={bx}
              y={MT + DH - bh}
              width={barW}
              height={bh}
              fill="var(--border-dark)"
              opacity={0.55}
            />
          )
        })}

        {/* ── Swimlane baseline ── */}
        <line x1={ML} y1={MT + DH + GAP / 2} x2={W - MR} y2={MT + DH + GAP / 2} stroke="var(--border)" strokeWidth={0.5} />

        {/* ── Swimlanes ── */}
        {categorias.map((cat, ci) => {
          const y = swimlaneTop(ci)
          const color = CAT_COLOR[cat] ?? 'var(--ink-light)'
          return (
            <g key={cat}>
              {/* Horizontal line */}
              <line x1={ML} y1={y} x2={W - MR} y2={y} stroke={color} strokeWidth={0.5} opacity={0.3} />
              {/* Category label */}
              <text
                x={ML - 8}
                y={y + 4}
                fontSize="9"
                fill={color}
                textAnchor="end"
                letterSpacing="1"
                style={{ textTransform: 'uppercase' }}
              >
                {cat}
              </text>
              {/* Event dots con beeswarm para evitar solapamiento */}
              {(() => {
                const evsCat = eventos.filter(e => e.categoria === cat)
                const items = evsCat.map(ev => ({
                  cx: xOf(ev.fecha_deteccion),
                  r: 4 + ev.score_importancia * 8,
                }))
                const cyArr = beeswarm(items, y, SH / 2 - 4)
                return evsCat.map((ev, idx) => {
                  const cx = items[idx].cx
                  const r = items[idx].r
                  const cy = cyArr[idx]
                  return (
                    <circle
                      key={ev.id}
                      cx={cx}
                      cy={cy}
                      r={r}
                      fill={color}
                      opacity={0.75}
                      stroke="var(--paper)"
                      strokeWidth={1}
                      style={{ cursor: 'pointer' }}
                      onMouseEnter={e => {
                        const svg = (e.target as SVGElement).closest('svg')!.getBoundingClientRect()
                        const rect = (e.target as SVGElement).getBoundingClientRect()
                        setTooltip({
                          x: rect.left - svg.left + rect.width / 2,
                          y: rect.top - svg.top - 8,
                          ev,
                        })
                      }}
                      onMouseLeave={() => setTooltip(null)}
                      onClick={() => { window.location.href = `/eventos/${ev.id}` }}
                    />
                  )
                })
              })()}
            </g>
          )
        })}

        {/* ── X-axis ── */}
        <line x1={ML} y1={MT + DH + GAP + categorias.length * SH} x2={W - MR} y2={MT + DH + GAP + categorias.length * SH} stroke="var(--border-dark)" strokeWidth={0.75} />
        {ticks.map(day => {
          const x = xOf(day + 'T12:00:00')
          const axisY = MT + DH + GAP + categorias.length * SH
          return (
            <g key={day}>
              <line x1={x} y1={axisY} x2={x} y2={axisY + 4} stroke="var(--border-dark)" strokeWidth={0.75} />
              <text x={x} y={axisY + 14} fontSize="9" fill="var(--ink-light)" textAnchor="middle">
                {formatTick(new Date(day + 'T12:00:00'))}
              </text>
            </g>
          )
        })}
      </svg>

      {/* ── Tooltip ── */}
      {tooltip && (
        <div style={{
          position: 'absolute',
          left: tooltip.x,
          top: tooltip.y,
          transform: 'translate(-50%, -100%)',
          background: 'var(--ink)',
          color: 'var(--paper)',
          padding: '0.45rem 0.65rem',
          fontSize: '0.72rem',
          fontFamily: "'IM Fell English', Georgia, serif",
          lineHeight: 1.45,
          pointerEvents: 'none',
          maxWidth: '220px',
          zIndex: 50,
        }}>
          <div style={{ fontWeight: 700, marginBottom: '0.2rem', fontFamily: "'Playfair Display', Georgia, serif", fontSize: '0.78rem' }}>
            {tooltip.ev.titulo}
          </div>
          <div style={{ opacity: 0.75, fontSize: '0.65rem' }}>
            {tooltip.ev.mediosNombres.join(' · ')}
          </div>
          <div style={{ opacity: 0.75, fontSize: '0.65rem', marginTop: '0.15rem' }}>
            {Math.round(tooltip.ev.score_importancia * 100)}% importancia
          </div>
        </div>
      )}
    </div>
  )
}
