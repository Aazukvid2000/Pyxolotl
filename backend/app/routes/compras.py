"""
Rutas de compras y carrito
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Usuario, Juego, CarritoItem, Compra, ItemCompra, BibliotecaItem, EstadoCompra, EstadoJuego
from app.schemas import CompraCreate, CompraResponse, CarritoItemResponse, Message
from app.dependencies import get_current_active_user
from app.utils.email import email_service
import secrets

router = APIRouter(prefix="/api", tags=["Compras y Carrito"])

# ==================== CARRITO ====================

@router.post("/carrito/agregar/{juego_id}", response_model=Message)
async def agregar_al_carrito(
    juego_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Agrega un juego al carrito"""
    
    juego = db.query(Juego).filter(
        Juego.id == juego_id,
        Juego.estado == EstadoJuego.APROBADO
    ).first()
    
    if not juego:
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    
    # Verificar si ya está en el carrito
    existing = db.query(CarritoItem).filter(
        CarritoItem.usuario_id == current_user.id,
        CarritoItem.juego_id == juego_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Ya está en el carrito")
    
    cart_item = CarritoItem(usuario_id=current_user.id, juego_id=juego_id)
    db.add(cart_item)
    db.commit()
    
    return {"message": "Juego agregado al carrito", "success": True}

@router.get("/carrito", response_model=List[CarritoItemResponse])
async def obtener_carrito(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Obtiene el carrito del usuario"""
    items = db.query(CarritoItem).filter(CarritoItem.usuario_id == current_user.id).all()
    return items

@router.delete("/carrito/{item_id}", response_model=Message)
async def eliminar_del_carrito(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Elimina un item del carrito"""
    item = db.query(CarritoItem).filter(
        CarritoItem.id == item_id,
        CarritoItem.usuario_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    
    db.delete(item)
    db.commit()
    
    return {"message": "Item eliminado del carrito", "success": True}

# ==================== COMPRAS ====================

@router.post("/compras/procesar", response_model=CompraResponse)
async def procesar_compra(
    compra_data: CompraCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Procesa una compra"""
    
    # Obtener juegos
    juegos = db.query(Juego).filter(Juego.id.in_(compra_data.juegos_ids)).all()
    
    if len(juegos) != len(compra_data.juegos_ids):
        raise HTTPException(status_code=400, detail="Algunos juegos no existen")
    
    # Calcular totales
    subtotal = sum(j.precio for j in juegos)
    iva = subtotal * 0.16
    total = subtotal + iva
    
    # Crear compra
    numero_orden = f"PX-{secrets.token_hex(4).upper()}"
    
    compra = Compra(
        usuario_id=current_user.id,
        subtotal=subtotal,
        iva=iva,
        total=total,
        estado=EstadoCompra.COMPLETADA,
        metodo_pago=compra_data.metodo_pago,
        numero_orden=numero_orden
    )
    
    db.add(compra)
    db.flush()
    
    # Crear items de compra y agregar a biblioteca
    for juego in juegos:
        item = ItemCompra(compra_id=compra.id, juego_id=juego.id, precio=juego.precio)
        db.add(item)
        
        # Agregar a biblioteca
        biblioteca_item = BibliotecaItem(
            usuario_id=current_user.id,
            juego_id=juego.id,
            es_gratuito=False
        )
        db.add(biblioteca_item)
        
        # Actualizar estadísticas
        juego.total_ventas += 1
        juego.total_descargas += 1
    
    # Limpiar carrito
    db.query(CarritoItem).filter(
        CarritoItem.usuario_id == current_user.id,
        CarritoItem.juego_id.in_(compra_data.juegos_ids)
    ).delete(synchronize_session=False)
    
    db.commit()
    db.refresh(compra)
    
    # Enviar email
    juegos_email = [{"titulo": j.titulo, "precio": j.precio} for j in juegos]
    email_service.send_purchase_confirmation(
        current_user.email,
        current_user.nombre,
        numero_orden,
        juegos_email,
        total
    )
    
    return compra

@router.get("/compras/historial", response_model=List[CompraResponse])
async def obtener_historial_compras(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Obtiene el historial de compras del usuario"""
    compras = db.query(Compra).filter(Compra.usuario_id == current_user.id).all()
    return compras
