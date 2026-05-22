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

    # Artículo representativo de cada evento reciente (últimos 7 días)
    desde_evento = datetime.utcnow() - timedelta(days=7)
    eventos_recientes = (
        db.query(Evento)
        .filter(Evento.fecha_deteccion >= desde_evento)
        .all()
    )
    art_por_evento = {}
    for ev in eventos_recientes:
        arts_ev = db.query(Articulo).filter(Articulo.evento_id == ev.id).all()
        if arts_ev:
            art_por_evento[ev.id] = max(arts_ev, key=_longitud_texto)

    existing_ids = list(art_por_evento.keys())
    arts_existentes = [art_por_evento[eid] for eid in existing_ids]

    # Embeddings: nuevos + representativos de eventos existentes
    model = _get_model()
    all_arts = nuevos + arts_existentes
    all_textos = [a.titulo + " " + (get_texto_analizable(a) or "") for a in all_arts]
    all_embeddings = model.encode(all_textos, show_progress_bar=False)

    nuevos_emb = all_embeddings[:len(nuevos)]
    existing_emb = all_embeddings[len(nuevos):]

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

    for i in range(len(nuevos)):
        for j in range(i + 1, len(nuevos)):
            if sim_matrix[i][j] > 0.65:
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

        art_principal = max(grupo_arts, key=_longitud_texto)
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
    logger.info(f"Eventos creados: {eventos_creados}, artículos agregados a eventos existentes: {arts_agregados}")
    return eventos_creados
