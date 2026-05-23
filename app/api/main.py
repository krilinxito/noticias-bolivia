from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.scheduler import iniciar_scheduler, detener_scheduler
from app.api.routes import noticias, medios, chat, sesgos, stats, eventos


@asynccontextmanager
async def lifespan(app: FastAPI):
    iniciar_scheduler()
    yield
    detener_scheduler()


app = FastAPI(
    title="Noticias Bolivia API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(noticias.router, prefix="/noticias", tags=["noticias"])
app.include_router(medios.router, prefix="/medios", tags=["medios"])
app.include_router(eventos.router, prefix="/eventos", tags=["eventos"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(sesgos.router, prefix="/sesgos", tags=["sesgos"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])


@app.get("/", tags=["estado"])
def root():
    return {"status": "ok", "fecha": datetime.now()}
