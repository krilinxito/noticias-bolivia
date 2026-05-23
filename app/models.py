from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Medio(Base):
    __tablename__ = "medios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    url_rss = Column(String, nullable=False)
    linea_editorial = Column(String, nullable=True)
    region = Column(String, nullable=True)
    activo = Column(Boolean, default=True)

    articulos = relationship("Articulo", back_populates="medio")


class Tema(Base):
    __tablename__ = "temas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    titulo = Column(String)
    imagen_url = Column(String, nullable=True)
    fecha_deteccion = Column(DateTime, default=datetime.utcnow)
    score_importancia = Column(Float, default=0.0)
    keywords = Column(JSON, nullable=True)

    episodios = relationship("Episodio", back_populates="tema")


class Episodio(Base):
    __tablename__ = "episodios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    titulo = Column(String)
    imagen_url = Column(String, nullable=True)
    fecha_deteccion = Column(DateTime, default=datetime.utcnow)
    score_importancia = Column(Float, default=0.0)
    keywords = Column(JSON, nullable=True)
    tema_id = Column(Integer, ForeignKey("temas.id"), nullable=True)

    tema = relationship("Tema", back_populates="episodios")
    articulos = relationship("Articulo", back_populates="episodio")


class Articulo(Base):
    __tablename__ = "articulos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medio_id = Column(Integer, ForeignKey("medios.id"), nullable=False)
    episodio_id = Column(Integer, ForeignKey("episodios.id"), nullable=True)
    titulo = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False)
    resumen_rss = Column(Text, nullable=True)
    cuerpo = Column(Text, nullable=True)
    fecha_publicacion = Column(DateTime, nullable=True)
    fecha_scraping = Column(DateTime, default=datetime.utcnow)
    analisis = Column(JSON, nullable=True)
    imagen_url = Column(String, nullable=True)

    medio = relationship("Medio", back_populates="articulos")
    episodio = relationship("Episodio", back_populates="articulos")
