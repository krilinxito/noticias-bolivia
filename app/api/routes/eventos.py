from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import Articulo, Evento, Medio

router = APIRouter()


def get_db():
    with SessionLocal() as db:
        yield db


def _medios_dict(db):
    return {m.id: m.nombre for m in db.query(Medio).all()}


def _fmt_utc(dt):
    return dt.isoformat() + 'Z' if dt else None


def _fmt_bol(dt):
    return dt.isoformat() + '-04:00' if dt else None


def _serializar_articulo(a):
    return {
        "id": a.id,
        "titulo": a.titulo,
        "url": a.url,
        "fecha_publicacion": _fmt_bol(a.fecha_publicacion),
        "analisis": a.analisis,
        "imagen_url": a.imagen_url,
        "cuerpo": a.cuerpo[:400] if a.cuerpo else None,
        "resumen_rss": a.resumen_rss,
    }


def _serializar_evento(ev, medios, incluir_articulos=True):
    imagen = ev.imagen_url or next(
        (a.imagen_url for a in ev.articulos if a.imagen_url), None
    ) if incluir_articulos else ev.imagen_url

    base = {
        "id": ev.id,
        "titulo": ev.titulo,
        "fecha_deteccion": _fmt_utc(ev.fecha_deteccion),
        "score_importancia": ev.score_importancia,
        "keywords": ev.keywords,
        "imagen_url": imagen,
    }
    if incluir_articulos:
        por_medio = {}
        for a in ev.articulos:
            nombre = medios.get(a.medio_id, "Desconocido")
            por_medio.setdefault(nombre, []).append(_serializar_articulo(a))
        base["articulos_por_medio"] = por_medio
    else:
        medios_names = sorted({medios.get(a.medio_id, "?") for a in ev.articulos})
        sesgos = [
            float(a.analisis["sesgo"])
            for a in ev.articulos
            if a.analisis and a.analisis.get("sesgo") is not None
        ]
        base["medios"] = medios_names
        base["sesgo_promedio"] = round(sum(sesgos) / len(sesgos), 3) if sesgos else None
        base["medios_count"] = len(medios_names)
    return base


@router.get("")
def listar_eventos(limit: int = 200, db: Session = Depends(get_db)):
    medios = _medios_dict(db)
    evs = (
        db.query(Evento)
        .options(joinedload(Evento.articulos))
        .order_by(Evento.fecha_deteccion.desc())
        .limit(limit)
        .all()
    )
    return [_serializar_evento(ev, medios, incluir_articulos=False) for ev in evs]


@router.get("/{evento_id}")
def obtener_evento(evento_id: int, db: Session = Depends(get_db)):
    medios = _medios_dict(db)
    ev = (
        db.query(Evento)
        .options(joinedload(Evento.articulos))
        .filter(Evento.id == evento_id)
        .first()
    )
    if not ev:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return _serializar_evento(ev, medios, incluir_articulos=True)
