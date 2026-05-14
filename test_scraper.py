from app.database import SessionLocal
from app.scraper import correr_scraping

with SessionLocal() as db:
    stats = correr_scraping(db)
    print(f"Artículos nuevos: {stats['nuevos']}")
    print(f"Cuerpos obtenidos: {stats['cuerpos']}")
    print(f"Errores: {stats['errores']}")
