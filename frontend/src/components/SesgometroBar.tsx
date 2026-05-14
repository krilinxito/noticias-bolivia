interface Props {
  nombre: string
  sesgo: number | null | undefined
}

export default function SesgometroBar({ nombre, sesgo }: Props) {
  if (sesgo == null) return (
    <div className="text-xs text-gray-500">{nombre}: sesgo no calculado</div>
  )

  const pct = ((sesgo + 1) / 2) * 100
  const color = sesgo < -0.3 ? 'bg-red-500' : sesgo > 0.3 ? 'bg-green-500' : 'bg-gray-400'

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-400">
        <span>{nombre}</span>
        <span className={sesgo < -0.3 ? 'text-red-400' : sesgo > 0.3 ? 'text-green-400' : 'text-gray-400'}>
          {sesgo > 0 ? '+' : ''}{sesgo.toFixed(2)}
        </span>
      </div>
      <div className="relative h-2 bg-gray-700 rounded-full">
        <div className="absolute top-0 bottom-0 w-px bg-gray-500" style={{ left: '50%' }} />
        <div
          className={`absolute top-0 bottom-0 rounded-full ${color}`}
          style={{ left: '50%', width: `${Math.abs(sesgo) * 50}%`, transform: sesgo < 0 ? 'translateX(-100%)' : '' }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-gray-600">
        <span>negativo</span><span>neutral</span><span>positivo</span>
      </div>
    </div>
  )
}
