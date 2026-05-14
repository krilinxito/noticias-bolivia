# Noticias Bolivia — El Observador Digital

## Descripción

Plataforma de minería de datos que monitorea 6 medios bolivianos, agrupa noticias en eventos por similitud semántica y detecta sesgo editorial comparando la cobertura entre medios. Interfaz web estilo periódico con 5 vistas + chat con IA.

Medios cubiertos: Red Uno, El Deber, Brújula Digital, Los Tiempos, Erbol, La Razón.

---

## Pipeline completo

```
5 medios (portal scraping) + La Razón (RSS)
        │
        ▼
[portal.py / rss.py] ──► [article.py] ── cuerpo + fecha_publicacion ──► BD (articulos)
        │
        ▼
[embeddings.py] ── MiniLM embeddings → cosine sim > 0.65 → Union-Find
               └── KeyBERT keywords ──────────────────────────────────► BD (eventos)
        │
        ▼
[gemini.py]
  ├─ analizar_articulo()     ── flash-lite → {tono, temas, fuentes} (20/ciclo)
  └─ analizar_sesgo_evento() ── flash     → {sesgo[-1,+1], resumen} (3/ciclo)
        │                                                      ▼
        └─────────────────────────────────────────────── BD (articulos.analisis JSON)
        │
        ▼
[FastAPI] → /noticias  /medios  /eventos  /sesgos  /chat
        │
        ▼
[Astro SSR + Node] → /  /eventos  /sesgos  /timeline  /serie
```

**Scheduler (APScheduler in-process)**:
- Cada 30 min: scraping (`job_scraping`)
- Cada 60 min: agrupación + tono + sesgo (`job_analisis`)

---

## Stack técnico

| Tecnología | Versión | Motivo |
|---|---|---|
| Python | 3.11 | Type hints modernos, asyncio |
| FastAPI | latest | Async, Swagger automático, Pydantic |
| SQLAlchemy + Alembic | latest | ORM + migraciones versionadas |
| PostgreSQL (Supabase) | 15 | Datos relacionales + JSON nativo |
| feedparser | 6.x | RSS/Atom robusto |
| BeautifulSoup4 + lxml | latest | Scraping tolerante a HTML malformado |
| sentence-transformers | latest | Embeddings multilingües locales |
| paraphrase-multilingual-MiniLM-L12-v2 | — | 120MB, CPU-friendly, bueno en español |
| keybert | latest | Keywords semánticas sin fine-tuning |
| scikit-learn | latest | Similitud coseno |
| google-genai | latest | SDK Gemini (nuevo, reemplaza `google-generativeai`) |
| Gemini 2.5-flash-lite | — | Tono por artículo: rápido y barato |
| Gemini 2.5-flash | — | Comparación de sesgo entre medios |
| APScheduler | latest | Cron in-process |
| loguru | latest | Logging estructurado |
| Astro | 6.x | SSR con islas React, output:server |
| @astrojs/node | latest | Adapter standalone para producción |
| React + Tailwind CSS v4 | latest | UI interactiva (componentes de isla) |

---

## Estrategia de scraping por medio

| Medio | Estrategia | Notas |
|---|---|---|
| Red Uno | Portal (listing page) | Pattern: contiene dígitos ≥ 6 en path |
| El Deber | Portal (listing page) | Pattern: slug con `_` al final |
| Brújula Digital | Portal (listing page) | Slug ≥ 10 chars |
| Los Tiempos | Portal (listing page) | Pattern: path con 8 dígitos consecutivos |
| Erbol | Portal (listing page) | Pattern flexible, acepta chars URL-encoded |
| La Razón | RSS (fallback) | SPA de React, scraping directo imposible |

El scraping por portal funciona así: se descarga la página de listado, se extraen todos los `<a>`, se filtra por regex y se guardan solo las URLs nuevas (deduplicación por UNIQUE en BD). El cuerpo y fecha se obtienen después visitando cada artículo.

---

## Esquema de base de datos

### `medios`
| Campo | Tipo | Descripción |
|---|---|---|
| id | Integer PK | — |
| nombre | String | Nombre del medio |
| url_rss | String | URL del feed RSS |
| linea_editorial | String | `comercial`, `liberal`, `independiente`, `comunitario`, `tradicional` |
| region | String | `santa cruz`, `cochabamba`, `nacional` |
| activo | Boolean | Si se incluye en el scraping |

### `eventos`
| Campo | Tipo | Descripción |
|---|---|---|
| id | Integer PK | — |
| titulo | String | Título del artículo más representativo del cluster |
| fecha_deteccion | DateTime | Cuándo se creó el evento (UTC naive, `datetime.utcnow()`) |
| score_importancia | Float | `medios_distintos / 6` |
| temas | JSON | Keywords extraídas con KeyBERT |

### `articulos`
| Campo | Tipo | Descripción |
|---|---|---|
| id | Integer PK | — |
| medio_id | FK → medios | — |
| evento_id | FK → eventos | Null hasta que corra el agrupador |
| titulo | String | Título del artículo |
| url | String UNIQUE | URL original |
| resumen_rss | Text | Resumen del feed (puede ser null) |
| cuerpo | Text | Texto completo (puede ser null) |
| fecha_publicacion | DateTime | Fecha en hora Bolivia (UTC-4), naive |
| fecha_scraping | DateTime | Cuándo fue guardado (UTC naive) |
| analisis | JSON | Ver formato abajo |

### Campo `analisis` (JSON)

```json
{
  "tono": "positivo | negativo | neutral | sin_texto",
  "temas": ["política", "tierras"],
  "fuentes_citadas": ["gobierno", "oposición", "expertos", "anónimas"],
  "sesgo": -0.3,
  "sesgo_descripcion": "El medio enfatiza los aspectos negativos de la medida",
  "resumen_comparativo": "Brújula Digital cubre con más detalle que La Razón..."
}
```

`sesgo` y `sesgo_descripcion` solo aparecen cuando el artículo pertenece a un evento con 2+ medios distintos. `resumen_comparativo` es compartido entre todos los artículos del mismo evento.

### Timezone importante
- `fecha_deteccion` y `fecha_scraping` → UTC (`datetime.utcnow()`) → la API devuelve con sufijo `Z`
- `fecha_publicacion` → hora Bolivia UTC-4, scrapeada de los medios sin timezone → la API devuelve con sufijo `-04:00`
- El frontend usa `timeZone: 'America/La_Paz'` en todos los formateadores de fecha

---

## Variables de entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DATABASE_URL` | URL PostgreSQL (Session Pooler de Supabase recomendado) | `postgresql://postgres.xxx:pass@aws-0-us-east-1.pooler.supabase.com:5432/postgres` |
| `GEMINI_API_KEY` | API key de Google AI Studio (gratuita) | `AIzaSy...` |
| `PUBLIC_API_URL` | URL pública del backend (usada por frontend SSR y browser) | `https://api.tu-dominio.com` |

> Usar el **Session Pooler** de Supabase si la red no tiene IPv6.

---

## Cómo correr el proyecto

```bash
# 1. Crear entorno
conda create -n noticias-bolivia python=3.11
conda activate noticias-bolivia

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar credenciales
cp .env.example .env
# Editar .env con DATABASE_URL, GEMINI_API_KEY y PUBLIC_API_URL

# 4. Crear tablas en la BD
alembic upgrade head

# 5. Insertar medios iniciales
python seed.py

# 6. Levantar backend (scheduler arranca automáticamente)
uvicorn app.api.main:app --reload

# 7. Levantar frontend (otra terminal)
cd frontend
npm install
npm run dev
```

API disponible en http://localhost:8000 — Swagger en http://localhost:8000/docs
Frontend en http://localhost:4321

### Correr análisis manualmente

```bash
# Análisis completo (embeddings + tono + sesgo)
python -c "
from app.database import SessionLocal
from app.scheduler import job_analisis
job_analisis()
"

# Solo scraping
python test_scraper.py
```

### Con Docker Compose (para pruebas locales antes de Dokploy)

```bash
PUBLIC_API_URL=http://localhost:8000 docker compose up --build
```

---

## Despliegue en Dokploy (OVHcloud VPS)

Dos servicios en Dokploy:

| Servicio | Dockerfile | Puerto | Variables |
|---|---|---|---|
| backend | `Dockerfile.backend` | 8000 | `DATABASE_URL`, `GEMINI_API_KEY` |
| frontend | `Dockerfile.frontend` | 4321 | `PUBLIC_API_URL` (build arg + env var) |

Traefik gestiona SSL y enruta por dominio. `PUBLIC_API_URL` debe apuntar al dominio HTTPS del backend (lo usa tanto el SSR de Astro como el ChatWidget en el browser).

---

## Frontend — páginas

| Ruta | Descripción |
|---|---|
| `/` | Portada: evento destacado + secciones por categoría + chat IA |
| `/eventos` | Feed cronológico de todos los eventos (filtro por categoría) |
| `/eventos/[id]` | Detalle del evento: sesgómetro, cobertura por medio, extractos |
| `/sesgos` | Divergencia editorial: ranking de eventos con mayor diferencia de cobertura |
| `/timeline` | Artículos raw ordenados por fecha + distribución de categorías |
| `/serie` | Serie temporal: beeswarm de eventos + densidad diaria de artículos |
| `/medios` | Información de los 6 medios monitoreados |

### Categorías detectadas automáticamente

Sin cambios en la BD — se infieren en el frontend a partir de los `temas` del evento o del título del artículo (`frontend/src/lib/categorias.ts`):

| Categoría | Color |
|---|---|
| Política | `#8b1a1a` (rojo editorial) |
| Economía | `#1a3a6a` (azul oscuro) |
| Deportes | `#1a4a1a` (verde oscuro) |
| Sociedad | `#6a3a1a` (marrón) |
| Internacional | `#4a1a6a` (púrpura) |
| Cultura | `#6a4a1a` (ocre) |
| General | `#5a4a32` (tinta estándar) |

---

## Capas de análisis

| Capa | Qué mide | Cómo |
|---|---|---|
| **Cobertura** | Qué medios publicaron sobre el evento | Agrupación por `evento_id` |
| **Importancia** | Cuán relevante es el evento | `score = medios_distintos / 6` |
| **Temas** | Palabras clave del evento | KeyBERT sobre texto combinado del cluster |
| **Tono** | Postura del medio ante la noticia | Gemini flash-lite: positivo / negativo / neutral |
| **Sesgo** | Diferencia de enfoque entre medios | Gemini flash: escala -1.0 a +1.0 |

---

## Decisiones de diseño

**Scraping híbrido**: Los RSS bolivianos tienen hasta 2-3 semanas de retraso. Se usa scraping directo del portal para 5 medios. La Razón es una SPA de React — imposible scraping directo, se mantiene en RSS.

**Embeddings locales + Gemini solo para editorial**: MiniLM corre en CPU gratis. Gemini se reserva para lo que requiere comprensión profunda: tono y comparación de sesgo.

**Umbral de similitud 0.65**: Calibrado empíricamente. Con 0.75 había muy pocos agrupamientos cross-media; con 0.65 se capturan eventos compartidos sin agrupar artículos no relacionados.

**PostgreSQL + JSON**: Un solo servicio (Supabase), queries SQL sobre campos relacionales con flexibilidad JSON para `analisis` que varía según el estado del procesamiento.

**APScheduler in-process**: Para un proyecto monolítico no necesita Celery + Redis. Se inicia en el lifespan de FastAPI y se detiene limpiamente en el shutdown.

---

## Limitaciones conocidas

- **Rate limiting Gemini**: El tier gratuito permite ~20 req/día. El análisis de tono progresa lentamente — el scheduler analiza máximo 20 artículos/hora.
- **La Razón**: Solo RSS. El feed puede tener artículos con hasta 1-2 semanas de retraso.
- **Poco solapamiento cross-media**: Los 6 medios cubren regiones distintas (SC, CBBA, nacional). Con más datos históricos el análisis de sesgo se vuelve más rico.
- **Serie temporal**: Requiere 2-3 semanas de datos continuos para mostrar patrones útiles.
- **Velocidad de embeddings**: En CPU, agrupar 100 artículos tarda ~70 segundos.
- **Bloqueos HTTP**: Brújula Digital y Erbol retornan 500 en algunos artículos — se manejan silenciosamente.
