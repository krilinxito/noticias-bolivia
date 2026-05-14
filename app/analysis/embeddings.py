from datetime import datetime, timedelta

import numpy as np
from sqlalchemy import or_
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from loguru import logger

from app.models import Articulo, Evento

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


def agrupar_en_eventos(db):
    desde_scraping = datetime.utcnow() - timedelta(hours=48)
    desde_publicacion = datetime.utcnow() - timedelta(days=30)
    articulos = (
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

    if not articulos:
        logger.info("No hay artículos nuevos para agrupar")
        return 0

    logger.info(f"Agrupando {len(articulos)} artículos en eventos...")

    textos = [
        a.titulo + " " + (get_texto_analizable(a) or "")
        for a in articulos
    ]

    model = _get_model()
    embeddings = model.encode(textos, show_progress_bar=False)
    sim_matrix = cosine_similarity(embeddings)

    # Union-Find para agrupar artículos con similitud > 0.75
    parent = list(range(len(articulos)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i in range(len(articulos)):
        for j in range(i + 1, len(articulos)):
            if sim_matrix[i][j] > 0.65:
                union(i, j)

    # Agrupar por raíz
    grupos = {}
    for i, art in enumerate(articulos):
        raiz = find(i)
        grupos.setdefault(raiz, []).append(i)

    eventos_creados = 0
    for indices in grupos.values():
        grupo_arts = [articulos[i] for i in indices]

        # Título: artículo con más texto
        def longitud_texto(a):
            t = get_texto_analizable(a)
            return len(t) if t else 0

        art_principal = max(grupo_arts, key=longitud_texto)

        medios_distintos = len({a.medio_id for a in grupo_arts})
        score = medios_distintos / 6.0

        textos_grupo = [get_texto_analizable(a) for a in grupo_arts]
        temas = _extraer_temas([t for t in textos_grupo if t])

        evento = Evento(
            titulo=art_principal.titulo,
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
    logger.info(f"Eventos creados: {eventos_creados}")
    return eventos_creados
