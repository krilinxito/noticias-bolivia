from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Articulo, Medio

router = APIRouter()


def _fmt_utc(dt):
    return dt.isoformat() + 'Z' if dt else None


def _fmt_bol(dt):
    return dt.isoformat() + '-04:00' if dt else None


def get_db():
    with SessionLocal() as db:
        yield db


@router.get("")
def listar_noticias(
    limit: int = 20,
    offset: int = 0,
    medio_id: Optional[int] = None,
    medio_nombre: Optional[str] = None,
    evento_id: Optional[int] = None,
    orden: str = "scraping",
    db: Session = Depends(get_db),
):
    medios_map = {m.id: m for m in db.query(Medio).all()}

    q = db.query(Articulo)
    if medio_id is not None:
        q = q.filter(Articulo.medio_id == medio_id)
    if medio_nombre is not None:
        ids = [m.id for m in medios_map.values() if m.nombre == medio_nombre]
        q = q.filter(Articulo.medio_id.in_(ids))
    if evento_id is not None:
        q = q.filter(Articulo.evento_id == evento_id)
    if orden == "fecha":
        q = q.filter(Articulo.fecha_publicacion.isnot(None)).order_by(Articulo.fecha_publicacion.desc())
    else:
        q = q.order_by(Articulo.fecha_scraping.desc())

    articulos = q.offset(offset).limit(limit).all()
    return [
        {
            "id": a.id,
            "titulo": a.titulo,
            "url": a.url,
            "fecha_publicacion": _fmt_bol(a.fecha_publicacion),
            "medio": {"id": m.id, "nombre": m.nombre} if (m := medios_map.get(a.medio_id)) else None,
            "analisis": a.analisis,
        }
        for a in articulos
    ]


@router.get("/{articulo_id}")
def obtener_noticia(articulo_id: int, db: Session = Depends(get_db)):
    a = db.query(Articulo).filter(Articulo.id == articulo_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    medio = db.query(Medio).filter(Medio.id == a.medio_id).first()
    return {
        "id": a.id,
        "titulo": a.titulo,
        "url": a.url,
        "resumen_rss": a.resumen_rss,
        "cuerpo": a.cuerpo,
        "fecha_publicacion": _fmt_bol(a.fecha_publicacion),
        "fecha_scraping": _fmt_utc(a.fecha_scraping),
        "medio": {"id": medio.id, "nombre": medio.nombre, "linea_editorial": medio.linea_editorial} if medio else None,
        "analisis": a.analisis,
    }
