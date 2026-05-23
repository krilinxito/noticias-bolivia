from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.database import SessionLocal

scheduler = BackgroundScheduler()


def job_scraping():
    logger.info("Scheduler: iniciando scraping...")
    from app.scraper import correr_scraping
    with SessionLocal() as db:
        stats = correr_scraping(db)
    logger.info(f"Scheduler: scraping completo {stats}")


def job_analisis():
    logger.info("Scheduler: iniciando análisis...")
    from sqlalchemy import func, distinct as sql_distinct
    from app.analysis.embeddings import agrupar_en_episodios, agrupar_en_temas
    from app.analysis.gemini import analizar_articulo, analizar_sesgo_episodio
    from app.models import Articulo

    with SessionLocal() as db:
        # Nivel 1: agrupar artículos en episodios (sucesos puntuales, estricto)
        agrupar_en_episodios(db)

        # Nivel 2: agrupar episodios en temas (historia en curso, laxo)
        agrupar_en_temas(db)

        # Tono: artículos en episodios sin analizar, máx 50 por ciclo
        arts = (
            db.query(Articulo)
            .filter(
                Articulo.analisis == None,
                Articulo.episodio_id.isnot(None),
            )
            .limit(50)
            .all()
        )
        tono_ok = 0
        for a in arts:
            try:
                analizar_articulo(a, db)
                tono_ok += 1
            except Exception:
                logger.warning("Cuota de tono agotada, continuando con sesgo")
                break
        logger.info(f"Tono: {tono_ok}/{len(arts)} artículos analizados")

        # Sesgo: episodios con 2+ medios que ya tienen tono analizado
        candidatos = (
            db.query(Articulo.episodio_id)
            .filter(
                Articulo.episodio_id.isnot(None),
                Articulo.analisis.isnot(None),
            )
            .group_by(Articulo.episodio_id)
            .having(func.count(sql_distinct(Articulo.medio_id)) >= 2)
            .all()
        )
        sin_sesgo = []
        for (eid,) in candidatos:
            arts_ep = db.query(Articulo).filter(Articulo.episodio_id == eid).all()
            tiene_sesgo = any(
                a.analisis and a.analisis.get('sesgo') is not None
                for a in arts_ep
            )
            if not tiene_sesgo:
                sin_sesgo.append(eid)

        sesgo_ok = 0
        for eid in sin_sesgo:
            try:
                analizar_sesgo_episodio(eid, db)
                sesgo_ok += 1
            except Exception:
                logger.warning("Cuota de sesgo agotada, deteniendo")
                break
        logger.info(f"Sesgo: {sesgo_ok}/{len(sin_sesgo)} episodios analizados")

    logger.info("Scheduler: análisis completo")


def iniciar_scheduler():
    scheduler.add_job(job_scraping, CronTrigger(hour=10, minute=0), id="scraping")
    scheduler.add_job(job_analisis, CronTrigger(hour=11, minute=0), id="analisis")
    scheduler.start()
    logger.info("Scheduler iniciado (ciclo diario 06:00 / 07:00 Bolivia)")


def detener_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler detenido")
