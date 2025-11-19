# 🎮 Pyxolotl - Plataforma de Videojuegos Indie

Marketplace de videojuegos indie mexicanos con sistema completo de publicación, compra y descarga.

## 📋 Características

- ✅ Sistema de autenticación (Comprador/Desarrollador/Admin)
- ✅ Catálogo de juegos con búsqueda y filtros
- ✅ Publicación de juegos por desarrolladores
- ✅ Sistema de revisión por administradores
- ✅ Carrito de compras y proceso de pago simulado
- ✅ Descarga de juegos comprados
- ✅ Sistema de reseñas y calificaciones
- ✅ Panel de administración visual
- ✅ Juegos gratuitos y de pago
- ✅ Upload de archivos (imágenes, videos, juegos)

## 🛠️ Stack Tecnológico

### Backend
- Python 3.11
- FastAPI (Framework web)
- SQLAlchemy (ORM)
- MySQL 8.0
- JWT (Autenticación)
- Bcrypt (Encriptación)
- SendGrid (Email)
- Cloudinary (Almacenamiento de archivos grandes)

### Frontend
- HTML5 / CSS3
- JavaScript Vanilla
- Fetch API

### Deployment
- Railway (Hosting)
- Docker (Containerización)
- Nginx (Proxy reverso)

## 📦 Estructura del Proyecto

```
pyxolotl-project/
├── backend/                 # Backend FastAPI
│   ├── app/
│   │   ├── main.py         # Punto de entrada
│   │   ├── config.py       # Configuración
│   │   ├── database.py     # Conexión BD
│   │   ├── models.py       # Modelos SQLAlchemy
│   │   ├── schemas.py      # Schemas Pydantic
│   │   ├── routes/         # Endpoints API
│   │   └── utils/          # Utilidades
│   ├── uploads/            # Archivos temporales
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/               # Frontend estático
│   ├── pixolot.html       # Página principal
│   ├── publicar-juego.html
│   ├── producto-detalle.html
│   ├── pago.html
│   ├── inicio.html
│   ├── admin.html         # Panel administrador
│   ├── biblioteca.html    # Juegos del usuario
│   ├── styles.css
│   ├── main.js
│   └── card.js
│
├── docs/                   # Documentación
│   ├── 01-SETUP.md
│   ├── 02-DEPLOYMENT.md
│   └── 03-API.md
│
├── scripts/               # Scripts útiles
│   ├── init_admin.py
│   └── test_connection.py
│
├── railway.json           # Configuración Railway
├── docker-compose.yml     # Docker local
└── README.md
```

## 🚀 Guía Rápida de Deployment

Ver documentación completa en: `docs/02-DEPLOYMENT.md`

### Paso 1: Crear cuentas necesarias
1. Railway: https://railway.app
2. SendGrid: https://sendgrid.com
3. Cloudinary: https://cloudinary.com

### Paso 2: Configurar GitHub
1. Crear repositorio `Pyxolotl`
2. Subir este código

### Paso 3: Deploy en Railway
1. Importar desde GitHub
2. Configurar variables de entorno
3. Deploy automático

## 👤 Usuario Administrador

Email: sinuhevidals@gmail.com
Ver: `docs/01-SETUP.md` para crear la cuenta admin

## 📝 Licencia

Proyecto estudiantil - Universidad Tecnológica de la Mixteca

## 👥 Equipo

- Betanzo Bolaños Samantha
- Flores Canseco Joe Anthony
- Flores Ruiz Santiago Gabriel
- Peralta Segoviano Jairo Havith
- Vidals Sibaja Sinuhé

---

**Documentación completa en carpeta `/docs/`**
