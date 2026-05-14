from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import Articulo, Evento, Medio

router = APIRouter()


def get_db():
    with SessionLocal() as db:
        yield db


@router.get("")
def listar_sesgos(limit: int = 30, db: Session = Depends(get_db)):
    medios_map = {m.id: m.nombre for m in db.query(Medio).all()}

    eventos = (
        db.query(Evento)
        .options(joinedload(Evento.articulos))
        .all()
    )

    resultado = []
    for ev in eventos:
        medios_con_sesgo = []
        resumen = None

        for a in ev.articulos:
            if not a.analisis:
                continue
            sesgo = a.analisis.get("sesgo")
            if sesgo is None:
                continue
            nombre = medios_map.get(a.medio_id, "Desconocido")
            medios_con_sesgo.append({
                "medio": nombre,
                "sesgo": round(float(sesgo), 2),
                "tono": a.analisis.get("tono"),
                "sesgo_descripcion": a.analisis.get("sesgo_descripcion"),
            })
            if not resumen:
                resumen = a.analisis.get("resumen_comparativo")

        if len(medios_con_sesgo) < 2:
            continue

        sesgos = [m["sesgo"] for m in medios_con_sesgo]
        divergencia = round(max(sesgos) - min(sesgos), 2)

        resultado.append({
            "id": ev.id,
            "titulo": ev.titulo,
            "fecha_deteccion": ev.fecha_deteccion,
            "divergencia": divergencia,
            "resumen_comparativo": resumen,
            "medios": sorted(medios_con_sesgo, key=lambda x: x["sesgo"]),
        })

    resultado.sort(key=lambda x: x["divergencia"], reverse=True)
    return resultado[:limit]
