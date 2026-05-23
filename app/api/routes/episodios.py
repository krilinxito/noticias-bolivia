from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import Articulo, Episodio, Medio
from app.api.routes.temas import _medios_dict, _serializar_episodio, _fmt_utc

router = APIRouter()


def get_db():
    with SessionLocal() as db:
        yield db


@router.get("")
def listar_episodios(limit: int = 200, db: Session = Depends(get_db)):
    medios = _medios_dict(db)
    eps = (
        db.query(Episodio)
        .options(joinedload(Episodio.articulos))
        .order_by(Episodio.fecha_deteccion.desc())
        .limit(limit)
        .all()
    )
    result = []
    for ep in eps:
        arts = ep.articulos
        sesgos = [
            float(a.analisis["sesgo"])
            for a in arts
            if a.analisis and a.analisis.get("sesgo") is not None
        ]
        sesgo_promedio = round(sum(sesgos) / len(sesgos), 3) if sesgos else None
        medios_names = sorted({medios.get(a.medio_id, "?") for a in arts})
        result.append({
            "id": ep.id,
            "titulo": ep.titulo,
            "fecha_deteccion": _fmt_utc(ep.fecha_deteccion),
            "score_importancia": ep.score_importancia,
            "keywords": ep.keywords,
            "imagen_url": ep.imagen_url,
            "tema_id": ep.tema_id,
            "medios": medios_names,
            "sesgo_promedio": sesgo_promedio,
            "medios_count": len(medios_names),
        })
    return result


@router.get("/{episodio_id}")
def obtener_episodio(episodio_id: int, db: Session = Depends(get_db)):
    medios = _medios_dict(db)
    ep = (
        db.query(Episodio)
        .options(joinedload(Episodio.articulos))
        .filter(Episodio.id == episodio_id)
        .first()
    )
    if not ep:
        raise HTTPException(status_code=404, detail="Episodio no encontrado")
    return _serializar_episodio(ep, medios, incluir_articulos=True)
