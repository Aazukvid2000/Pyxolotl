"""
Rutas de administración para Pyxolotl
=====================================
Endpoints para gestionar usuarios y juegos desde el panel de admin.
Requiere autenticación como administrador.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json
import os
import re

from app.database import get_db
from app.models import (
    Usuario, TokenVerificacion, Resena, Compra, Juego,
    CarritoItem, BibliotecaItem, DescargaLog, ItemCompra
)
from app.dependencies import get_current_active_user

# Cloudinary (opcional)
try:
    import cloudinary
    import cloudinary.uploader
    CLOUDINARY_ENABLED = bool(os.getenv("CLOUDINARY_CLOUD_NAME"))
except ImportError:
    CLOUDINARY_ENABLED = False

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# ==================== SCHEMAS ====================

class AdminStats(BaseModel):
    total_usuarios: int
    usuarios_verificados: int
    total_juegos: int
    juegos_aprobados: int
    total_compras: int
    total_descargas: int

class UsuarioAdmin(BaseModel):
    id: int
    nombre: str
    email: str
    tipo_cuenta: str
    verificado: bool
    num_juegos: int
    num_compras: int
    
    class Config:
        from_attributes = True

class JuegoAdmin(BaseModel):
    id: int
    titulo: str
    desarrollador_nombre: str
    precio: float
    estado: str
    total_descargas: int
    total_resenas: int
    
    class Config:
        from_attributes = True

class DeleteResponse(BaseModel):
    success: bool
    message: str
    registros_eliminados: int = 0
    archivos_eliminados: int = 0

# ==================== HELPERS ====================

def verificar_admin(user: Usuario):
    """Verifica que el usuario sea administrador"""
    # Verificar por tipo_cuenta O por lista de emails de admin
    admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
    is_admin_by_type = user.tipo_cuenta == "administrador"
    is_admin_by_email = user.email in admin_emails if admin_emails[0] else False
    
    if not (is_admin_by_type or is_admin_by_email):
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")

def extract_public_id(url: str) -> Optional[str]:
    """Extrae el public_id de una URL de Cloudinary"""
    if not url or "cloudinary" not in url:
        return None
    
    try:
        pattern = r'/upload/(?:v\d+/)?(.+?)(?:\.\w+)?$'
        match = re.search(pattern, url)
        if match:
            public_id = match.group(1)
            return re.sub(r'\.\w+$', '', public_id)
        return None
    except:
        return None

def delete_cloudinary_resource(url: str, resource_type: str = "image") -> bool:
    """Elimina un recurso de Cloudinary"""
    if not CLOUDINARY_ENABLED:
        return False
    
    public_id = extract_public_id(url)
    if not public_id:
        return False
    
    try:
        result = cloudinary.uploader.destroy(
            public_id,
            resource_type=resource_type,
            invalidate=True
        )
        return result.get("result") == "ok"
    except:
        return False

def eliminar_archivos_juego(juego: Juego) -> int:
    """Elimina los archivos de Cloudinary de un juego"""
    eliminados = 0
    
    if juego.portada_url and "cloudinary" in juego.portada_url:
        if delete_cloudinary_resource(juego.portada_url):
            eliminados += 1
    
    if juego.screenshots_urls:
        try:
            screenshots = json.loads(juego.screenshots_urls) if isinstance(juego.screenshots_urls, str) else juego.screenshots_urls
            for url in screenshots:
                if url and "cloudinary" in url:
                    if delete_cloudinary_resource(url):
                        eliminados += 1
        except:
            pass
    
    if juego.trailer_url and "cloudinary" in juego.trailer_url:
        if delete_cloudinary_resource(juego.trailer_url, "video"):
            eliminados += 1
    
    if juego.archivo_juego_url and "cloudinary" in juego.archivo_juego_url:
        if delete_cloudinary_resource(juego.archivo_juego_url, "raw"):
            eliminados += 1
    
    return eliminados

# ==================== ENDPOINTS ====================

@router.get("/stats", response_model=AdminStats)
async def obtener_estadisticas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Obtiene estadísticas generales del sistema"""
    verificar_admin(current_user)
    
    return AdminStats(
        total_usuarios=db.query(Usuario).count(),
        usuarios_verificados=db.query(Usuario).filter(Usuario.verificado == True).count(),
        total_juegos=db.query(Juego).count(),
        juegos_aprobados=db.query(Juego).filter(Juego.estado == "aprobado").count(),
        total_compras=db.query(Compra).count(),
        total_descargas=db.query(DescargaLog).count()
    )

@router.get("/usuarios", response_model=List[UsuarioAdmin])
async def listar_usuarios(
    skip: int = 0,
    limit: int = 50,
    verificado: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Lista todos los usuarios"""
    verificar_admin(current_user)
    
    query = db.query(Usuario)
    
    if verificado is not None:
        query = query.filter(Usuario.verificado == verificado)
    
    usuarios = query.offset(skip).limit(limit).all()
    
    result = []
    for user in usuarios:
        result.append(UsuarioAdmin(
            id=user.id,
            nombre=user.nombre,
            email=user.email,
            tipo_cuenta=user.tipo_cuenta,
            verificado=user.verificado,
            num_juegos=db.query(Juego).filter(Juego.desarrollador_id == user.id).count(),
            num_compras=db.query(Compra).filter(Compra.usuario_id == user.id).count()
        ))
    
    return result

@router.get("/juegos", response_model=List[JuegoAdmin])
async def listar_juegos_admin(
    skip: int = 0,
    limit: int = 50,
    estado: Optional[str] = None,
    desarrollador_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Lista todos los juegos"""
    verificar_admin(current_user)
    
    query = db.query(Juego)
    
    if estado:
        query = query.filter(Juego.estado == estado)
    
    if desarrollador_id:
        query = query.filter(Juego.desarrollador_id == desarrollador_id)
    
    juegos = query.offset(skip).limit(limit).all()
    
    result = []
    for juego in juegos:
        result.append(JuegoAdmin(
            id=juego.id,
            titulo=juego.titulo,
            desarrollador_nombre=juego.desarrollador.nombre if juego.desarrollador else "Desconocido",
            precio=juego.precio or 0,
            estado=juego.estado.value,
            total_descargas=juego.total_descargas or 0,
            total_resenas=db.query(Resena).filter(Resena.juego_id == juego.id).count()
        ))
    
    return result

@router.delete("/juego/{juego_id}", response_model=DeleteResponse)
async def eliminar_juego(
    juego_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Elimina un juego específico con todas sus relaciones.
    
    Orden de eliminación:
    1. Reseñas
    2. Items de compra
    3. Items de carrito
    4. Items de biblioteca
    5. Registros de descarga
    6. Archivos en Cloudinary
    7. El juego
    """
    verificar_admin(current_user)
    
    juego = db.query(Juego).filter(Juego.id == juego_id).first()
    
    if not juego:
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    
    registros = 0
    titulo = juego.titulo
    
    try:
        # 1. Eliminar reseñas
        count = db.query(Resena).filter(Resena.juego_id == juego_id).delete()
        registros += count
        
        # 2. Eliminar items de compra
        count = db.query(ItemCompra).filter(ItemCompra.juego_id == juego_id).delete()
        registros += count
        
        # 3. Eliminar items de carrito
        count = db.query(CarritoItem).filter(CarritoItem.juego_id == juego_id).delete()
        registros += count
        
        # 4. Eliminar items de biblioteca
        count = db.query(BibliotecaItem).filter(BibliotecaItem.juego_id == juego_id).delete()
        registros += count
        
        # 5. Eliminar registros de descarga
        count = db.query(DescargaLog).filter(DescargaLog.juego_id == juego_id).delete()
        registros += count
        
        # 6. Eliminar archivos de Cloudinary
        archivos = eliminar_archivos_juego(juego)
        
        # 7. Eliminar el juego
        db.delete(juego)
        db.commit()
        
        return DeleteResponse(
            success=True,
            message=f"Juego '{titulo}' eliminado correctamente",
            registros_eliminados=registros + 1,
            archivos_eliminados=archivos
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar: {str(e)}")

@router.delete("/usuario/{user_id}", response_model=DeleteResponse)
async def eliminar_usuario(
    user_id: int,
    eliminar_juegos: bool = Query(True, description="Si es True, también elimina los juegos del usuario"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Elimina un usuario con todas sus relaciones.
    
    Orden de eliminación:
    1. Tokens de verificación
    2. Reseñas del usuario
    3. Items de carrito
    4. Items de biblioteca
    5. Registros de descarga
    6. Items de compra
    7. Compras
    8. Juegos publicados (opcional)
    9. Avatar en Cloudinary
    10. El usuario
    """
    verificar_admin(current_user)
    
    # No permitir auto-eliminación
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
    
    usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    registros = 0
    archivos = 0
    nombre = usuario.nombre
    
    try:
        # 1. Tokens
        count = db.query(TokenVerificacion).filter(TokenVerificacion.usuario_id == user_id).delete()
        registros += count
        
        # 2. Reseñas del usuario
        count = db.query(Resena).filter(Resena.usuario_id == user_id).delete()
        registros += count
        
        # 3. Items de carrito
        count = db.query(CarritoItem).filter(CarritoItem.usuario_id == user_id).delete()
        registros += count
        
        # 4. Items de biblioteca
        count = db.query(BibliotecaItem).filter(BibliotecaItem.usuario_id == user_id).delete()
        registros += count
        
        # 5. Registros de descarga
        count = db.query(DescargaLog).filter(DescargaLog.usuario_id == user_id).delete()
        registros += count
        
        # 6-7. Compras y sus items
        compras = db.query(Compra).filter(Compra.usuario_id == user_id).all()
        for compra in compras:
            db.query(ItemCompra).filter(ItemCompra.compra_id == compra.id).delete()
            registros += 1
        count = db.query(Compra).filter(Compra.usuario_id == user_id).delete()
        registros += count
        
        # 8. Juegos publicados
        if eliminar_juegos:
            juegos = db.query(Juego).filter(Juego.desarrollador_id == user_id).all()
            for juego in juegos:
                # Eliminar relaciones del juego
                db.query(Resena).filter(Resena.juego_id == juego.id).delete()
                db.query(ItemCompra).filter(ItemCompra.juego_id == juego.id).delete()
                db.query(CarritoItem).filter(CarritoItem.juego_id == juego.id).delete()
                db.query(BibliotecaItem).filter(BibliotecaItem.juego_id == juego.id).delete()
                db.query(DescargaLog).filter(DescargaLog.juego_id == juego.id).delete()
                
                # Eliminar archivos
                archivos += eliminar_archivos_juego(juego)
                
                db.delete(juego)
                registros += 1
        
        # 9. Avatar
        if usuario.avatar_url and "cloudinary" in usuario.avatar_url:
            if delete_cloudinary_resource(usuario.avatar_url):
                archivos += 1
        
        # 10. El usuario
        db.delete(usuario)
        db.commit()
        
        return DeleteResponse(
            success=True,
            message=f"Usuario '{nombre}' eliminado correctamente",
            registros_eliminados=registros + 1,
            archivos_eliminados=archivos
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar: {str(e)}")

@router.delete("/usuario/{user_id}/juegos", response_model=DeleteResponse)
async def eliminar_juegos_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Elimina SOLO los juegos de un usuario (mantiene su cuenta).
    """
    verificar_admin(current_user)
    
    usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    juegos = db.query(Juego).filter(Juego.desarrollador_id == user_id).all()
    
    if not juegos:
        return DeleteResponse(
            success=True,
            message="El usuario no tiene juegos publicados",
            registros_eliminados=0,
            archivos_eliminados=0
        )
    
    registros = 0
    archivos = 0
    
    try:
        for juego in juegos:
            # Eliminar relaciones
            registros += db.query(Resena).filter(Resena.juego_id == juego.id).delete()
            registros += db.query(ItemCompra).filter(ItemCompra.juego_id == juego.id).delete()
            registros += db.query(CarritoItem).filter(CarritoItem.juego_id == juego.id).delete()
            registros += db.query(BibliotecaItem).filter(BibliotecaItem.juego_id == juego.id).delete()
            registros += db.query(DescargaLog).filter(DescargaLog.juego_id == juego.id).delete()
            
            # Eliminar archivos
            archivos += eliminar_archivos_juego(juego)
            
            # Eliminar juego
            db.delete(juego)
            registros += 1
        
        db.commit()
        
        return DeleteResponse(
            success=True,
            message=f"{len(juegos)} juegos de '{usuario.nombre}' eliminados",
            registros_eliminados=registros,
            archivos_eliminados=archivos
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar: {str(e)}")

@router.delete("/usuarios/no-verificados", response_model=DeleteResponse)
async def limpiar_usuarios_no_verificados(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Elimina todos los usuarios que no han verificado su email"""
    verificar_admin(current_user)
    
    usuarios = db.query(Usuario).filter(Usuario.verificado == False).all()
    
    if not usuarios:
        return DeleteResponse(
            success=True,
            message="No hay usuarios sin verificar",
            registros_eliminados=0,
            archivos_eliminados=0
        )
    
    registros = 0
    archivos = 0
    
    try:
        for user in usuarios:
            # Eliminar tokens
            registros += db.query(TokenVerificacion).filter(TokenVerificacion.usuario_id == user.id).delete()
            
            # Eliminar avatar
            if user.avatar_url and "cloudinary" in user.avatar_url:
                if delete_cloudinary_resource(user.avatar_url):
                    archivos += 1
            
            # Eliminar usuario
            db.delete(user)
            registros += 1
        
        db.commit()
        
        return DeleteResponse(
            success=True,
            message=f"{len(usuarios)} usuarios no verificados eliminados",
            registros_eliminados=registros,
            archivos_eliminados=archivos
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar: {str(e)}")
