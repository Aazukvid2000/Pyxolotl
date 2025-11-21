// ============================================
// PYXOLOTL - Configuración de API
// Conecta el frontend con el backend
// ============================================

// URL del backend (cambiar en producción)
const API_URL = window.location.hostname === 'localhost' 
  ? 'http://localhost:8000'
  : 'https://pyxolotl-production.up.railway.app';

// ============================================
// AUTENTICACIÓN
// ============================================

// Guardar token JWT
function setAuthToken(token) {
  localStorage.setItem('auth_token', token);
}

// Obtener token JWT
function getAuthToken() {
  return localStorage.getItem('auth_token');
}

// Eliminar token
function clearAuthToken() {
  localStorage.removeItem('auth_token');
}

// Headers con autenticación
function getAuthHeaders() {
  const token = getAuthToken();
  if (token) {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
  }
  return {
    'Content-Type': 'application/json'
  };
}

// ============================================
// API CALLS
// ============================================

// Registro
async function apiRegistro(nombre, email, password, tipoCuenta = 'comprador') {
  const response = await fetch(`${API_URL}/api/auth/registro`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      nombre,
      email,
      password,
      tipo_cuenta: tipoCuenta
    })
  });
  return response.json();
}

// Login
async function apiLogin(email, password) {
  const response = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  
  const data = await response.json();
  
  if (response.ok && data.access_token) {
    setAuthToken(data.access_token);
    localStorage.setItem('current_user', JSON.stringify(data.usuario));
  }
  
  return data;
}

// Obtener catálogo de juegos
async function apiGetJuegos(filtros = {}) {
  const params = new URLSearchParams(filtros);
  const response = await fetch(`${API_URL}/api/juegos/catalogo?${params}`);
  return response.json();
}

// Obtener detalle de un juego
async function apiGetJuego(id) {
  const response = await fetch(`${API_URL}/api/juegos/${id}`);
  return response.json();
}

// Publicar juego
async function apiPublicarJuego(formData) {
  const token = getAuthToken();
  const response = await fetch(`${API_URL}/api/juegos/publicar`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData  // FormData ya tiene el content-type correcto
  });
  return response.json();
}

// Agregar al carrito
async function apiAgregarCarrito(juegoId) {
  const response = await fetch(`${API_URL}/api/carrito/agregar/${juegoId}`, {
    method: 'POST',
    headers: getAuthHeaders()
  });
  return response.json();
}

// Obtener carrito
async function apiGetCarrito() {
  const response = await fetch(`${API_URL}/api/carrito`, {
    headers: getAuthHeaders()
  });
  return response.json();
}

// Procesar compra
async function apiProcesarCompra(juegosIds, metodoPago = 'tarjeta') {
  const response = await fetch(`${API_URL}/api/compras/procesar`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      juegos_ids: juegosIds,
      metodo_pago: metodoPago
    })
  });
  return response.json();
}

// Obtener biblioteca
async function apiGetBiblioteca() {
  const response = await fetch(`${API_URL}/api/biblioteca`, {
    headers: getAuthHeaders()
  });
  return response.json();
}

// Descargar juego
function apiDescargarJuego(juegoId) {
  const token = getAuthToken();
  window.open(`${API_URL}/api/biblioteca/descargar/${juegoId}?token=${token}`, '_blank');
}

// Obtener juego gratis
async function apiGetJuegoGratis(juegoId) {
  const response = await fetch(`${API_URL}/api/juegos/${juegoId}/descargar-gratis`, {
    method: 'POST',
    headers: getAuthHeaders()
  });
  return response.json();
}

// ============================================
// ADMIN - Solo para administradores
// ============================================

// Obtener juegos pendientes
async function apiGetJuegosPendientes() {
  const response = await fetch(`${API_URL}/api/juegos/admin/pendientes`, {
    headers: getAuthHeaders()
  });
  return response.json();
}

// Aprobar/Rechazar juego
async function apiAprobarJuego(juegoId, aprobado, motivo = null) {
  const response = await fetch(`${API_URL}/api/juegos/${juegoId}/aprobar`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      aprobado,
      motivo_rechazo: motivo
    })
  });
  return response.json();
}

// ============================================
// UTILIDADES
// ============================================

// Verificar si está autenticado
function isAuthenticated() {
  return !!getAuthToken();
}

// Obtener usuario actual
function getCurrentUser() {
  const userStr = localStorage.getItem('current_user');
  return userStr ? JSON.parse(userStr) : null;
}

// Cerrar sesión
function logout() {
  clearAuthToken();
  localStorage.removeItem('current_user');
  window.location.href = '/inicio.html';
}

console.log('✅ API configurada. Backend:', API_URL);
