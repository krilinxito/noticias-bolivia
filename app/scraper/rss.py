import time
from datetime import datetime, timedelta, timezone
import feedparser
from bs4 import BeautifulSoup
from loguru import logger

from app.models import Articulo

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "es-ES,es;q=0.9",
}


def _limpiar_html(texto):
    if not texto:
        return ""
    return BeautifulSoup(texto, "lxml").get_text(separator=" ", strip=True)


def _extraer_cuerpo_rss(entry):
    # Prioridad 1: campo content con texto completo
    content = entry.get("content")
    if content:
        texto = _limpiar_html(content[0].get("value", ""))
        if len(texto) > 500:
            return texto, None

    # Prioridad 2: summary largo = cuerpo completo
    summary = entry.get("summary", "")
    texto_summary = _limpiar_html(summary)
    if len(texto_summary) > 500:
        return texto_summary, texto_summary[:500]

    # Prioridad 3: summary corto = solo resumen
    return None, texto_summary or None


def _parsed_to_datetime(t):
    if t:
        try:
            return datetime(*t[:6])
        except Exception:
            pass
    return None


def fetch_feed(medio, db):
    nuevos = 0
    for intento in range(3):
        try:
            feed = feedparser.parse(medio.url_rss, request_headers=HEADERS)
            break
        except Exception as e:
            if intento == 2:
                logger.error(f"{medio.nombre}: error al parsear feed — {e}")
                return 0
            time.sleep(2 ** intento)

    limite_antiguedad = datetime.now(timezone.utc) - timedelta(days=30)

    for entry in feed.entries:
        url = entry.get("link")
        if not url:
            continue

        if db.query(Articulo).filter(Articulo.url == url).first():
            continue

        titulo = entry.get("title", "Sin título")
        cuerpo, resumen_rss = _extraer_cuerpo_rss(entry)
        fecha = _parsed_to_datetime(entry.get("published_parsed"))

        # Descartar artículos viejos que los RSS mezclan con los recientes
        if fecha and fecha.replace(tzinfo=timezone.utc) < limite_antiguedad:
            continue

        # Descartar entradas sin contenido real (páginas en blanco, publicidad)
        tiene_contenido = (cuerpo and len(cuerpo) > 50) or (resumen_rss and len(resumen_rss) > 30)
        if not tiene_contenido and not titulo or titulo in ("Sin título", "Publicidad"):
            continue

        articulo = Articulo(
            medio_id=medio.id,
            titulo=titulo,
            url=url,
            resumen_rss=resumen_rss,
            cuerpo=cuerpo,
            fecha_publicacion=fecha,
        )
        db.add(articulo)
        db.flush()
        nuevos += 1
        time.sleep(2)

    db.commit()
    logger.info(f"{medio.nombre}: {nuevos} artículos nuevos")
    return nuevos
