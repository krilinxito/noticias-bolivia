import { useState, useMemo } from 'react'

const TONO_COLOR: Record<string, string> = {
  positivo: '#1a4a1a', negativo: '#8b1a1a', neutral: '#5a4a32',
}
const TONO_ES: Record<string, string> = {
  positivo: 'positivo', negativo: 'negativo', neutral: 'neutral',
}

function puntaje(art: any): number {
  let s = 0
  if (art.analisis?.sesgo != null) s += 3
  if (art.analisis?.tono && art.analisis.tono !== 'sin_texto') s += 2
  if (art.cuerpo && art.cuerpo.length > 50) s += 1
  return s
}

const POR_PAGINA = 6

interface Props {
  articulos_por_medio: Record<string, any[]>
}

export default function CoberturaArticulos({ articulos_por_medio }: Props) {
  const medios = Object.keys(articulos_por_medio)
  const [filtro, setFiltro] = useState('Todos')
  const [pagina, setPagina] = useState(0)

  const todos = useMemo(() => {
    const flat: any[] = []
    for (const [medio, arts] of Object.entries(articulos_por_medio)) {
      for (const art of arts) flat.push({ ...art, medio })
    }
    return flat.sort((a, b) => puntaje(b) - puntaje(a))
  }, [articulos_por_medio])

  const filtrados = useMemo(() => {
    return filtro === 'Todos' ? todos : todos.filter(a => a.medio === filtro)
  }, [todos, filtro])

  const totalPags = Math.ceil(filtrados.length / POR_PAGINA)
  const enPagina = filtrados.slice(pagina * POR_PAGINA, (pagina + 1) * POR_PAGINA)

  function cambiarFiltro(f: string) {
    setFiltro(f)
    setPagina(0)
  }

  const btnBase: React.CSSProperties = {
    fontFamily: "'IM Fell English', Georgia, serif",
    fontSize: '0.7rem',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    padding: '0.25rem 0.6rem',
    cursor: 'pointer',
    transition: 'background 0.15s, color 0.15s',
  }

  return (
    <div>
      {/* Filtro por medio */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '1.25rem' }}>
        {['Todos', ...medios].map(m => {
          const activo = filtro === m
          return (
            <button
              key={m}
              onClick={() => cambiarFiltro(m)}
              style={{
                ...btnBase,
                border: `1px solid ${activo ? 'var(--ink)' : 'var(--border)'}`,
                background: activo ? 'var(--ink)' : 'transparent',
                color: activo ? 'var(--paper)' : 'var(--ink)',
              }}
            >
              {m}
              {m !== 'Todos' && (
                <span style={{ marginLeft: '0.3rem', opacity: 0.6 }}>
                  ({articulos_por_medio[m]?.length ?? 0})
                </span>
              )}
            </button>
          )
        })}
        <span style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.7rem', color: 'var(--ink-light)', alignSelf: 'center', marginLeft: '0.25rem' }}>
          {filtrados.length} artículo{filtrados.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Artículos */}
      {enPagina.map((art: any) => {
        const analisis = art.analisis
        const sesgo: number | null = analisis?.sesgo ?? null
        const tono: string | null = (analisis?.tono && analisis.tono !== 'sin_texto') ? analisis.tono : null
        const tonoColor = tono ? (TONO_COLOR[tono] ?? '#5a4a32') : '#5a4a32'
        const extracto: string | null =
          analisis?.sesgo_descripcion ??
          (art.cuerpo && art.cuerpo.length > 50
            ? art.cuerpo.slice(0, 280) + (art.cuerpo.length >= 280 ? '…' : '')
            : null) ??
          (art.resumen_rss && art.resumen_rss.length > 20
            ? art.resumen_rss.slice(0, 280) + (art.resumen_rss.length >= 280 ? '…' : '')
            : null)

        return (
          <div
            key={art.id}
            style={{ borderBottom: '1px solid var(--border)', padding: '1.25rem 0', display: 'grid', gridTemplateColumns: '8rem 1fr', gap: '1.25rem' }}
          >
            {/* Columna izquierda */}
            <div>
              <p style={{ fontFamily: "'Playfair Display', Georgia, serif", fontWeight: 700, fontSize: '0.9rem', marginBottom: '0.35rem' }}>
                {art.medio}
              </p>
              {tono && (
                <div style={{ display: 'inline-block', border: `1px solid ${tonoColor}`, padding: '0.1rem 0.4rem', marginBottom: '0.4rem' }}>
                  <span style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: tonoColor }}>
                    {TONO_ES[tono] ?? tono}
                  </span>
                </div>
              )}
              {sesgo !== null && (
                <div style={{ marginTop: '0.4rem' }}>
                  <div style={{ height: '4px', background: 'var(--border)', position: 'relative', marginBottom: '0.2rem' }}>
                    <div style={{ position: 'absolute', left: '50%', top: '-2px', width: '1px', height: '8px', background: 'var(--border-dark)' }} />
                    <div style={{
                      position: 'absolute', height: '4px',
                      background: sesgo < 0 ? '#8b1a1a' : '#1a4a1a',
                      ...(sesgo < 0
                        ? { right: '50%', width: `${Math.abs(sesgo) * 50}%` }
                        : { left: '50%', width: `${sesgo * 50}%` }),
                    }} />
                  </div>
                  <span style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.65rem', color: 'var(--ink-light)' }}>
                    {sesgo > 0 ? '+' : ''}{sesgo.toFixed(2)}
                  </span>
                </div>
              )}
              {art.fecha_publicacion && (
                <p style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.63rem', color: 'var(--ink-light)', marginTop: '0.5rem' }}>
                  {new Date(art.fecha_publicacion).toLocaleDateString('es-BO', { day: 'numeric', month: 'short' })}
                </p>
              )}
            </div>

            {/* Columna derecha */}
            <div>
              <a
                href={art.url}
                target="_blank"
                rel="noreferrer"
                style={{ fontFamily: "'Playfair Display', Georgia, serif", fontWeight: 600, fontSize: '0.95rem', textDecoration: 'underline', textUnderlineOffset: '3px', display: 'block', marginBottom: '0.5rem', color: 'var(--ink)', lineHeight: 1.35 }}
              >
                {art.titulo}
              </a>
              {extracto && (
                <p style={{
                  fontFamily: 'Georgia, serif',
                  fontSize: '0.82rem',
                  lineHeight: 1.6,
                  color: 'var(--ink-light)',
                  fontStyle: analisis?.sesgo_descripcion ? 'italic' : 'normal',
                  borderLeft: analisis?.sesgo_descripcion ? '2px solid var(--border)' : 'none',
                  paddingLeft: analisis?.sesgo_descripcion ? '0.6rem' : '0',
                }}>
                  {extracto}
                </p>
              )}
            </div>
          </div>
        )
      })}

      {/* Paginación */}
      {totalPags > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '1.25rem', justifyContent: 'center' }}>
          <button
            onClick={() => setPagina(p => Math.max(0, p - 1))}
            disabled={pagina === 0}
            style={{ ...btnBase, border: '1px solid var(--border)', background: 'transparent', color: pagina === 0 ? 'var(--ink-light)' : 'var(--ink)', cursor: pagina === 0 ? 'default' : 'pointer' }}
          >
            ← Anterior
          </button>
          <span style={{ fontFamily: "'IM Fell English', Georgia, serif", fontSize: '0.75rem', color: 'var(--ink-light)' }}>
            {pagina + 1} / {totalPags}
          </span>
          <button
            onClick={() => setPagina(p => Math.min(totalPags - 1, p + 1))}
            disabled={pagina >= totalPags - 1}
            style={{ ...btnBase, border: '1px solid var(--border)', background: 'transparent', color: pagina >= totalPags - 1 ? 'var(--ink-light)' : 'var(--ink)', cursor: pagina >= totalPags - 1 ? 'default' : 'pointer' }}
          >
            Siguiente →
          </button>
        </div>
      )}
    </div>
  )
}
