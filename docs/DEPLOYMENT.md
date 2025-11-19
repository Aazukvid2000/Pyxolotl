# 🚀 Guía de Deployment - Pyxolotl en Railway

Esta guía te llevará paso a paso para desplegar Pyxolotl en Railway.

## 📋 Requisitos Previos

Antes de empezar, necesitas crear cuentas en:

1. **GitHub** (si no tienes): https://github.com
2. **Railway**: https://railway.app
3. **SendGrid**: https://sendgrid.com (para emails)
4. **Cloudinary**: https://cloudinary.com (para archivos grandes)

---

## Paso 1: Crear Cuentas (15 min)

### 1.1 Cuenta de Railway

1. Ve a https://railway.app
2. Haz clic en "Start a New Project"
3. Inicia sesión con GitHub (recomendado)
4. Completa el registro

### 1.2 Cuenta de SendGrid

1. Ve a https://sendgrid.com/free
2. Regístrate con tu email
3. Verifica tu cuenta por email
4. Una vez dentro:
   - Ve a Settings → API Keys
   - Crea una nueva API Key
   - Guarda la key (la usarás después)

### 1.3 Cuenta de Cloudinary

1. Ve a https://cloudinary.com/users/register_free
2. Regístrate gratis
3. Una vez dentro del Dashboard:
   - Anota tu "Cloud Name"
   - Ve a Settings → Security
   - Anota tu "API Key" y "API Secret"

---

## Paso 2: Subir Código a GitHub (10 min)

### 2.1 Crear Repositorio

1. Ve a https://github.com/new
2. Nombre del repositorio: `Pyxolotl`
3. Privado o Público (tu elección)
4. NO inicializar con README
5. Crear repositorio

### 2.2 Subir el Código

```bash
# En la carpeta pyxolotl-project/
git init
git add .
git commit -m "Initial commit - Pyxolotl"
git branch -M main
git remote add origin https://github.com/Aazukvid2000/Pyxolotl.git
git push -u origin main
```

---

## Paso 3: Desplegar en Railway (10 min)

### 3.1 Crear Proyecto en Railway

1. En Railway Dashboard, clic en "New Project"
2. Selecciona "Deploy from GitHub repo"
3. Autoriza Railway a acceder a tu GitHub
4. Selecciona el repositorio `Pyxolotl`

### 3.2 Crear Base de Datos MySQL

1. En tu proyecto Railway, clic en "+ New"
2. Selecciona "Database" → "MySQL"
3. Railway creará automáticamente la base de datos
4. Copia la `DATABASE_URL` (la necesitarás)

### 3.3 Configurar Variables de Entorno

1. En Railway, clic en tu servicio backend
2. Ve a la pestaña "Variables"
3. Agrega las siguientes variables:

```
DATABASE_URL=mysql+pymysql://... (copia la URL de MySQL de Railway)
SECRET_KEY=pyxolotl-super-secret-key-2025-change-me
DEBUG=False

FRONTEND_URL=https://pyxolotl.railway.app
BACKEND_URL=https://pyxolotl-backend.railway.app

SENDGRID_API_KEY=(tu API key de SendGrid)
SENDGRID_FROM_EMAIL=noreply@pyxolotl.com

CLOUDINARY_CLOUD_NAME=(tu cloud name)
CLOUDINARY_API_KEY=(tu API key)
CLOUDINARY_API_SECRET=(tu API secret)

ADMIN_EMAIL=sinuhevidals@gmail.com
ADMIN_PASSWORD=PyxAdmin2025!
```

4. Guarda las variables

### 3.4 Primer Deploy

1. Railway detectará automáticamente el `Dockerfile`
2. Empezará a construir la imagen
3. Espera 3-5 minutos
4. Una vez completado, obtendrás una URL como: `https://pyxolotl-backend.railway.app`

---

## Paso 4: Inicializar Administrador (2 min)

### 4.1 Ejecutar Script de Inicialización

En Railway, ve a tu servicio → pestaña "Settings" → Deploy Logs

O ejecuta localmente:

```bash
cd pyxolotl-project
python scripts/init_admin.py
```

Esto creará tu usuario administrador con:
- Email: sinuhevidals@gmail.com
- Password: PyxAdmin2025! (cámbialo después)

---

## Paso 5: Desplegar Frontend (5 min)

### 5.1 Crear Servicio de Frontend

1. En Railway, en tu proyecto, clic en "+ New"
2. Selecciona "GitHub Repo" → mismo repositorio
3. En Settings:
   - Root Directory: `frontend`
   - Build Command: (vacío)
   - Start Command: `python -m http.server 8080`

4. Railway generará una URL para el frontend

### 5.2 Actualizar URLs

Vuelve a las variables del backend y actualiza:

```
FRONTEND_URL=(URL del frontend de Railway)
```

---

## Paso 6: Verificar Funcionamiento

### 6.1 Probar Backend

Ve a: `https://tu-backend.railway.app/docs`

Deberías ver la documentación interactiva de la API.

### 6.2 Probar Frontend

Ve a: `https://tu-frontend.railway.app`

Deberías ver la página principal de Pyxolotl.

### 6.3 Login Admin

1. Ve a `https://tu-frontend.railway.app/inicio.html`
2. Inicia sesión con:
   - Email: sinuhevidals@gmail.com
   - Password: PyxAdmin2025!
3. Ve a `/admin.html` para acceder al panel

---

## 🎉 ¡Listo!

Tu plataforma Pyxolotl está desplegada y funcionando 24/7.

## 📝 Próximos Pasos

1. **Cambia la contraseña del admin**
2. **Compra un dominio personalizado** (opcional)
   - En Namecheap: ~$12 USD/año
   - Configurarlo en Railway: Settings → Domains

3. **Monitorea tu uso**
   - Railway Hobby: $5 USD/mes
   - Revisa métricas en el dashboard

---

## 🐛 Solución de Problemas

### Error: "Cannot connect to database"
- Verifica que `DATABASE_URL` esté correcta
- Asegúrate de que el servicio MySQL esté activo

### Error: "Module not found"
- Verifica que `requirements.txt` esté completo
- Reconstruye el proyecto en Railway

### No se envían emails
- Verifica que `SENDGRID_API_KEY` sea correcta
- Revisa los logs de SendGrid

---

## 📞 Soporte

Si tienes problemas, revisa:
- Railway Logs: En tu servicio → Deploy Logs
- Railway Status: https://railway.app/status
- Documentación: https://docs.railway.app

---

**¡Tu plataforma está lista para recibir desarrolladores indie! 🎮**
