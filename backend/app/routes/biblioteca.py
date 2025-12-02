"""
Rutas de biblioteca y descargas
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.database import get_db
from app.models import Usuario, BibliotecaItem, Juego, DescargaLog, TipoDescarga
from app.schemas import BibliotecaItemResponse
from app.dependencies import get_current_active_user
import os

router = APIRouter(prefix="/api/biblioteca", tags=["Biblioteca"])

@router.get("/", response_model=List[BibliotecaItemResponse])
async def obtener_biblioteca(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Obtiene la biblioteca de juegos del usuario"""
    items = db.query(BibliotecaItem).options(
        joinedload(BibliotecaItem.juego).joinedload(Juego.desarrollador)
    ).filter(
        BibliotecaItem.usuario_id == current_user.id
    ).all()
    return items

@router.get("/descargar/{juego_id}")
async def descargar_juego(
    juego_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Descarga un juego que el usuario posee"""
    
    # Verificar que el usuario tenga el juego
    biblioteca_item = db.query(BibliotecaItem).filter(
        BibliotecaItem.usuario_id == current_user.id,
        BibliotecaItem.juego_id == juego_id
    ).first()
    
    if not biblioteca_item:
        raise HTTPException(status_code=403, detail="No tienes este juego")
    
    # Obtener juego
    juego = db.query(Juego).filter(Juego.id == juego_id).first()
    
    # Registrar descarga
    log = DescargaLog(usuario_id=current_user.id, juego_id=juego_id)
    db.add(log)
    db.commit()
    
    # Si es link externo, redirigir
    if juego.tipo_descarga == TipoDescarga.LINK:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=juego.archivo_juego_url)
    
    # Si es archivo local, servirlo
    file_path = juego.archivo_juego_url.lstrip('/')
    full_path = os.path.join(os.getcwd(), file_path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(
        path=full_path,
        filename=f"{juego.titulo}.zip",
        media_type="application/zip"
    )
