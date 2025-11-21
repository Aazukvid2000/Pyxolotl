// ============================================
// PYXOLOTL - Sistema de Carrito de Compras
// Manejo del carrito con localStorage y modal
// ============================================

// Obtener carrito desde localStorage
function getCart() {
  const cart = localStorage.getItem('cart');
  return cart ? JSON.parse(cart) : [];
}

// Guardar carrito en localStorage
function saveCart(cart) {
  localStorage.setItem('cart', JSON.stringify(cart));
  updateCartUI();
}

// Agregar juego al carrito
function addToCart(gameId, gameTitle, gamePrice, gameImage = null) {
  let cart = getCart();
  
  // Verificar si el juego ya está en el carrito
  const existingItem = cart.find(item => item.id === gameId);
  
  if (existingItem) {
    alert('Este juego ya está en tu carrito');
    return;
  }
  
  // Agregar nuevo item
  cart.push({
    id: gameId,
    title: gameTitle,
    price: parseFloat(gamePrice),
    image: gameImage
  });
  
  saveCart(cart);
  alert(`✅ "${gameTitle}" agregado al carrito`);
}

// Eliminar juego del carrito
function removeFromCart(gameId) {
  let cart = getCart();
  cart = cart.filter(item => item.id !== gameId);
  saveCart(cart);
}

// Limpiar carrito
function clearCart() {
  localStorage.removeItem('cart');
  updateCartUI();
}

// Actualizar UI del carrito
function updateCartUI() {
  const cart = getCart();
  const cartCount = document.getElementById('cartCount');
  const cartItems = document.getElementById('cartItems');
  const cartEmpty = document.getElementById('cartEmpty');
  const cartSummary = document.getElementById('cartSummary');
  const checkoutBtn = document.getElementById('checkoutBtn');
  
  // Actualizar contador
  if (cartCount) {
    cartCount.textContent = cart.length;
  }
  
  // Si no hay elementos en el modal, no hacer nada
  if (!cartItems) return;
  
  // Limpiar contenido
  cartItems.innerHTML = '';
  
  if (cart.length === 0) {
    cartEmpty.style.display = 'block';
    cartSummary.style.display = 'none';
    if (checkoutBtn) checkoutBtn.style.display = 'none';
    return;
  }
  
  cartEmpty.style.display = 'none';
  cartSummary.style.display = 'block';
  if (checkoutBtn) checkoutBtn.style.display = 'block';
  
  // Renderizar items
  cart.forEach(item => {
    const itemDiv = document.createElement('div');
    itemDiv.style.cssText = 'display:flex;justify-content:space-between;align-items:center;padding:12px;background:rgba(255,255,255,0.03);border-radius:8px;margin-bottom:8px';
    
    itemDiv.innerHTML = `
      <div style="flex:1">
        <div style="font-weight:600">${item.title}</div>
        <div style="color:var(--accent-1);font-size:16px;margin-top:4px">$${item.price.toFixed(2)}</div>
      </div>
      <button class="btn-remove" data-id="${item.id}" style="background:rgba(255,59,48,0.2);color:#ff3b30;border:none;padding:8px 12px;border-radius:6px;cursor:pointer;font-weight:600">
        Quitar
      </button>
    `;
    
    cartItems.appendChild(itemDiv);
  });
  
  // Event listeners para botones de quitar
  document.querySelectorAll('.btn-remove').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const gameId = parseInt(e.target.getAttribute('data-id'));
      removeFromCart(gameId);
    });
  });
  
  // Calcular totales
  const subtotal = cart.reduce((sum, item) => sum + item.price, 0);
  const tax = subtotal * 0.16;
  const total = subtotal + tax;
  
  document.getElementById('subtotal').textContent = `$${subtotal.toFixed(2)}`;
  document.getElementById('tax').textContent = `$${tax.toFixed(2)}`;
  document.getElementById('total').textContent = `$${total.toFixed(2)}`;
}

// Modal de carrito
const cartModal = document.getElementById('cartModal');
const cartBtn = document.getElementById('cartBtn');
const closeCartBtn = document.querySelector('.close-cart');

if (cartBtn) {
  cartBtn.addEventListener('click', () => {
    updateCartUI();
    cartModal.style.display = 'flex';
  });
}

if (closeCartBtn) {
  closeCartBtn.addEventListener('click', () => {
    cartModal.style.display = 'none';
  });
}

// Cerrar modal al hacer clic fuera
if (cartModal) {
  cartModal.addEventListener('click', (e) => {
    if (e.target === cartModal) {
      cartModal.style.display = 'none';
    }
  });
}

// Botón de checkout
const checkoutBtn = document.getElementById('checkoutBtn');
if (checkoutBtn) {
  checkoutBtn.addEventListener('click', () => {
    const cart = getCart();
    
    if (cart.length === 0) {
      alert('Tu carrito está vacío');
      return;
    }
    
    // Verificar autenticación
    if (typeof isAuthenticated === 'function' && !isAuthenticated()) {
      alert('Debes iniciar sesión para comprar');
      window.location.href = 'inicio.html';
      return;
    }
    
    // Ir a página de pago
    window.location.href = 'pago.html';
  });
}

// Exponer funciones globalmente para que otros scripts las usen
window.addToCart = addToCart;
window.removeFromCart = removeFromCart;
window.clearCart = clearCart;
window.getCart = getCart;

// Inicializar contador al cargar la página
document.addEventListener('DOMContentLoaded', () => {
  updateCartUI();
});