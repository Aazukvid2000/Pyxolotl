"""
Rutas de autenticación
Registro, login, verificación de email, recuperación de contraseña
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
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
from app.config import settings
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
        # No mostrar error técnico al usuario, validar email
        if "does not contain a valid email" in str(e) or "invalid" in str(e).lower():
            # Eliminar usuario si el email no es válido
            db.delete(new_user)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico no es válido"
            )
    
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

# ==================== VERIFICACIÓN DE EMAIL (PÁGINA HTML) ====================

@router.get("/verificar", response_class=HTMLResponse)
async def verificar_email_page(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Página HTML de verificación de email
    Muestra un mensaje visual de éxito o error al usuario
    """
    
    # Buscar el token en la base de datos
    token_db = db.query(TokenVerificacion).filter(
        TokenVerificacion.token == token,
        TokenVerificacion.tipo == "email"
    ).first()
    
    # Verificar si el token existe
    if not token_db:
        return HTML_ERROR_PAGE("El enlace de verificación no es válido o ha expirado.")
    
    # Verificar si el token ya fue usado
    if token_db.usado:
        return HTML_ALREADY_VERIFIED_PAGE()
    
    # Verificar si el token expiró (24 horas)
    if datetime.utcnow() > token_db.fecha_expiracion:
        return HTML_ERROR_PAGE("El enlace de verificación ha expirado. Por favor solicita uno nuevo.")
    
    # Buscar el usuario
    usuario = db.query(Usuario).filter(Usuario.id == token_db.usuario_id).first()
    
    if not usuario:
        return HTML_ERROR_PAGE("Usuario no encontrado.")
    
    # Si el usuario ya está verificado
    if usuario.verificado:
        return HTML_ALREADY_VERIFIED_PAGE()
    
    # Marcar el usuario como verificado
    usuario.verificado = True
    token_db.usado = True
    db.commit()
    
    logger.info(f"✅ Email verificado exitosamente: {usuario.email}")
    
    return HTML_SUCCESS_PAGE(usuario.nombre)


# ==================== VERIFICACIÓN DE EMAIL (API JSON) ====================

@router.get("/verificar/{token}", response_model=Message)
async def verificar_email(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Verifica el email del usuario mediante token (respuesta JSON)
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


# ==================== FUNCIONES AUXILIARES PARA HTML ====================

def HTML_SUCCESS_PAGE(nombre_usuario: str):
    """Página HTML de verificación exitosa"""
    
    frontend_url = settings.FRONTEND_URL
    
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>✅ Verificación Exitosa - Pyxolotl</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }}
            
            .container {{
                background: white;
                border-radius: 20px;
                padding: 60px 40px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-width: 500px;
                width: 100%;
                text-align: center;
                animation: slideUp 0.5s ease;
            }}
            
            @keyframes slideUp {{
                from {{
                    opacity: 0;
                    transform: translateY(30px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}
            
            .icon {{
                font-size: 100px;
                margin-bottom: 24px;
                animation: bounce 1s ease infinite;
            }}
            
            @keyframes bounce {{
                0%, 100% {{ transform: translateY(0); }}
                50% {{ transform: translateY(-15px); }}
            }}
            
            h1 {{
                font-size: 36px;
                color: #333;
                margin-bottom: 16px;
                font-weight: 700;
            }}
            
            p {{
                font-size: 18px;
                color: #666;
                margin-bottom: 32px;
                line-height: 1.6;
            }}
            
            .highlight {{
                color: #667eea;
                font-weight: 600;
            }}
            
            .btn {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                padding: 18px 48px;
                border-radius: 50px;
                font-size: 18px;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }}
            
            .btn:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">🎉</div>
            <h1>¡Cuenta Verificada!</h1>
            <p>
                ¡Bienvenido <span class="highlight">{nombre_usuario}</span>!<br>
                Tu cuenta ha sido verificada exitosamente.<br>
                Ya puedes iniciar sesión y comenzar a explorar.
            </p>
            <a href="{frontend_url}/inicio.html" class="btn">Iniciar Sesión</a>
        </div>
    </body>
    </html>
    """


def HTML_ALREADY_VERIFIED_PAGE():
    """Página HTML cuando la cuenta ya estaba verificada"""
    
    frontend_url = settings.FRONTEND_URL
    
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>✅ Cuenta Verificada - Pyxolotl</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }}
            
            .container {{
                background: white;
                border-radius: 20px;
                padding: 60px 40px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-width: 500px;
                width: 100%;
                text-align: center;
                animation: slideUp 0.5s ease;
            }}
            
            @keyframes slideUp {{
                from {{
                    opacity: 0;
                    transform: translateY(30px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}
            
            .icon {{
                font-size: 100px;
                margin-bottom: 24px;
            }}
            
            h1 {{
                font-size: 36px;
                color: #333;
                margin-bottom: 16px;
                font-weight: 700;
            }}
            
            p {{
                font-size: 18px;
                color: #666;
                margin-bottom: 32px;
                line-height: 1.6;
            }}
            
            .btn {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                padding: 18px 48px;
                border-radius: 50px;
                font-size: 18px;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }}
            
            .btn:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">✅</div>
            <h1>Cuenta Ya Verificada</h1>
            <p>
                Tu cuenta ya estaba verificada anteriormente.<br>
                Puedes iniciar sesión normalmente.
            </p>
            <a href="{frontend_url}/inicio.html" class="btn">Iniciar Sesión</a>
        </div>
    </body>
    </html>
    """


def HTML_ERROR_PAGE(error_message: str):
    """Página HTML de error en la verificación"""
    
    frontend_url = settings.FRONTEND_URL
    
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>❌ Error de Verificación - Pyxolotl</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }}
            
            .container {{
                background: white;
                border-radius: 20px;
                padding: 60px 40px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-width: 500px;
                width: 100%;
                text-align: center;
                animation: slideUp 0.5s ease;
            }}
            
            @keyframes slideUp {{
                from {{
                    opacity: 0;
                    transform: translateY(30px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}
            
            .icon {{
                font-size: 100px;
                color: #f44336;
                margin-bottom: 24px;
            }}
            
            h1 {{
                font-size: 36px;
                color: #333;
                margin-bottom: 16px;
                font-weight: 700;
            }}
            
            p {{
                font-size: 18px;
                color: #666;
                margin-bottom: 32px;
                line-height: 1.6;
            }}
            
            .btn {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                padding: 18px 48px;
                border-radius: 50px;
                font-size: 18px;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }}
            
            .btn:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">⚠️</div>
            <h1>Error de Verificación</h1>
            <p>{error_message}</p>
            <a href="{frontend_url}/inicio.html" class="btn">Regresar al Inicio</a>
        </div>
    </body>
    </html>
    """