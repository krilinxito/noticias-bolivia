interface MedioSesgo { medio: string; sesgo: number; tono?: string | null }
interface Props { medios: MedioSesgo[] }

function colorSesgo(s: number) {
  if (s <= -0.3) return '#8b1a1a'
  if (s >= 0.3) return '#1a4a1a'
  return '#5a4a32'
}

function asignarLados(medios: MedioSesgo[]): boolean[] {
  const sorted = [...medios.entries()].sort((a, b) => a[1].sesgo - b[1].sesgo)
  const arriba = new Array(medios.length).fill(false)
  for (let i = 0; i < sorted.length; i++) {
    const [idx] = sorted[i]
    const pct = ((sorted[i][1].sesgo + 1) / 2) * 100
    const prevPct = i > 0 ? ((sorted[i - 1][1].sesgo + 1) / 2) * 100 : -999
    arriba[idx] = Math.abs(pct - prevPct) < 12 ? !arriba[sorted[i - 1][0]] : false
  }
  return arriba
}

export default function SesgometroComparativo({ medios }: Props) {
  const conSesgo = medios.filter(m => m.sesgo !== null && m.sesgo !== undefined)
  if (conSesgo.length === 0) return null
  const lados = asignarLados(conSesgo)

  return (
    <div style={{ margin: '1.5rem 0' }}>
      {/* Barra base */}
      <div style={{ position: 'relative', height: '2px', background: 'var(--border)', margin: '2.5rem 0 3rem' }}>
        <div style={{ position: 'absolute', left: '50%', top: '-4px', width: '1px', height: '10px', background: 'var(--border-dark)' }} />
        <span style={{ position: 'absolute', left: '0', bottom: '-18px', fontSize: '0.65rem', fontFamily: 'Georgia,serif', color: 'var(--ink-light)' }}>negativo</span>
        <span style={{ position: 'absolute', right: '0', bottom: '-18px', fontSize: '0.65rem', fontFamily: 'Georgia,serif', color: 'var(--ink-light)' }}>positivo</span>

        {conSesgo.map((m, idx) => {
          const pct = ((m.sesgo + 1) / 2) * 100
          const color = colorSesgo(m.sesgo)
          const esArriba = lados[idx]
          return (
            <div key={m.medio} style={{ position: 'absolute', left: `${pct}%`, top: '-7px', transform: 'translateX(-50%)', textAlign: 'center' }}>
              <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: color, margin: '0 auto', border: '1.5px solid var(--paper)' }} />
              <div style={{
                position: 'absolute', left: '50%', transform: 'translateX(-50%)',
                width: '1px', background: color, opacity: 0.35,
                ...(esArriba ? { bottom: '10px', height: '18px' } : { top: '10px', height: '14px' })
              }} />
              <div style={{
                position: 'absolute', left: '50%', transform: 'translateX(-50%)',
                whiteSpace: 'nowrap', fontSize: '0.65rem',
                fontFamily: "'IM Fell English', Georgia, serif", color,
                ...(esArriba ? { bottom: '26px' } : { top: '22px' })
              }}>
                {m.medio}
                <br />
                <span style={{ fontSize: '0.6rem', color: 'var(--ink-light)' }}>{m.sesgo > 0 ? '+' : ''}{m.sesgo.toFixed(2)}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
