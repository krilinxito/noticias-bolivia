from datetime import datetime, timedelta
from loguru import logger

from app.models import Articulo, Medio
from app.scraper.portal import scrape_portal, CONFIGS as PORTAL_CONFIGS
from app.scraper.rss import fetch_feed
from app.scraper.article import scrape_articulo

LIMITE_DIAS = 7


def correr_scraping(db):
    stats = {"nuevos": 0, "cuerpos": 0, "errores": 0, "descartados": 0}

    medios = db.query(Medio).filter(Medio.activo == True).all()
    logger.info(f"Scraping {len(medios)} medios...")

    for medio in medios:
        try:
            if medio.nombre in PORTAL_CONFIGS:
                stats["nuevos"] += scrape_portal(medio, db)
            else:
                stats["nuevos"] += fetch_feed(medio, db)
        except Exception as e:
            logger.error(f"{medio.nombre}: {e}")
            stats["errores"] += 1

    sin_cuerpo = db.query(Articulo).filter(Articulo.cuerpo == None).all()
    logger.info(f"Scrapeando cuerpo de {len(sin_cuerpo)} artículos...")

    limite = datetime.utcnow() - timedelta(days=LIMITE_DIAS)

    for articulo in sin_cuerpo:
        try:
            resultado = scrape_articulo(articulo.url)
            fecha = resultado.get("fecha_publicacion")

            # Actualizar fecha si no la teníamos
            if fecha and articulo.fecha_publicacion is None:
                articulo.fecha_publicacion = fecha

            # Descartar artículos viejos o sin contenido ni fecha (links muertos)
            fecha_efectiva = articulo.fecha_publicacion or fecha
            if fecha_efectiva and fecha_efectiva < limite:
                db.delete(articulo)
                stats["descartados"] += 1
                continue
            if not resultado["cuerpo"] and not fecha_efectiva:
                db.delete(articulo)
                stats["descartados"] += 1
                continue

            if resultado["cuerpo"]:
                articulo.cuerpo = resultado["cuerpo"]
                stats["cuerpos"] += 1
            if resultado.get("imagen_url") and articulo.imagen_url is None:
                articulo.imagen_url = resultado["imagen_url"]
            db.add(articulo)
        except Exception as e:
            logger.error(f"Error cuerpo {articulo.url}: {e}")
            stats["errores"] += 1

    db.commit()
    logger.info(f"Scraping completo: {stats}")
    return stats
