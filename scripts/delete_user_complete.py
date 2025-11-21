#!/usr/bin/env python3
"""
Script para eliminar usuarios con todas sus relaciones en Pyxolotl
Elimina: MySQL (tokens, reseñas, compras, juegos) + Cloudinary (archivos)
Uso: python delete_user_complete.py
"""

import sys
import os
import re
import json
from typing import List, Dict, Optional

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Agregar el directorio backend al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database import SessionLocal
from app.models import Usuario, TokenVerificacion, Resena, Compra, Juego, CarritoItem, BibliotecaItem, DescargaLog
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Configurar Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# ==================== UTILIDADES CLOUDINARY ====================

def extract_public_id(url: str) -> Optional[str]:
    """
    Extrae el public_id de una URL de Cloudinary
    
    Ejemplos:
    https://res.cloudinary.com/dikxre04b/image/upload/v123/pyxolotl/avatares/foto.jpg
    -> pyxolotl/avatares/foto
    """
    if not url or "cloudinary" not in url:
        return None
    
    try:
        # Patrón: después de /upload/vXXX/ o /upload/
        pattern = r'/upload/(?:v\d+/)?(.+?)(?:\.\w+)?$'
        match = re.search(pattern, url)
        
        if match:
            public_id = match.group(1)
            # Remover extensión si quedó
            public_id = re.sub(r'\.\w+$', '', public_id)
            return public_id
        
        return None
    except Exception as e:
        print(f"   ⚠️  Error extrayendo public_id de {url}: {e}")
        return None

def delete_cloudinary_resource(url: str, resource_type: str = "image") -> bool:
    """
    Elimina un recurso de Cloudinary
    
    Args:
        url: URL del recurso
        resource_type: Tipo (image, video, raw)
    
    Returns:
        True si se eliminó exitosamente
    """
    public_id = extract_public_id(url)
    
    if not public_id:
        return False
    
    try:
        result = cloudinary.uploader.destroy(
            public_id,
            resource_type=resource_type,
            invalidate=True
        )
        
        if result.get("result") == "ok":
            print(f"   ✅ Eliminado de Cloudinary: {public_id}")
            return True
        else:
            print(f"   ⚠️  No se pudo eliminar: {public_id} - {result}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error al eliminar {public_id}: {e}")
        return False

def delete_cloudinary_folder(folder_path: str) -> int:
    """
    Elimina una carpeta completa de Cloudinary
    
    Args:
        folder_path: Ruta de la carpeta (ej: pyxolotl/juegos/123)
    
    Returns:
        Número de archivos eliminados
    """
    deleted_count = 0
    
    try:
        # Obtener todos los recursos en la carpeta
        for resource_type in ["image", "video", "raw"]:
            try:
                resources = cloudinary.api.resources(
                    type="upload",
                    prefix=folder_path,
                    resource_type=resource_type,
                    max_results=500
                )
                
                for resource in resources.get("resources", []):
                    public_id = resource["public_id"]
                    
                    try:
                        cloudinary.uploader.destroy(
                            public_id,
                            resource_type=resource_type,
                            invalidate=True
                        )
                        deleted_count += 1
                        print(f"   ✅ Eliminado: {public_id}")
                    except Exception as e:
                        print(f"   ⚠️  Error eliminando {public_id}: {e}")
                        
            except Exception as e:
                # Es normal si no hay recursos de ese tipo
                if "Resource not found" not in str(e):
                    print(f"   ⚠️  Error buscando {resource_type} en {folder_path}: {e}")
        
        # Intentar eliminar la carpeta vacía
        try:
            cloudinary.api.delete_folder(folder_path)
            print(f"   ✅ Carpeta eliminada: {folder_path}")
        except Exception as e:
            # Es normal si la carpeta no existe o no está vacía
            pass
            
    except Exception as e:
        print(f"   ❌ Error al limpiar carpeta {folder_path}: {e}")
    
    return deleted_count

# ==================== FUNCIONES DE BASE DE DATOS ====================

def listar_usuarios():
    """Muestra todos los usuarios en la base de datos"""
    db = SessionLocal()
    try:
        usuarios = db.query(Usuario).all()
        
        if not usuarios:
            print("No hay usuarios en la base de datos.")
            return
        
        print("\n" + "="*80)
        print("USUARIOS EN LA BASE DE DATOS:")
        print("="*80)
        print(f"{'ID':<5} {'Nombre':<25} {'Email':<30} {'Tipo':<15} {'Verificado':<10}")
        print("-"*80)
        
        for user in usuarios:
            verificado = "✅ Sí" if user.verificado else "❌ No"
            print(f"{user.id:<5} {user.nombre:<25} {user.email:<30} {user.tipo_cuenta:<15} {verificado:<10}")
        
        print("="*80 + "\n")
        
    finally:
        db.close()

def contar_relaciones(user_id: int, db) -> Dict[str, int]:
    """Cuenta cuántos registros relacionados tiene el usuario"""
    return {
        'tokens': db.query(TokenVerificacion).filter(TokenVerificacion.usuario_id == user_id).count(),
        'resenas': db.query(Resena).filter(Resena.usuario_id == user_id).count(),
        'compras': db.query(Compra).filter(Compra.usuario_id == user_id).count(),
        'juegos': db.query(Juego).filter(Juego.desarrollador_id == user_id).count(),
        'carrito': db.query(CarritoItem).filter(CarritoItem.usuario_id == user_id).count(),
        'biblioteca': db.query(BibliotecaItem).filter(BibliotecaItem.usuario_id == user_id).count(),
        'descargas': db.query(DescargaLog).filter(DescargaLog.usuario_id == user_id).count()
    }

def obtener_archivos_cloudinary_usuario(user_id: int, db) -> Dict[str, List[str]]:
    """
    Obtiene todas las URLs de Cloudinary asociadas al usuario
    
    Returns:
        Dict con listas de URLs por tipo de recurso
    """
    archivos = {
        'avatar': [],
        'juegos_imagenes': [],
        'juegos_videos': [],
        'juegos_archivos': [],
        'recibos': []
    }
    
    # 1. Avatar del usuario
    usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
    if usuario and usuario.avatar_url and "cloudinary" in usuario.avatar_url:
        archivos['avatar'].append(usuario.avatar_url)
    
    # 2. Archivos de juegos publicados por el usuario
    juegos = db.query(Juego).filter(Juego.desarrollador_id == user_id).all()
    
    for juego in juegos:
        # Portada
        if juego.portada_url and "cloudinary" in juego.portada_url:
            archivos['juegos_imagenes'].append(juego.portada_url)
        
        # Screenshots (JSON array)
        if juego.screenshots_urls:
            try:
                screenshots = json.loads(juego.screenshots_urls)
                for screenshot_url in screenshots:
                    if "cloudinary" in screenshot_url:
                        archivos['juegos_imagenes'].append(screenshot_url)
            except:
                pass
        
        # Trailer
        if juego.trailer_url and "cloudinary" in juego.trailer_url:
            archivos['juegos_videos'].append(juego.trailer_url)
        
        # Archivo del juego
        if juego.archivo_juego_url and "cloudinary" in juego.archivo_juego_url:
            archivos['juegos_archivos'].append(juego.archivo_juego_url)
    
    # 3. Recibos de compras
    compras = db.query(Compra).filter(Compra.usuario_id == user_id).all()
    for compra in compras:
        if compra.recibo_url and "cloudinary" in compra.recibo_url:
            archivos['recibos'].append(compra.recibo_url)
    
    return archivos

def limpiar_cloudinary_usuario(user_id: int, db) -> int:
    """
    Elimina todos los archivos de Cloudinary del usuario
    
    Returns:
        Número total de archivos eliminados
    """
    print(f"\n☁️  Limpiando archivos de Cloudinary...")
    
    archivos = obtener_archivos_cloudinary_usuario(user_id, db)
    total_eliminados = 0
    
    # Contar totales
    total_archivos = (
        len(archivos['avatar']) +
        len(archivos['juegos_imagenes']) +
        len(archivos['juegos_videos']) +
        len(archivos['juegos_archivos']) +
        len(archivos['recibos'])
    )
    
    if total_archivos == 0:
        print("   ℹ️  No hay archivos en Cloudinary para este usuario")
        return 0
    
    print(f"   📊 Archivos encontrados en Cloudinary:")
    print(f"      - Avatar: {len(archivos['avatar'])}")
    print(f"      - Imágenes de juegos: {len(archivos['juegos_imagenes'])}")
    print(f"      - Videos de juegos: {len(archivos['juegos_videos'])}")
    print(f"      - Archivos de juegos: {len(archivos['juegos_archivos'])}")
    print(f"      - Recibos: {len(archivos['recibos'])}")
    print(f"      TOTAL: {total_archivos} archivos\n")
    
    # Eliminar avatares
    for url in archivos['avatar']:
        if delete_cloudinary_resource(url, "image"):
            total_eliminados += 1
    
    # Eliminar imágenes de juegos
    for url in archivos['juegos_imagenes']:
        if delete_cloudinary_resource(url, "image"):
            total_eliminados += 1
    
    # Eliminar videos de juegos
    for url in archivos['juegos_videos']:
        if delete_cloudinary_resource(url, "video"):
            total_eliminados += 1
    
    # Eliminar archivos de juegos
    for url in archivos['juegos_archivos']:
        if delete_cloudinary_resource(url, "raw"):
            total_eliminados += 1
    
    # Eliminar recibos
    for url in archivos['recibos']:
        if delete_cloudinary_resource(url, "raw"):
            total_eliminados += 1
    
    # Eliminar carpetas de juegos del usuario
    juegos = db.query(Juego).filter(Juego.desarrollador_id == user_id).all()
    for juego in juegos:
        folder_path = f"pyxolotl/juegos/{juego.id}"
        deleted = delete_cloudinary_folder(folder_path)
        if deleted > 0:
            print(f"   ✅ Carpeta del juego {juego.id} limpiada: {deleted} archivos")
    
    return total_eliminados

def eliminar_usuario_completo(user_id: int) -> bool:
    """Elimina un usuario y TODAS sus relaciones (MySQL + Cloudinary)"""
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        
        if not usuario:
            print(f"❌ No se encontró ningún usuario con ID {user_id}")
            return False
        
        # Contar relaciones
        relaciones = contar_relaciones(user_id, db)
        
        # Obtener archivos de Cloudinary
        archivos = obtener_archivos_cloudinary_usuario(user_id, db)
        total_cloudinary = sum(len(urls) for urls in archivos.values())
        
        # Mostrar información del usuario a eliminar
        print(f"\n⚠️  VAS A ELIMINAR AL SIGUIENTE USUARIO Y TODOS SUS DATOS:")
        print(f"   ID: {usuario.id}")
        print(f"   Nombre: {usuario.nombre}")
        print(f"   Email: {usuario.email}")
        print(f"   Tipo: {usuario.tipo_cuenta}")
        
        print(f"\n📊 REGISTROS EN MySQL QUE SE ELIMINARÁN:")
        print(f"   - Tokens de verificación: {relaciones['tokens']}")
        print(f"   - Reseñas: {relaciones['resenas']}")
        print(f"   - Compras: {relaciones['compras']}")
        print(f"   - Juegos publicados: {relaciones['juegos']}")
        print(f"   - Items en carrito: {relaciones['carrito']}")
        print(f"   - Items en biblioteca: {relaciones['biblioteca']}")
        print(f"   - Registros de descarga: {relaciones['descargas']}")
        print(f"   TOTAL MySQL: {sum(relaciones.values())} registros")
        
        print(f"\n☁️  ARCHIVOS EN CLOUDINARY QUE SE ELIMINARÁN:")
        print(f"   - Avatar: {len(archivos['avatar'])}")
        print(f"   - Imágenes de juegos: {len(archivos['juegos_imagenes'])}")
        print(f"   - Videos de juegos: {len(archivos['juegos_videos'])}")
        print(f"   - Archivos de juegos: {len(archivos['juegos_archivos'])}")
        print(f"   - Recibos: {len(archivos['recibos'])}")
        print(f"   TOTAL Cloudinary: {total_cloudinary} archivos")
        
        print(f"\n💀 TOTAL GENERAL: {sum(relaciones.values()) + total_cloudinary + 1} elementos")
        
        confirmacion = input("\n¿Estás ABSOLUTAMENTE seguro? Escribe 'ELIMINAR TODO' para confirmar: ")
        
        if confirmacion != 'ELIMINAR TODO':
            print("❌ Operación cancelada")
            return False
        
        # PASO 1: Eliminar archivos de Cloudinary
        cloudinary_eliminados = limpiar_cloudinary_usuario(user_id, db)
        print(f"\n✅ {cloudinary_eliminados} archivos eliminados de Cloudinary")
        
        # PASO 2: Eliminar registros de MySQL
        print("\n🗑️  Eliminando registros de MySQL...")
        
        # 2.1 Tokens
        if relaciones['tokens'] > 0:
            db.query(TokenVerificacion).filter(TokenVerificacion.usuario_id == user_id).delete()
            print(f"   ✅ {relaciones['tokens']} tokens eliminados")
        
        # 2.2 Reseñas
        if relaciones['resenas'] > 0:
            db.query(Resena).filter(Resena.usuario_id == user_id).delete()
            print(f"   ✅ {relaciones['resenas']} reseñas eliminadas")
        
        # 2.3 Items de carrito
        if relaciones['carrito'] > 0:
            db.query(CarritoItem).filter(CarritoItem.usuario_id == user_id).delete()
            print(f"   ✅ {relaciones['carrito']} items de carrito eliminados")
        
        # 2.4 Items de biblioteca
        if relaciones['biblioteca'] > 0:
            db.query(BibliotecaItem).filter(BibliotecaItem.usuario_id == user_id).delete()
            print(f"   ✅ {relaciones['biblioteca']} items de biblioteca eliminados")
        
        # 2.5 Registros de descarga
        if relaciones['descargas'] > 0:
            db.query(DescargaLog).filter(DescargaLog.usuario_id == user_id).delete()
            print(f"   ✅ {relaciones['descargas']} registros de descarga eliminados")
        
        # 2.6 Compras (con cascade a items_compra)
        if relaciones['compras'] > 0:
            db.query(Compra).filter(Compra.usuario_id == user_id).delete()
            print(f"   ✅ {relaciones['compras']} compras eliminadas")
        
        # 2.7 Juegos publicados (con cascade a reseñas, items, etc.)
        if relaciones['juegos'] > 0:
            db.query(Juego).filter(Juego.desarrollador_id == user_id).delete()
            print(f"   ✅ {relaciones['juegos']} juegos eliminados")
        
        # 2.8 Finalmente, eliminar el usuario
        db.delete(usuario)
        db.commit()
        
        print(f"\n✅✅✅ Usuario '{usuario.nombre}' completamente eliminado")
        print(f"      - MySQL: {sum(relaciones.values()) + 1} registros")
        print(f"      - Cloudinary: {cloudinary_eliminados} archivos")
        return True
        
    except Exception as e:
        print(f"\n❌ Error al eliminar usuario: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def eliminar_usuario_por_email(email: str) -> bool:
    """Elimina un usuario por su email"""
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.email == email).first()
        
        if not usuario:
            print(f"❌ No se encontró ningún usuario con email {email}")
            return False
        
        db.close()
        return eliminar_usuario_completo(usuario.id)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if db:
            db.close()

def limpiar_usuarios_no_verificados():
    """Elimina todos los usuarios que no han verificado su email"""
    db = SessionLocal()
    try:
        usuarios_no_verificados = db.query(Usuario).filter(Usuario.verificado == False).all()
        
        if not usuarios_no_verificados:
            print("✅ No hay usuarios sin verificar")
            return
        
        print(f"\n⚠️  Se encontraron {len(usuarios_no_verificados)} usuarios sin verificar:")
        for user in usuarios_no_verificados:
            print(f"   - {user.nombre} ({user.email})")
        
        confirmacion = input("\n¿Eliminar TODOS estos usuarios (incluyendo archivos)? Escribe 'SI' para confirmar: ")
        
        if confirmacion != 'SI':
            print("❌ Operación cancelada")
            return
        
        eliminados = 0
        for user in usuarios_no_verificados:
            print(f"\n--- Eliminando: {user.nombre} ---")
            
            # Limpiar Cloudinary
            cloudinary_count = limpiar_cloudinary_usuario(user.id, db)
            
            # Eliminar tokens
            db.query(TokenVerificacion).filter(TokenVerificacion.usuario_id == user.id).delete()
            
            # Eliminar usuario
            db.delete(user)
            eliminados += 1
            
            print(f"✅ Usuario eliminado ({cloudinary_count} archivos de Cloudinary)")
        
        db.commit()
        print(f"\n✅✅✅ {eliminados} usuarios no verificados eliminados completamente")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

# ==================== MENÚ ====================

def menu_principal():
    """Menú principal del script"""
    while True:
        print("\n" + "="*70)
        print("GESTOR DE USUARIOS - PYXOLOTL")
        print("(Eliminación completa: MySQL + Cloudinary)")
        print("="*70)
        print("1. Listar todos los usuarios")
        print("2. Eliminar usuario por ID (+ TODOS sus archivos)")
        print("3. Eliminar usuario por Email (+ TODOS sus archivos)")
        print("4. Limpiar usuarios no verificados (+ archivos)")
        print("5. Salir")
        print("="*70)
        
        opcion = input("\nSelecciona una opción (1-5): ").strip()
        
        if opcion == '1':
            listar_usuarios()
            
        elif opcion == '2':
            listar_usuarios()
            try:
                user_id = int(input("\nIngresa el ID del usuario a eliminar: "))
                eliminar_usuario_completo(user_id)
            except ValueError:
                print("❌ ID inválido. Debe ser un número.")
                
        elif opcion == '3':
            listar_usuarios()
            email = input("\nIngresa el email del usuario a eliminar: ").strip()
            if email:
                eliminar_usuario_por_email(email)
            else:
                print("❌ Email inválido")
        
        elif opcion == '4':
            limpiar_usuarios_no_verificados()
                
        elif opcion == '5':
            print("\n👋 ¡Hasta luego!")
            break
            
        else:
            print("❌ Opción inválida. Por favor selecciona 1-5.")

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║    SCRIPT DE ELIMINACIÓN COMPLETA DE USUARIOS             ║
    ║                    PYXOLOTL                               ║
    ║                                                           ║
    ║  ⚠️  Este script elimina:                                ║
    ║     • Usuario de MySQL                                   ║
    ║     • Todas sus relaciones (compras, juegos, etc.)      ║
    ║     • TODOS sus archivos en Cloudinary                   ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # Verificar configuración de Cloudinary
    if not os.getenv("CLOUDINARY_CLOUD_NAME"):
        print("⚠️  ADVERTENCIA: Cloudinary no configurado en .env")
        print("   Solo se eliminarán registros de MySQL\n")
        continuar = input("¿Deseas continuar de todos modos? (SI/NO): ")
        if continuar != "SI":
            print("❌ Operación cancelada")
            sys.exit(0)
    
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\n❌ Operación cancelada por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)