// ============================================
// PYXOLOTL - Configuración de API
// ============================================

const API_URL = window.location.hostname === 'localhost' 
  ? 'http://localhost:8000'
  : 'https://pyxolotl-production.up.railway.app';

// --- AUTENTICACIÓN ---

function setAuthToken(token) {
  localStorage.setItem('auth_token', token);
}

function getAuthToken() {
  return localStorage.getItem('auth_token');
}

function clearAuthToken() {
  localStorage.removeItem('auth_token');
}

function getAuthHeaders() {
  const token = getAuthToken();
  if (token) {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
  }
  return { 'Content-Type': 'application/json' };
}

function isAuthenticated() {
  return !!getAuthToken();
}

function getCurrentUser() {
  const userStr = localStorage.getItem('current_user');
  return userStr ? JSON.parse(userStr) : null;
}

// --- API CALLS ---

async function apiRegistro(nombre, email, password, tipoCuenta = 'comprador') {
  const response = await fetch(`${API_URL}/api/auth/registro`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nombre, email, password, tipo_cuenta: tipoCuenta })
  });
  return response.json();
}

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

async function apiGetJuegos(filtros = {}) {
  try {
    let url = `${API_URL}/api/juegos/catalogo`;
    const { estado, ...otrosFiltros } = filtros;
    const params = new URLSearchParams(otrosFiltros);
    if (params.toString()) url += `?${params.toString()}`;
    
    const response = await fetch(url);
    if (!response.ok) throw new Error('Error al obtener catálogo');
    return await response.json();
  } catch (error) {
    console.error(error);
    return [];
  }
}

async function apiGetJuego(id) {
  const response = await fetch(`${API_URL}/api/juegos/${id}`);
  if (!response.ok) throw new Error('Juego no encontrado');
  return response.json();
}

async function apiPublicarJuego(formData) {
  const token = getAuthToken();
  const response = await fetch(`${API_URL}/api/juegos/publicar`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
  });
  return response.json();
}

// --- RESEÑAS (CORREGIDO) ---

async function apiGetResenas(juegoId) {
  try {
    const response = await fetch(`${API_URL}/api/juegos/${juegoId}/resenas`);
    if (!response.ok) throw new Error('Error al obtener reseñas');
    return await response.json();
  } catch (error) {
    console.error('Error en apiGetResenas:', error);
    return [];
  }
}

async function apiCrearResena(juegoId, calificacion, texto) {
  // NOTA: El backend espera calificacion y texto en el body, el juego_id va en la URL
  const response = await fetch(`${API_URL}/api/juegos/${juegoId}/resenas`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      calificacion: parseInt(calificacion),
      texto: texto
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Error al publicar reseña');
  }
  
  return response.json();
}

async function apiEliminarResena(juegoId, resenaId) {
  const response = await fetch(`${API_URL}/api/juegos/${juegoId}/resenas/${resenaId}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  return response.json();
}

// --- OTROS ---

async function apiGetJuegoGratis(juegoId) {
  const response = await fetch(`${API_URL}/api/juegos/${juegoId}/descargar-gratis`, {
    method: 'POST',
    headers: getAuthHeaders()
  });
  return response.json();
}