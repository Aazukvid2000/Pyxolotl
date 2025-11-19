// ============================================
// PIXOLOT - Sistema de Carrito Completo
// ============================================
console.log('🛒 Cart.js cargado correctamente');

// Estructura de datos de los juegos
const gamesData = {
  '1': {
    id: '1',
    title: 'Nebula Runner',
    price: '15.99',
    thumb: 'NR',
    desc: 'Un endless runner espacial con estética retro y música synthwave.'
  },
  '2': {
    id: '2',
    title: 'Echoes',
    price: '19.99',
    thumb: 'E',
    desc: 'Aventura narrativa con puzles sonoros y ambientes inmersivos.'
  },
  '3': {
    id: '3',
    title: 'Moss & Code',
    price: '12.99',
    thumb: 'M',
    desc: 'Plataformas y rompecabezas donde la biología y la programación se combinan.'
  },
  '4': {
    id: '4',
    title: 'Starbound Chef',
    price: '9.99',
    thumb: 'SC',
    desc: 'Juego de cocina en estaciones espaciales con física divertida.'
  }
};

console.log('📦 Juegos disponibles:', Object.keys(gamesData).length);

// ============================================
// FUNCIONES DEL CARRITO
// ============================================

function getCart() {
  return JSON.parse(localStorage.getItem('pixolotCart') || '[]');
}

function saveCart(cart) {
  localStorage.setItem('pixolotCart', JSON.stringify(cart));
  updateCartCount();
}

function addToCart(gameId) {
  const cart = getCart();
  const game = gamesData[gameId];
  
  if (!game) {
    alert('❌ Juego no encontrado');
    return;
  }
  
  const exists = cart.find(item => item.id === gameId);
  
  if (exists) {
    alert('⚠️ Este juego ya está en tu carrito');
  } else {
    cart.push(game);
    saveCart(cart);
    alert('✅ ¡Juego agregado al carrito!');
  }
}

function removeFromCart(gameId) {
  let cart = getCart();
  cart = cart.filter(item => item.id !== gameId);
  saveCart(cart);
  renderCart();
}

function updateCartCount() {
  const cart = getCart();
  const countElements = document.querySelectorAll('#cartCount');
  countElements.forEach(el => {
    el.textContent = cart.length;
  });
}

function calculateTotals() {
  const cart = getCart();
  const subtotal = cart.reduce((sum, item) => sum + parseFloat(item.price), 0);
  const tax = subtotal * 0.16;
  const total = subtotal + tax;
  
  return { subtotal, tax, total };
}

// ============================================
// RENDERIZADO DEL CARRITO
// ============================================

function renderCart() {
  const cartItemsContainer = document.getElementById('cartItems');
  const cartEmpty = document.getElementById('cartEmpty');
  const cart = getCart();
  
  if (!cartItemsContainer) return;
  
  if (cart.length === 0) {
    cartItemsContainer.innerHTML = '';
    if (cartEmpty) cartEmpty.style.display = 'block';
    return;
  }
  
  if (cartEmpty) cartEmpty.style.display = 'none';
  
  cartItemsContainer.innerHTML = cart.map(item => `
    <div class="cart-item">
      <div class="cart-item-thumb">${item.thumb}</div>
      <div class="cart-item-info">
        <div class="cart-item-title">${item.title}</div>
        <div class="cart-item-price">$${parseFloat(item.price).toFixed(2)}</div>
      </div>
      <button class="cart-item-remove" onclick="removeFromCart('${item.id}')">🗑️</button>
    </div>
  `).join('');
  
  const { subtotal, tax, total } = calculateTotals();
  
  const subtotalEl = document.getElementById('subtotal');
  const taxEl = document.getElementById('tax');
  const totalEl = document.getElementById('total');
  
  if (subtotalEl) subtotalEl.textContent = `$${subtotal.toFixed(2)}`;
  if (taxEl) taxEl.textContent = `$${tax.toFixed(2)}`;
  if (totalEl) totalEl.textContent = `$${total.toFixed(2)}`;
}

// ============================================
// MODAL DEL CARRITO
// ============================================

function openCartModal() {
  const modal = document.getElementById('cartModal');
  if (modal) {
    renderCart();
    modal.classList.add('show');
  }
}

function closeCartModal() {
  const modal = document.getElementById('cartModal');
  if (modal) {
    modal.classList.remove('show');
  }
}

// ============================================
// CHECKOUT
// ============================================

function proceedToCheckout() {
  const cart = getCart();
  
  if (cart.length === 0) {
    alert('❌ Tu carrito está vacío');
    return;
  }
  
  // Guardar carrito en sessionStorage para la página de pago
  sessionStorage.setItem('checkoutCart', JSON.stringify(cart));
  
  // Redirigir a página de pago
  window.location.href = 'pago.html';
}

// ============================================
// SNAKE GAME MODAL
// ============================================

function openSnakeGame() {
  const modal = document.getElementById('snakeModal');
  if (modal) {
    modal.style.display = 'flex';
    // Reiniciar el juego si es necesario
    if (typeof resetGame === 'function') {
      resetGame();
    }
  }
}

function closeSnakeGame() {
  const modal = document.getElementById('snakeModal');
  if (modal) {
    modal.style.display = 'none';
  }
}

// ============================================
// INICIALIZACIÓN
// ============================================

document.addEventListener('DOMContentLoaded', () => {
  // Actualizar contador del carrito
  updateCartCount();
  
  // Botón del carrito
  const cartBtn = document.getElementById('cartBtn');
  if (cartBtn) {
    cartBtn.addEventListener('click', openCartModal);
  }
  
  // Cerrar modales
  const closeCartBtn = document.querySelector('.close-cart');
  if (closeCartBtn) {
    closeCartBtn.addEventListener('click', closeCartModal);
  }
  
  const closeSnakeBtn = document.querySelector('.close-snake');
  if (closeSnakeBtn) {
    closeSnakeBtn.addEventListener('click', closeSnakeGame);
  }
  
  // Cerrar modal al hacer clic fuera
  const cartModal = document.getElementById('cartModal');
  if (cartModal) {
    cartModal.addEventListener('click', (e) => {
      if (e.target === cartModal) {
        closeCartModal();
      }
    });
  }
  
  const snakeModal = document.getElementById('snakeModal');
  if (snakeModal) {
    snakeModal.addEventListener('click', (e) => {
      if (e.target === snakeModal) {
        closeSnakeGame();
      }
    });
  }
  
  // Botones "Agregar al carrito"
  document.querySelectorAll('.add-to-cart').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const gameId = btn.dataset.id;
      addToCart(gameId);
    });
  });
  
  // Botón "Jugar Snake"
  document.querySelectorAll('.play-snake-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      openSnakeGame();
    });
  });
  
  // Botón checkout
  const checkoutBtn = document.getElementById('checkoutBtn');
  if (checkoutBtn) {
    checkoutBtn.addEventListener('click', proceedToCheckout);
  }
  
  // Prevenir que las cards abran el modal de preview (conflicto)
  document.querySelectorAll('.card').forEach(card => {
    card.addEventListener('click', (e) => {
      // Solo abrir detalles si no se hizo clic en un botón
      if (!e.target.classList.contains('btn') && 
          !e.target.classList.contains('add-to-cart') &&
          !e.target.classList.contains('play-snake-btn')) {
        const gameId = card.dataset.id;
        if (gameId) {
          window.location.href = `producto-detalle.html?id=${gameId}`;
        }
      }
    });
  });
  
  // Menu mobile
  const menuBtn = document.getElementById('menuBtn');
  const nav = document.querySelector('.nav');
  if (menuBtn && nav) {
    menuBtn.addEventListener('click', () => {
      nav.classList.toggle('open');
      menuBtn.classList.toggle('open');
    });
  }
});

// Hacer funciones globales para que puedan ser llamadas desde HTML
window.addToCart = addToCart;
window.removeFromCart = removeFromCart;
window.openCartModal = openCartModal;
window.closeCartModal = closeCartModal;
window.proceedToCheckout = proceedToCheckout;
window.openSnakeGame = openSnakeGame;
window.closeSnakeGame = closeSnakeGame;