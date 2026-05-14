from apscheduler.schedulers.background import BackgroundScheduler
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

        # Tono: analizar artículos pendientes
        arts = db.query(Articulo).filter(Articulo.analisis == None).limit(20).all()
        for a in arts:
            analizar_articulo(a, db)

        # Sesgo: eventos con 2+ medios que aún no tienen sesgo calculado
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
            if len(sin_sesgo) >= 3:
                break
        for eid in sin_sesgo:
            analizar_sesgo_evento(eid, db)
        logger.info(f"Sesgo: {len(sin_sesgo)} eventos analizados")

    logger.info("Scheduler: análisis completo")


def iniciar_scheduler():
    scheduler.add_job(job_scraping, "interval", minutes=30, id="scraping")
    scheduler.add_job(job_analisis, "interval", minutes=60, id="analisis")
    scheduler.start()
    logger.info("Scheduler iniciado")


def detener_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler detenido")
