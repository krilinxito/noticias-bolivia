from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Orígenes que pueden llamar a la API desde un navegador. Separados por coma.
# En "*" cualquier web ajena podría embeber el chat y gastar la cuota de Gemini.
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "https://observador-digital.maxi42.space,http://localhost:4321",
    ).split(",")
    if o.strip()
]

# Peticiones a /chat por IP y por ventana. Cada una dispara varias llamadas a
# Gemini con function calling, así que sin techo la cuota se agota sola.
CHAT_LIMITE = int(os.getenv("CHAT_LIMITE", "10"))
CHAT_VENTANA_SEG = int(os.getenv("CHAT_VENTANA_SEG", "60"))
