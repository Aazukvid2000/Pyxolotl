// ============================================
// PIXOLOT - main.js
// Sistema principal de interactividad
// ============================================

console.log('⚡ Main.js cargado');

document.addEventListener('DOMContentLoaded', () => {
  console.log('🚀 DOM cargado, inicializando Pixolot...');
  
  // ============================================
  // LOGO FALLBACK
  // ============================================
  const brandImg = document.getElementById('brandImg');
  const brandFallback = document.getElementById('brandFallback');
  
  if (brandImg) {
    brandImg.addEventListener('error', () => {
      console.log('⚠️ Imagen del logo no encontrada, usando fallback');
      if (brandFallback) {
        brandFallback.textContent = brandImg.dataset.initials || 'PX';
        brandFallback.style.display = 'inline-flex';
        brandImg.style.display = 'none';
      }
    });
    
    brandImg.addEventListener('load', () => {
      if (brandFallback) brandFallback.style.display = 'none';
    });
    
    if (!brandImg.getAttribute('src')) {
      brandImg.dispatchEvent(new Event('error'));
    }
  } else if (brandFallback) {
    brandFallback.style.display = 'inline-flex';
  }
  
  // ============================================
  // MENÚ MÓVIL
  // ============================================
  const menuBtn = document.getElementById('menuBtn');
  const nav = document.querySelector('.nav');
  
  if (menuBtn && nav) {
    menuBtn.addEventListener('click', () => {
      nav.classList.toggle('open');
      menuBtn.classList.toggle('open');
      console.log('📱 Menú móvil toggled');
    });
  }
  
  // ============================================
  // CARRITO - BOTÓN ABRIR
  // ============================================
  const cartBtn = document.getElementById('cartBtn');
  if (cartBtn) {
    cartBtn.addEventListener('click', (e) => {
      e.preventDefault();
      console.log('🛒 Abriendo carrito...');
      openCartModal();
    });
  }
  
  // ============================================
  // BOTONES "AGREGAR AL CARRITO"
  // ============================================
  const addToCartButtons = document.querySelectorAll('.add-to-cart');
  console.log(`🔘 Botones "Agregar" encontrados: ${addToCartButtons.length}`);
  
  addToCartButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      e.preventDefault();
      const gameId = btn.dataset.id;
      console.log(`➕ Agregando juego ID: ${gameId}`);
      addToCart(gameId);
    });
  });
  
  // ============================================
  // BOTÓN "JUGAR SNAKE"
  // ============================================
  const playSnakeButtons = document.querySelectorAll('.play-snake-btn');
  console.log(`🎮 Botones "Jugar Snake" encontrados: ${playSnakeButtons.length}`);
  
  playSnakeButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      e.preventDefault();
      console.log('🐍 Abriendo Snake Game...');
      openSnakeGame();
    });
  });
  
  // ============================================
  // CARDS - IR A DETALLE (solo juegos de pago)
  // ============================================
  document.querySelectorAll('.card:not(.free-game)').forEach(card => {
    card.style.cursor = 'pointer';
    card.addEventListener('click', (e) => {
      // No redirigir si se clickeó un botón
      if (e.target.closest('button') || e.target.closest('.btn')) {
        return;
      }
      
      const gameId = card.dataset.id;
      if (gameId) {
        console.log(`🎯 Ir a detalle del juego: ${gameId}`);
        window.location.href = `producto-detalle.html?id=${gameId}`;
      }
    });
  });
  
  // ============================================
  // MODAL CARRITO - CERRAR
  // ============================================
  const closeCartBtn = document.querySelector('.close-cart');
  if (closeCartBtn) {
    closeCartBtn.addEventListener('click', closeCartModal);
  }
  
  const cartModal = document.getElementById('cartModal');
  if (cartModal) {
    cartModal.addEventListener('click', (e) => {
      if (e.target === cartModal) {
        closeCartModal();
      }
    });
  }
  
  // ============================================
  // MODAL SNAKE - CERRAR
  // ============================================
  const closeSnakeBtn = document.querySelector('.close-snake');
  if (closeSnakeBtn) {
    closeSnakeBtn.addEventListener('click', closeSnakeGame);
  }
  
  const snakeModal = document.getElementById('snakeModal');
  if (snakeModal) {
    snakeModal.addEventListener('click', (e) => {
      if (e.target === snakeModal) {
        closeSnakeGame();
      }
    });
  }
  
  // ============================================
  // BOTÓN CHECKOUT
  // ============================================
  const checkoutBtn = document.getElementById('checkoutBtn');
  if (checkoutBtn) {
    checkoutBtn.addEventListener('click', proceedToCheckout);
  }
  
  // ============================================
  // ACTUALIZAR CONTADOR INICIAL
  // ============================================
  if (typeof updateCartCount === 'function') {
    updateCartCount();
    console.log('✅ Contador del carrito actualizado');
  }
  
  console.log('✨ Pixolot inicializado correctamente');
});