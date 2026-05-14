from app.database import SessionLocal
from app.models import Medio

MEDIOS = [
    {"nombre": "Red Uno",        "url_rss": "https://www.reduno.com.bo/rss",       "region": "santa cruz",  "linea_editorial": "comercial"},
    {"nombre": "El Deber",       "url_rss": "https://eldeber.com.bo/feed",          "region": "santa cruz",  "linea_editorial": "liberal"},
    {"nombre": "Brújula Digital","url_rss": "https://brujuladigital.net/rss.xml",   "region": "nacional",    "linea_editorial": "independiente"},
    {"nombre": "Los Tiempos",    "url_rss": "https://www.lostiempos.com/rss.xml",   "region": "cochabamba",  "linea_editorial": "liberal"},
    {"nombre": "Erbol",          "url_rss": "https://erbol.com.bo/rss.xml",         "region": "nacional",    "linea_editorial": "comunitario"},
    {"nombre": "La Razón",       "url_rss": "https://www.la-razon.com/rss",         "region": "nacional",    "linea_editorial": "tradicional"},
]

with SessionLocal() as db:
    for data in MEDIOS:
        existe = db.query(Medio).filter(Medio.nombre == data["nombre"]).first()
        if not existe:
            db.add(Medio(**data))
    db.commit()
    print(f"Seed completo: {db.query(Medio).count()} medios en BD")
