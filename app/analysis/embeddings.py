from datetime import datetime, timedelta
import re

import numpy as np
from sqlalchemy import or_
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from loguru import logger

from app.models import Articulo, Episodio, Tema

_model = None
_kw_model = None
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

_STOP_ES = {
    'de', 'la', 'el', 'en', 'y', 'a', 'que', 'del', 'los', 'las', 'un', 'una',
    'por', 'con', 'se', 'no', 'es', 'al', 'su', 'sus', 'lo', 'para', 'como',
    'más', 'pero', 'este', 'esta', 'ese', 'esa', 'esos', 'estas', 'son', 'fue',
    'han', 'hay', 'sobre', 'tras', 'ante', 'bajo', 'desde', 'hasta', 'entre',
    'sin', 'según', 'durante', 'también', 'ya', 'o', 'e', 'ni', 'si', 'le',
    'les', 'nos', 'me', 'te', 'era', 'ser', 'está', 'están', 'será',
}


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


def _palabras_titulo(titulo: str) -> set:
    return {
        p for p in re.findall(r'[a-záéíóúüñ]+', titulo.lower())
        if len(p) >= 4 and p not in _STOP_ES
    }


def _extraer_keywords(textos):
    texto_combinado = " ".join(t for t in textos if t)
    if len(texto_combinado) < 30:
        return []
    try:
        kws = _get_kw_model().extract_keywords(
            texto_combinado,
            keyphrase_ngram_range=(1, 2),
            stop_words=None,
            top_n=5,
        )
        return [kw for kw, score in kws if score > 0.3]
    except Exception as e:
        logger.warning(f"Error extrayendo keywords: {e}")
        return []


def _longitud_texto(a):
    t = get_texto_analizable(a)
    return len(t) if t else 0


def _misma_ventana(a, b, horas=48):
    if not a.fecha_publicacion or not b.fecha_publicacion:
        return True
    diff = abs((a.fecha_publicacion - b.fecha_publicacion).total_seconds())
    return diff <= horas * 3600


# ─────────────────────────────────────────────────────────────────────────────
# Nivel 1: agrupar artículos en episodios (sucesos puntuales)
# Clustering estricto: sim > 0.75, medios distintos, ≥2 keywords comunes, 48h
# ─────────────────────────────────────────────────────────────────────────────

def agrupar_en_episodios(db):
    desde_scraping = datetime.utcnow() - timedelta(hours=25)
    desde_publicacion = datetime.utcnow() - timedelta(days=7)
    nuevos = (
        db.query(Articulo)
        .filter(
            Articulo.episodio_id == None,
            Articulo.fecha_scraping >= desde_scraping,
            or_(
                Articulo.fecha_publicacion == None,
                Articulo.fecha_publicacion >= desde_publicacion,
            ),
        )
        .all()
    )

    if not nuevos:
        logger.info("No hay artículos nuevos para agrupar en episodios")
        return 0

    logger.info(f"Agrupando {len(nuevos)} artículos nuevos en episodios...")

    # Centroide promedio de cada episodio reciente (últimos 3 días)
    desde_episodio = datetime.utcnow() - timedelta(days=3)
    episodios_recientes = (
        db.query(Episodio)
        .filter(Episodio.fecha_deteccion >= desde_episodio)
        .all()
    )
    arts_por_episodio = {}
    for ep in episodios_recientes:
        arts_ep = db.query(Articulo).filter(Articulo.episodio_id == ep.id).all()
        if arts_ep:
            arts_por_episodio[ep.id] = arts_ep

    existing_ids = list(arts_por_episodio.keys())

    model = _get_model()
    nuevos_textos = [a.titulo + " " + (get_texto_analizable(a) or "") for a in nuevos]

    ep_textos_planos = []
    ep_slice = []
    for eid in existing_ids:
        arts = arts_por_episodio[eid]
        textos = [a.titulo + " " + (get_texto_analizable(a) or "") for a in arts]
        ep_slice.append((len(ep_textos_planos), len(ep_textos_planos) + len(textos)))
        ep_textos_planos.extend(textos)

    all_textos = nuevos_textos + ep_textos_planos
    all_embeddings = model.encode(all_textos, show_progress_bar=False)

    nuevos_emb = all_embeddings[:len(nuevos)]
    ep_all_emb = all_embeddings[len(nuevos):]

    if existing_ids:
        existing_emb = np.array([
            np.mean(ep_all_emb[s:e], axis=0)
            for s, e in ep_slice
        ])
    else:
        existing_emb = np.array([])

    # Union-Find estricto: sim > 0.75, medios distintos, ≥2 keywords, ventana 48h
    sim_matrix = cosine_similarity(nuevos_emb)
    parent = list(range(len(nuevos)))
    palabras_nuevos = [_palabras_titulo(a.titulo) for a in nuevos]

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
            if (sim_matrix[i][j] > 0.75
                    and nuevos[i].medio_id != nuevos[j].medio_id
                    and len(palabras_nuevos[i] & palabras_nuevos[j]) >= 2
                    and _misma_ventana(nuevos[i], nuevos[j], horas=48)):
                union(i, j)

    grupos = {}
    for i in range(len(nuevos)):
        raiz = find(i)
        grupos.setdefault(raiz, []).append(i)

    episodios_creados = 0
    arts_agregados = 0

    for indices in grupos.values():
        grupo_arts = [nuevos[i] for i in indices]
        cluster_emb = np.mean([nuevos_emb[i] for i in indices], axis=0).reshape(1, -1)

        # Intentar asignar a un episodio existente
        if len(existing_emb) > 0:
            sims = cosine_similarity(cluster_emb, existing_emb)[0]
            best_idx = int(np.argmax(sims))
            if sims[best_idx] > 0.75:
                cluster_palabras = set().union(*[_palabras_titulo(a.titulo) for a in grupo_arts])
                ep_palabras = set().union(*[
                    _palabras_titulo(a.titulo)
                    for a in arts_por_episodio[existing_ids[best_idx]]
                ])
                if len(cluster_palabras & ep_palabras) >= 2:
                    eid = existing_ids[best_idx]
                    for art in grupo_arts:
                        art.episodio_id = eid
                        db.add(art)
                    arts_agregados += len(grupo_arts)
                    continue

        # Crear episodio nuevo solo si 2+ medios distintos
        medios_distintos = len({a.medio_id for a in grupo_arts})
        if medios_distintos < 2:
            continue

        grupo_embs = np.array([nuevos_emb[i] for i in indices])
        sims_centroid = cosine_similarity(cluster_emb, grupo_embs)[0]
        art_principal = grupo_arts[int(np.argmax(sims_centroid))]

        imagen = art_principal.imagen_url or next(
            (a.imagen_url for a in grupo_arts if a.imagen_url), None
        )
        score = medios_distintos / 6.0
        keywords = _extraer_keywords([get_texto_analizable(a) for a in grupo_arts if get_texto_analizable(a)])

        episodio = Episodio(
            titulo=art_principal.titulo,
            imagen_url=imagen,
            score_importancia=score,
            keywords=keywords,
        )
        db.add(episodio)
        db.flush()

        for art in grupo_arts:
            art.episodio_id = episodio.id
            db.add(art)

        episodios_creados += 1

    db.commit()
    logger.info(f"Episodios creados: {episodios_creados}, artículos agregados a episodios existentes: {arts_agregados}")
    return episodios_creados


# ─────────────────────────────────────────────────────────────────────────────
# Nivel 2: agrupar episodios en temas (historias en curso)
# Clustering laxo: sim > 0.65, ≥1 keyword común
# ─────────────────────────────────────────────────────────────────────────────

def agrupar_en_temas(db):
    desde = datetime.utcnow() - timedelta(hours=48)
    sin_tema = (
        db.query(Episodio)
        .filter(
            Episodio.tema_id == None,
            Episodio.fecha_deteccion >= desde,
        )
        .all()
    )

    if not sin_tema:
        logger.info("No hay episodios nuevos para agrupar en temas")
        return 0

    logger.info(f"Agrupando {len(sin_tema)} episodios en temas...")

    # Centroides de temas existentes (últimos 14 días)
    desde_tema = datetime.utcnow() - timedelta(days=14)
    temas_recientes = (
        db.query(Tema)
        .filter(Tema.fecha_deteccion >= desde_tema)
        .all()
    )
    eps_por_tema = {}
    for t in temas_recientes:
        eps = db.query(Episodio).filter(Episodio.tema_id == t.id).all()
        if eps:
            eps_por_tema[t.id] = eps

    model = _get_model()

    # Embeddings de episodios sin tema
    nuevos_textos = [
        ep.titulo + " " + " ".join(ep.keywords or [])
        for ep in sin_tema
    ]

    # Embeddings de todos los episodios de temas existentes (para centroides)
    tema_ids = list(eps_por_tema.keys())
    tema_textos_planos = []
    tema_slice = []
    for tid in tema_ids:
        eps = eps_por_tema[tid]
        textos = [e.titulo + " " + " ".join(e.keywords or []) for e in eps]
        tema_slice.append((len(tema_textos_planos), len(tema_textos_planos) + len(textos)))
        tema_textos_planos.extend(textos)

    all_textos = nuevos_textos + tema_textos_planos
    all_emb = model.encode(all_textos, show_progress_bar=False)

    nuevos_emb = all_emb[:len(sin_tema)]
    tema_all_emb = all_emb[len(sin_tema):]

    if tema_ids:
        tema_centroids = np.array([
            np.mean(tema_all_emb[s:e], axis=0)
            for s, e in tema_slice
        ])
    else:
        tema_centroids = np.array([])

    palabras_nuevos = [_palabras_titulo(ep.titulo) for ep in sin_tema]

    temas_creados = 0

    for i, ep in enumerate(sin_tema):
        asignado = False

        if len(tema_centroids) > 0:
            sims = cosine_similarity(nuevos_emb[i].reshape(1, -1), tema_centroids)[0]
            best_idx = int(np.argmax(sims))
            if sims[best_idx] > 0.65:
                # Verificar solapamiento de keywords
                tid = tema_ids[best_idx]
                tema_palabras = set().union(*[
                    _palabras_titulo(e.titulo)
                    for e in eps_por_tema[tid]
                ])
                if palabras_nuevos[i] & tema_palabras:
                    tema = db.query(Tema).filter(Tema.id == tid).first()
                    ep.tema_id = tid
                    db.add(ep)
                    # Actualizar score e imagen del tema si este episodio es más relevante
                    if ep.score_importancia >= tema.score_importancia:
                        tema.score_importancia = ep.score_importancia
                        if ep.imagen_url:
                            tema.imagen_url = ep.imagen_url
                        db.add(tema)
                    # Actualizar centroides locales
                    eps_por_tema[tid].append(ep)
                    old_s, old_e = tema_slice[best_idx]
                    nuevo_texto = ep.titulo + " " + " ".join(ep.keywords or [])
                    nuevo_emb = model.encode([nuevo_texto], show_progress_bar=False)[0]
                    tema_all_emb_list = list(tema_all_emb)
                    tema_all_emb_list.insert(old_e, nuevo_emb)
                    tema_all_emb = np.array(tema_all_emb_list)
                    new_end = old_e + 1
                    tema_slice[best_idx] = (old_s, new_end)
                    for k in range(best_idx + 1, len(tema_slice)):
                        s, e = tema_slice[k]
                        tema_slice[k] = (s + 1, e + 1)
                    tema_centroids[best_idx] = np.mean(tema_all_emb[old_s:new_end], axis=0)
                    asignado = True

        if not asignado and ep.score_importancia >= 0.33:
            # Crear nuevo tema
            nuevo_tema = Tema(
                titulo=ep.titulo,
                imagen_url=ep.imagen_url,
                score_importancia=ep.score_importancia,
                keywords=ep.keywords,
            )
            db.add(nuevo_tema)
            db.flush()
            ep.tema_id = nuevo_tema.id
            db.add(ep)
            eps_por_tema[nuevo_tema.id] = [ep]
            nuevo_texto = ep.titulo + " " + " ".join(ep.keywords or [])
            nuevo_emb = model.encode([nuevo_texto], show_progress_bar=False)
            tema_ids.append(nuevo_tema.id)
            tema_slice.append((len(tema_all_emb), len(tema_all_emb) + 1))
            if len(tema_all_emb) > 0:
                tema_all_emb = np.vstack([tema_all_emb, nuevo_emb])
                tema_centroids = np.vstack([tema_centroids, nuevo_emb])
            else:
                tema_all_emb = nuevo_emb
                tema_centroids = nuevo_emb
            temas_creados += 1

    db.commit()
    logger.info(f"Temas creados: {temas_creados}, episodios asignados a temas existentes: {len(sin_tema) - temas_creados}")
    return temas_creados
