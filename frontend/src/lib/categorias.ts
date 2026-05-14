export const CATEGORIAS: Record<string, string[]> = {
  'Política':      ['gobierno', 'presidente', 'ley', 'congreso', 'senado', 'elecciones', 'ministr', 'diputad', 'partido', 'alcalde', 'gobernador', 'asamblea', 'decreto', 'lara', 'arce', 'paz'],
  'Economía':      ['econom', 'precio', 'dólar', 'mercado', 'inflaci', 'banco', 'exporta', 'importa', 'gasolin', 'combustible', 'deuda', 'presupuesto', 'impuest', 'industria', 'empresa'],
  'Deportes':      ['fútbol', 'deporte', 'selección', 'liga', 'campeonat', 'equipo', 'jugador', 'bolívar', 'strong', 'wilstermann', 'oriente', 'gol', 'torneo', 'atletismo'],
  'Sociedad':      ['salud', 'educaci', 'comunidad', 'vecino', 'protest', 'bloqueo', 'huelga', 'marcha', 'social', 'familia', 'mujer', 'violencia', 'seguridad', 'policial', 'crimen'],
  'Internacional': ['eeuu', 'argentina', 'brasil', 'venezuela', 'trump', 'mundial', 'global', 'internacion', 'china', 'rusia', 'europa', 'colombia', 'perú', 'chile', 'iran'],
  'Cultura':       ['música', 'arte', 'cultura', 'festival', 'cine', 'teatro', 'libro', 'patrimoni', 'carnaval', 'folklore', 'danza', 'tradici'],
}

export const CAT_COLOR: Record<string, string> = {
  'Política':      '#8b1a1a',
  'Economía':      '#1a3a6a',
  'Deportes':      '#1a4a1a',
  'Sociedad':      '#6a3a1a',
  'Internacional': '#4a1a6a',
  'Cultura':       '#6a4a1a',
  'General':       '#5a4a32',
}

export function detectarCategoria(temas: string[]): string {
  if (!temas || temas.length === 0) return 'General'
  const texto = temas.join(' ').toLowerCase()
  for (const [cat, keywords] of Object.entries(CATEGORIAS)) {
    if (keywords.some(k => texto.includes(k))) return cat
  }
  return 'General'
}
