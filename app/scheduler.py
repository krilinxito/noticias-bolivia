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
    from app.analysis.embeddings import agrupar_en_eventos
    from app.analysis.gemini import analizar_articulo, analizar_sesgo_evento
    from app.models import Articulo
    with SessionLocal() as db:
        agrupar_en_eventos(db)

        # Tono: solo artículos en eventos (multi-medio), máx 50 por ciclo
        arts = (
            db.query(Articulo)
            .filter(
                Articulo.analisis == None,
                Articulo.evento_id.isnot(None),
            )
            .limit(50)
            .all()
        )
        for a in arts:
            analizar_articulo(a, db)
        logger.info(f"Tono: {len(arts)} artículos analizados")

        # Sesgo: todos los eventos con 2+ medios que aún no tienen sesgo
        candidatos = (
            db.query(Articulo.evento_id)
            .filter(
                Articulo.evento_id.isnot(None),
                Articulo.analisis.isnot(None),
            )
            .group_by(Articulo.evento_id)
            .having(func.count(sql_distinct(Articulo.medio_id)) >= 2)
            .all()
        )
        sin_sesgo = []
        for (eid,) in candidatos:
            arts_ev = db.query(Articulo).filter(Articulo.evento_id == eid).all()
            tiene_sesgo = any(
                a.analisis and a.analisis.get('sesgo') is not None
                for a in arts_ev
            )
            if not tiene_sesgo:
                sin_sesgo.append(eid)
        for eid in sin_sesgo:
            analizar_sesgo_evento(eid, db)
        logger.info(f"Sesgo: {len(sin_sesgo)} eventos analizados")

    logger.info("Scheduler: análisis completo")


def iniciar_scheduler():
    # 06:00 Bolivia (UTC-4) = 10:00 UTC
    scheduler.add_job(job_scraping, CronTrigger(hour=10, minute=0), id="scraping")
    # Análisis 1 hora después para dar margen al scraping
    scheduler.add_job(job_analisis, CronTrigger(hour=11, minute=0), id="analisis")
    scheduler.start()
    logger.info("Scheduler iniciado (ciclo diario 06:00 / 07:00 Bolivia)")


def detener_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler detenido")
