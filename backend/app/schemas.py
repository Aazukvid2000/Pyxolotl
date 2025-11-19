"""
Schemas Pydantic para validación de datos
Define la estructura de requests y responses
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from app.models import TipoCuenta, EstadoJuego, TipoDescarga, EstadoCompra

# ==================== USUARIO SCHEMAS ====================

class UsuarioBase(BaseModel):
    email: EmailStr
    nombre: str = Field(..., min_length=2, max_length=100)

class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=6)
    tipo_cuenta: TipoCuenta = TipoCuenta.COMPRADOR

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str

class UsuarioResponse(UsuarioBase):
    id: int
    tipo_cuenta: TipoCuenta
    verificado: bool
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    fecha_registro: datetime
    
    class Config:
        from_attributes = True

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

class PasswordChange(BaseModel):
    password_actual: str
    password_nueva: str = Field(..., min_length=6)

# ==================== AUTENTICACIÓN SCHEMAS ====================

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse

class TokenData(BaseModel):
    email: Optional[str] = None

# ==================== JUEGO SCHEMAS ====================

class JuegoBase(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=200)
    descripcion: str = Field(..., min_length=10)
    genero: str
    precio: float = Field(..., ge=0.0)
    requisitos: Optional[str] = None

class JuegoCreate(JuegoBase):
    tipo_descarga: TipoDescarga = TipoDescarga.ARCHIVO
    archivo_juego_url: Optional[str] = None  # Se llena después del upload
    link_externo: Optional[str] = None
    
    @validator('precio')
    def validar_precio(cls, v):
        if v < 0:
            raise ValueError('El precio no puede ser negativo')
        return round(v, 2)

class JuegoUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    genero: Optional[str] = None
    precio: Optional[float] = None
    requisitos: Optional[str] = None

class JuegoResponse(JuegoBase):
    id: int
    portada_url: str
    screenshots_urls: Optional[str] = None
    trailer_url: Optional[str] = None
    tipo_descarga: TipoDescarga
    archivo_juego_url: str
    tamano_mb: Optional[float] = None
    estado: EstadoJuego
    desarrollador_id: int
    calificacion_promedio: float
    total_resenas: int
    total_descargas: int
    total_ventas: int
    fecha_creacion: datetime
    
    # Info del desarrollador
    desarrollador: Optional[UsuarioResponse] = None
    
    class Config:
        from_attributes = True

class JuegoListResponse(BaseModel):
    """Response simplificado para listas/catálogo"""
    id: int
    titulo: str
    descripcion: str
    genero: str
    precio: float
    portada_url: str
    calificacion_promedio: float
    total_resenas: int
    estado: EstadoJuego
    
    class Config:
        from_attributes = True

class JuegoApproval(BaseModel):
    """Schema para aprobar/rechazar juegos"""
    aprobado: bool
    motivo_rechazo: Optional[str] = None

# ==================== CARRITO SCHEMAS ====================

class CarritoItemCreate(BaseModel):
    juego_id: int

class CarritoItemResponse(BaseModel):
    id: int
    juego_id: int
    fecha_agregado: datetime
    juego: JuegoListResponse
    
    class Config:
        from_attributes = True

# ==================== COMPRA SCHEMAS ====================

class CompraCreate(BaseModel):
    juegos_ids: List[int]
    metodo_pago: str = "tarjeta"

class ItemCompraResponse(BaseModel):
    id: int
    juego_id: int
    precio: float
    juego: JuegoListResponse
    
    class Config:
        from_attributes = True

class CompraResponse(BaseModel):
    id: int
    usuario_id: int
    subtotal: float
    iva: float
    total: float
    estado: EstadoCompra
    metodo_pago: str
    numero_orden: str
    recibo_url: Optional[str] = None
    fecha_compra: datetime
    items: List[ItemCompraResponse]
    
    class Config:
        from_attributes = True

# ==================== RESEÑA SCHEMAS ====================

class ResenaCreate(BaseModel):
    juego_id: int
    calificacion: int = Field(..., ge=1, le=5)
    texto: str = Field(..., min_length=10, max_length=1000)

class ResenaUpdate(BaseModel):
    calificacion: Optional[int] = Field(None, ge=1, le=5)
    texto: Optional[str] = Field(None, min_length=10, max_length=1000)

class ResenaResponse(BaseModel):
    id: int
    usuario_id: int
    juego_id: int
    calificacion: int
    texto: str
    fecha_creacion: datetime
    usuario: UsuarioResponse
    
    class Config:
        from_attributes = True

# ==================== BIBLIOTECA SCHEMAS ====================

class BibliotecaItemResponse(BaseModel):
    id: int
    juego_id: int
    fecha_obtencion: datetime
    es_gratuito: bool
    juego: JuegoResponse
    
    class Config:
        from_attributes = True

# ==================== BÚSQUEDA Y FILTROS ====================

class JuegosFiltros(BaseModel):
    """Parámetros de búsqueda y filtrado"""
    busqueda: Optional[str] = None
    genero: Optional[str] = None
    precio_min: Optional[float] = None
    precio_max: Optional[float] = None
    solo_gratuitos: bool = False
    ordenar_por: str = "fecha_creacion"  # fecha_creacion, precio, calificacion
    orden: str = "desc"  # asc o desc
    pagina: int = 1
    por_pagina: int = 20

# ==================== RESPUESTAS GENÉRICAS ====================

class Message(BaseModel):
    """Mensaje genérico de respuesta"""
    message: str
    success: bool = True

class ErrorResponse(BaseModel):
    """Respuesta de error"""
    detail: str
    success: bool = False

# ==================== ESTADÍSTICAS (Admin) ====================

class EstadisticasAdmin(BaseModel):
    """Estadísticas para el panel de administrador"""
    total_usuarios: int
    total_juegos: int
    juegos_pendientes: int
    total_ventas: int
    ingresos_totales: float
    usuarios_nuevos_mes: int
    ventas_mes: int
