"""
Aplicación principal FastAPI - Pyxolotl Backend
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings
from app.database import engine, Base
from app.routes import auth, juegos, compras, biblioteca, admin
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Crear tablas en la base de datos
Base.metadata.create_all(bind=engine)

# Middleware para manejar HTTPS detrás de proxy (Railway, Heroku, etc.)
class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Detectar si la conexión original era HTTPS
        forwarded_proto = request.headers.get("x-forwarded-proto", "http")
        if forwarded_proto == "https":
            # Actualizar el scope para que FastAPI sepa que es HTTPS
            request.scope["scheme"] = "https"
        response = await call_next(request)
        return response

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API para plataforma de videojuegos indie",
    debug=settings.DEBUG
)

# Agregar middleware de HTTPS primero
app.add_middleware(HTTPSRedirectMiddleware)

# Configurar CORS - permitir todos los orígenes para evitar problemas
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Montar directorio de uploads como archivos estáticos
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Incluir routers
app.include_router(auth.router)
app.include_router(juegos.router)
app.include_router(compras.router)
app.include_router(biblioteca.router)
app.include_router(admin.router)

# Ruta raíz
@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs": "/docs"
    }

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
