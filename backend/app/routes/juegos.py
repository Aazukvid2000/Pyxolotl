"""
Rutas de juegos
Publicar, buscar, filtrar, aprobar/rechazar juegos
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
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
    
    # Crear registro inicial del juego
    new_game = Juego(
        titulo=titulo,
        descripcion=descripcion,
        genero=genero,
        precio=precio,
        requisitos=requisitos,
        desarrollador_id=current_user.id,
        estado=EstadoJuego.EN_REVISION,
        portada_url="temp",  # Se actualiza después
        tipo_descarga=TipoDescarga(tipo_descarga)
    )
    
    db.add(new_game)
    db.flush()  # Obtener ID sin commit
    
    try:
        # Guardar portada
        portada_url = await file_service.save_image(portada, new_game.id, "portada")
        new_game.portada_url = portada_url
        
        # Guardar screenshots
        screenshots_urls = []
        for idx, screenshot in enumerate(screenshots):
            url = await file_service.save_image(screenshot, new_game.id, f"screenshot_{idx}")
            screenshots_urls.append(url)
        new_game.screenshots_urls = json.dumps(screenshots_urls)
        
        # Guardar trailer si existe
        if trailer:
            trailer_url = await file_service.save_video(trailer, new_game.id)
            new_game.trailer_url = trailer_url
        
        # Guardar archivo del juego o link
        if tipo_descarga == "archivo":
            if not archivo_juego:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Debes subir el archivo del juego"
                )
            
            game_url, size_mb = await file_service.save_game_file(archivo_juego, new_game.id)
            new_game.archivo_juego_url = game_url
            new_game.tamano_mb = size_mb
            
        else:  # link externo
            if not link_externo:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Debes proporcionar un link externo"
                )
            new_game.archivo_juego_url = link_externo
        
        db.commit()
        db.refresh(new_game)
        
        logger.info(f"Juego publicado: {titulo} por {current_user.email}")
        
        return new_game
        
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
        juego.fecha_aprobacion = db.func.now()
        
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
