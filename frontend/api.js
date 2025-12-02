// ============================================
// PYXOLOTL - Configuración de API
// Conecta el frontend con el backend
// ============================================

// URL del backend - SIEMPRE usar HTTPS en producción
const API_URL = window.location.hostname === 'localhost' 
  ? 'http://localhost:8000'
  : 'https://pyxolotl-production.up.railway.app';

// Exponer globalmente
window.API_URL = API_URL;

// ============================================
// SISTEMA DE NOTIFICACIONES (Toast)
// ============================================

// Crear contenedor de toasts si no existe
function initToastContainer() {
  if (document.getElementById('toast-container')) return;
  
  const container = document.createElement('div');
  container.id = 'toast-container';
  container.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 10000;
    display: flex;
    flex-direction: column;
    gap: 10px;
    pointer-events: none;
  `;
  document.body.appendChild(container);
  
  // Agregar estilos
  const style = document.createElement('style');
  style.textContent = `
    .pyxo-toast {
      padding: 16px 24px;
      border-radius: 12px;
      color: #fff;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 12px;
      box-shadow: 0 10px 40px rgba(0,0,0,0.4);
      animation: toastSlideIn 0.4s ease;
      pointer-events: auto;
      max-width: 400px;
      backdrop-filter: blur(10px);
    }
    .pyxo-toast.success {
      background: linear-gradient(135deg, rgba(67,233,123,0.95), rgba(56,249,215,0.95));
      color: #07102a;
    }
    .pyxo-toast.error {
      background: linear-gradient(135deg, rgba(255,71,87,0.95), rgba(255,99,72,0.95));
    }
    .pyxo-toast.warning {
      background: linear-gradient(135deg, rgba(255,193,7,0.95), rgba(255,152,0,0.95));
      color: #07102a;
    }
    .pyxo-toast.info {
      background: linear-gradient(135deg, rgba(123,97,255,0.95), rgba(78,163,255,0.95));
    }
    .pyxo-toast-icon { font-size: 24px; }
    .pyxo-toast-message { flex: 1; line-height: 1.4; }
    .pyxo-toast-close {
      background: none;
      border: none;
      color: inherit;
      cursor: pointer;
      font-size: 20px;
      opacity: 0.7;
      transition: opacity 0.2s;
    }
    .pyxo-toast-close:hover { opacity: 1; }
    @keyframes toastSlideIn {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
    @keyframes toastSlideOut {
      from { transform: translateX(0); opacity: 1; }
      to { transform: translateX(100%); opacity: 0; }
    }
  `;
  document.head.appendChild(style);
}

// Mostrar toast
function showToast(message, type = 'info', duration = 4000) {
  initToastContainer();
  
  const icons = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️'
  };
  
  const toast = document.createElement('div');
  toast.className = `pyxo-toast ${type}`;
  toast.innerHTML = `
    <span class="pyxo-toast-icon">${icons[type]}</span>
    <span class="pyxo-toast-message">${message}</span>
    <button class="pyxo-toast-close" onclick="this.parentElement.remove()">×</button>
  `;
  
  document.getElementById('toast-container').appendChild(toast);
  
  // Auto-remove
  setTimeout(() => {
    toast.style.animation = 'toastSlideOut 0.4s ease forwards';
    setTimeout(() => toast.remove(), 400);
  }, duration);
  
  return toast;
}

// Funciones de conveniencia
function toastSuccess(message) { return showToast(message, 'success'); }
function toastError(message) { return showToast(message, 'error'); }
function toastWarning(message) { return showToast(message, 'warning'); }
function toastInfo(message) { return showToast(message, 'info'); }

// Reemplazar alert nativo
window.originalAlert = window.alert;
window.alert = function(message) {
  // Detectar tipo por contenido
  if (message.includes('✅') || message.toLowerCase().includes('éxito') || message.toLowerCase().includes('agregado')) {
    toastSuccess(message.replace(/[✅❌⚠️ℹ️]/g, '').trim());
  } else if (message.includes('❌') || message.toLowerCase().includes('error')) {
    toastError(message.replace(/[✅❌⚠️ℹ️]/g, '').trim());
  } else if (message.includes('⚠️') || message.toLowerCase().includes('debes')) {
    toastWarning(message.replace(/[✅❌⚠️ℹ️]/g, '').trim());
  } else {
    toastInfo(message.replace(/[✅❌⚠️ℹ️]/g, '').trim());
  }
};

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

// ✅ CORREGIDO: Obtener catálogo de juegos
async function apiGetJuegos(filtros = {}) {
  try {
    // Construir URL con parámetros si existen
    let url = `${API_URL}/api/juegos/catalogo`;
    
    // Remover el parámetro 'estado' si existe (el backend ya filtra por APROBADO)
    const { estado, ...otrosFiltros } = filtros;
    
    const params = new URLSearchParams(otrosFiltros);
    if (params.toString()) {
      url += `?${params.toString()}`;
    }
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      console.error('Error al obtener juegos:', response.status, response.statusText);
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Verificar que data sea un array
    if (!Array.isArray(data)) {
      console.error('La respuesta no es un array:', data);
      return [];
    }
    
    return data;
    
  } catch (error) {
    console.error('Error en apiGetJuegos:', error);
    return [];
  }
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
  const response = await fetch(`${API_URL}/api/biblioteca/`, {
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

// Cambiar contraseña
async function apiCambiarPassword(currentPassword, newPassword) {
  const response = await fetch(`${API_URL}/api/auth/cambiar-password`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      password_actual: currentPassword,
      password_nueva: newPassword
    })
  });
  return response.json();
}

// ============================================
// ADMIN - Solo para administradores
// ============================================

// Obtener estadísticas de admin
async function apiGetAdminStats() {
  const response = await fetch(`${API_URL}/api/admin/stats`, {
    headers: getAuthHeaders()
  });
  return response.json();
}

// Obtener lista de usuarios (admin)
async function apiGetAdminUsuarios(skip = 0, limit = 50, verificado = null) {
  let url = `${API_URL}/api/admin/usuarios?skip=${skip}&limit=${limit}`;
  if (verificado !== null) url += `&verificado=${verificado}`;
  const response = await fetch(url, {
    headers: getAuthHeaders()
  });
  return response.json();
}

// Obtener lista de juegos (admin)
async function apiGetAdminJuegos(skip = 0, limit = 50, estado = null) {
  let url = `${API_URL}/api/admin/juegos?skip=${skip}&limit=${limit}`;
  if (estado) url += `&estado=${estado}`;
  const response = await fetch(url, {
    headers: getAuthHeaders()
  });
  return response.json();
}

// Eliminar usuario (admin)
async function apiDeleteUsuario(userId) {
  const response = await fetch(`${API_URL}/api/admin/usuario/${userId}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  return response.json();
}

// Eliminar juego (admin)
async function apiDeleteJuego(juegoId) {
  const response = await fetch(`${API_URL}/api/admin/juego/${juegoId}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  return response.json();
}

// Eliminar SOLO los juegos de un usuario (mantiene la cuenta)
async function apiDeleteJuegosUsuario(userId) {
  const response = await fetch(`${API_URL}/api/admin/usuario/${userId}/juegos`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  return response.json();
}

// Limpiar usuarios no verificados
async function apiLimpiarNoVerificados() {
  const response = await fetch(`${API_URL}/api/admin/usuarios/no-verificados`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  return response.json();
}

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
// RESEÑAS
// ============================================

// Obtener reseñas de un juego
async function apiGetResenas(juegoId) {
  try {
    const response = await fetch(`${API_URL}/api/juegos/${juegoId}/resenas`);
    if (!response.ok) {
      throw new Error('Error al obtener reseñas');
    }
    return response.json();
  } catch (error) {
    console.error('Error en apiGetResenas:', error);
    return [];
  }
}

// Crear una reseña
async function apiCrearResena(juegoId, calificacion, texto) {
  const response = await fetch(`${API_URL}/api/juegos/${juegoId}/resenas`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      juego_id: juegoId,
      calificacion: calificacion,
      texto: texto
    })
  });
  return response.json();
}

// Eliminar una reseña
async function apiEliminarResena(juegoId, resenaId) {
  const response = await fetch(`${API_URL}/api/juegos/${juegoId}/resenas/${resenaId}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
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