# El Observador Digital

Plataforma de minería de datos que monitorea 6 medios digitales bolivianos, agrupa las noticias en
**eventos** por similitud semántica y mide el **sesgo editorial** comparando cómo cubre cada medio el
mismo hecho.

La pregunta que responde: *cuando dos periódicos cuentan la misma noticia, ¿en qué se diferencian?*

Medios cubiertos: Red Uno · El Deber · Brújula Digital · Los Tiempos · Erbol · La Razón.

---

## El pipeline

```
6 medios  (5 por scraping de portada + La Razón por RSS)
    │
    ▼
[portal.py / rss.py] ──► [article.py]  cuerpo, fecha e imagen ──────────► BD · articulos
    │
    ▼
[embeddings.py]
    ├─ embeddings MiniLM multilingüe
    ├─ similitud coseno > 0.65  ──►  Union-Find  ──►  clusters
    ├─ filtro: solo clusters con 2+ medios distintos se vuelven evento
    └─ KeyBERT extrae las keywords del evento ─────────────────────────► BD · eventos
    │
    ▼
[gemini.py]
    ├─ analizar_articulo()      tono, temas y fuentes citadas
    └─ analizar_sesgo_evento()  sesgo en [-1, +1] + resumen comparativo
    │                                                                    ► BD · articulos.analisis
    ▼
[FastAPI]  /noticias  /eventos  /sesgos  /medios  /temas  /stats  /chat
    │
    ▼
[Astro SSR + islas React]  portada · eventos · sesgos · cronología · medios
```

**Por qué Union-Find:** la similitud coseno es una relación por pares, pero un evento es un grupo. Si
A≈B y B≈C, los tres son el mismo hecho aunque A y C no se parezcan directamente. Union-Find resuelve
esa transitividad en una pasada, sin necesidad de un algoritmo de clustering con número de grupos fijo.

**Por qué el filtro de 2+ medios:** un artículo que solo publicó un medio no permite comparar nada. El
sesgo únicamente existe como diferencia entre coberturas.

---

## Stack

| Capa | Tecnología | Por qué |
|---|---|---|
| API | FastAPI + Pydantic | Async, validación y Swagger automático |
| BD | PostgreSQL (Supabase) | Relacional + columnas JSON nativas para el análisis |
| Migraciones | SQLAlchemy + Alembic | Esquema versionado |
| Scraping | BeautifulSoup4 + lxml + feedparser | Tolerante a HTML mal formado |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` | 120 MB, corre en CPU, bueno en español |
| Keywords | KeyBERT | Semántica, sin fine-tuning |
| LLM | Gemini 2.0-flash-lite / 2.5-flash | Lite para tono (alta frecuencia), flash para sesgo (requiere comprensión) |
| Scheduler | APScheduler | Cron in-process, sin infraestructura extra |
| Frontend | Astro SSR + React + Tailwind v4 | Islas interactivas sobre HTML servido |
| Deploy | Docker Compose | Backend y frontend en un VPS |

Dos jobs diarios: scraping a las 10:00 UTC, agrupación y análisis a las 11:00 UTC.

---

## Límites de la API

El endpoint `/chat` llama a Gemini con *function calling*, así que una sola pregunta puede
disparar varias rondas contra el modelo. Para que una API pública no agote la cuota:

- **CORS acotado** a `CORS_ORIGINS` en vez de `*`, para que no lo puedan embeber desde otra web.
- **Límite por IP** en `/chat`: `CHAT_LIMITE` peticiones por `CHAT_VENTANA_SEG` segundos.
  Es un contador en memoria, suficiente para un despliegue de un solo contenedor; con varias
  réplicas cada proceso llevaría su propia cuenta y habría que moverlo a Redis.

Conviene además fijar una cuota diaria sobre la propia API key en Google AI Studio: es el
único techo que sigue valiendo aunque todo lo demás falle.

## Cómo correrlo

```bash
conda create -n noticias-bolivia python=3.11 && conda activate noticias-bolivia
pip install -r requirements.txt

cp .env.example .env        # DATABASE_URL, GEMINI_API_KEY, PUBLIC_API_URL
alembic upgrade head        # crear tablas
python seed.py              # cargar los 6 medios

uvicorn app.api.main:app --reload      # API en :8000, Swagger en /docs
cd frontend && npm install && npm run dev   # front en :4321
```

El scheduler arranca junto con la API. Para disparar el análisis a mano:

```bash
python -c "from app.scheduler import job_analisis; job_analisis()"
```

---

## Estructura

```
app/
├── scraper/      portal.py · rss.py · article.py
├── analysis/     embeddings.py (agrupación) · gemini.py (tono y sesgo)
├── api/routes/   noticias · eventos · sesgos · medios · temas · stats · chat
├── models.py     medios · eventos · articulos
└── scheduler.py  los dos jobs diarios
frontend/         Astro SSR + componentes React
alembic/          migraciones
```

Documentación técnica completa —esquema de BD, estrategia de scraping por medio, manejo de zonas
horarias y formato del campo `analisis`— en [`CLAUDE.md`](CLAUDE.md).
