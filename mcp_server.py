from mcp.server.fastmcp import FastMCP
from sqlalchemy import or_, func

from app.database import SessionLocal
from app.models import Articulo, Evento, Medio

mcp = FastMCP("noticias-bolivia")


@mcp.tool()
def buscar_noticias(query: str, medio: str = None, limit: int = 5) -> str:
    """Busca artículos bolivianos por texto. Filtra opcionalmente por nombre de medio."""
    with SessionLocal() as db:
        q = db.query(Articulo)
        for term in query.split():
            q = q.filter(or_(
                Articulo.titulo.ilike(f"%{term}%"),
                Articulo.cuerpo.ilike(f"%{term}%"),
                Articulo.resumen_rss.ilike(f"%{term}%"),
            ))
        if medio:
            m = db.query(Medio).filter(Medio.nombre.ilike(f"%{medio}%")).first()
            if m:
                q = q.filter(Articulo.medio_id == m.id)
        arts = q.limit(limit).all()
        if not arts:
            return "No se encontraron artículos."
        lineas = []
        for a in arts:
            m = db.query(Medio).filter(Medio.id == a.medio_id).first()
            tono = (a.analisis or {}).get("tono", "sin análisis")
            lineas.append(f"[{m.nombre if m else '?'}] {a.titulo} | tono: {tono} | {a.url}")
        return "\n".join(lineas)


@mcp.tool()
def get_eventos(min_importancia: float = 0.0, limit: int = 10) -> str:
    """Lista eventos noticiosos ordenados por importancia (cobertura multi-medio)."""
    with SessionLocal() as db:
        eventos = (
            db.query(Evento)
            .filter(Evento.score_importancia >= min_importancia)
            .order_by(Evento.score_importancia.desc())
            .limit(limit)
            .all()
        )
        if not eventos:
            return "No hay eventos."
        lineas = []
        for ev in eventos:
            arts = db.query(Articulo).filter(Articulo.evento_id == ev.id).all()
            medios_ids = {a.medio_id for a in arts}
            medios_nombres = []
            for mid in medios_ids:
                m = db.query(Medio).filter(Medio.id == mid).first()
                if m:
                    medios_nombres.append(m.nombre)
            keywords = ", ".join(ev.keywords or []) or "—"
            lineas.append(
                f"ID {ev.id} | importancia {ev.score_importancia:.2f} | {ev.titulo[:70]}\n"
                f"  Medios: {', '.join(medios_nombres)} | Keywords: {keywords}"
            )
        return "\n\n".join(lineas)


@mcp.tool()
def comparar_cobertura(evento_id: int) -> str:
    """Compara cómo distintos medios cubrieron un evento: tono y sesgo editorial."""
    with SessionLocal() as db:
        ev = db.query(Evento).filter(Evento.id == evento_id).first()
        if not ev:
            return f"Evento {evento_id} no encontrado."
        arts = db.query(Articulo).filter(Articulo.evento_id == evento_id).all()
        lineas = [f"Evento: {ev.titulo}\n"]
        for a in arts:
            m = db.query(Medio).filter(Medio.id == a.medio_id).first()
            analisis = a.analisis or {}
            tono = analisis.get("tono", "sin análisis")
            sesgo = analisis.get("sesgo")
            sesgo_str = f"{sesgo:+.2f}" if sesgo is not None else "no calculado"
            desc = analisis.get("sesgo_descripcion", "")
            lineas.append(f"{m.nombre if m else '?'}: tono={tono}, sesgo={sesgo_str}\n  {desc[:120]}")
        resumen = (arts[0].analisis or {}).get("resumen_comparativo", "") if arts else ""
        if resumen:
            lineas.append(f"\nResumen: {resumen}")
        return "\n".join(lineas)


@mcp.tool()
def resumen_estadisticas() -> str:
    """Estadísticas generales: artículos, análisis completados, eventos detectados."""
    with SessionLocal() as db:
        total = db.query(func.count(Articulo.id)).scalar()
        con_analisis = db.query(func.count(Articulo.id)).filter(Articulo.analisis != None).scalar()
        total_eventos = db.query(func.count(Evento.id)).scalar()
        medios = db.query(Medio).all()
        dist = []
        for m in medios:
            n = db.query(func.count(Articulo.id)).filter(Articulo.medio_id == m.id).scalar()
            dist.append(f"  {m.nombre}: {n}")
        return (
            f"Total artículos: {total} ({con_analisis} analizados)\n"
            f"Eventos detectados: {total_eventos}\n"
            f"Por medio:\n" + "\n".join(dist)
        )


if __name__ == "__main__":
    mcp.run()
