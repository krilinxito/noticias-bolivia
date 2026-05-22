import type { ChatMessage, Evento, Medio, Articulo, CardChat } from '../types'

const API_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000'

export const getEventos = (limit = 50): Promise<Evento[]> =>
  fetch(`${API_URL}/eventos?limit=${limit}`).then(r => r.json())

export const getEvento = (id: number): Promise<Evento> =>
  fetch(`${API_URL}/eventos/${id}`).then(r => r.json())

export const getMedios = (): Promise<Medio[]> =>
  fetch(`${API_URL}/medios`).then(r => r.json())

export const getNoticias = (params?: {
  limit?: number
  offset?: number
  medio_nombre?: string
  orden?: 'scraping' | 'fecha'
}): Promise<Articulo[]> => {
  const q = new URLSearchParams()
  if (params?.limit) q.set('limit', String(params.limit))
  if (params?.offset) q.set('offset', String(params.offset))
  if (params?.medio_nombre) q.set('medio_nombre', params.medio_nombre)
  if (params?.orden) q.set('orden', params.orden)
  return fetch(`${API_URL}/noticias?${q}`).then(r => r.json())
}

export interface EventoSesgo {
  id: number
  titulo: string
  fecha_deteccion: string
  divergencia: number
  resumen_comparativo: string | null
  medios: { medio: string; sesgo: number; tono: string | null; sesgo_descripcion: string | null }[]
}

export const getSesgos = (limit = 30): Promise<EventoSesgo[]> =>
  fetch(`${API_URL}/sesgos?limit=${limit}`).then(r => r.json())

export const chat = (mensaje: string, historial: ChatMessage[]): Promise<{ respuesta: string; tools_usadas: string[]; cards: CardChat[] }> =>
  fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mensaje, historial }),
  }).then(r => r.json())

export interface Stats {
  total_eventos: number
  total_articulos: number
  articulos_analizados: number
  medio_mas_activo: { nombre: string | null; total: number }
  evento_mas_divergente: { id: number; titulo: string; divergencia: number } | null
}

export const getStats = (): Promise<Stats> =>
  fetch(`${API_URL}/stats`).then(r => r.json())
