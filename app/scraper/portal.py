import re
import time

import requests
from bs4 import BeautifulSoup
from loguru import logger

from app.models import Articulo

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
}

CONFIGS = {
    "Erbol": {
        "listing_url": "https://erbol.com.bo",
        "base_url": "https://erbol.com.bo",
        # Permite URL encoding (%C3%B3, etc.) en sección y slug
        "url_pattern": r"^/[^/\s]+/[^/\s]{10,}$",
        "exclude_fragments": ["/tags/", "/user/", "/rss", "/search"],
    },
    "Red Uno": {
        "listing_url": "https://www.reduno.com.bo/noticias",
        "base_url": "https://www.reduno.com.bo",
        "url_pattern": r"^/(noticias|deportes|politica|economia|internacional|comunidad|policial|uno-decide)/\S+\d{6,}",
        "exclude_fragments": [],
    },
    "Los Tiempos": {
        "listing_url": "https://www.lostiempos.com",
        "base_url": "https://www.lostiempos.com",
        "url_pattern": r"/\d{8}/",
        "exclude_fragments": [],
    },
    # La Razón usa RSS porque su sitio es un SPA (renderiza con JavaScript)
    # "La Razón": { ... },
    "El Deber": {
        "listing_url": "https://eldeber.com.bo",
        "base_url": "https://eldeber.com.bo",
        "url_pattern": r"^/[a-z\-]+/[a-z0-9\-]{10,}_",
        "exclude_fragments": ["/tag/", "/autor/", "/seccion/"],
    },
    "Brújula Digital": {
        "listing_url": "https://brujuladigital.net",
        "base_url": "https://brujuladigital.net",
        # Noticias: /seccion/YYYY/MM/DD/slug  |  Opinión: /opinion/slug
        "url_pattern": r"^/[a-z\-]+/(\d{4}/\d{2}/\d{2}/.+|[a-z0-9\-]{10,})",
        "exclude_fragments": ["/tag/", "/autor/", "/categoria/"],
    },
}


def _fetch(url, reintentos=3):
    for i in range(reintentos):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                return r.text
            logger.warning(f"HTTP {r.status_code} en {url}")
        except Exception as e:
            logger.warning(f"Intento {i + 1} fallido para {url}: {e}")
        if i < reintentos - 1:
            time.sleep(2 ** i)
    return None


def scrape_portal(medio, db) -> int:
    config = CONFIGS.get(medio.nombre)
    if not config:
        logger.warning(f"{medio.nombre}: sin config de portal, saltando")
        return 0

    html = _fetch(config["listing_url"])
    if not html:
        logger.error(f"{medio.nombre}: no se pudo obtener la portada")
        return 0

    soup = BeautifulSoup(html, "lxml")
    candidatos: dict[str, str] = {}

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip().split("?")[0].rstrip("/")
        if not href:
            continue

        # Normalizar a URL absoluta
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = config["base_url"] + href
        elif not href.startswith("http"):
            continue

        # Solo URLs del mismo dominio
        if not href.startswith(config["base_url"]):
            continue

        path = href[len(config["base_url"]):]

        if not re.search(config["url_pattern"], path):
            continue
        if any(ex in path for ex in config["exclude_fragments"]):
            continue

        titulo = tag.get_text(strip=True)
        # Si el link ya está pero con título vacío, preferir el que tiene texto
        if href not in candidatos or len(titulo) > len(candidatos[href]):
            candidatos[href] = titulo[:250] if titulo else ""

    # Filtrar titulos vacíos o muy cortos (links de iconos/imágenes)
    candidatos = {url: t for url, t in candidatos.items() if len(t) >= 10}

    # Limitar a las primeras 20 URLs nuevas por medio por ciclo
    MAX_POR_MEDIO = 20

    nuevos = 0
    for url, titulo in list(candidatos.items())[:MAX_POR_MEDIO * 3]:
        if nuevos >= MAX_POR_MEDIO:
            break
        if db.query(Articulo).filter(Articulo.url == url).first():
            continue
        art = Articulo(medio_id=medio.id, url=url, titulo=titulo)
        db.add(art)
        nuevos += 1

    if nuevos:
        db.commit()

    logger.info(f"{medio.nombre}: {nuevos} artículos nuevos ({len(candidatos)} candidatos encontrados)")
    return nuevos
