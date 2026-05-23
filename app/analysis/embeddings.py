from datetime import datetime, timedelta
import re

import numpy as np
from sqlalchemy import or_
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from loguru import logger

from app.models import Articulo, Evento

_STOP_ES = {
    'de', 'la', 'el', 'en', 'y', 'a', 'que', 'del', 'los', 'las', 'un', 'una',
    'por', 'con', 'se', 'no', 'es', 'al', 'su', 'sus', 'lo', 'para', 'como',
    'más', 'pero', 'este', 'esta', 'ese', 'esa', 'esos', 'estas', 'son', 'fue',
    'han', 'hay', 'sobre', 'tras', 'ante', 'bajo', 'desde', 'hasta', 'entre',
    'sin', 'según', 'durante', 'también', 'ya', 'o', 'e', 'ni', 'si', 'le',
    'les', 'nos', 'me', 'te', 'su', 'era', 'ser', 'está', 'están', 'será',
}


def _palabras_titulo(titulo: str) -> set:
    """Palabras significativas del título (≥4 chars, sin stop words)."""
    return {
        p for p in re.findall(r'[a-záéíóúüñ]+', titulo.lower())
        if len(p) >= 4 and p not in _STOP_ES
    }

_model = None
_kw_model = None
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def _get_model():
    global _model
    if _model is None:
        logger.info("Cargando modelo de embeddings...")
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _get_kw_model():
    global _kw_model
    if _kw_model is None:
        _kw_model = KeyBERT(model=MODEL_NAME)
    return _kw_model


def get_texto_analizable(articulo):
    if articulo.cuerpo and len(articulo.cuerpo.strip()) > 50:
        return articulo.cuerpo
    if articulo.resumen_rss and len(articulo.resumen_rss.strip()) > 20:
        return articulo.resumen_rss
    return None


def generar_embedding(texto):
    return _get_model().encode(texto).tolist()


def _extraer_temas(textos):
    texto_combinado = " ".join(t for t in textos if t)
    if len(texto_combinado) < 30:
        return []
    try:
        keywords = _get_kw_model().extract_keywords(
            texto_combinado,
            keyphrase_ngram_range=(1, 2),
            stop_words=None,
            top_n=5,
        )
        return [kw for kw, score in keywords if score > 0.3]
    except Exception as e:
        logger.warning(f"Error extrayendo temas: {e}")
        return []


def _longitud_texto(a):
    t = get_texto_analizable(a)
    return len(t) if t else 0


def agrupar_en_eventos(db):
    desde_scraping = datetime.utcnow() - timedelta(hours=25)
    desde_publicacion = datetime.utcnow() - timedelta(days=30)
    nuevos = (
        db.query(Articulo)
        .filter(
            Articulo.evento_id == None,
            Articulo.fecha_scraping >= desde_scraping,
            or_(
                Articulo.fecha_publicacion == None,
                Articulo.fecha_publicacion >= desde_publicacion,
            ),
        )
        .all()
    )

    if not nuevos:
        logger.info("No hay artículos nuevos para agrupar")
        return 0

    logger.info(f"Agrupando {len(nuevos)} artículos nuevos...")

    # Centroide promedio de cada evento reciente (últimos 7 días)
    desde_evento = datetime.utcnow() - timedelta(days=7)
    eventos_recientes = (
        db.query(Evento)
        .filter(Evento.fecha_deteccion >= desde_evento)
        .all()
    )
    arts_por_evento = {}
    for ev in eventos_recientes:
        arts_ev = db.query(Articulo).filter(Articulo.evento_id == ev.id).all()
        if arts_ev:
            arts_por_evento[ev.id] = arts_ev

    existing_ids = list(arts_por_evento.keys())

    # Embeddings: nuevos primero, luego todos los artículos de eventos existentes
    model = _get_model()
    nuevos_textos = [a.titulo + " " + (get_texto_analizable(a) or "") for a in nuevos]

    # Calcular centroides de eventos existentes a partir del promedio de sus artículos
    ev_textos_planos = []
    ev_slice = []  # (start, end) en ev_textos_planos para cada evento
    for eid in existing_ids:
        arts = arts_por_evento[eid]
        textos = [a.titulo + " " + (get_texto_analizable(a) or "") for a in arts]
        ev_slice.append((len(ev_textos_planos), len(ev_textos_planos) + len(textos)))
        ev_textos_planos.extend(textos)

    all_textos = nuevos_textos + ev_textos_planos
    all_embeddings = model.encode(all_textos, show_progress_bar=False)

    nuevos_emb = all_embeddings[:len(nuevos)]
    ev_all_emb = all_embeddings[len(nuevos):]

    # Centroide = media de embeddings de todos los artículos del evento
    if existing_ids:
        existing_emb = np.array([
            np.mean(ev_all_emb[s:e], axis=0)
            for s, e in ev_slice
        ])
    else:
        existing_emb = np.array([])

    # Union-Find solo entre artículos nuevos
    sim_matrix = cosine_similarity(nuevos_emb)
    parent = list(range(len(nuevos)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    palabras_nuevos = [_palabras_titulo(a.titulo) for a in nuevos]

    for i in range(len(nuevos)):
        for j in range(i + 1, len(nuevos)):
            if sim_matrix[i][j] > 0.65 and palabras_nuevos[i] & palabras_nuevos[j]:
                union(i, j)

    grupos = {}
    for i in range(len(nuevos)):
        raiz = find(i)
        grupos.setdefault(raiz, []).append(i)

    eventos_creados = 0
    arts_agregados = 0

    for indices in grupos.values():
        grupo_arts = [nuevos[i] for i in indices]
        cluster_emb = np.mean([nuevos_emb[i] for i in indices], axis=0).reshape(1, -1)

        # Intentar asignar a un evento existente
        if len(existing_emb) > 0:
            sims = cosine_similarity(cluster_emb, existing_emb)[0]
            best_idx = int(np.argmax(sims))
            if sims[best_idx] > 0.65:
                # Verificar solapamiento de palabras clave con el evento candidato
                cluster_palabras = set().union(*[_palabras_titulo(a.titulo) for a in grupo_arts])
                ev_palabras = set().union(*[
                    _palabras_titulo(a.titulo)
                    for a in arts_por_evento[existing_ids[best_idx]]
                ])
                if cluster_palabras & ev_palabras:
                    evento_id = existing_ids[best_idx]
                    for art in grupo_arts:
                        art.evento_id = evento_id
                        db.add(art)
                    arts_agregados += len(grupo_arts)
                    continue

        # Crear evento nuevo solo si 2+ medios distintos
        medios_distintos = len({a.medio_id for a in grupo_arts})
        if medios_distintos < 2:
            continue

        grupo_embs = np.array([nuevos_emb[i] for i in indices])
        sims_centroid = cosine_similarity(cluster_emb, grupo_embs)[0]
        art_principal = grupo_arts[int(np.argmax(sims_centroid))]
        score = medios_distintos / 6.0
        textos_grupo = [get_texto_analizable(a) for a in grupo_arts]
        temas = _extraer_temas([t for t in textos_grupo if t])

        # Imagen: art_principal primero; si no tiene, primer artículo del grupo con imagen
        imagen = art_principal.imagen_url or next(
            (a.imagen_url for a in grupo_arts if a.imagen_url), None
        )
        evento = Evento(
            titulo=art_principal.titulo,
            imagen_url=imagen,
            score_importancia=score,
            temas=temas,
        )
        db.add(evento)
        db.flush()

        for art in grupo_arts:
            art.evento_id = evento.id
            db.add(art)

        eventos_creados += 1

    db.commit()
    logger.info(f"Eventos creados: {eventos_creados}, artículos agregados a eventos existentes: {arts_agregados}")
    return eventos_creados
