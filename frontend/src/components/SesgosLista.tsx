import type { EventoSesgo } from '../lib/api'

interface Props { eventos: EventoSesgo[] }

function colorSesgo(s: number) {
  if (s <= -0.3) return '#8b1a1a'
  if (s >= 0.3) return '#1a4a1a'
  return '#5a4a32'
}

// Asigna arriba/abajo para evitar solapamiento de etiquetas
function asignarLados(medios: { sesgo: number }[]): boolean[] {
  const sorted = [...medios.entries()].sort((a, b) => a[1].sesgo - b[1].sesgo)
  const arriba = new Array(medios.length).fill(false)
  for (let i = 0; i < sorted.length; i++) {
    const [idx] = sorted[i]
    const pct = ((sorted[i][1].sesgo + 1) / 2) * 100
    const prevPct = i > 0 ? ((sorted[i - 1][1].sesgo + 1) / 2) * 100 : -999
    // Si está a menos de 12% del anterior, alternamos
    arriba[idx] = Math.abs(pct - prevPct) < 12 ? !arriba[sorted[i - 1][0]] : false
  }
  return arriba
}

export default function SesgosLista({ eventos }: Props) {
  if (eventos.length === 0) {
    return (
      <p style={{ fontFamily: "'IM Fell English', Georgia, serif", fontStyle: 'italic', color: 'var(--ink-light)' }}>
        Sin datos de sesgo aún. El análisis se ejecuta periódicamente.
      </p>
    )
  }

  return (
    <div>
      {eventos.map((ev, i) => {
        const menor = ev.medios[0]
        const mayor = ev.medios[ev.medios.length - 1]
        const lados = asignarLados(ev.medios)

        return (
          <div key={ev.id} style={{ borderBottom: '1px solid var(--border)', borderTop: i === 0 ? '1px solid var(--border)' : 'none', padding: '1.25rem 0' }}>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.6rem' }}>
              <a href={`/eventos/${ev.id}`} style={{ fontFamily: "'Playfair Display', Georgia, serif", fontWeight: 700, fontSize: '1rem', textDecoration: 'underline', color: 'var(--ink)', flex: 1, paddingRight: '1rem', lineHeight: 1.3 }}>
                {ev.titulo}
              </a>
              <span style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.75rem', color: 'var(--ink-light)', whiteSpace: 'nowrap' }}>
                Δ {ev.divergencia.toFixed(2)}
              </span>
            </div>

            {/* Dot-plot horizontal */}
            <div style={{ position: 'relative', height: '2px', background: 'var(--border)', margin: '2.5rem 0 3rem' }}>
              <div style={{ position: 'absolute', left: '50%', top: '-4px', width: '1px', height: '10px', background: 'var(--border-dark)' }} />
              <span style={{ position: 'absolute', left: 0, bottom: '-18px', fontSize: '0.6rem', fontFamily: 'Georgia,serif', color: 'var(--ink-light)' }}>negativo</span>
              <span style={{ position: 'absolute', right: 0, bottom: '-18px', fontSize: '0.6rem', fontFamily: 'Georgia,serif', color: 'var(--ink-light)' }}>positivo</span>

              {ev.medios.map((m, idx) => {
                const pct = ((m.sesgo + 1) / 2) * 100
                const color = colorSesgo(m.sesgo)
                const esArriba = lados[idx]
                return (
                  <div key={m.medio} style={{ position: 'absolute', left: `${pct}%`, top: '-7px', transform: 'translateX(-50%)', textAlign: 'center' }}>
                    <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: color, margin: '0 auto', border: '1.5px solid var(--paper)' }} />
                    {/* Línea vertical conectora */}
                    <div style={{
                      position: 'absolute', left: '50%', transform: 'translateX(-50%)',
                      width: '1px', background: color, opacity: 0.35,
                      ...(esArriba
                        ? { bottom: '10px', height: '18px' }
                        : { top: '10px', height: '14px' })
                    }} />
                    {/* Etiqueta */}
                    <div style={{
                      position: 'absolute', left: '50%', transform: 'translateX(-50%)',
                      whiteSpace: 'nowrap', fontSize: '0.62rem',
                      fontFamily: "'IM Fell English', Georgia, serif", color,
                      ...(esArriba ? { bottom: '26px' } : { top: '22px' })
                    }}>
                      {m.medio}
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Extremos */}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontFamily: "'IM Fell English', Georgia, serif", marginBottom: '0.5rem' }}>
              <span style={{ color: '#8b1a1a' }}>{menor.medio}: {menor.sesgo.toFixed(2)}</span>
              <span style={{ color: '#1a4a1a' }}>{mayor.medio}: +{mayor.sesgo.toFixed(2)}</span>
            </div>

            {ev.resumen_comparativo && (
              <p style={{ fontFamily: 'Georgia, serif', fontStyle: 'italic', fontSize: '0.8rem', color: 'var(--ink-light)', lineHeight: 1.55, borderLeft: '2px solid var(--border)', paddingLeft: '0.75rem' }}>
                {ev.resumen_comparativo}
              </p>
            )}
          </div>
        )
      })}
    </div>
  )
}
