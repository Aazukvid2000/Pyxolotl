#!/usr/bin/env python3
"""
Script de Administración Avanzada para Pyxolotl
===============================================
Permite eliminar selectivamente:
- Usuario completo (con todos sus datos)
- Solo los juegos de un usuario (manteniendo su cuenta)
- Un juego específico
- Usuarios no verificados

También incluye funciones de utilidad para el panel de admin.

Uso: python admin_manager.py
"""

import sys
import os
import re
import json
from typing import List, Dict, Optional
from datetime import datetime

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Agregar el directorio backend al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database import SessionLocal
from app.models import (
    Usuario, TokenVerificacion, Resena, Compra, Juego, 
    CarritoItem, BibliotecaItem, DescargaLog, ItemCompra
)
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
    """Extrae el public_id de una URL de Cloudinary"""
    if not url or "cloudinary" not in url:
        return None
    
    try:
        pattern = r'/upload/(?:v\d+/)?(.+?)(?:\.\w+)?$'
        match = re.search(pattern, url)
        
        if match:
            public_id = match.group(1)
            public_id = re.sub(r'\.\w+$', '', public_id)
            return public_id
        
        return None
    except Exception as e:
        print(f"   ⚠️  Error extrayendo public_id de {url}: {e}")
        return None

def delete_cloudinary_resource(url: str, resource_type: str = "image") -> bool:
    """Elimina un recurso de Cloudinary"""
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
            print(f"   ⚠️  No se pudo eliminar: {public_id}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error al eliminar {public_id}: {e}")
        return False

def delete_cloudinary_folder(folder_path: str) -> int:
    """Elimina una carpeta completa de Cloudinary"""
    deleted_count = 0
    
    try:
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
                if "Resource not found" not in str(e):
                    pass
        
        try:
            cloudinary.api.delete_folder(folder_path)
            print(f"   ✅ Carpeta eliminada: {folder_path}")
        except:
            pass
            
    except Exception as e:
        print(f"   ❌ Error al limpiar carpeta {folder_path}: {e}")
    
    return deleted_count

# ==================== FUNCIONES DE LISTADO ====================

def listar_usuarios():
    """Muestra todos los usuarios"""
    db = SessionLocal()
    try:
        usuarios = db.query(Usuario).all()
        
        if not usuarios:
            print("No hay usuarios en la base de datos.")
            return
        
        print("\n" + "="*90)
        print("USUARIOS EN LA BASE DE DATOS:")
        print("="*90)
        print(f"{'ID':<5} {'Nombre':<20} {'Email':<30} {'Tipo':<12} {'Verificado':<10} {'Juegos':<8}")
        print("-"*90)
        
        for user in usuarios:
            verificado = "✅ Sí" if user.verificado else "❌ No"
            num_juegos = db.query(Juego).filter(Juego.desarrollador_id == user.id).count()
            print(f"{user.id:<5} {user.nombre[:18]:<20} {user.email[:28]:<30} {user.tipo_cuenta:<12} {verificado:<10} {num_juegos:<8}")
        
        print("="*90 + "\n")
        
    finally:
        db.close()

def listar_juegos(filtro_usuario_id: int = None):
    """Muestra todos los juegos, opcionalmente filtrados por usuario"""
    db = SessionLocal()
    try:
        query = db.query(Juego)
        if filtro_usuario_id:
            query = query.filter(Juego.desarrollador_id == filtro_usuario_id)
        
        juegos = query.all()
        
        if not juegos:
            print("No hay juegos que mostrar.")
            return
        
        print("\n" + "="*100)
        print("JUEGOS EN LA BASE DE DATOS:")
        print("="*100)
        print(f"{'ID':<5} {'Título':<30} {'Desarrollador':<20} {'Precio':<10} {'Estado':<12} {'Descargas':<10}")
        print("-"*100)
        
        for juego in juegos:
            dev_name = juego.desarrollador.nombre if juego.desarrollador else "Desconocido"
            precio_str = f"${juego.precio:.2f}" if juego.precio else "GRATIS"
            print(f"{juego.id:<5} {juego.titulo[:28]:<30} {dev_name[:18]:<20} {precio_str:<10} {juego.estado.value:<12} {juego.total_descargas or 0:<10}")
        
        print("="*100 + "\n")
        
    finally:
        db.close()

# ==================== FUNCIONES DE CONTEO ====================

def contar_relaciones_usuario(user_id: int, db) -> Dict[str, int]:
    """Cuenta registros relacionados de un usuario"""
    return {
        'tokens': db.query(TokenVerificacion).filter(TokenVerificacion.usuario_id == user_id).count(),
        'resenas': db.query(Resena).filter(Resena.usuario_id == user_id).count(),
        'compras': db.query(Compra).filter(Compra.usuario_id == user_id).count(),
        'juegos': db.query(Juego).filter(Juego.desarrollador_id == user_id).count(),
        'carrito': db.query(CarritoItem).filter(CarritoItem.usuario_id == user_id).count(),
        'biblioteca': db.query(BibliotecaItem).filter(BibliotecaItem.usuario_id == user_id).count(),
        'descargas': db.query(DescargaLog).filter(DescargaLog.usuario_id == user_id).count()
    }

def contar_relaciones_juego(juego_id: int, db) -> Dict[str, int]:
    """Cuenta registros relacionados de un juego"""
    return {
        'resenas': db.query(Resena).filter(Resena.juego_id == juego_id).count(),
        'items_compra': db.query(ItemCompra).filter(ItemCompra.juego_id == juego_id).count(),
        'carrito': db.query(CarritoItem).filter(CarritoItem.juego_id == juego_id).count(),
        'biblioteca': db.query(BibliotecaItem).filter(BibliotecaItem.juego_id == juego_id).count(),
        'descargas': db.query(DescargaLog).filter(DescargaLog.juego_id == juego_id).count()
    }

# ==================== FUNCIONES DE ELIMINACIÓN ====================

def eliminar_archivos_juego(juego: Juego) -> int:
    """Elimina los archivos de Cloudinary de un juego"""
    eliminados = 0
    
    # Portada
    if juego.portada_url and "cloudinary" in juego.portada_url:
        if delete_cloudinary_resource(juego.portada_url):
            eliminados += 1
    
    # Screenshots
    if juego.screenshots_urls:
        try:
            screenshots = json.loads(juego.screenshots_urls) if isinstance(juego.screenshots_urls, str) else juego.screenshots_urls
            for url in screenshots:
                if url and "cloudinary" in url:
                    if delete_cloudinary_resource(url):
                        eliminados += 1
        except:
            pass
    
    # Trailer (video)
    if juego.trailer_url and "cloudinary" in juego.trailer_url:
        if delete_cloudinary_resource(juego.trailer_url, "video"):
            eliminados += 1
    
    # Archivo del juego
    if juego.archivo_juego_url and "cloudinary" in juego.archivo_juego_url:
        if delete_cloudinary_resource(juego.archivo_juego_url, "raw"):
            eliminados += 1
    
    return eliminados

def eliminar_juego(juego_id: int, confirmar: bool = True) -> bool:
    """
    Elimina un juego específico con todas sus relaciones.
    
    ORDEN DE ELIMINACIÓN (hijos antes que padre):
    1. Reseñas del juego
    2. Items de compra que incluyan el juego
    3. Items de carrito
    4. Items de biblioteca
    5. Registros de descarga
    6. Archivos en Cloudinary
    7. El juego
    """
    db = SessionLocal()
    try:
        juego = db.query(Juego).filter(Juego.id == juego_id).first()
        
        if not juego:
            print(f"❌ No se encontró el juego con ID {juego_id}")
            return False
        
        relaciones = contar_relaciones_juego(juego_id, db)
        
        print(f"\n{'='*60}")
        print(f"JUEGO A ELIMINAR: {juego.titulo}")
        print(f"{'='*60}")
        print(f"ID: {juego.id}")
        print(f"Desarrollador: {juego.desarrollador.nombre if juego.desarrollador else 'N/A'}")
        print(f"\n📊 REGISTROS RELACIONADOS:")
        print(f"   - Reseñas: {relaciones['resenas']}")
        print(f"   - Items de compra: {relaciones['items_compra']}")
        print(f"   - Items en carrito: {relaciones['carrito']}")
        print(f"   - Items en biblioteca: {relaciones['biblioteca']}")
        print(f"   - Registros de descarga: {relaciones['descargas']}")
        
        if confirmar:
            confirmacion = input(f"\n⚠️  ¿Eliminar este juego? (escribe 'SI' para confirmar): ")
            if confirmacion != 'SI':
                print("❌ Operación cancelada")
                return False
        
        print("\n🗑️  Eliminando registros...")
        
        # 1. Eliminar reseñas
        if relaciones['resenas'] > 0:
            db.query(Resena).filter(Resena.juego_id == juego_id).delete()
            print(f"   ✅ {relaciones['resenas']} reseñas eliminadas")
        
        # 2. Eliminar items de compra
        if relaciones['items_compra'] > 0:
            db.query(ItemCompra).filter(ItemCompra.juego_id == juego_id).delete()
            print(f"   ✅ {relaciones['items_compra']} items de compra eliminados")
        
        # 3. Eliminar items de carrito
        if relaciones['carrito'] > 0:
            db.query(CarritoItem).filter(CarritoItem.juego_id == juego_id).delete()
            print(f"   ✅ {relaciones['carrito']} items de carrito eliminados")
        
        # 4. Eliminar items de biblioteca
        if relaciones['biblioteca'] > 0:
            db.query(BibliotecaItem).filter(BibliotecaItem.juego_id == juego_id).delete()
            print(f"   ✅ {relaciones['biblioteca']} items de biblioteca eliminados")
        
        # 5. Eliminar registros de descarga
        if relaciones['descargas'] > 0:
            db.query(DescargaLog).filter(DescargaLog.juego_id == juego_id).delete()
            print(f"   ✅ {relaciones['descargas']} registros de descarga eliminados")
        
        # 6. Eliminar archivos de Cloudinary
        print("\n☁️  Eliminando archivos de Cloudinary...")
        archivos_eliminados = eliminar_archivos_juego(juego)
        print(f"   ✅ {archivos_eliminados} archivos eliminados")
        
        # 7. Eliminar el juego
        db.delete(juego)
        db.commit()
        
        print(f"\n✅✅✅ Juego '{juego.titulo}' eliminado completamente")
        return True
        
    except Exception as e:
        print(f"\n❌ Error al eliminar juego: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def eliminar_juegos_de_usuario(user_id: int) -> bool:
    """Elimina SOLO los juegos de un usuario (mantiene la cuenta)"""
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        
        if not usuario:
            print(f"❌ No se encontró el usuario con ID {user_id}")
            return False
        
        juegos = db.query(Juego).filter(Juego.desarrollador_id == user_id).all()
        
        if not juegos:
            print(f"ℹ️  El usuario {usuario.nombre} no tiene juegos publicados")
            return True
        
        print(f"\n{'='*60}")
        print(f"JUEGOS DEL USUARIO: {usuario.nombre}")
        print(f"{'='*60}")
        
        for juego in juegos:
            print(f"   - [{juego.id}] {juego.titulo}")
        
        confirmacion = input(f"\n⚠️  ¿Eliminar los {len(juegos)} juegos de este usuario? (escribe 'SI'): ")
        if confirmacion != 'SI':
            print("❌ Operación cancelada")
            return False
        
        eliminados = 0
        for juego in juegos:
            print(f"\n--- Eliminando: {juego.titulo} ---")
            if eliminar_juego(juego.id, confirmar=False):
                eliminados += 1
        
        print(f"\n✅✅✅ {eliminados}/{len(juegos)} juegos eliminados")
        print(f"      La cuenta del usuario '{usuario.nombre}' se mantiene activa")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    finally:
        db.close()

def eliminar_usuario_completo(user_id: int) -> bool:
    """
    Elimina un usuario con TODAS sus relaciones.
    
    ORDEN DE ELIMINACIÓN (hijos antes que padre):
    1. Tokens de verificación
    2. Reseñas escritas por el usuario
    3. Items de carrito
    4. Items de biblioteca
    5. Registros de descarga
    6. Items de compra
    7. Compras
    8. Juegos publicados (con sus relaciones)
    9. Avatar en Cloudinary
    10. El usuario
    """
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        
        if not usuario:
            print(f"❌ No se encontró el usuario con ID {user_id}")
            return False
        
        relaciones = contar_relaciones_usuario(user_id, db)
        
        print(f"\n{'='*60}")
        print(f"⚠️  ADVERTENCIA: ELIMINACIÓN COMPLETA DE USUARIO")
        print(f"{'='*60}")
        print(f"Nombre: {usuario.nombre}")
        print(f"Email: {usuario.email}")
        print(f"Tipo: {usuario.tipo_cuenta}")
        print(f"\n📊 REGISTROS QUE SE ELIMINARÁN:")
        print(f"   - Tokens: {relaciones['tokens']}")
        print(f"   - Reseñas: {relaciones['resenas']}")
        print(f"   - Compras: {relaciones['compras']}")
        print(f"   - Juegos publicados: {relaciones['juegos']}")
        print(f"   - Items en carrito: {relaciones['carrito']}")
        print(f"   - Items en biblioteca: {relaciones['biblioteca']}")
        print(f"   - Registros de descarga: {relaciones['descargas']}")
        
        confirmacion = input("\n⚠️  Escribe 'ELIMINAR USUARIO' para confirmar: ")
        if confirmacion != 'ELIMINAR USUARIO':
            print("❌ Operación cancelada")
            return False
        
        print("\n🗑️  Eliminando registros...")
        
        # 1. Tokens
        if relaciones['tokens'] > 0:
            db.query(TokenVerificacion).filter(TokenVerificacion.usuario_id == user_id).delete()
            print(f"   ✅ {relaciones['tokens']} tokens eliminados")
        
        # 2. Reseñas del usuario
        if relaciones['resenas'] > 0:
            db.query(Resena).filter(Resena.usuario_id == user_id).delete()
            print(f"   ✅ {relaciones['resenas']} reseñas eliminadas")
        
        # 3. Items de carrito
        if relaciones['carrito'] > 0:
            db.query(CarritoItem).filter(CarritoItem.usuario_id == user_id).delete()
            print(f"   ✅ {relaciones['carrito']} items de carrito eliminados")
        
        # 4. Items de biblioteca
        if relaciones['biblioteca'] > 0:
            db.query(BibliotecaItem).filter(BibliotecaItem.usuario_id == user_id).delete()
            print(f"   ✅ {relaciones['biblioteca']} items de biblioteca eliminados")
        
        # 5. Registros de descarga
        if relaciones['descargas'] > 0:
            db.query(DescargaLog).filter(DescargaLog.usuario_id == user_id).delete()
            print(f"   ✅ {relaciones['descargas']} registros de descarga eliminados")
        
        # 6-7. Compras y sus items
        if relaciones['compras'] > 0:
            # Primero eliminar items de compra
            compras_ids = [c.id for c in db.query(Compra).filter(Compra.usuario_id == user_id).all()]
            for compra_id in compras_ids:
                db.query(ItemCompra).filter(ItemCompra.compra_id == compra_id).delete()
            db.query(Compra).filter(Compra.usuario_id == user_id).delete()
            print(f"   ✅ {relaciones['compras']} compras eliminadas")
        
        # 8. Juegos publicados
        if relaciones['juegos'] > 0:
            juegos = db.query(Juego).filter(Juego.desarrollador_id == user_id).all()
            for juego in juegos:
                # Eliminar relaciones del juego
                db.query(Resena).filter(Resena.juego_id == juego.id).delete()
                db.query(ItemCompra).filter(ItemCompra.juego_id == juego.id).delete()
                db.query(CarritoItem).filter(CarritoItem.juego_id == juego.id).delete()
                db.query(BibliotecaItem).filter(BibliotecaItem.juego_id == juego.id).delete()
                db.query(DescargaLog).filter(DescargaLog.juego_id == juego.id).delete()
                
                # Eliminar archivos de Cloudinary
                eliminar_archivos_juego(juego)
                
                # Eliminar el juego
                db.delete(juego)
            print(f"   ✅ {relaciones['juegos']} juegos eliminados")
        
        # 9. Avatar en Cloudinary
        if usuario.avatar_url and "cloudinary" in usuario.avatar_url:
            delete_cloudinary_resource(usuario.avatar_url)
            print("   ✅ Avatar eliminado de Cloudinary")
        
        # 10. El usuario
        db.delete(usuario)
        db.commit()
        
        print(f"\n✅✅✅ Usuario '{usuario.nombre}' completamente eliminado")
        return True
        
    except Exception as e:
        print(f"\n❌ Error al eliminar usuario: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def limpiar_usuarios_no_verificados():
    """Elimina todos los usuarios no verificados"""
    db = SessionLocal()
    try:
        usuarios = db.query(Usuario).filter(Usuario.verificado == False).all()
        
        if not usuarios:
            print("✅ No hay usuarios sin verificar")
            return
        
        print(f"\n⚠️  Se encontraron {len(usuarios)} usuarios sin verificar:")
        for user in usuarios:
            print(f"   - {user.nombre} ({user.email})")
        
        confirmacion = input("\n¿Eliminar TODOS? (escribe 'SI'): ")
        if confirmacion != 'SI':
            print("❌ Operación cancelada")
            return
        
        eliminados = 0
        for user in usuarios:
            print(f"\n--- Eliminando: {user.nombre} ---")
            
            # Eliminar tokens
            db.query(TokenVerificacion).filter(TokenVerificacion.usuario_id == user.id).delete()
            
            # Eliminar avatar si existe
            if user.avatar_url and "cloudinary" in user.avatar_url:
                delete_cloudinary_resource(user.avatar_url)
            
            # Eliminar usuario
            db.delete(user)
            eliminados += 1
        
        db.commit()
        print(f"\n✅✅✅ {eliminados} usuarios no verificados eliminados")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

# ==================== MENÚ INTERACTIVO ====================

def menu_principal():
    """Menú principal del script"""
    while True:
        print("\n" + "="*70)
        print("🎮 ADMINISTRADOR DE PYXOLOTL")
        print("="*70)
        print("1. 📋 Listar usuarios")
        print("2. 🎮 Listar juegos")
        print("3. 🗑️  Eliminar un JUEGO específico")
        print("4. 🎯 Eliminar SOLO los juegos de un usuario")
        print("5. 💀 Eliminar usuario COMPLETO (todo)")
        print("6. 🧹 Limpiar usuarios no verificados")
        print("7. 🔍 Ver juegos de un usuario")
        print("8. ❌ Salir")
        print("="*70)
        
        opcion = input("\nSelecciona una opción (1-8): ").strip()
        
        if opcion == '1':
            listar_usuarios()
            
        elif opcion == '2':
            listar_juegos()
            
        elif opcion == '3':
            listar_juegos()
            try:
                juego_id = int(input("\nID del juego a eliminar: "))
                eliminar_juego(juego_id)
            except ValueError:
                print("❌ ID inválido")
                
        elif opcion == '4':
            listar_usuarios()
            try:
                user_id = int(input("\nID del usuario: "))
                eliminar_juegos_de_usuario(user_id)
            except ValueError:
                print("❌ ID inválido")
                
        elif opcion == '5':
            listar_usuarios()
            try:
                user_id = int(input("\nID del usuario a eliminar COMPLETAMENTE: "))
                eliminar_usuario_completo(user_id)
            except ValueError:
                print("❌ ID inválido")
                
        elif opcion == '6':
            limpiar_usuarios_no_verificados()
            
        elif opcion == '7':
            listar_usuarios()
            try:
                user_id = int(input("\nID del usuario: "))
                listar_juegos(filtro_usuario_id=user_id)
            except ValueError:
                print("❌ ID inválido")
                
        elif opcion == '8':
            print("\n👋 ¡Hasta luego!")
            break
            
        else:
            print("❌ Opción inválida")

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║          ADMINISTRADOR DE PYXOLOTL v2.0                     ║
    ║                                                              ║
    ║  Este script permite eliminar selectivamente:               ║
    ║  • Un juego específico                                      ║
    ║  • Solo los juegos de un usuario                           ║
    ║  • Un usuario completo con todo                            ║
    ║  • Usuarios no verificados                                  ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    if not os.getenv("CLOUDINARY_CLOUD_NAME"):
        print("⚠️  ADVERTENCIA: Cloudinary no configurado")
        print("   Solo se eliminarán registros de MySQL\n")
    
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\n❌ Operación cancelada")
        sys.exit(0)
