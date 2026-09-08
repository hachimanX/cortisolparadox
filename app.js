/**
 * The Cortisol Paradox — Sales Funnel Interactive Controller
 * Features: Payhip Checkout Integration, Exit-Intent Modal, 30-Minute Live Countdown, Sticky Bar, FAQ Accordion
 */

document.addEventListener('DOMContentLoaded', () => {

  // 1. OFFICIAL PAYHIP CHECKOUT LINKS
  const CHECKOUT_CONFIG = {
    standardBundleUrl37: 'https://payhip.com/b/lrapH',
    downsellFlashUrl27:  'https://payhip.com/b/lrapH?coupon=FLASH10',
  };

  // 2. STICKY CHECKOUT BAR
  const stickyBar = document.querySelector('.sticky-checkout-bar');
  const heroSection = document.querySelector('.hero-section');

  if (stickyBar && heroSection) {
    window.addEventListener('scroll', () => {
      const heroBottom = heroSection.getBoundingClientRect().bottom;
      if (heroBottom < 0) {
        stickyBar.classList.add('visible');
      } else {
        stickyBar.classList.remove('visible');
      }
    });
  }

  // 3. FAQ ACCORDION
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(item => {
    const questionBtn = item.querySelector('.faq-question');
    if (questionBtn) {
      questionBtn.addEventListener('click', () => {
        const isActive = item.classList.contains('active');
        faqItems.forEach(other => other.classList.remove('active'));
        if (!isActive) {
          item.classList.add('active');
        }
      });
    }
  });

  // 4. 30-MINUTE LIVE COUNTDOWN TIMER (PERSISTENT)
  const timerElements = document.querySelectorAll('.timer-clock');
  const STORAGE_KEY = 'cortisol_flash_expiry_v1';
  let expiryTime = localStorage.getItem(STORAGE_KEY);

  if (!expiryTime || isNaN(expiryTime) || Number(expiryTime) < Date.now()) {
    expiryTime = Date.now() + 30 * 60 * 1000;
    localStorage.setItem(STORAGE_KEY, expiryTime);
  }

  function updateTimer() {
    const remainingMs = Number(expiryTime) - Date.now();
    if (remainingMs <= 0) {
      timerElements.forEach(el => el.textContent = "00:00");
      return;
    }

    const totalSeconds = Math.floor(remainingMs / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;

    const formatted = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    timerElements.forEach(el => el.textContent = formatted);
  }

  updateTimer();
  setInterval(updateTimer, 1000);

  // 5. EXIT-INTENT DOWNSELL MODAL (<dialog>)
  const exitModal = document.getElementById('exitModal');
  const closeBtn = document.querySelector('.modal-close-btn');
  const declineBtn = document.querySelector('.modal-decline-link');

  let modalAlreadyShown = sessionStorage.getItem('exitModalTriggered');

  function openExitModal() {
    if (modalAlreadyShown) return;
    if (exitModal && typeof exitModal.showModal === 'function') {
      exitModal.showModal();
      modalAlreadyShown = true;
      sessionStorage.setItem('exitModalTriggered', 'true');
    }
  }

  // Desktop Mouse Leave Intent
  document.addEventListener('mouseleave', (e) => {
    if (e.clientY <= 20) {
      openExitModal();
    }
  });

  // Mobile / Inactive Fallback
  setTimeout(() => {
    openExitModal();
  }, 75000);

  // Close handlers
  if (closeBtn && exitModal) {
    closeBtn.addEventListener('click', () => exitModal.close());
  }
  if (declineBtn && exitModal) {
    declineBtn.addEventListener('click', () => exitModal.close());
  }

  // Modern Light-Dismiss: click outside modal content box to close
  if (exitModal) {
    exitModal.addEventListener('click', (event) => {
      if (event.target !== exitModal) return;
      const rect = exitModal.getBoundingClientRect();
      const isDialogContent = (
        rect.top <= event.clientY &&
        event.clientY <= rect.top + rect.height &&
        rect.left <= event.clientX &&
        event.clientX <= rect.left + rect.width
      );
      if (!isDialogContent) {
        exitModal.close();
      }
    });
  }

  // 6. CONNECT REAL PAYHIP CHECKOUT URLS DYNAMICALLY
  const standardButtons = document.querySelectorAll('.trigger-checkout-37');
  standardButtons.forEach(btn => {
    btn.href = CHECKOUT_CONFIG.standardBundleUrl37;
  });

  const downsellButtons = document.querySelectorAll('.trigger-checkout-27');
  downsellButtons.forEach(btn => {
    btn.href = CHECKOUT_CONFIG.downsellFlashUrl27;
  });

});
