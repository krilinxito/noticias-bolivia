from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import Articulo, Episodio, Medio, Tema

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


def _serializar_articulo(a, medios):
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


def _serializar_episodio(ep, medios, incluir_articulos=True):
    por_medio = {}
    if incluir_articulos:
        for a in ep.articulos:
            nombre = medios.get(a.medio_id, "Desconocido")
            por_medio.setdefault(nombre, []).append(_serializar_articulo(a, medios))

    imagen = ep.imagen_url or next(
        (a.imagen_url for a in ep.articulos if a.imagen_url), None
    ) if incluir_articulos else ep.imagen_url

    base = {
        "id": ep.id,
        "titulo": ep.titulo,
        "fecha_deteccion": _fmt_utc(ep.fecha_deteccion),
        "score_importancia": ep.score_importancia,
        "keywords": ep.keywords,
        "imagen_url": imagen,
        "tema_id": ep.tema_id,
    }
    if incluir_articulos:
        base["articulos_por_medio"] = por_medio
    else:
        base["medios"] = list(set(medios.get(a.medio_id, "?") for a in ep.articulos))
    return base


def _serializar_tema(tema, medios, incluir_episodios=False):
    todos_medios = set()
    for ep in tema.episodios:
        for a in ep.articulos:
            todos_medios.add(medios.get(a.medio_id, "Desconocido"))

    imagen = tema.imagen_url or next(
        (ep.imagen_url for ep in sorted(tema.episodios, key=lambda e: e.score_importancia, reverse=True) if ep.imagen_url),
        None,
    )

    base = {
        "id": tema.id,
        "titulo": tema.titulo,
        "fecha_deteccion": _fmt_utc(tema.fecha_deteccion),
        "score_importancia": tema.score_importancia,
        "keywords": tema.keywords,
        "imagen_url": imagen,
        "medios": sorted(todos_medios),
        "episodios_count": len(tema.episodios),
    }
    if incluir_episodios:
        base["episodios"] = [
            _serializar_episodio(ep, medios, incluir_articulos=True)
            for ep in sorted(tema.episodios, key=lambda e: e.score_importancia, reverse=True)
        ]
    return base


@router.get("")
def listar_temas(limit: int = 50, db: Session = Depends(get_db)):
    medios = _medios_dict(db)
    temas = (
        db.query(Tema)
        .options(
            joinedload(Tema.episodios).joinedload(Episodio.articulos)
        )
        .order_by(Tema.score_importancia.desc())
        .limit(limit)
        .all()
    )
    return [_serializar_tema(t, medios, incluir_episodios=False) for t in temas]


@router.get("/{tema_id}")
def obtener_tema(tema_id: int, db: Session = Depends(get_db)):
    medios = _medios_dict(db)
    tema = (
        db.query(Tema)
        .options(
            joinedload(Tema.episodios).joinedload(Episodio.articulos)
        )
        .filter(Tema.id == tema_id)
        .first()
    )
    if not tema:
        raise HTTPException(status_code=404, detail="Tema no encontrado")
    return _serializar_tema(tema, medios, incluir_episodios=True)
