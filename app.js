/**
 * The Cortisol Paradox — page behavior
 * Sticky purchase bar only.
 */

document.addEventListener('DOMContentLoaded', () => {
  const stickyBar = document.querySelector('.sticky-checkout-bar');
  const heroSection = document.querySelector('.hero-section');

  if (!stickyBar || !heroSection) return;

  const syncSticky = () => {
    const show = heroSection.getBoundingClientRect().bottom < 0;
    stickyBar.classList.toggle('visible', show);
    stickyBar.setAttribute('aria-hidden', show ? 'false' : 'true');
    if (show) {
      stickyBar.removeAttribute('inert');
    } else {
      stickyBar.setAttribute('inert', '');
    }
  };

  syncSticky();
  window.addEventListener('scroll', syncSticky, { passive: true });
});
