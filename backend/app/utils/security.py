"""
Utilidades de seguridad
Manejo de JWT tokens y encriptación de contraseñas
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
import secrets

# Contexto para hash de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ==================== PASSWORD HASHING ====================

def get_password_hash(password: str) -> str:
    """Encripta una contraseña usando bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña coincide con su hash"""
    return pwd_context.verify(plain_password, hashed_password)

# ==================== JWT TOKENS ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un token JWT de acceso
    
    Args:
        data: Datos a incluir en el token (ej: {"sub": "usuario@email.com"})
        expires_delta: Tiempo de expiración (opcional)
    
    Returns:
        Token JWT como string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodifica y verifica un token JWT
    
    Args:
        token: Token JWT a decodificar
    
    Returns:
        Datos del token o None si es inválido
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None

# ==================== TOKENS DE VERIFICACIÓN ====================

def generate_verification_token() -> str:
    """
    Genera un token seguro para verificación de email o reset de contraseña
    
    Returns:
        Token aleatorio de 32 caracteres hexadecimales
    """
    return secrets.token_urlsafe(32)

def is_token_expired(expiration_date: datetime) -> bool:
    """
    Verifica si un token ha expirado
    
    Args:
        expiration_date: Fecha de expiración del token
    
    Returns:
        True si expiró, False si aún es válido
    """
    return datetime.utcnow() > expiration_date

# ==================== VALIDACIONES ====================

def validate_file_extension(filename: str, allowed_extensions: list) -> bool:
    """
    Valida que un archivo tenga una extensión permitida
    
    Args:
        filename: Nombre del archivo
        allowed_extensions: Lista de extensiones permitidas (sin punto)
    
    Returns:
        True si la extensión es válida
    """
    if '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in allowed_extensions

def sanitize_filename(filename: str) -> str:
    """
    Sanitiza un nombre de archivo para evitar problemas de seguridad
    
    Args:
        filename: Nombre original del archivo
    
    Returns:
        Nombre sanitizado
    """
    # Remueve caracteres peligrosos
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    return filename

def generate_unique_filename(original_filename: str, prefix: str = "") -> str:
    """
    Genera un nombre de archivo único
    
    Args:
        original_filename: Nombre original del archivo
        prefix: Prefijo opcional
    
    Returns:
        Nombre único con timestamp y token aleatorio
    """
    import os
    from datetime import datetime
    
    # Obtener extensión
    _, ext = os.path.splitext(original_filename)
    
    # Generar timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Token aleatorio corto
    random_token = secrets.token_hex(4)
    
    # Combinar
    if prefix:
        return f"{prefix}_{timestamp}_{random_token}{ext}"
    else:
        return f"{timestamp}_{random_token}{ext}"
