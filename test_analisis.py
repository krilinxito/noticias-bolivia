from app.database import SessionLocal
from app.analysis.embeddings import agrupar_en_eventos
from app.analysis.gemini import analizar_articulo, analizar_sesgo_evento
from app.models import Articulo, Evento

with SessionLocal() as db:
    print("Agrupando en eventos...")
    n = agrupar_en_eventos(db)
    print(f"Eventos creados: {n}")

    print("\nAnalizando artículos con Gemini (máx 5)...")
    articulos = db.query(Articulo).filter(Articulo.analisis == None).limit(5).all()
    for a in articulos:
        analizar_articulo(a, db)
        print(f"  ✓ {a.titulo[:50]} → {a.analisis}")

    print("\nAnalizando sesgo por evento (máx 3)...")
    eventos = db.query(Evento).limit(3).all()
    for e in eventos:
        analizar_sesgo_evento(e.id, db)
        print(f"  ✓ {e.titulo[:50]} (importancia: {e.score_importancia:.2f})")
