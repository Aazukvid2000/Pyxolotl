"""
Configuración de conexión a base de datos MySQL
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Motor de base de datos
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verifica conexión antes de usar
    pool_recycle=3600,   # Recicla conexiones cada hora
    echo=settings.DEBUG  # Muestra SQL queries en debug
)

# Sesión de base de datos
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base para modelos
Base = declarative_base()

# Dependencia para obtener sesión de BD
def get_db():
    """
    Generador que proporciona una sesión de base de datos
    y la cierra automáticamente al terminar
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
