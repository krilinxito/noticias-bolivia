import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from loguru import logger

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "es-ES,es;q=0.9",
}

SELECTORES = [
    "article",
    "[class*='article-body']",
    "[class*='article_body']",
    "[class*='content-body']",
    "[class*='nota-body']",
    "[class*='cuerpo']",
    ".entry-content",
    "main",
]

RUIDO = ["script", "style", "nav", "footer", "aside", "[class*='ad']"]


def _parse_fecha(s: str) -> datetime | None:
    if not s:
        return None
    s = s.strip()[:19]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def _extraer_fecha(soup) -> datetime | None:
    # 1. OpenGraph
    meta = soup.find("meta", property="article:published_time")
    if meta and meta.get("content"):
        f = _parse_fecha(meta["content"])
        if f:
            return f

    # 2. JSON-LD NewsArticle
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = data[0]
            fecha_str = data.get("datePublished") or data.get("dateCreated")
            if fecha_str:
                f = _parse_fecha(fecha_str)
                if f:
                    return f
        except Exception:
            pass

    # 3. <time datetime>
    time_tag = soup.find("time", attrs={"datetime": True})
    if time_tag:
        return _parse_fecha(time_tag["datetime"])

    return None


def scrape_articulo(url) -> dict:
    """Retorna {cuerpo: str|None, fecha_publicacion: datetime|None}"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        logger.warning(f"Error HTTP {url}: {e}")
        return {"cuerpo": None, "fecha_publicacion": None}

    try:
        soup = BeautifulSoup(r.text, "lxml")
        fecha = _extraer_fecha(soup)

        for selector in RUIDO:
            for tag in soup.select(selector):
                tag.decompose()

        cuerpo = None
        for selector in SELECTORES:
            elemento = soup.select_one(selector)
            if elemento:
                texto = elemento.get_text(separator=" ", strip=True)
                if len(texto) >= 200:
                    cuerpo = texto
                    break

        return {"cuerpo": cuerpo, "fecha_publicacion": fecha}

    except Exception as e:
        logger.warning(f"Error parsing {url}: {e}")
        return {"cuerpo": None, "fecha_publicacion": None}


def scrape_cuerpo(url) -> str | None:
    return scrape_articulo(url)["cuerpo"]
