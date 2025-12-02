"""
Rutas de juegos
Publicar, buscar, filtrar, aprobar/rechazar juegos
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import List, Optional
from app.database import get_db
from app.models import Usuario, Juego, EstadoJuego, TipoDescarga, BibliotecaItem
from app.schemas import (
    JuegoResponse,
    JuegoListResponse,
    JuegosFiltros,
    JuegoApproval,
    Message
)
from app.dependencies import (
    get_current_developer,
    get_current_admin,
    get_current_user_optional,
    get_current_active_user
)
from app.utils.files import file_service
from app.utils.email import email_service
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/juegos", tags=["Juegos"])

# ==================== PUBLICAR JUEGO (Desarrollador) ====================

@router.post("/publicar", response_model=JuegoResponse, status_code=status.HTTP_201_CREATED)
async def publicar_juego(
    titulo: str = Form(...),
    descripcion: str = Form(...),
    genero: str = Form(...),
    precio: float = Form(...),
    requisitos: Optional[str] = Form(None),
    tipo_descarga: str = Form(...),  # "archivo" o "link"
    link_externo: Optional[str] = Form(None),
    
    portada: UploadFile = File(...),
    screenshots: List[UploadFile] = File(...),
    trailer: Optional[UploadFile] = File(None),
    archivo_juego: Optional[UploadFile] = File(None),
    
    current_user: Usuario = Depends(get_current_developer),
    db: Session = Depends(get_db)
):
    """Desarrollador publica un nuevo juego"""
    
    try:
        # ========== VALIDACIONES PREVIAS ==========
        # Validar archivo del juego o link ANTES de crear el registro
        archivo_juego_url = None
        tamano_mb = None
        
        if tipo_descarga == "archivo":
            if not archivo_juego:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Debes subir el archivo del juego"
                )
            # Validar que el archivo tenga contenido
            if archivo_juego.size == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El archivo del juego está vacío"
                )
        else:  # link externo
            if not link_externo:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Debes proporcionar un link externo"
                )
            archivo_juego_url = link_externo
        
        # ========== SUBIR ARCHIVOS PRIMERO (sin ID de juego) ==========
        # Usamos un ID temporal basado en timestamp para organizar archivos
        import time
        temp_id = f"temp_{current_user.id}_{int(time.time())}"
        
        # Guardar portada
        logger.info(f"Subiendo portada para juego temporal {temp_id}")
        portada_url = await file_service.save_image(portada, None, "portada")
        
        # Guardar screenshots
        screenshots_urls = []
        for idx, screenshot in enumerate(screenshots):
            # Verificar que el screenshot tenga contenido
            if screenshot.size and screenshot.size > 0:
                url = await file_service.save_image(screenshot, None, f"screenshot_{idx}")
                screenshots_urls.append(url)
        
        # Guardar trailer si existe
        trailer_url = None
        if trailer and trailer.size and trailer.size > 0:
            logger.info(f"Subiendo trailer para juego temporal {temp_id}")
            trailer_url = await file_service.save_video(trailer, 0)
        
        # Guardar archivo del juego si es tipo archivo
        if tipo_descarga == "archivo" and archivo_juego:
            logger.info(f"Subiendo archivo del juego para {temp_id}")
            try:
                game_url, size_mb = await file_service.save_game_file(archivo_juego, 0)
                archivo_juego_url = game_url
                tamano_mb = size_mb
                logger.info(f"Archivo del juego subido exitosamente: {game_url}")
            except Exception as upload_error:
                logger.error(f"Error al subir archivo del juego: {str(upload_error)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error al subir el archivo del juego: {str(upload_error)}"
                )
        
        # ========== VERIFICAR QUE TENEMOS URL DEL ARCHIVO ==========
        if not archivo_juego_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo obtener la URL del archivo del juego"
            )
        
        # ========== CREAR REGISTRO EN BD (con todos los datos) ==========
        new_game = Juego(
            titulo=titulo,
            descripcion=descripcion,
            genero=genero,
            precio=precio,
            requisitos=requisitos,
            desarrollador_id=current_user.id,
            estado=EstadoJuego.EN_REVISION,
            portada_url=portada_url,
            screenshots_urls=json.dumps(screenshots_urls) if screenshots_urls else None,
            trailer_url=trailer_url,
            tipo_descarga=TipoDescarga(tipo_descarga),
            archivo_juego_url=archivo_juego_url,
            tamano_mb=tamano_mb
        )
        
        db.add(new_game)
        db.commit()
        db.refresh(new_game)
        
        logger.info(f"Juego publicado exitosamente: {titulo} (ID: {new_game.id}) por {current_user.email}")
        
        return new_game
        
    except HTTPException:
        # Re-lanzar excepciones HTTP sin modificar
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al publicar juego: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al publicar juego: {str(e)}"
        )

# ==================== OBTENER CATÁLOGO (Público) ====================

@router.get("/catalogo", response_model=List[JuegoListResponse])
async def obtener_catalogo(
    busqueda: Optional[str] = None,
    genero: Optional[str] = None,
    precio_min: Optional[float] = None,
    precio_max: Optional[float] = None,
    solo_gratuitos: bool = False,
    ordenar_por: str = "fecha_creacion",
    orden: str = "desc",
    pagina: int = 1,
    por_pagina: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[Usuario] = Depends(get_current_user_optional)
):
    """
    Obtiene el catálogo de juegos aprobados
    Soporta búsqueda, filtros y paginación
    """
    
    # Base query: solo juegos aprobados
    query = db.query(Juego).filter(Juego.estado == EstadoJuego.APROBADO)
    
    # Aplicar filtros
    if busqueda:
        search_filter = or_(
            Juego.titulo.ilike(f"%{busqueda}%"),
            Juego.descripcion.ilike(f"%{busqueda}%")
        )
        query = query.filter(search_filter)
    
    if genero:
        query = query.filter(Juego.genero == genero)
    
    if precio_min is not None:
        query = query.filter(Juego.precio >= precio_min)
    
    if precio_max is not None:
        query = query.filter(Juego.precio <= precio_max)
    
    if solo_gratuitos:
        query = query.filter(Juego.precio == 0.0)
    
    # Ordenamiento
    if ordenar_por == "precio":
        order_col = Juego.precio
    elif ordenar_por == "calificacion":
        order_col = Juego.calificacion_promedio
    else:
        order_col = Juego.fecha_creacion
    
    if orden == "asc":
        query = query.order_by(order_col.asc())
    else:
        query = query.order_by(order_col.desc())
    
    # Paginación
    offset = (pagina - 1) * por_pagina
    juegos = query.offset(offset).limit(por_pagina).all()
    
    return juegos

# ==================== OBTENER DETALLE DE JUEGO ====================

@router.get("/{juego_id}", response_model=JuegoResponse)
async def obtener_juego(
    juego_id: int,
    db: Session = Depends(get_db)
):
    """Obtiene los detalles de un juego específico"""
    
    juego = db.query(Juego).filter(Juego.id == juego_id).first()
    
    if not juego:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Juego no encontrado"
        )
    
    # Solo mostrar juegos aprobados al público
    if juego.estado != EstadoJuego.APROBADO:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Juego no disponible"
        )
    
    return juego

# ==================== JUEGOS PENDIENTES (Admin) ====================

@router.get("/admin/juego/{juego_id}", response_model=JuegoResponse)
async def obtener_juego_admin(
    juego_id: int,
    db: Session = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin)
):
    """Admin puede ver cualquier juego independientemente de su estado"""
    
    juego = db.query(Juego).filter(Juego.id == juego_id).first()
    
    if not juego:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Juego no encontrado"
        )
    
    return juego

@router.get("/admin/pendientes", response_model=List[JuegoResponse])
async def obtener_juegos_pendientes(
    db: Session = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin)
):
    """Obtiene todos los juegos pendientes de revisión"""
    
    juegos = db.query(Juego).filter(
        Juego.estado == EstadoJuego.EN_REVISION
    ).all()
    
    return juegos

# ==================== APROBAR/RECHAZAR JUEGO (Admin) ====================

@router.post("/{juego_id}/aprobar", response_model=Message)
async def aprobar_juego(
    juego_id: int,
    approval_data: JuegoApproval,
    db: Session = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin)
):
    """Admin aprueba o rechaza un juego"""
    
    juego = db.query(Juego).filter(Juego.id == juego_id).first()
    
    if not juego:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Juego no encontrado"
        )
    
    if approval_data.aprobado:
        # Aprobar
        juego.estado = EstadoJuego.APROBADO
        juego.aprobado_por_id = current_admin.id
        juego.fecha_aprobacion = func.now()
        
        # Enviar email al desarrollador
        desarrollador = db.query(Usuario).filter(Usuario.id == juego.desarrollador_id).first()
        email_service.send_game_approved(
            desarrollador.email,
            desarrollador.nombre,
            juego.titulo
        )
        
        mensaje = "Juego aprobado y publicado exitosamente"
        
    else:
        # Rechazar
        juego.estado = EstadoJuego.RECHAZADO
        juego.motivo_rechazo = approval_data.motivo_rechazo
        
        # Enviar email al desarrollador
        desarrollador = db.query(Usuario).filter(Usuario.id == juego.desarrollador_id).first()
        email_service.send_game_rejected(
            desarrollador.email,
            desarrollador.nombre,
            juego.titulo,
            approval_data.motivo_rechazo or "No especificado"
        )
        
        mensaje = "Juego rechazado. Desarrollador notificado."
    
    db.commit()
    
    logger.info(f"Juego {juego_id} {'aprobado' if approval_data.aprobado else 'rechazado'} por {current_admin.email}")
    
    return {"message": mensaje, "success": True}

# ==================== DESCARGAR JUEGO GRATIS ====================

@router.post("/{juego_id}/descargar-gratis", response_model=Message)
async def obtener_juego_gratis(
    juego_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Agrega un juego gratuito a la biblioteca del usuario"""
    
    juego = db.query(Juego).filter(
        Juego.id == juego_id,
        Juego.precio == 0.0,
        Juego.estado == EstadoJuego.APROBADO
    ).first()
    
    if not juego:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Juego gratuito no encontrado"
        )
    
    # Verificar si ya lo tiene
    existing = db.query(BibliotecaItem).filter(
        BibliotecaItem.usuario_id == current_user.id,
        BibliotecaItem.juego_id == juego_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya tienes este juego en tu biblioteca"
        )
    
    # Agregar a biblioteca
    biblioteca_item = BibliotecaItem(
        usuario_id=current_user.id,
        juego_id=juego_id,
        es_gratuito=True
    )
    
    db.add(biblioteca_item)
    
    # Actualizar estadísticas
    juego.total_descargas += 1
    
    db.commit()
    
    logger.info(f"Juego gratuito {juego_id} agregado a biblioteca de {current_user.email}")
    
    return {
        "message": "Juego agregado a tu biblioteca. Ya puedes descargarlo.",
        "success": True
    }

# ==================== RESEÑAS ====================

from app.models import Resena
from app.schemas import ResenaCreate, ResenaResponse

@router.get("/{juego_id}/resenas", response_model=List[ResenaResponse])
async def obtener_resenas(
    juego_id: int,
    db: Session = Depends(get_db)
):
    """Obtiene todas las reseñas de un juego"""
    
    # Verificar que el juego existe
    juego = db.query(Juego).filter(Juego.id == juego_id).first()
    if not juego:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Juego no encontrado"
        )
    
    resenas = db.query(Resena).filter(
        Resena.juego_id == juego_id
    ).order_by(Resena.fecha_creacion.desc()).all()
    
    return resenas

@router.post("/{juego_id}/resenas", response_model=ResenaResponse, status_code=status.HTTP_201_CREATED)
async def crear_resena(
    juego_id: int,
    resena_data: ResenaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Crea una nueva reseña para un juego"""
    
    # Verificar que el juego existe y está aprobado
    juego = db.query(Juego).filter(
        Juego.id == juego_id,
        Juego.estado == EstadoJuego.APROBADO
    ).first()
    
    if not juego:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Juego no encontrado"
        )
    
    # Verificar que el usuario no haya dejado ya una reseña
    existing_resena = db.query(Resena).filter(
        Resena.usuario_id == current_user.id,
        Resena.juego_id == juego_id
    ).first()
    
    if existing_resena:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya has dejado una reseña para este juego"
        )
    
    # Crear la reseña
    nueva_resena = Resena(
        usuario_id=current_user.id,
        juego_id=juego_id,
        calificacion=resena_data.calificacion,
        texto=resena_data.texto
    )
    
    db.add(nueva_resena)
    
    # Actualizar estadísticas del juego
    juego.total_resenas += 1
    
    # Recalcular calificación promedio
    todas_resenas = db.query(Resena).filter(Resena.juego_id == juego_id).all()
    total_calificaciones = sum(r.calificacion for r in todas_resenas) + resena_data.calificacion
    juego.calificacion_promedio = total_calificaciones / (len(todas_resenas) + 1)
    
    db.commit()
    db.refresh(nueva_resena)
    
    logger.info(f"Reseña creada para juego {juego_id} por {current_user.email}")
    
    return nueva_resena

@router.delete("/{juego_id}/resenas/{resena_id}", response_model=Message)
async def eliminar_resena(
    juego_id: int,
    resena_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Elimina una reseña (solo el autor puede hacerlo)"""
    
    resena = db.query(Resena).filter(
        Resena.id == resena_id,
        Resena.juego_id == juego_id
    ).first()
    
    if not resena:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reseña no encontrada"
        )
    
    # Solo el autor puede eliminar su reseña
    if resena.usuario_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes eliminar esta reseña"
        )
    
    # Actualizar estadísticas del juego
    juego = db.query(Juego).filter(Juego.id == juego_id).first()
    juego.total_resenas -= 1
    
    # Recalcular calificación promedio
    otras_resenas = db.query(Resena).filter(
        Resena.juego_id == juego_id,
        Resena.id != resena_id
    ).all()
    
    if otras_resenas:
        juego.calificacion_promedio = sum(r.calificacion for r in otras_resenas) / len(otras_resenas)
    else:
        juego.calificacion_promedio = 0.0
    
    db.delete(resena)
    db.commit()
    
    logger.info(f"Reseña {resena_id} eliminada por {current_user.email}")
    
    return {"message": "Reseña eliminada correctamente", "success": True}