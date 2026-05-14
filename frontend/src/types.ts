export interface Medio {
  id: number
  nombre: string
  linea_editorial: string
  region: string
  total_articulos: number
}

export interface Analisis {
  tono?: string
  temas?: string[]
  fuentes_citadas?: string[]
  sesgo?: number
  sesgo_descripcion?: string
  resumen_comparativo?: string
}

export interface Articulo {
  id: number
  titulo: string
  url: string
  fecha_publicacion?: string
  medio?: { id: number; nombre: string }
  analisis?: Analisis
  cuerpo?: string
}

export interface ArticuloPorMedio {
  [medio: string]: Articulo[]
}

export interface Evento {
  id: number
  titulo: string
  fecha_deteccion: string
  score_importancia: number
  temas?: string[]
  articulos_por_medio: ArticuloPorMedio
}

export interface ChatMessage {
  rol: 'usuario' | 'asistente'
  texto: string
}
