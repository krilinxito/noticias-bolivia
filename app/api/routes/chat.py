import json
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from google.genai import types
from loguru import logger

from app.analysis.gemini import _get_client, MODEL_FLASH
from app.database import SessionLocal
from app.models import Articulo, Evento, Medio

router = APIRouter()

SYSTEM_PROMPT = """Eres un analista de medios bolivianos. Tu función es responder preguntas
sobre cobertura noticiosa, sesgo editorial y tendencias en los 6 medios que monitoreamos:
Red Uno, El Deber, Brújula Digital, Los Tiempos, Erbol, La Razón.

Reglas:
- Usa SIEMPRE las herramientas antes de responder — nunca respondas solo con conocimiento previo.
- Para preguntas sobre un tema concreto (política, economía, deportes, etc.) usa buscar_noticias
  con palabras clave relevantes para obtener el contenido real de los artículos.
- Para comparar cómo distintos medios cubrieron un evento, primero usa get_eventos para encontrar
  el ID del evento y luego comparar_cobertura con ese ID.
- Si una búsqueda devuelve pocos resultados, intenta con términos más cortos o sinónimos.
- Cita los medios y títulos concretos que sustenten tu respuesta.
- Sé conciso, específico y responde siempre en español."""

TOOLS = types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="buscar_noticias",
        description="Busca artículos por texto en título, cuerpo y resumen. Filtra opcionalmente por nombre de medio.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "query": types.Schema(type="STRING", description="Texto a buscar"),
                "medio": types.Schema(type="STRING", description="Nombre del medio (opcional)"),
                "limit": types.Schema(type="INTEGER", description="Máximo de resultados (default 5)"),
            },
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_eventos",
        description="Lista eventos noticiosos ordenados por importancia (qué tan cubiertos por múltiples medios).",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "min_importancia": types.Schema(type="NUMBER", description="Score mínimo 0.0-1.0 (default 0.0)"),
                "limit": types.Schema(type="INTEGER", description="Máximo de resultados (default 10)"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="comparar_cobertura",
        description="Compara cómo distintos medios cubrieron el mismo evento: tono y sesgo por medio.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "evento_id": types.Schema(type="INTEGER", description="ID del evento a comparar"),
            },
            required=["evento_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="resumen_estadisticas",
        description="Estadísticas generales: total artículos, distribución por medio, eventos detectados.",
        parameters=types.Schema(type="OBJECT", properties={}),
    ),
])


def get_db():
    with SessionLocal() as db:
        yield db


def _buscar_noticias(db: Session, query: str, medio: str = None, limit: int = 5) -> str:
    terms = [t for t in query.split() if len(t) > 2]
    if not terms:
        terms = query.split()

    term_filters = [
        or_(
            Articulo.titulo.ilike(f"%{t}%"),
            Articulo.cuerpo.ilike(f"%{t}%"),
            Articulo.resumen_rss.ilike(f"%{t}%"),
        )
        for t in terms
    ]
    q = db.query(Articulo).filter(or_(*term_filters))

    if medio:
        m = db.query(Medio).filter(Medio.nombre.ilike(f"%{medio}%")).first()
        if m:
            q = q.filter(Articulo.medio_id == m.id)

    arts = q.order_by(Articulo.fecha_publicacion.desc()).limit(limit).all()
    if not arts:
        return "No se encontraron artículos para esa búsqueda."

    resultados = []
    for a in arts:
        m = db.query(Medio).filter(Medio.id == a.medio_id).first()
        tono = (a.analisis or {}).get("tono", "sin análisis")
        extracto = ""
        if a.cuerpo:
            extracto = a.cuerpo[:300].replace("\n", " ").strip()
        elif a.resumen_rss:
            extracto = a.resumen_rss[:300].replace("\n", " ").strip()
        fecha = a.fecha_publicacion.strftime("%d/%m/%Y") if a.fecha_publicacion else "?"
        resultados.append(
            f"[{m.nombre if m else '?'}] {fecha} — {a.titulo} (tono: {tono})\n"
            f"  {extracto}"
        )
    return "\n\n".join(resultados)


def _get_eventos(db: Session, min_importancia: float = 0.0, limit: int = 10) -> str:
    eventos = (
        db.query(Evento)
        .filter(Evento.score_importancia >= min_importancia)
        .order_by(Evento.score_importancia.desc())
        .limit(limit)
        .all()
    )
    if not eventos:
        return "No hay eventos que cumplan los criterios."
    resultados = []
    for ev in eventos:
        arts = db.query(Articulo).filter(Articulo.evento_id == ev.id).all()
        medios_nombres = list({
            db.query(Medio).filter(Medio.id == a.medio_id).first().nombre
            for a in arts
            if db.query(Medio).filter(Medio.id == a.medio_id).first()
        })
        temas = ", ".join(ev.temas or []) or "sin temas"
        resultados.append(
            f"- ID {ev.id} | importancia {ev.score_importancia:.2f} | {ev.titulo[:60]}\n"
            f"  Medios: {', '.join(medios_nombres)} | Temas: {temas}"
        )
    return "\n".join(resultados)


def _comparar_cobertura(db: Session, evento_id: int) -> str:
    ev = db.query(Evento).filter(Evento.id == evento_id).first()
    if not ev:
        return f"Evento {evento_id} no encontrado."
    arts = db.query(Articulo).filter(Articulo.evento_id == evento_id).all()
    if not arts:
        return "El evento no tiene artículos asociados."
    resultados = [f"Evento: {ev.titulo}\n"]
    for a in arts:
        m = db.query(Medio).filter(Medio.id == a.medio_id).first()
        analisis = a.analisis or {}
        tono = analisis.get("tono", "sin análisis")
        sesgo = analisis.get("sesgo")
        sesgo_str = f"{sesgo:+.2f}" if sesgo is not None else "no calculado"
        desc = analisis.get("sesgo_descripcion", "")[:100]
        resultados.append(
            f"- {m.nombre if m else '?'}: tono={tono}, sesgo={sesgo_str}\n"
            f"  {desc}"
        )
    resumen = (arts[0].analisis or {}).get("resumen_comparativo", "")
    if resumen:
        resultados.append(f"\nResumen comparativo: {resumen}")
    return "\n".join(resultados)


def _resumen_estadisticas(db: Session) -> str:
    total = db.query(func.count(Articulo.id)).scalar()
    con_analisis = db.query(func.count(Articulo.id)).filter(Articulo.analisis != None).scalar()
    total_eventos = db.query(func.count(Evento.id)).scalar()
    medios = db.query(Medio).all()
    dist = []
    for m in medios:
        n = db.query(func.count(Articulo.id)).filter(Articulo.medio_id == m.id).scalar()
        dist.append(f"  {m.nombre}: {n} artículos")
    return (
        f"Total artículos: {total} ({con_analisis} con análisis, {total - con_analisis} sin)\n"
        f"Eventos detectados: {total_eventos}\n"
        f"Distribución por medio:\n" + "\n".join(dist)
    )


TOOL_HANDLERS = {
    "buscar_noticias": lambda db, args: _buscar_noticias(db, **args),
    "get_eventos": lambda db, args: _get_eventos(db, **args),
    "comparar_cobertura": lambda db, args: _comparar_cobertura(db, **args),
    "resumen_estadisticas": lambda db, args: _resumen_estadisticas(db),
}


class Mensaje(BaseModel):
    rol: str
    texto: str


class ChatRequest(BaseModel):
    mensaje: str
    historial: List[Mensaje] = []


@router.post("")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    client = _get_client()

    contents = []
    for h in req.historial:
        role = "model" if h.rol == "asistente" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=h.texto)]))
    contents.append(types.Content(role="user", parts=[types.Part(text=req.mensaje)]))

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[TOOLS],
        temperature=0.2,
    )

    tools_usadas = []
    MAX_ROUNDS = 3

    for _ in range(MAX_ROUNDS):
        response = client.models.generate_content(
            model=MODEL_FLASH,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0].content
        function_calls = [p for p in candidate.parts if p.function_call]

        if not function_calls:
            break

        contents.append(candidate)

        function_parts = []
        for p in function_calls:
            fc = p.function_call
            nombre = fc.name
            args = dict(fc.args) if fc.args else {}
            logger.info(f"Chat tool call: {nombre}({args})")
            tools_usadas.append(nombre)

            try:
                resultado = TOOL_HANDLERS[nombre](db, args)
            except Exception as e:
                resultado = f"Error ejecutando {nombre}: {e}"

            function_parts.append(types.Part(
                function_response=types.FunctionResponse(
                    name=nombre,
                    response={"result": resultado},
                )
            ))

        contents.append(types.Content(role="user", parts=function_parts))

    respuesta = response.text or "No pude generar una respuesta."
    return {"respuesta": respuesta, "tools_usadas": tools_usadas}
