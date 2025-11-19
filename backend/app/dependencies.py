"""
Dependencias de autenticación
Funciones reutilizables para proteger endpoints
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario, TipoCuenta
from app.utils.security import decode_access_token
from typing import Optional

# Esquema de seguridad Bearer
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Usuario:
    """
    Obtiene el usuario actual desde el token JWT
    
    Raises:
        HTTPException: Si el token es inválido o el usuario no existe
    
    Returns:
        Usuario autenticado
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Decodificar token
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise credentials_exception
    
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    
    # Buscar usuario en BD
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    
    if usuario is None:
        raise credentials_exception
    
    return usuario

async def get_current_active_user(
    current_user: Usuario = Depends(get_current_user)
) -> Usuario:
    """
    Verifica que el usuario esté verificado
    
    Raises:
        HTTPException: Si el usuario no está verificado
    
    Returns:
        Usuario verificado
    """
    if not current_user.verificado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta no verificada. Por favor verifica tu email."
        )
    
    return current_user

async def get_current_developer(
    current_user: Usuario = Depends(get_current_active_user)
) -> Usuario:
    """
    Verifica que el usuario sea desarrollador o administrador
    
    Raises:
        HTTPException: Si no tiene permisos de desarrollador
    
    Returns:
        Usuario desarrollador
    """
    if current_user.tipo_cuenta not in [TipoCuenta.DESARROLLADOR, TipoCuenta.ADMINISTRADOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere cuenta de desarrollador"
        )
    
    return current_user

async def get_current_admin(
    current_user: Usuario = Depends(get_current_active_user)
) -> Usuario:
    """
    Verifica que el usuario sea administrador
    
    Raises:
        HTTPException: Si no es administrador
    
    Returns:
        Usuario administrador
    """
    if current_user.tipo_cuenta != TipoCuenta.ADMINISTRADOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador"
        )
    
    return current_user

def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[Usuario]:
    """
    Obtiene el usuario actual si está autenticado, None si no
    Útil para endpoints que funcionan con o sin autenticación
    
    Returns:
        Usuario o None
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        
        if payload is None:
            return None
        
        email: str = payload.get("sub")
        if email is None:
            return None
        
        usuario = db.query(Usuario).filter(Usuario.email == email).first()
        return usuario
        
    except:
        return None
