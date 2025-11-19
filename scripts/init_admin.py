"""
Script para crear o promocionar usuario administrador
Ejecutar después del primer deployment
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Usuario, TipoCuenta
from app.utils.security import get_password_hash
from app.config import settings

def init_admin():
    db = SessionLocal()
    
    try:
        # Buscar si ya existe el usuario con ese email
        admin_user = db.query(Usuario).filter(
            Usuario.email == settings.ADMIN_EMAIL
        ).first()
        
        if admin_user:
            # Usuario existe, promocionar a admin si no lo es
            if admin_user.tipo_cuenta != TipoCuenta.ADMINISTRADOR:
                admin_user.tipo_cuenta = TipoCuenta.ADMINISTRADOR
                admin_user.verificado = True
                db.commit()
                print(f"✅ Usuario {settings.ADMIN_EMAIL} promocionado a administrador")
            else:
                print(f"ℹ️  Usuario {settings.ADMIN_EMAIL} ya es administrador")
        
        else:
            # Crear nuevo usuario administrador
            new_admin = Usuario(
                nombre="Administrador",
                email=settings.ADMIN_EMAIL,
                password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                tipo_cuenta=TipoCuenta.ADMINISTRADOR,
                verificado=True
            )
            
            db.add(new_admin)
            db.commit()
            
            print(f"✅ Usuario administrador creado:")
            print(f"   Email: {settings.ADMIN_EMAIL}")
            print(f"   Password: {settings.ADMIN_PASSWORD}")
            print(f"   ⚠️  CAMBIA LA CONTRASEÑA DESPUÉS DEL PRIMER LOGIN")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
    
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Inicializando administrador...")
    init_admin()
    print("✨ Proceso completado")
