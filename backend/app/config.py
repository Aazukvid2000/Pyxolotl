"""
Configuración de la aplicación Pyxolotl
Maneja variables de entorno y configuraciones globales
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Información de la aplicación
    APP_NAME: str = "Pyxolotl"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Base de datos MySQL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:password@localhost:3306/pyxolotl"
    )
    
    # JWT Autenticación
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "pyxolotl-secret-key-change-in-production-2025"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 días
    
    # CORS (permite requests desde el frontend)
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://pyxolotl.railway.app",
        "https://pyxolotl-backend.railway.app",
        "https://pyxolotl-frontend-production.up.railway.app",
        "https://pyxolotl-production.up.railway.app"
    ]
    
    # SendGrid (Email)
    SENDGRID_API_KEY: Optional[str] = os.getenv("SENDGRID_API_KEY")
    SENDGRID_FROM_EMAIL: str = os.getenv(
        "SENDGRID_FROM_EMAIL",
        "noreply@pyxolotl.com"
    )
    SENDGRID_FROM_NAME: str = "Pyxolotl"
    
    # Cloudinary (Almacenamiento de archivos)
    CLOUDINARY_CLOUD_NAME: Optional[str] = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: Optional[str] = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: Optional[str] = os.getenv("CLOUDINARY_API_SECRET")
    
    # Archivos - Límites
    MAX_IMAGE_SIZE_MB: int = 5
    MAX_VIDEO_SIZE_MB: int = 50
    MAX_GAME_SIZE_MB: int = 500
    
    # Archivos - Formatos permitidos
    ALLOWED_IMAGE_FORMATS: list = ["jpg", "jpeg", "png", "webp"]
    ALLOWED_VIDEO_FORMATS: list = ["mp4", "webm"]
    ALLOWED_GAME_FORMATS: list = ["zip", "rar", "7z", "exe"]
    
    # URLs
    FRONTEND_URL: str = os.getenv(
        "FRONTEND_URL",
        "http://localhost:3000"
    )
    BACKEND_URL: str = os.getenv(
        "BACKEND_URL",
        "http://localhost:8000"
    )
    
    # Email templates
    EMAIL_VERIFICATION_SUBJECT: str = "Verifica tu cuenta - Pyxolotl"
    EMAIL_PURCHASE_SUBJECT: str = "Confirmación de compra - Pyxolotl"
    EMAIL_GAME_APPROVED_SUBJECT: str = "Tu juego ha sido aprobado - Pyxolotl"
    EMAIL_GAME_REJECTED_SUBJECT: str = "Tu juego necesita cambios - Pyxolotl"
    
    # Paginación
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Anthropic Claude API (Búsqueda Inteligente)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    
    # Stripe (Pagos)
    STRIPE_SECRET_KEY: Optional[str] = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY: Optional[str] = os.getenv("STRIPE_PUBLISHABLE_KEY")
    
    # Administrador inicial
    ADMIN_EMAIL: str = "sinuhevidals@gmail.com"
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "PyxolotlAdmin2025!")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Instancia global de configuración
settings = Settings()