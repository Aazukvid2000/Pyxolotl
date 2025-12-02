"""
Utilidades para manejo de archivos
Upload local y a Cloudinary según tamaño
"""

import os
import cloudinary
import cloudinary.uploader
from fastapi import UploadFile
from app.config import settings
from app.utils.security import generate_unique_filename, sanitize_filename
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Configurar Cloudinary
if settings.CLOUDINARY_CLOUD_NAME:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET
    )
else:
    logger.warning("Cloudinary no configurado - solo almacenamiento local")

# Directorios de uploads
UPLOAD_DIR = "uploads"
JUEGOS_DIR = os.path.join(UPLOAD_DIR, "juegos")
AVATARES_DIR = os.path.join(UPLOAD_DIR, "avatares")
TEMP_DIR = os.path.join(UPLOAD_DIR, "temp")

# Crear directorios si no existen
for directory in [UPLOAD_DIR, JUEGOS_DIR, AVATARES_DIR, TEMP_DIR]:
    os.makedirs(directory, exist_ok=True)

class FileService:
    """Servicio para manejo de archivos"""
    
    @staticmethod
    def get_file_size_mb(file: UploadFile) -> float:
        """Obtiene el tamaño de un archivo en MB"""
        file.file.seek(0, 2)  # Ir al final
        size_bytes = file.file.tell()
        file.file.seek(0)  # Volver al inicio
        return size_bytes / (1024 * 1024)  # Convertir a MB
    
    @staticmethod
    async def save_local_file(
        file: UploadFile,
        subdirectory: str,
        prefix: str = ""
    ) -> str:
        """
        Guarda un archivo localmente
        
        Args:
            file: Archivo a guardar
            subdirectory: Subdirectorio dentro de uploads/
            prefix: Prefijo para el nombre del archivo
        
        Returns:
            Ruta relativa del archivo guardado
        """
        try:
            # Sanitizar y generar nombre único
            safe_filename = sanitize_filename(file.filename)
            unique_filename = generate_unique_filename(safe_filename, prefix)
            
            # Ruta completa
            directory = os.path.join(UPLOAD_DIR, subdirectory)
            os.makedirs(directory, exist_ok=True)
            
            file_path = os.path.join(directory, unique_filename)
            
            # Guardar archivo
            contents = await file.read()
            with open(file_path, "wb") as f:
                f.write(contents)
            
            # Resetear posición del archivo
            await file.seek(0)
            
            # Retornar ruta relativa (para guardar en BD)
            relative_path = os.path.join(subdirectory, unique_filename)
            
            logger.info(f"Archivo guardado localmente: {relative_path}")
            return f"/{UPLOAD_DIR}/{relative_path}"
            
        except Exception as e:
            logger.error(f"Error al guardar archivo local: {str(e)}")
            raise
    
    @staticmethod
    async def upload_to_cloudinary(
        file: UploadFile,
        folder: str,
        resource_type: str = "auto"
    ) -> Optional[str]:
        """
        Sube un archivo a Cloudinary
        
        Args:
            file: Archivo a subir
            folder: Carpeta en Cloudinary
            resource_type: Tipo de recurso (image, video, raw, auto)
        
        Returns:
            URL pública del archivo o None si falla
        """
        if not settings.CLOUDINARY_CLOUD_NAME:
            logger.warning("Cloudinary no configurado, usando almacenamiento local")
            return None
        
        try:
            # Leer contenido del archivo
            contents = await file.read()
            await file.seek(0)
            
            # Subir a Cloudinary
            result = cloudinary.uploader.upload(
                contents,
                folder=folder,
                resource_type=resource_type,
                use_filename=True,
                unique_filename=True
            )
            
            url = result.get("secure_url")
            logger.info(f"Archivo subido a Cloudinary: {url}")
            
            return url
            
        except Exception as e:
            logger.error(f"Error al subir a Cloudinary: {str(e)}")
            return None
    
    @staticmethod
    async def save_image(
        file: UploadFile,
        juego_id: Optional[int] = None,
        tipo: str = "screenshot"
    ) -> str:
        """
        Guarda una imagen (portada o screenshot)
        
        Args:
            file: Archivo de imagen
            juego_id: ID del juego (opcional)
            tipo: Tipo de imagen (portada, screenshot, avatar)
        
        Returns:
            URL pública de la imagen
        """
        # Validar tamaño
        size_mb = FileService.get_file_size_mb(file)
        if size_mb > settings.MAX_IMAGE_SIZE_MB:
            raise ValueError(f"Imagen muy grande. Máximo: {settings.MAX_IMAGE_SIZE_MB}MB")
        
        # Decidir dónde guardar según tamaño
        if size_mb > 2:  # Imágenes >2MB a Cloudinary
            folder = f"pyxolotl/juegos/{juego_id}" if juego_id else "pyxolotl/avatares"
            url = await FileService.upload_to_cloudinary(file, folder, "image")
            
            if url:
                return url
        
        # Fallback o imágenes pequeñas: guardar localmente
        if juego_id:
            subdirectory = f"juegos/{juego_id}/imagenes"
        else:
            subdirectory = "avatares"
        
        return await FileService.save_local_file(file, subdirectory, tipo)
    
    @staticmethod
    async def save_video(file: UploadFile, juego_id: int) -> str:
        """
        Guarda un video (trailer)
        
        Args:
            file: Archivo de video
            juego_id: ID del juego
        
        Returns:
            URL pública del video
        """
        # Validar tamaño
        size_mb = FileService.get_file_size_mb(file)
        if size_mb > settings.MAX_VIDEO_SIZE_MB:
            raise ValueError(f"Video muy grande. Máximo: {settings.MAX_VIDEO_SIZE_MB}MB")
        
        # Videos >10MB a Cloudinary (casi siempre)
        if size_mb > 10:
            folder = f"pyxolotl/juegos/{juego_id}"
            url = await FileService.upload_to_cloudinary(file, folder, "video")
            
            if url:
                return url
        
        # Fallback: local
        subdirectory = f"juegos/{juego_id}/videos"
        return await FileService.save_local_file(file, subdirectory, "trailer")
    
    @staticmethod
    async def save_game_file(file: UploadFile, juego_id: int) -> Tuple[str, float]:
        """
        Guarda el archivo del juego (.zip, .rar, etc.)
        SIEMPRE sube a Cloudinary para evitar pérdida de archivos en Railway
        
        Args:
            file: Archivo del juego
            juego_id: ID del juego
        
        Returns:
            Tupla (URL, tamaño en MB)
        """
        # Validar tamaño
        size_mb = FileService.get_file_size_mb(file)
        if size_mb > settings.MAX_GAME_SIZE_MB:
            raise ValueError(f"Archivo muy grande. Máximo: {settings.MAX_GAME_SIZE_MB}MB")
        
        # SIEMPRE subir a Cloudinary (Railway no persiste archivos locales)
        folder = f"pyxolotl/juegos/{juego_id}/archivos"
        url = await FileService.upload_to_cloudinary(file, folder, "raw")
        
        if url:
            logger.info(f"Archivo de juego subido a Cloudinary: {url}")
            return url, size_mb
        
        # Solo usar local como último recurso (desarrollo sin Cloudinary)
        logger.warning("Cloudinary no disponible, usando almacenamiento local (NO RECOMENDADO para producción)")
        subdirectory = f"juegos/{juego_id}/archivos"
        url = await FileService.save_local_file(file, subdirectory, "game")
        
        return url, size_mb
    
    @staticmethod
    def delete_local_file(file_path: str) -> bool:
        """
        Elimina un archivo local
        
        Args:
            file_path: Ruta del archivo
        
        Returns:
            True si se eliminó exitosamente
        """
        try:
            # Remover el / inicial si existe
            if file_path.startswith('/'):
                file_path = file_path[1:]
            
            full_path = os.path.join(os.getcwd(), file_path)
            
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"Archivo eliminado: {file_path}")
                return True
            else:
                logger.warning(f"Archivo no encontrado: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error al eliminar archivo: {str(e)}")
            return False

# Instancia global
file_service = FileService()
