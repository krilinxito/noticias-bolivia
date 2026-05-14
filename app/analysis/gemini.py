import json
import time

from google import genai
from google.genai import types
from loguru import logger

from app.config import GEMINI_API_KEY
from app.analysis.embeddings import get_texto_analizable
from app.models import Articulo, Evento, Medio

_client = None

MODEL_LITE = "gemini-2.5-flash-lite"
MODEL_FLASH = "gemini-2.5-flash"


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _parsear_json(texto):
    try:
        raw = texto.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        return json.loads(raw)
    except Exception:
        return {"error": "parse_failed"}


def _generar(modelo, prompt):
    response = _get_client().models.generate_content(
        model=modelo,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
        ),
    )
    return response.text


def analizar_articulo(articulo, db):
    if articulo.analisis:
        return

    texto = get_texto_analizable(articulo)
    if texto is None:
        articulo.analisis = {"tono": "sin_texto", "temas": [], "fuentes_citadas": []}
        db.add(articulo)
        db.commit()
        return

    prompt = f"""Analiza este artículo de noticias boliviano.
Responde ÚNICAMENTE con JSON válido, sin texto adicional ni markdown.
Formato exacto:
{{"tono": "positivo|negativo|neutral", "temas": ["tema1", "tema2"], "fuentes_citadas": ["gobierno", "oposición", "expertos", "anónimas"]}}
Artículo: {articulo.titulo}. {texto[:1500]}"""

    try:
        resultado = _parsear_json(_generar(MODEL_LITE, prompt))
    except Exception as e:
        logger.error(f"Error Gemini artículo {articulo.id}: {e}")
        resultado = {"error": str(e)[:200]}

    articulo.analisis = resultado
    db.add(articulo)
    db.commit()
    time.sleep(4)


def analizar_sesgo_evento(evento_id, db):
    evento = db.query(Evento).filter(Evento.id == evento_id).first()
    if not evento:
        return

    articulos = db.query(Articulo).filter(Articulo.evento_id == evento_id).all()

    por_medio = {}
    for art in articulos:
        texto = get_texto_analizable(art)
        if texto:
            medio = db.query(Medio).filter(Medio.id == art.medio_id).first()
            if medio:
                por_medio[medio.nombre] = (art, texto)

    if len(por_medio) < 2:
        logger.info(f"Evento {evento_id}: menos de 2 medios con texto, skip sesgo")
        return

    bloques = [
        f"Medio: {nombre}\nTítulo: {art.titulo}\nTexto: {texto[:800]}\n---"
        for nombre, (art, texto) in por_medio.items()
    ]
    texto_comparativo = "\n".join(bloques)

    prompt = f"""Compara cómo estos medios bolivianos cubren el mismo evento.
Responde ÚNICAMENTE con JSON válido, sin texto adicional ni markdown.
Formato exacto:
{{"sesgo_por_medio": {{"nombre_medio": {{"sesgo": 0.0, "descripcion": "..."}}}}, "resumen_comparativo": "texto breve"}}
Donde sesgo va de -1.0 (muy negativo) a 1.0 (muy positivo).
{texto_comparativo}"""

    try:
        resultado = _parsear_json(_generar(MODEL_FLASH, prompt))
    except Exception as e:
        logger.error(f"Error Gemini sesgo evento {evento_id}: {e}")
        return

    sesgo_por_medio = resultado.get("sesgo_por_medio", {})
    for nombre, (art, _) in por_medio.items():
        datos_sesgo = sesgo_por_medio.get(nombre, {})
        analisis_actual = art.analisis or {}
        analisis_actual["sesgo"] = datos_sesgo.get("sesgo")
        analisis_actual["sesgo_descripcion"] = datos_sesgo.get("descripcion")
        analisis_actual["resumen_comparativo"] = resultado.get("resumen_comparativo")
        art.analisis = analisis_actual
        db.add(art)

    db.commit()
    logger.info(f"Sesgo analizado evento {evento_id}: {len(por_medio)} medios")
    time.sleep(4)
