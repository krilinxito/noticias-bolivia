"""
Ejecuta el pipeline completo manualmente:
  1. (Opcional) Reset de la BD
  2. Scraping de los 6 medios
  3. Análisis: embeddings → eventos → tono (Gemini flash-lite) → sesgo (Gemini flash)

Uso:
  python run_pipeline.py           # scraping + análisis
  python run_pipeline.py --reset   # reset BD primero, luego scraping + análisis
  python run_pipeline.py --solo-scraping
  python run_pipeline.py --solo-analisis
"""
import sys
import time
from datetime import datetime

from loguru import logger
from app.database import SessionLocal
from app.models import Articulo, Evento


def reset_bd():
    print("\n[1/3] Reset de la base de datos...")
    with SessionLocal() as db:
        n_arts = db.query(Articulo).delete()
        n_evs = db.query(Evento).delete()
        db.commit()
    print(f"      Eliminados {n_arts} artículos y {n_evs} eventos.")


def correr_scraping():
    print("\n[2/3] Scraping de medios...")
    t0 = time.time()
    from app.scraper import correr_scraping as _scraping
    with SessionLocal() as db:
        stats = _scraping(db)
    elapsed = round(time.time() - t0)
    print(f"      Nuevos: {stats['nuevos']} | Cuerpos: {stats['cuerpos']} | "
          f"Descartados: {stats.get('descartados', 0)} | Errores: {stats['errores']} | {elapsed}s")


def correr_analisis():
    print("\n[3/3] Análisis (embeddings + Gemini)...")
    t0 = time.time()
    from app.scheduler import job_analisis
    job_analisis()
    elapsed = round(time.time() - t0)
    print(f"      Análisis completado en {elapsed}s")


def mostrar_resumen():
    print("\n─── Resumen final ───")
    with SessionLocal() as db:
        arts = db.query(Articulo).count()
        evs = db.query(Evento).count()
        analizados = db.query(Articulo).filter(Articulo.analisis.isnot(None)).count()
        en_eventos = db.query(Articulo).filter(Articulo.evento_id.isnot(None)).count()
    print(f"  Artículos totales : {arts}")
    print(f"  En eventos        : {en_eventos}")
    print(f"  Analizados        : {analizados}")
    print(f"  Eventos creados   : {evs}")
    print(f"\nFinalizado: {datetime.now().strftime('%H:%M:%S')}")


def main():
    args = sys.argv[1:]
    solo_scraping = '--solo-scraping' in args
    solo_analisis = '--solo-analisis' in args
    hacer_reset = '--reset' in args

    print("=" * 45)
    print("  El Observador Digital — Pipeline manual")
    print("=" * 45)

    if hacer_reset:
        confirmar = input("\n¿Vaciar la BD antes de empezar? (s/N): ").strip().lower()
        if confirmar == 's':
            reset_bd()
        else:
            print("      Reset cancelado, continuando...")

    if solo_analisis:
        correr_analisis()
    elif solo_scraping:
        correr_scraping()
    else:
        correr_scraping()
        correr_analisis()

    mostrar_resumen()


if __name__ == "__main__":
    main()
