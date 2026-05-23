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
  imagen_url?: string | null
}

export interface ArticuloPorMedio {
  [medio: string]: Articulo[]
}

export interface Tema {
  id: number
  titulo: string
  fecha_deteccion: string
  score_importancia: number
  keywords?: string[] | null
  imagen_url?: string | null
  medios: string[]
  episodios_count: number
}

export interface Episodio {
  id: number
  titulo: string
  fecha_deteccion: string
  score_importancia: number
  keywords?: string[] | null
  imagen_url?: string | null
  tema_id?: number | null
  articulos_por_medio?: ArticuloPorMedio
  medios?: string[]
  sesgo_promedio?: number | null
  medios_count?: number
}

export interface ChatMessage {
  rol: 'usuario' | 'asistente'
  texto: string
}

export type CardChat =
  | { tipo: 'evento'; id: number; titulo: string; medios: string[]; score_importancia: number; imagen_url: string | null; fecha_deteccion: string | null }
  | { tipo: 'articulo'; id: number; titulo: string; url: string; medio: string; imagen_url: string | null; tono: string | null }
