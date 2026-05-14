from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import SessionLocal
from app.models import Articulo, Medio

router = APIRouter()


def get_db():
    with SessionLocal() as db:
        yield db


@router.get("")
def listar_medios(db: Session = Depends(get_db)):
    medios = db.query(Medio).filter(Medio.activo == True).all()
    resultado = []
    for m in medios:
        total = db.query(func.count(Articulo.id)).filter(Articulo.medio_id == m.id).scalar()
        resultado.append({
            "id": m.id,
            "nombre": m.nombre,
            "url_rss": m.url_rss,
            "linea_editorial": m.linea_editorial,
            "region": m.region,
            "total_articulos": total,
        })
    return resultado
