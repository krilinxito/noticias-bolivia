import type { Episodio } from '../types'
import SesgometroBar from './SesgometroBar'

const TONO_BADGE: Record<string, string> = {
  positivo: 'bg-green-900 text-green-300',
  negativo: 'bg-red-900 text-red-300',
  neutral: 'bg-gray-700 text-gray-300',
  sin_texto: 'bg-gray-800 text-gray-500',
}

interface Props { evento: Episodio }

export default function ComparativaMedios({ evento }: Props) {
  const medios = Object.entries(evento.articulos_por_medio)

  if (medios.length === 0) return <p className="text-gray-500 text-sm">Sin artículos comparables.</p>

  const resumen = medios[0]?.[1]?.[0]?.analisis?.resumen_comparativo

  return (
    <div className="space-y-4">
      {resumen && (
        <div className="bg-blue-950 border border-blue-800 rounded-lg p-4 text-sm text-blue-200">
          <span className="font-semibold text-blue-400">Resumen comparativo: </span>{resumen}
        </div>
      )}

      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${Math.min(medios.length, 3)}, minmax(0, 1fr))` }}>
        {medios.map(([nombre, articulos]) => {
          const art = articulos[0]
          const analisis = art?.analisis
          const tono = analisis?.tono || 'sin_texto'
          const sesgo = analisis?.sesgo

          return (
            <div key={nombre} className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white text-sm">{nombre}</span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${TONO_BADGE[tono] || TONO_BADGE.sin_texto}`}>
                  {tono}
                </span>
              </div>

              {art && (
                <a href={art.url} target="_blank" rel="noreferrer"
                  className="text-xs text-gray-300 hover:text-blue-400 line-clamp-3 block transition-colors">
                  {art.titulo}
                </a>
              )}

              <SesgometroBar nombre={nombre} sesgo={sesgo} />

              {analisis?.fuentes_citadas && analisis.fuentes_citadas.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {analisis.fuentes_citadas.map(f => (
                    <span key={f} className="text-[10px] bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">{f}</span>
                  ))}
                </div>
              )}

              {analisis?.sesgo_descripcion && (
                <p className="text-[10px] text-gray-500 leading-relaxed">{analisis.sesgo_descripcion}</p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
