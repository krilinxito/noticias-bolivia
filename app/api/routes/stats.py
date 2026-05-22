from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import Articulo, Evento, Medio

router = APIRouter()


def get_db():
    with SessionLocal() as db:
        yield db


@router.get("")
def estadisticas(db: Session = Depends(get_db)):
    total_eventos = db.query(Evento).count()
    total_articulos = db.query(Articulo).count()
    articulos_analizados = db.query(Articulo).filter(Articulo.analisis.isnot(None)).count()

    # Medio con más artículos
    fila_medio = (
        db.query(Articulo.medio_id, func.count().label("n"))
        .group_by(Articulo.medio_id)
        .order_by(func.count().desc())
        .first()
    )
    if fila_medio:
        medio_obj = db.get(Medio, fila_medio[0])
        medio_mas_activo = {"nombre": medio_obj.nombre if medio_obj else "?", "total": fila_medio[1]}
    else:
        medio_mas_activo = {"nombre": None, "total": 0}

    # Evento más divergente (misma lógica que sesgos.py)
    evento_mas_divergente = None
    eventos = db.query(Evento).options(joinedload(Evento.articulos)).all()
    mejor_div = -1.0
    for ev in eventos:
        sesgos = [
            float(a.analisis["sesgo"])
            for a in ev.articulos
            if a.analisis and a.analisis.get("sesgo") is not None
        ]
        if len(sesgos) < 2:
            continue
        div = round(max(sesgos) - min(sesgos), 2)
        if div > mejor_div:
            mejor_div = div
            evento_mas_divergente = {"id": ev.id, "titulo": ev.titulo, "divergencia": div}

    return {
        "total_eventos": total_eventos,
        "total_articulos": total_articulos,
        "articulos_analizados": articulos_analizados,
        "medio_mas_activo": medio_mas_activo,
        "evento_mas_divergente": evento_mas_divergente,
    }
