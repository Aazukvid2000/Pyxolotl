"""
Rutas de compras y carrito
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models import Usuario, Juego, CarritoItem, Compra, ItemCompra, BibliotecaItem, EstadoCompra, EstadoJuego
from app.schemas import CompraCreate, CompraResponse, CarritoItemResponse, Message
from app.dependencies import get_current_active_user
from app.utils.email import email_service
from app.config import settings
import secrets
import stripe
import logging

logger = logging.getLogger(__name__)

# Configurar Stripe
if settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY

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

# ==================== STRIPE - CREAR PAYMENT INTENT ====================

class CreatePaymentIntentRequest(BaseModel):
    juegos_ids: List[int]

class PaymentIntentResponse(BaseModel):
    client_secret: str
    amount: int
    currency: str

@router.post("/pagos/crear-intent", response_model=PaymentIntentResponse)
async def crear_payment_intent(
    data: CreatePaymentIntentRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Crea un PaymentIntent de Stripe para procesar el pago"""
    
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe no está configurado")
    
    # Obtener juegos
    juegos = db.query(Juego).filter(Juego.id.in_(data.juegos_ids)).all()
    
    if len(juegos) != len(data.juegos_ids):
        raise HTTPException(status_code=400, detail="Algunos juegos no existen")
    
    # Calcular total en centavos (Stripe usa centavos)
    subtotal = sum(j.precio for j in juegos)
    iva = subtotal * 0.16
    comision = 15  # $15 MXN
    total = subtotal + iva + comision
    
    # Convertir a centavos (Stripe maneja enteros)
    amount_cents = int(total * 100)
    
    try:
        # Crear PaymentIntent en Stripe
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="mxn",
            metadata={
                "usuario_id": str(current_user.id),
                "usuario_email": current_user.email,
                "juegos_ids": ",".join(str(j.id) for j in juegos),
                "juegos_titulos": ", ".join(j.titulo for j in juegos)
            }
        )
        
        logger.info(f"PaymentIntent creado: {intent.id} para usuario {current_user.email}")
        
        return {
            "client_secret": intent.client_secret,
            "amount": amount_cents,
            "currency": "mxn"
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Error de Stripe: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error de Stripe: {str(e)}")

# ==================== COMPRAS ====================

class CompraStripeCreate(BaseModel):
    juegos_ids: List[int]
    payment_intent_id: str
    metodo_pago: str = "stripe"

@router.post("/compras/procesar", response_model=CompraResponse)
async def procesar_compra(
    compra_data: CompraCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Procesa una compra (modo legacy sin Stripe)"""
    
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

@router.post("/compras/confirmar-stripe", response_model=CompraResponse)
async def confirmar_compra_stripe(
    compra_data: CompraStripeCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Confirma una compra después de que Stripe procese el pago"""
    
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe no está configurado")
    
    try:
        # Verificar el estado del PaymentIntent
        intent = stripe.PaymentIntent.retrieve(compra_data.payment_intent_id)
        
        if intent.status != "succeeded":
            raise HTTPException(
                status_code=400, 
                detail=f"El pago no fue completado. Estado: {intent.status}"
            )
        
        # Verificar que el usuario coincide
        if intent.metadata.get("usuario_id") != str(current_user.id):
            raise HTTPException(status_code=403, detail="PaymentIntent no pertenece a este usuario")
            
    except stripe.error.StripeError as e:
        logger.error(f"Error verificando PaymentIntent: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error verificando pago: {str(e)}")
    
    # Obtener juegos
    juegos = db.query(Juego).filter(Juego.id.in_(compra_data.juegos_ids)).all()
    
    if len(juegos) != len(compra_data.juegos_ids):
        raise HTTPException(status_code=400, detail="Algunos juegos no existen")
    
    # Calcular totales
    subtotal = sum(j.precio for j in juegos)
    iva = subtotal * 0.16
    comision = 15
    total = subtotal + iva + comision
    
    # Crear compra
    numero_orden = f"PX-{secrets.token_hex(4).upper()}"
    
    compra = Compra(
        usuario_id=current_user.id,
        subtotal=subtotal,
        iva=iva,
        total=total,
        estado=EstadoCompra.COMPLETADA,
        metodo_pago="stripe",
        numero_orden=numero_orden
    )
    
    db.add(compra)
    db.flush()
    
    # Crear items de compra y agregar a biblioteca
    for juego in juegos:
        item = ItemCompra(compra_id=compra.id, juego_id=juego.id, precio=juego.precio)
        db.add(item)
        
        # Verificar si ya tiene el juego en biblioteca
        existing = db.query(BibliotecaItem).filter(
            BibliotecaItem.usuario_id == current_user.id,
            BibliotecaItem.juego_id == juego.id
        ).first()
        
        if not existing:
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
    
    logger.info(f"Compra Stripe completada: {numero_orden} para {current_user.email}")
    
    return compra

@router.get("/compras/historial", response_model=List[CompraResponse])
async def obtener_historial_compras(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Obtiene el historial de compras del usuario"""
    compras = db.query(Compra).filter(Compra.usuario_id == current_user.id).all()
    return compras