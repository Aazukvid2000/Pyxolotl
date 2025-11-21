#!/usr/bin/env python3
"""
Script para eliminar usuarios con todas sus relaciones en Pyxolotl
Elimina: tokens, reseñas, compras, juegos del usuario
Uso: python delete_user_complete.py
"""

import sys
import os

# Agregar el directorio backend al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database import SessionLocal
from app.models import Usuario, TokenVerificacion, Resena, Compra, Juego
from sqlalchemy import or_

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
            verificado = "✅ Sí" if user.verified else "❌ No"
            print(f"{user.id:<5} {user.nombre:<25} {user.email:<30} {user.tipo_cuenta:<15} {verificado:<10}")
        
        print("="*80 + "\n")
        
    finally:
        db.close()

def contar_relaciones(user_id, db):
    """Cuenta cuántos registros relacionados tiene el usuario"""
    tokens = db.query(TokenVerificacion).filter(TokenVerificacion.usuario_id == user_id).count()
    resenas = db.query(Resena).filter(Resena.usuario_id == user_id).count()
    compras = db.query(Compra).filter(Compra.usuario_id == user_id).count()
    juegos = db.query(Juego).filter(Juego.desarrollador_id == user_id).count()
    
    return {
        'tokens': tokens,
        'resenas': resenas,
        'compras': compras,
        'juegos': juegos
    }

def eliminar_usuario_completo(user_id):
    """Elimina un usuario y TODAS sus relaciones"""
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        
        if not usuario:
            print(f"❌ No se encontró ningún usuario con ID {user_id}")
            return False
        
        # Contar relaciones
        relaciones = contar_relaciones(user_id, db)
        
        # Mostrar información del usuario a eliminar
        print(f"\n⚠️  VAS A ELIMINAR AL SIGUIENTE USUARIO Y TODOS SUS DATOS:")
        print(f"   ID: {usuario.id}")
        print(f"   Nombre: {usuario.nombre}")
        print(f"   Email: {usuario.email}")
        print(f"   Tipo: {usuario.tipo_cuenta}")
        print(f"\n📊 REGISTROS RELACIONADOS QUE SE ELIMINARÁN:")
        print(f"   - Tokens de verificación: {relaciones['tokens']}")
        print(f"   - Reseñas: {relaciones['resenas']}")
        print(f"   - Compras: {relaciones['compras']}")
        print(f"   - Juegos publicados: {relaciones['juegos']}")
        print(f"\n   TOTAL: {sum(relaciones.values())} registros relacionados")
        
        confirmacion = input("\n¿Estás ABSOLUTAMENTE seguro? Escribe 'ELIMINAR TODO' para confirmar: ")
        
        if confirmacion != 'ELIMINAR TODO':
            print("❌ Operación cancelada")
            return False
        
        print("\n🗑️  Eliminando registros relacionados...")
        
        # 1. Eliminar tokens de verificación
        if relaciones['tokens'] > 0:
            db.query(TokenVerificacion).filter(TokenVerificacion.usuario_id == user_id).delete()
            print(f"   ✅ {relaciones['tokens']} tokens eliminados")
        
        # 2. Eliminar reseñas
        if relaciones['resenas'] > 0:
            db.query(Resena).filter(Resena.usuario_id == user_id).delete()
            print(f"   ✅ {relaciones['resenas']} reseñas eliminadas")
        
        # 3. Eliminar compras
        if relaciones['compras'] > 0:
            db.query(Compra).filter(Compra.usuario_id == user_id).delete()
            print(f"   ✅ {relaciones['compras']} compras eliminadas")
        
        # 4. Eliminar juegos publicados
        if relaciones['juegos'] > 0:
            db.query(Juego).filter(Juego.desarrollador_id == user_id).delete()
            print(f"   ✅ {relaciones['juegos']} juegos eliminados")
        
        # 5. Finalmente, eliminar el usuario
        db.delete(usuario)
        db.commit()
        
        print(f"\n✅✅✅ Usuario '{usuario.nombre}' y todos sus datos eliminados exitosamente")
        return True
        
    except Exception as e:
        print(f"\n❌ Error al eliminar usuario: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def eliminar_usuario_por_email(email):
    """Elimina un usuario por su email"""
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.email == email).first()
        
        if not usuario:
            print(f"❌ No se encontró ningún usuario con email {email}")
            return False
        
        # Usar la función de eliminación completa
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
        usuarios_no_verificados = db.query(Usuario).filter(Usuario.verified == False).all()
        
        if not usuarios_no_verificados:
            print("✅ No hay usuarios sin verificar")
            return
        
        print(f"\n⚠️  Se encontraron {len(usuarios_no_verificados)} usuarios sin verificar:")
        for user in usuarios_no_verificados:
            print(f"   - {user.nombre} ({user.email})")
        
        confirmacion = input("\n¿Eliminar TODOS estos usuarios? Escribe 'SI' para confirmar: ")
        
        if confirmacion != 'SI':
            print("❌ Operación cancelada")
            return
        
        eliminados = 0
        for user in usuarios_no_verificados:
            # Eliminar tokens primero
            db.query(TokenVerificacion).filter(TokenVerificacion.usuario_id == user.id).delete()
            # Eliminar usuario
            db.delete(user)
            eliminados += 1
        
        db.commit()
        print(f"\n✅ {eliminados} usuarios no verificados eliminados")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

def menu_principal():
    """Menú principal del script"""
    while True:
        print("\n" + "="*60)
        print("GESTOR DE USUARIOS - PYXOLOTL (Con eliminación completa)")
        print("="*60)
        print("1. Listar todos los usuarios")
        print("2. Eliminar usuario por ID (+ todas sus relaciones)")
        print("3. Eliminar usuario por Email (+ todas sus relaciones)")
        print("4. Limpiar usuarios no verificados")
        print("5. Salir")
        print("="*60)
        
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
    ║  ⚠️  Este script elimina el usuario Y todos sus datos    ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\n❌ Operación cancelada por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)