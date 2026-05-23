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
  sesgo_promedio: number | null
}

interface Props {
  eventos: EventoSerie[]
  categorias: string[]
  minFecha: string
  maxFecha: string
}

const ML = 80
const MR = 20
const MT = 16
const SH = 64
const XH = 36
const W = 900

function formatTick(d: Date) {
  return d.toLocaleDateString('es-BO', { day: 'numeric', month: 'short' })
}

function lerpHex(a: string, b: string, t: number): string {
  const parse = (h: string) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]
  const [ar, ag, ab] = parse(a)
  const [br, bg, bb] = parse(b)
  return `rgb(${Math.round(ar + (br - ar) * t)},${Math.round(ag + (bg - ag) * t)},${Math.round(ab + (bb - ab) * t)})`
}

function colorSesgo(s: number | null, fallback: string): string {
  if (s === null || s === undefined) return fallback
  const t = (s + 1) / 2
  return t < 0.5 ? lerpHex('#8b1a1a', '#8a7a62', t * 2) : lerpHex('#8a7a62', '#1a4a1a', (t - 0.5) * 2)
}

function beeswarm(items: { cx: number; r: number }[], yCenter: number, maxOffset: number): number[] {
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
    if (!placed) cy[i] = yCenter
  }
  return cy
}

export default function CronologiaChart({ eventos, categorias, minFecha, maxFecha }: Props) {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; ev: EventoSerie } | null>(null)

  const t0 = new Date(minFecha).getTime()
  const t1 = new Date(maxFecha).getTime()
  const chartW = W - ML - MR
  const H = MT + categorias.length * SH + XH

  function xOf(isoDate: string) {
    const t = new Date(isoDate).getTime()
    return ML + ((t - t0) / (t1 - t0)) * chartW
  }

  const days: string[] = []
  const cur = new Date(minFecha)
  const end = new Date(maxFecha)
  while (cur <= end) {
    days.push(cur.toISOString().slice(0, 10))
    cur.setDate(cur.getDate() + 1)
  }
  const maxTicks = Math.max(2, Math.floor(chartW / 65))
  const tickStep = Math.max(1, Math.ceil(days.length / maxTicks))
  const ticks = days.filter((_, i) => i % tickStep === 0)

  const swimlaneTop = (catIdx: number) => MT + catIdx * SH + SH / 2

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: '100%', height: 'auto', fontFamily: "'IM Fell English', Georgia, serif", overflow: 'visible' }}
      >
        {categorias.map((cat, ci) => {
          const y = swimlaneTop(ci)
          const color = CAT_COLOR[cat] ?? 'var(--ink-light)'
          return (
            <g key={cat}>
              <line x1={ML} y1={y} x2={W - MR} y2={y} stroke={color} strokeWidth={0.5} opacity={0.3} />
              <text x={ML - 8} y={y + 4} fontSize="9" fill={color} textAnchor="end" letterSpacing="1" style={{ textTransform: 'uppercase' }}>
                {cat}
              </text>
              {(() => {
                const evsCat = eventos.filter(e => e.categoria === cat)
                const items = evsCat.map(ev => ({ cx: xOf(ev.fecha_deteccion), r: 4 + ev.score_importancia * 8 }))
                const cyArr = beeswarm(items, y, SH / 2 - 4)
                return evsCat.map((ev, idx) => {
                  const cx = items[idx].cx
                  const r = items[idx].r
                  const cy = cyArr[idx]
                  const dotColor = colorSesgo(ev.sesgo_promedio, color)
                  return (
                    <circle
                      key={ev.id}
                      cx={cx} cy={cy} r={r}
                      fill={dotColor}
                      opacity={0.82}
                      stroke="var(--paper)"
                      strokeWidth={1}
                      style={{ cursor: 'pointer' }}
                      onMouseEnter={e => {
                        const svg = (e.target as SVGElement).closest('svg')!.getBoundingClientRect()
                        const rect = (e.target as SVGElement).getBoundingClientRect()
                        setTooltip({ x: rect.left - svg.left + rect.width / 2, y: rect.top - svg.top - 8, ev })
                      }}
                      onMouseLeave={() => setTooltip(null)}
                      onClick={() => { window.location.href = `/episodios/${ev.id}` }}
                    />
                  )
                })
              })()}
            </g>
          )
        })}

        <line x1={ML} y1={MT + categorias.length * SH} x2={W - MR} y2={MT + categorias.length * SH} stroke="var(--border-dark)" strokeWidth={0.75} />
        {ticks.map(day => {
          const x = xOf(day + 'T12:00:00')
          const axisY = MT + categorias.length * SH
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

      {/* Leyenda */}
      <div style={{ marginTop: '1rem', display: 'flex', gap: '2.5rem', flexWrap: 'wrap', fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.7rem', color: 'var(--ink-light)', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          <span style={{ fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Sesgo editorial</span>
          <div style={{ width: '120px', height: '8px', background: 'linear-gradient(to right, #8b1a1a, #8a7a62, #1a4a1a)', borderRadius: '1px' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', width: '120px', fontSize: '0.6rem' }}>
            <span>Neg.</span><span>Neutral</span><span>Pos.</span>
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          <span style={{ fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Importancia</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {[4, 8, 12].map((r, i) => (
              <svg key={i} width={r * 2 + 4} height={r * 2 + 4} viewBox={`0 0 ${r * 2 + 4} ${r * 2 + 4}`} style={{ display: 'block' }}>
                <circle cx={r + 2} cy={r + 2} r={r} fill="var(--ink-light)" opacity={0.45} />
              </svg>
            ))}
          </div>
          <div style={{ display: 'flex', gap: '0.4rem', fontSize: '0.6rem' }}>
            <span>Baja</span><span style={{ marginLeft: '0.35rem' }}>Media</span><span style={{ marginLeft: '0.3rem' }}>Alta</span>
          </div>
        </div>
        <span style={{ alignSelf: 'flex-end', paddingBottom: '0.15rem' }}>· Click en punto → detalle del evento</span>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div style={{
          position: 'absolute', left: tooltip.x, top: tooltip.y,
          transform: 'translate(-50%, -100%)',
          background: 'var(--ink)', color: 'var(--paper)',
          padding: '0.45rem 0.65rem', fontSize: '0.72rem',
          fontFamily: "'IM Fell English', Georgia, serif",
          lineHeight: 1.45, pointerEvents: 'none', maxWidth: '220px', zIndex: 50,
        }}>
          <div style={{ fontWeight: 700, marginBottom: '0.2rem', fontFamily: "'Playfair Display', Georgia, serif", fontSize: '0.78rem' }}>
            {tooltip.ev.titulo}
          </div>
          <div style={{ opacity: 0.75, fontSize: '0.65rem' }}>{tooltip.ev.mediosNombres.join(' · ')}</div>
          <div style={{ opacity: 0.75, fontSize: '0.65rem', marginTop: '0.15rem' }}>
            {Math.round(tooltip.ev.score_importancia * 100)}% importancia
          </div>
          <div style={{ opacity: 0.75, fontSize: '0.65rem', marginTop: '0.1rem' }}>
            {tooltip.ev.sesgo_promedio !== null
              ? `Sesgo: ${tooltip.ev.sesgo_promedio >= 0 ? '+' : ''}${tooltip.ev.sesgo_promedio.toFixed(2)}`
              : 'Sesgo: sin datos'}
          </div>
        </div>
      )}
    </div>
  )
}
