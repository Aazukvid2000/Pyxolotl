"""
Modelos de base de datos - SQLAlchemy
Define la estructura de todas las tablas en MySQL
"""

from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

# ==================== ENUMS ====================

class TipoCuenta(str, enum.Enum):
    """Tipos de cuenta de usuario"""
    COMPRADOR = "comprador"
    DESARROLLADOR = "desarrollador"
    ADMINISTRADOR = "administrador"

class EstadoJuego(str, enum.Enum):
    """Estados posibles de un juego"""
    BORRADOR = "borrador"
    EN_REVISION = "en_revision"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"

class TipoDescarga(str, enum.Enum):
    """Tipo de descarga del juego"""
    ARCHIVO = "archivo"  # Archivo subido al servidor
    LINK = "link"        # Link externo (Google Drive, etc.)

class EstadoCompra(str, enum.Enum):
    """Estados de una compra"""
    PENDIENTE = "pendiente"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"
    REEMBOLSADA = "reembolsada"

# ==================== MODELOS ====================

class Usuario(Base):
    """Tabla de usuarios del sistema"""
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    tipo_cuenta = Column(Enum(TipoCuenta), default=TipoCuenta.COMPRADOR)
    verificado = Column(Boolean, default=False)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    juegos_publicados = relationship("Juego", back_populates="desarrollador", foreign_keys="Juego.desarrollador_id")
    compras = relationship("Compra", back_populates="usuario")
    resenas = relationship("Resena", back_populates="usuario")
    carrito_items = relationship("CarritoItem", back_populates="usuario")
    biblioteca_items = relationship("BibliotecaItem", back_populates="usuario")
    descargas = relationship("DescargaLog", back_populates="usuario")


class Juego(Base):
    """Tabla de videojuegos"""
    __tablename__ = "juegos"
    
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(200), nullable=False, index=True)
    descripcion = Column(Text, nullable=False)
    genero = Column(String(50), nullable=False, index=True)
    precio = Column(Float, nullable=False, default=0.0)
    requisitos = Column(Text, nullable=True)
    
    # Archivos multimedia
    portada_url = Column(String(500), nullable=False)
    screenshots_urls = Column(Text, nullable=True)  # JSON array de URLs
    trailer_url = Column(String(500), nullable=True)
    
    # Archivo del juego
    tipo_descarga = Column(Enum(TipoDescarga), default=TipoDescarga.ARCHIVO)
    archivo_juego_url = Column(String(500), nullable=False)
    tamano_mb = Column(Float, nullable=True)
    
    # Estado y aprobación
    estado = Column(Enum(EstadoJuego), default=EstadoJuego.EN_REVISION, index=True)
    desarrollador_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    aprobado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_aprobacion = Column(DateTime(timezone=True), nullable=True)
    motivo_rechazo = Column(Text, nullable=True)
    
    # Estadísticas
    calificacion_promedio = Column(Float, default=0.0)
    total_resenas = Column(Integer, default=0)
    total_descargas = Column(Integer, default=0)
    total_ventas = Column(Integer, default=0)
    
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    desarrollador = relationship("Usuario", back_populates="juegos_publicados", foreign_keys=[desarrollador_id])
    aprobado_por = relationship("Usuario", foreign_keys=[aprobado_por_id])
    resenas = relationship("Resena", back_populates="juego", cascade="all, delete-orphan")
    items_compra = relationship("ItemCompra", back_populates="juego")
    carrito_items = relationship("CarritoItem", back_populates="juego")
    biblioteca_items = relationship("BibliotecaItem", back_populates="juego")
    descargas = relationship("DescargaLog", back_populates="juego")


class CarritoItem(Base):
    """Items en el carrito de compras"""
    __tablename__ = "carrito_items"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    juego_id = Column(Integer, ForeignKey("juegos.id"), nullable=False)
    fecha_agregado = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="carrito_items")
    juego = relationship("Juego", back_populates="carrito_items")


class Compra(Base):
    """Registro de compras"""
    __tablename__ = "compras"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    
    subtotal = Column(Float, nullable=False)
    iva = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    
    estado = Column(Enum(EstadoCompra), default=EstadoCompra.COMPLETADA)
    
    # Método de pago (simulado)
    metodo_pago = Column(String(50), nullable=False)
    
    # Recibo
    recibo_url = Column(String(500), nullable=True)
    numero_orden = Column(String(50), unique=True, nullable=False)
    
    fecha_compra = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="compras")
    items = relationship("ItemCompra", back_populates="compra", cascade="all, delete-orphan")


class ItemCompra(Base):
    """Items individuales de una compra"""
    __tablename__ = "items_compra"
    
    id = Column(Integer, primary_key=True, index=True)
    compra_id = Column(Integer, ForeignKey("compras.id"), nullable=False)
    juego_id = Column(Integer, ForeignKey("juegos.id"), nullable=False)
    precio = Column(Float, nullable=False)
    
    # Relaciones
    compra = relationship("Compra", back_populates="items")
    juego = relationship("Juego", back_populates="items_compra")


class BibliotecaItem(Base):
    """Juegos en la biblioteca del usuario (comprados o gratuitos)"""
    __tablename__ = "biblioteca_items"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    juego_id = Column(Integer, ForeignKey("juegos.id"), nullable=False)
    
    fecha_obtencion = Column(DateTime(timezone=True), server_default=func.now())
    es_gratuito = Column(Boolean, default=False)
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="biblioteca_items")
    juego = relationship("Juego", back_populates="biblioteca_items")


class Resena(Base):
    """Reseñas de juegos"""
    __tablename__ = "resenas"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    juego_id = Column(Integer, ForeignKey("juegos.id"), nullable=False)
    
    calificacion = Column(Integer, nullable=False)  # 1-5 estrellas
    texto = Column(Text, nullable=False)
    
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="resenas")
    juego = relationship("Juego", back_populates="resenas")


class DescargaLog(Base):
    """Registro de descargas de juegos"""
    __tablename__ = "descargas_log"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    juego_id = Column(Integer, ForeignKey("juegos.id"), nullable=False)
    
    fecha_descarga = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(50), nullable=True)
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="descargas")
    juego = relationship("Juego", back_populates="descargas")


class TokenVerificacion(Base):
    """Tokens para verificación de email y recuperación de contraseña"""
    __tablename__ = "tokens_verificacion"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    
    token = Column(String(255), unique=True, nullable=False, index=True)
    tipo = Column(String(50), nullable=False)  # 'email' o 'password_reset'
    
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_expiracion = Column(DateTime(timezone=True), nullable=False)
    usado = Column(Boolean, default=False)
