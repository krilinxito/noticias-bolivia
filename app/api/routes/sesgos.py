from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import Articulo, Episodio, Medio

router = APIRouter()


def get_db():
    with SessionLocal() as db:
        yield db


@router.get("")
def listar_sesgos(limit: int = 30, db: Session = Depends(get_db)):
    medios_map = {m.id: m.nombre for m in db.query(Medio).all()}

    episodios = (
        db.query(Episodio)
        .options(joinedload(Episodio.articulos))
        .all()
    )

    resultado = []
    for ep in episodios:
        medios_con_sesgo = []
        resumen = None

        for a in ep.articulos:
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
            "id": ep.id,
            "titulo": ep.titulo,
            "fecha_deteccion": ep.fecha_deteccion,
            "divergencia": divergencia,
            "resumen_comparativo": resumen,
            "medios": sorted(medios_con_sesgo, key=lambda x: x["sesgo"]),
        })

    resultado.sort(key=lambda x: x["divergencia"], reverse=True)
    return resultado[:limit]
