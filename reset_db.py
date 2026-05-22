"""Vacía artículos y eventos. Mantiene medios intactos."""
import sys

from app.database import SessionLocal
from app.models import Articulo, Evento


def main():
    print("Este script eliminará TODOS los artículos y eventos de la base de datos.")
    print("Los medios (6 fuentes) se conservan.\n")
    respuesta = input("¿Confirmar? (s/N): ").strip().lower()
    if respuesta != "s":
        print("Cancelado.")
        sys.exit(0)

    with SessionLocal() as db:
        n_arts = db.query(Articulo).delete()
        n_evs = db.query(Evento).delete()
        db.commit()

    print(f"\nEliminados: {n_arts} artículos, {n_evs} eventos.")
    print("Base de datos lista para el nuevo ciclo.")


if __name__ == "__main__":
    main()
