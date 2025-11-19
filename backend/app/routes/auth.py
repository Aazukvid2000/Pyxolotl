"""
Rutas de autenticación
Registro, login, verificación de email, recuperación de contraseña
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.models import Usuario, TokenVerificacion
from app.schemas import (
    UsuarioCreate,
    UsuarioLogin,
    UsuarioResponse,
    Token,
    Message,
    PasswordChange
)
from app.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    generate_verification_token
)
from app.utils.email import email_service
from app.dependencies import get_current_active_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

# ==================== VERIFICACIÓN MANUAL (TEMPORAL) ====================

@router.get("/force-verify-admin", response_model=Message)
async def force_verify_admin(db: Session = Depends(get_db)):
    """
    Endpoint temporal para forzar la verificación del administrador
    ⚠️ ELIMINAR EN PRODUCCIÓN
    """
    user = db.query(Usuario).filter(Usuario.email == "sinuhevidals@gmail.com").first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuario administrador no encontrado"
        )
    
    user.verificado = True
    db.commit()
    
    return Message(
        message=f"✅ Usuario {user.email} verificado exitosamente",
        success=True
    )

# ==================== REGISTRO ====================

@router.post("/registro", response_model=Message, status_code=status.HTTP_201_CREATED)
async def registrar_usuario(
    usuario_data: UsuarioCreate,
    db: Session = Depends(get_db)
):
    """
    Registra un nuevo usuario
    
    - Valida que el email no esté registrado
    - Encripta la contraseña
    - Envía email de verificación
    """
    # Verificar si el email ya existe
    existing_user = db.query(Usuario).filter(Usuario.email == usuario_data.email).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este correo ya está registrado"
        )
    
    # Crear usuario
    new_user = Usuario(
        nombre=usuario_data.nombre,
        email=usuario_data.email,
        password_hash=get_password_hash(usuario_data.password),
        tipo_cuenta=usuario_data.tipo_cuenta,
        verificado=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generar token de verificación
    verification_token = generate_verification_token()
    
    token_record = TokenVerificacion(
        usuario_id=new_user.id,
        token=verification_token,
        tipo="email",
        fecha_expiracion=datetime.utcnow() + timedelta(hours=24)
    )
    
    db.add(token_record)
    db.commit()
    
    # Enviar email de verificación
    logger.warning(f"🔔 INTENTANDO ENVIAR EMAIL DE VERIFICACIÓN a {new_user.email}")
    try:
        result = email_service.send_verification_email(
            new_user.email,
            new_user.nombre,
            verification_token
        )
        logger.warning(f"📧 Resultado del envío de email: {result}")
    except Exception as e:
        logger.error(f"❌ ERROR al enviar email: {str(e)}")
    
    logger.info(f"Usuario registrado: {new_user.email}")
    
    return {
        "message": "Cuenta creada exitosamente. Por favor verifica tu email.",
        "success": True
    }

# ==================== LOGIN ====================

@router.post("/login", response_model=Token)
async def login(
    login_data: UsuarioLogin,
    db: Session = Depends(get_db)
):
    """
    Inicia sesión
    
    - Valida credenciales
    - Retorna token JWT
    """
    # Buscar usuario
    usuario = db.query(Usuario).filter(Usuario.email == login_data.email).first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos"
        )
    
    # Verificar contraseña
    if not verify_password(login_data.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos"
        )
    
    # Crear token JWT
    access_token = create_access_token(data={"sub": usuario.email})
    
    logger.info(f"Login exitoso: {usuario.email}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario": usuario
    }

# ==================== VERIFICACIÓN DE EMAIL ====================

@router.get("/verificar/{token}", response_model=Message)
async def verificar_email(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Verifica el email del usuario mediante token
    """
    # Buscar token
    token_record = db.query(TokenVerificacion).filter(
        TokenVerificacion.token == token,
        TokenVerificacion.tipo == "email",
        TokenVerificacion.usado == False
    ).first()
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o ya utilizado"
        )
    
    # Verificar expiración
    if datetime.utcnow() > token_record.fecha_expiracion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El token ha expirado"
        )
    
    # Actualizar usuario
    usuario = db.query(Usuario).filter(Usuario.id == token_record.usuario_id).first()
    usuario.verificado = True
    
    # Marcar token como usado
    token_record.usado = True
    
    db.commit()
    
    logger.info(f"Email verificado: {usuario.email}")
    
    return {
        "message": "Email verificado exitosamente. Ya puedes iniciar sesión.",
        "success": True
    }

# ==================== PERFIL DEL USUARIO ====================

@router.get("/perfil", response_model=UsuarioResponse)
async def obtener_perfil(
    current_user: Usuario = Depends(get_current_active_user)
):
    """Obtiene el perfil del usuario autenticado"""
    return current_user

# ==================== CAMBIAR CONTRASEÑA ====================

@router.post("/cambiar-password", response_model=Message)
async def cambiar_password(
    password_data: PasswordChange,
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cambia la contraseña del usuario"""
    
    # Verificar contraseña actual
    if not verify_password(password_data.password_actual, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta"
        )
    
    # Actualizar contraseña
    current_user.password_hash = get_password_hash(password_data.password_nueva)
    db.commit()
    
    logger.info(f"Contraseña cambiada: {current_user.email}")
    
    return {
        "message": "Contraseña actualizada exitosamente",
        "success": True
    }

# ==================== RECUPERACIÓN DE CONTRASEÑA ====================

@router.post("/recuperar-password", response_model=Message)
async def solicitar_recuperacion_password(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Envía email para recuperar contraseña
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    
    if not usuario:
        # Por seguridad, no revelamos si el email existe
        return {
            "message": "Si el correo existe, recibirás un enlace de recuperación",
            "success": True
        }
    
    # Generar token
    reset_token = generate_verification_token()
    
    token_record = TokenVerificacion(
        usuario_id=usuario.id,
        token=reset_token,
        tipo="password_reset",
        fecha_expiracion=datetime.utcnow() + timedelta(hours=1)
    )
    
    db.add(token_record)
    db.commit()
    
    # TODO: Enviar email con enlace de recuperación
    logger.info(f"Recuperación de contraseña solicitada: {email}")
    
    return {
        "message": "Si el correo existe, recibirás un enlace de recuperación",
        "success": True
    }

@router.post("/resetear-password/{token}", response_model=Message)
async def resetear_password(
    token: str,
    nueva_password: str,
    db: Session = Depends(get_db)
):
    """
    Resetea la contraseña usando el token de recuperación
    """
    # Buscar token
    token_record = db.query(TokenVerificacion).filter(
        TokenVerificacion.token == token,
        TokenVerificacion.tipo == "password_reset",
        TokenVerificacion.usado == False
    ).first()
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o ya utilizado"
        )
    
    # Verificar expiración
    if datetime.utcnow() > token_record.fecha_expiracion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El token ha expirado"
        )
    
    # Actualizar contraseña
    usuario = db.query(Usuario).filter(Usuario.id == token_record.usuario_id).first()
    usuario.password_hash = get_password_hash(nueva_password)
    
    # Marcar token como usado
    token_record.usado = True
    
    db.commit()
    
    logger.info(f"Contraseña reseteada: {usuario.email}")
    
    return {
        "message": "Contraseña actualizada exitosamente",
        "success": True
    }