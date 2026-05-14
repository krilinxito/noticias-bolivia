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


def _serializar_evento(evento, medios):
    por_medio = {}
    for a in evento.articulos:
        nombre = medios.get(a.medio_id, "Desconocido")
        por_medio.setdefault(nombre, []).append({
            "id": a.id,
            "titulo": a.titulo,
            "url": a.url,
            "fecha_publicacion": _fmt_bol(a.fecha_publicacion),
            "analisis": a.analisis,
        })
    return {
        "id": evento.id,
        "titulo": evento.titulo,
        "fecha_deteccion": _fmt_utc(evento.fecha_deteccion),
        "score_importancia": evento.score_importancia,
        "temas": evento.temas,
        "articulos_por_medio": por_medio,
    }


@router.get("")
def listar_eventos(limit: int = 50, db: Session = Depends(get_db)):
    medios = _medios_dict(db)
    eventos = (
        db.query(Evento)
        .options(joinedload(Evento.articulos))
        .order_by(Evento.score_importancia.desc())
        .limit(limit)
        .all()
    )
    return [_serializar_evento(ev, medios) for ev in eventos]


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
    return _serializar_evento(ev, medios)
