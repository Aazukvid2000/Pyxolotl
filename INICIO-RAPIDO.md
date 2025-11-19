# 🎮 Pyxolotl - Inicio Rápido

## 📦 ¿Qué contiene este proyecto?

```
pyxolotl-project/
├── backend/           # API FastAPI + Python
├── frontend/          # HTML/CSS/JS
├── scripts/           # Scripts de inicialización  
├── docs/              # Documentación completa
└── railway.json       # Configuración de deployment
```

## 🚀 Desplegar en 3 Pasos

### 1. Crea las cuentas necesarias (15 min)
- Railway: https://railway.app
- SendGrid: https://sendgrid.com
- Cloudinary: https://cloudinary.com

### 2. Sube a GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/Aazukvid2000/Pyxolotl.git
git push -u origin main
```

### 3. Despliega en Railway
1. Nuevo proyecto → Desde GitHub
2. Agrega MySQL database
3. Configura variables de entorno (ver `.env.example`)
4. Deploy automático ✅

## 📖 Documentación Completa

Ver `docs/DEPLOYMENT.md` para guía paso a paso detallada.

## 👤 Cuenta Administrador

Después del deploy, ejecuta:
```bash
python scripts/init_admin.py
```

Credenciales:
- Email: sinuhevidals@gmail.com  
- Password: (ver .env.example)

## 🔗 URLs Importantes

- **Frontend**: https://pyxolotl.railway.app
- **API Docs**: https://pyxolotl-backend.railway.app/docs
- **Panel Admin**: https://pyxolotl.railway.app/admin.html

## 💰 Costos Estimados

- Railway Hobby: $5 USD/mes
- SendGrid: Gratis (100 emails/día)
- Cloudinary: Gratis (25GB)
- **Total: ~$100 MXN/mes**

## ✅ Features Implementados

- ✅ Registro y login de usuarios
- ✅ Tres tipos de cuenta (Comprador/Desarrollador/Admin)
- ✅ Publicación de juegos por desarrolladores
- ✅ Sistema de revisión y aprobación (Admin)
- ✅ Catálogo con búsqueda y filtros
- ✅ Carrito de compras
- ✅ Proceso de pago simulado
- ✅ Biblioteca de juegos
- ✅ Descargas de juegos
- ✅ Juegos gratuitos ($0.00)
- ✅ Sistema de reseñas
- ✅ Emails transaccionales
- ✅ Upload de archivos (local + Cloudinary)
- ✅ Panel de administrador

## 🆘 Soporte

¿Problemas? Revisa:
1. `docs/DEPLOYMENT.md` - Guía completa
2. Railway Logs - Para errores del servidor
3. Browser Console - Para errores del frontend

---

**¡Tu marketplace de juegos indie está listo! 🎉**
