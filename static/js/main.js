/* ============================================================
   Sathik Groups — Main JavaScript Module (Mobile-First)
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

  /* ──────────────────────────────────────────────────────────
     1. BRAND SPLASH ENTRANCE SCREEN (Only on initial entry)
     ────────────────────────────────────────────────────────── */
  const splash = document.getElementById('brand-splash');
  if (splash) {
    let alreadyShown = false;
    try {
      alreadyShown = sessionStorage.getItem('sathik_splash_shown');
    } catch (e) {}

    if (alreadyShown) {
      splash.style.display = 'none';
      splash.classList.add('hide');
    } else {
      try {
        sessionStorage.setItem('sathik_splash_shown', 'true');
      } catch (e) {}

      const hideSplash = () => {
        splash.classList.add('hide');
        setTimeout(() => {
          splash.style.display = 'none';
        }, 750);
      };

      // Hide after 1.5s (progress bar animation duration)
      setTimeout(hideSplash, 1500);

      // Allow tapping on mobile or desktop to skip early
      splash.addEventListener('click', hideSplash);
    }
  }

  /* ──────────────────────────────────────────────────────────
     2. MOBILE NAVIGATION — HAMBURGER TOGGLE
     ────────────────────────────────────────────────────────── */
  const navMenu = document.getElementById('nav-menu');
  const toggleBtn = document.getElementById('mobile-toggle-btn');
  const navbar = document.querySelector('.navbar');

  window.toggleMobileMenu = function () {
    if (!navMenu) return;
    const isOpen = navMenu.classList.toggle('active');
    if (toggleBtn) toggleBtn.classList.toggle('active', isOpen);
    // Prevent body scroll when drawer is open on mobile
    document.body.classList.toggle('menu-open', isOpen);
    if (toggleBtn) toggleBtn.setAttribute('aria-expanded', isOpen);
  };

  // Close menu when any nav-link or dropdown-item is tapped
  document.querySelectorAll('.nav-link, .dropdown-item').forEach(link => {
    link.addEventListener('click', () => {
      if (navMenu && navMenu.classList.contains('active')) {
        navMenu.classList.remove('active');
        if (toggleBtn) {
          toggleBtn.classList.remove('active');
          toggleBtn.setAttribute('aria-expanded', 'false');
        }
        document.body.classList.remove('menu-open');
      }
    });
  });

  /* ──────────────────────────────────────────────────────────
     2b. MOBILE VIEW STORE TITLE SCROLL TRANSITION
     ────────────────────────────────────────────────────────── */
  const brandText = document.getElementById('navbar-brand-text');
  const storeTitle = document.getElementById('navbar-store-title');
  if (brandText && storeTitle) {
    const handleScroll = () => {
      if (window.innerWidth <= 768) {
        if (window.scrollY > 120) {
          brandText.style.opacity = '0';
          brandText.style.transform = 'translateY(-8px)';
          brandText.style.pointerEvents = 'none';

          storeTitle.style.opacity = '1';
          storeTitle.style.transform = 'translateY(0)';
          storeTitle.style.pointerEvents = 'auto';
        } else {
          brandText.style.opacity = '1';
          brandText.style.transform = 'translateY(0)';
          brandText.style.pointerEvents = 'auto';

          storeTitle.style.opacity = '0';
          storeTitle.style.transform = 'translateY(8px)';
          storeTitle.style.pointerEvents = 'none';
        }
      } else {
        brandText.style.opacity = '1';
        brandText.style.transform = 'translateY(0)';
        brandText.style.pointerEvents = 'auto';

        storeTitle.style.opacity = '0';
        storeTitle.style.transform = 'translateY(8px)';
        storeTitle.style.pointerEvents = 'none';
      }
    };
    window.addEventListener('scroll', handleScroll);
    window.addEventListener('resize', handleScroll);
    handleScroll();
  }

  /* ──────────────────────────────────────────────────────────
     2c. SINGLE PAGE SCROLL SPY (NAVBAR ACTIVE STATE DYNAMIC SYNC)
     ────────────────────────────────────────────────────────── */
  const sections = document.querySelectorAll('section[id], header[id]');
  const navLinks = document.querySelectorAll('.nav-menu .nav-link');

  const onScroll = () => {
    let scrollPos = window.scrollY || document.documentElement.scrollTop;
    const headerHeight = document.querySelector('.navbar')?.offsetHeight || 80;
    
    // Map section IDs to corresponding navbar anchor targets
    const sectionToAnchor = {
      'hero': 'hero',
      'aboutUs': 'aboutUs',
      'product-range': 'product-range',
      'brands': 'brands',
      'testimonials': 'brands',
      'projects': 'contactUs',
      'contactUs': 'contactUs'
    };
    
    let currentSectionId = 'hero';
    
    // Check if we are at the bottom of the page
    if ((window.innerHeight + window.scrollY) >= document.documentElement.scrollHeight - 50) {
      currentSectionId = 'contactUs';
    } else {
      sections.forEach(section => {
        const sectionTop = section.offsetTop - headerHeight - 140;
        const sectionHeight = section.offsetHeight;
        if (scrollPos >= sectionTop && scrollPos < sectionTop + sectionHeight) {
          currentSectionId = section.getAttribute('id');
        }
      });
    }
    
    const targetAnchor = sectionToAnchor[currentSectionId] || currentSectionId;
    
    navLinks.forEach(link => {
      link.classList.remove('active');
      const href = link.getAttribute('href');
      if (href) {
        if (targetAnchor === 'hero') {
          if (href === '/' || href.endsWith('/') || href.endsWith('#hero')) {
            link.classList.add('active');
          }
        } else if (href.endsWith('#' + targetAnchor)) {
          link.classList.add('active');
        }
      }
    });
  };

  window.addEventListener('scroll', onScroll);
  onScroll();

  // Close menu on outside tap (mobile)
  document.addEventListener('click', (e) => {
    if (
      navMenu &&
      navMenu.classList.contains('active') &&
      !navMenu.contains(e.target) &&
      !toggleBtn.contains(e.target)
    ) {
      navMenu.classList.remove('active');
      if (toggleBtn) {
        toggleBtn.classList.remove('active');
        toggleBtn.setAttribute('aria-expanded', 'false');
      }
      document.body.classList.remove('menu-open');
    }
  });

  /* ──────────────────────────────────────────────────────────
     3. NAVBAR SCROLL SHADOW
     ────────────────────────────────────────────────────────── */
  if (navbar) {
    window.addEventListener('scroll', () => {
      navbar.classList.toggle('scrolled', window.scrollY > 10);
    }, { passive: true });
  }

  /* ──────────────────────────────────────────────────────────
     4. GLOBAL MODAL OPEN / CLOSE
     ────────────────────────────────────────────────────────── */
  window.openModal = function (modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.classList.add('show');
    document.body.classList.add('modal-open');
    // Focus first focusable input for accessibility
    const first = modal.querySelector('input, textarea, select, button');
    if (first) setTimeout(() => first.focus(), 100);
  };

  window.closeModal = function (modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.classList.remove('show');
    document.body.classList.remove('modal-open');
  };

  // Close modal on backdrop click (unless data-static-backdrop is enabled)
  document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) {
        if (backdrop.getAttribute('data-static-backdrop') === 'true' || backdrop.classList.contains('static-backdrop')) {
          // Do not exit on outside click - must click 'x' in the top
          return;
        }
        backdrop.classList.remove('show');
        document.body.classList.remove('modal-open');
      }
    });
  });

  // Close modal on ESC key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-backdrop.show').forEach(m => {
        m.classList.remove('show');
      });
      document.body.classList.remove('modal-open');
    }
  });

  /* ──────────────────────────────────────────────────────────
     5. PREPARE QUOTE MODAL (Product Page)
     ────────────────────────────────────────────────────────── */
  window.prepareQuoteModal = function (name, id, sku) {
    const nameField = document.getElementById('modal-product-name');
    const idField = document.getElementById('modal-product-id');
    const skuField = document.getElementById('modal-product-sku');
    if (nameField) nameField.value = name || '';
    if (idField) idField.value = id || '';
    if (skuField) skuField.value = sku || '';
    openModal('quote-modal');
  };

  /* ──────────────────────────────────────────────────────────
     6. STAT COUNTER ANIMATION (Intersection Observer)
     ────────────────────────────────────────────────────────── */
  const statNumbers = document.querySelectorAll('.stat-number');
  if (statNumbers.length && 'IntersectionObserver' in window) {
    const countUp = (el, target, suffix) => {
      let start = 0;
      const duration = 1400;
      const step = Math.ceil(target / (duration / 16));
      const timer = setInterval(() => {
        start += step;
        if (start >= target) {
          start = target;
          clearInterval(timer);
        }
        el.innerHTML = start.toLocaleString('en-IN') + '<span>' + suffix + '</span>';
      }, 16);
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        const raw = entry.target.textContent.trim();
        const suffix = raw.includes('+') ? '+' : '';
        const num = parseInt(raw.replace(/[^0-9]/g, ''), 10);
        if (!isNaN(num)) countUp(entry.target, num, suffix);
      });
    }, { threshold: 0.5 });

    statNumbers.forEach(el => observer.observe(el));
  }

  /* ──────────────────────────────────────────────────────────
     7. TOUCH-FRIENDLY CARD HOVER FEEDBACK
        (Adds 'touched' class on tap for .product-card, .trust-card, etc.)
     ────────────────────────────────────────────────────────── */
  const touchCards = document.querySelectorAll(
    '.product-card, .trust-card, .business-card, .brand-card-item'
  );
  touchCards.forEach(card => {
    card.addEventListener('touchstart', () => {
      card.classList.add('touched');
    }, { passive: true });
    card.addEventListener('touchend', () => {
      setTimeout(() => card.classList.remove('touched'), 300);
    }, { passive: true });
  });

  /* ──────────────────────────────────────────────────────────
     8. QUICK ENQUIRY FORM VALIDATION & SUBMISSION
     ────────────────────────────────────────────────────────── */
  const qeNameInput  = document.getElementById('qe-name');
  const qePhoneInput = document.getElementById('qe-phone');
  const qeEmailInput = document.getElementById('qe-email');
  const qeSubmitBtn  = document.getElementById('qe-submit-btn');

  function validateQuickEnquiryForm() {
    if (!qeNameInput || !qePhoneInput || !qeSubmitBtn) return false;

    let isValid = true;

    // 1. Name Validation (Required)
    const nameVal = qeNameInput.value.trim();
    const nameErr = document.getElementById('qe-name-error');
    if (nameVal.length === 0) {
      isValid = false;
      if (qeNameInput.dataset.touched) {
        if (nameErr) nameErr.textContent = 'Please enter your name';
        qeNameInput.classList.add('input-error');
      }
    } else {
      if (nameErr) nameErr.textContent = '';
      qeNameInput.classList.remove('input-error');
    }

    // 2. Mobile Validation (Required, numeric only, 10-15 digits)
    const phoneVal = qePhoneInput.value.replace(/\D/g, '');
    const phoneErr = document.getElementById('qe-phone-error');
    if (phoneVal.length < 10 || phoneVal.length > 15) {
      isValid = false;
      if (qePhoneInput.dataset.touched || phoneVal.length > 0) {
        if (phoneErr) phoneErr.textContent = 'Mobile number must be 10 to 15 digits';
        qePhoneInput.classList.add('input-error');
      }
    } else {
      if (phoneErr) phoneErr.textContent = '';
      qePhoneInput.classList.remove('input-error');
    }

    // 3. Email Validation (Optional, if provided must be valid)
    if (qeEmailInput && qeEmailInput.value.trim().length > 0) {
      const emailVal = qeEmailInput.value.trim();
      const emailErr = document.getElementById('qe-email-error');
      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailPattern.test(emailVal)) {
        isValid = false;
        if (emailErr) emailErr.textContent = 'Please enter a valid email address';
        qeEmailInput.classList.add('input-error');
      } else {
        if (emailErr) emailErr.textContent = '';
        qeEmailInput.classList.remove('input-error');
      }
    } else if (qeEmailInput) {
      const emailErr = document.getElementById('qe-email-error');
      if (emailErr) emailErr.textContent = '';
      qeEmailInput.classList.remove('input-error');
    }

    // Enable / Disable submit button
    qeSubmitBtn.disabled = !isValid;
    return isValid;
  }

  // Bind input listeners
  if (qeNameInput) {
    qeNameInput.addEventListener('input', () => {
      qeNameInput.dataset.touched = 'true';
      validateQuickEnquiryForm();
    });
    qeNameInput.addEventListener('blur', () => {
      qeNameInput.dataset.touched = 'true';
      validateQuickEnquiryForm();
    });
  }

  if (qePhoneInput) {
    qePhoneInput.addEventListener('input', (e) => {
      // Filter non-numeric input
      e.target.value = e.target.value.replace(/\D/g, '').slice(0, 15);
      qePhoneInput.dataset.touched = 'true';
      validateQuickEnquiryForm();
    });
    qePhoneInput.addEventListener('blur', () => {
      qePhoneInput.dataset.touched = 'true';
      validateQuickEnquiryForm();
    });
  }

  if (qeEmailInput) {
    qeEmailInput.addEventListener('input', validateQuickEnquiryForm);
    qeEmailInput.addEventListener('blur', validateQuickEnquiryForm);
  }

  // Quick Enquiry AJAX Submission Handler
  window.handleQuickEnquirySubmit = function (event, formEl) {
    event.preventDefault();
    if (!validateQuickEnquiryForm()) return;

    const submitBtn  = document.getElementById('qe-submit-btn');
    const btnSpinner = submitBtn ? submitBtn.querySelector('.btn-spinner') : null;
    const btnLabel   = submitBtn ? submitBtn.querySelector('.btn-label') : null;

    if (submitBtn) submitBtn.disabled = true;
    if (btnSpinner) btnSpinner.style.display = 'inline-block';
    if (btnLabel) btnLabel.textContent = 'Submitting...';

    const formData = new FormData(formEl);

    fetch('/enquiry/submit', {
      method: 'POST',
      body: formData
    })
    .then(res => res.json())
    .then(data => {
      if (btnSpinner) btnSpinner.style.display = 'none';
      if (btnLabel) btnLabel.textContent = 'Submit Enquiry';

      if (data.success) {
        formEl.reset();
        if (qeNameInput) delete qeNameInput.dataset.touched;
        if (qePhoneInput) delete qePhoneInput.dataset.touched;

        const waBtn = document.getElementById('qe-whatsapp-action-btn');
        if (waBtn && data.whatsapp_url) {
          waBtn.href = data.whatsapp_url;
          waBtn.style.display = 'flex';
        }

        closeModal('quick-enquiry-modal');
        openModal('quick-enquiry-success-modal');

        // Automatically open WhatsApp in a new tab for instant handoff
        if (data.whatsapp_url) {
          setTimeout(() => {
            try {
              window.open(data.whatsapp_url, '_blank');
            } catch (e) {
              console.log('Popup blocked; user can tap WhatsApp button.');
            }
          }, 600);
        }
      } else {
        if (submitBtn) submitBtn.disabled = false;
        alert(data.message || 'Submission failed. Please check your entries.');
      }
    })
    .catch(err => {
      if (btnSpinner) btnSpinner.style.display = 'none';
      if (btnLabel) btnLabel.textContent = 'Submit Enquiry';

      // Demo / fallback mode: show success popup gracefully
      formEl.reset();
      closeModal('quick-enquiry-modal');
      openModal('quick-enquiry-success-modal');
    });
  };

  /* ──────────────────────────────────────────────────────────
     9. HERO ADVERTISEMENT SLIDESHOW CONTROL
     ────────────────────────────────────────────────────────── */
  let currentSlide = 0;
  const slides = document.querySelectorAll('.hero-slide');
  const dots = document.querySelectorAll('.indicator-dot');
  let slideInterval = null;

  window.setSlide = function(index) {
    if (!slides.length) return;
    
    // Stop auto-play timer temporarily on manual click
    resetSlideTimer();
    
    // Deactivate current active slide and dot
    slides[currentSlide].classList.remove('active');
    if (dots[currentSlide]) dots[currentSlide].classList.remove('active');
    
    // Activate target slide and dot
    currentSlide = (index + slides.length) % slides.length;
    slides[currentSlide].classList.add('active');
    if (dots[currentSlide]) dots[currentSlide].classList.add('active');
    
    // Resume auto-play timer
    startSlideTimer();
  };

  window.nextSlide = function() {
    window.setSlide(currentSlide + 1);
  };

  window.prevSlide = function() {
    window.setSlide(currentSlide - 1);
  };

  function startSlideTimer() {
    if (slides.length > 1 && !slideInterval) {
      slideInterval = setInterval(window.nextSlide, 10000); // rotate every 10 seconds as requested
    }
  }

  function resetSlideTimer() {
    if (slideInterval) {
      clearInterval(slideInterval);
      slideInterval = null;
    }
  }

  // Initialize auto-rotation if slides exist
  if (slides.length > 0) {
    startSlideTimer();
  }

  // Touch and pointer swipe gesture navigation on hero section
  const heroEl = document.getElementById('hero');
  if (heroEl) {
    let startX = 0;
    let startY = 0;
    let endX = 0;
    let endY = 0;
    let isTracking = false;
    let isMouseDown = false;

    // Touch events for mobile/tablets
    heroEl.addEventListener('touchstart', function(e) {
      if (e.touches && e.touches.length === 1) {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
        endX = startX;
        endY = startY;
        isTracking = true;
      }
    }, { passive: true });

    heroEl.addEventListener('touchmove', function(e) {
      if (!isTracking || !e.touches || e.touches.length !== 1) return;
      endX = e.touches[0].clientX;
      endY = e.touches[0].clientY;
    }, { passive: true });

    heroEl.addEventListener('touchend', function() {
      if (!isTracking) return;
      isTracking = false;
      const deltaX = endX - startX;
      const deltaY = endY - startY;

      // Minimum swipe distance threshold (40px) with horizontal dominance
      if (Math.abs(deltaX) > 40 && Math.abs(deltaX) > Math.abs(deltaY) * 1.15) {
        if (deltaX < 0) {
          // Swiped left -> next slide
          window.nextSlide();
        } else {
          // Swiped right -> prev slide
          window.prevSlide();
        }
      }
    }, { passive: true });

    // Mouse drag events for desktop swipe
    heroEl.addEventListener('mousedown', function(e) {
      // Don't trigger swipe if clicking buttons, links or dots
      if (e.target.closest('a, button, input, .indicator-dot, .hero-arrow')) return;
      isMouseDown = true;
      startX = e.clientX;
      startY = e.clientY;
      endX = startX;
      endY = startY;
    });

    window.addEventListener('mousemove', function(e) {
      if (!isMouseDown) return;
      endX = e.clientX;
      endY = e.clientY;
    });

    window.addEventListener('mouseup', function(e) {
      if (!isMouseDown) return;
      isMouseDown = false;
      const deltaX = endX - startX;
      const deltaY = endY - startY;

      if (Math.abs(deltaX) > 60 && Math.abs(deltaX) > Math.abs(deltaY) * 1.2) {
        if (deltaX < 0) {
          window.nextSlide();
        } else {
          window.prevSlide();
        }
      }
    });
  }

  /* ──────────────────────────────────────────────────────────
     10. SHOPPING / QUOTE CART LOGIC
     ────────────────────────────────────────────────────────── */
  let quoteCart = [];
  try {
    quoteCart = JSON.parse(localStorage.getItem('quote_cart') || '[]');
  } catch (e) {
    quoteCart = [];
  }

  // Toast function
  window.showCartToast = function(message) {
    // Remove existing toasts
    document.querySelectorAll('.cart-toast').forEach(t => t.remove());
    
    const toast = document.createElement('div');
    toast.className = 'cart-toast';
    toast.innerHTML = `<span>🛒</span> <span>${message}</span>`;
    document.body.appendChild(toast);
    
    setTimeout(() => {
      toast.style.transition = 'opacity 0.5s';
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 500);
    }, 3000);
  };

  window.updateCartUI = function() {
    const count = quoteCart.length;
    
    const badge = document.getElementById('cart-badge');
    const badgeDesktop = document.getElementById('cart-badge-desktop');
    const badgeMobile = document.getElementById('cart-badge-mobile');
    
    if (badge) {
      badge.textContent = count;
      badge.style.display = count > 0 ? 'inline-block' : 'none';
    }
    if (badgeDesktop) {
      badgeDesktop.textContent = count;
      badgeDesktop.style.display = count > 0 ? 'inline-block' : 'none';
    }
    if (badgeMobile) {
      badgeMobile.textContent = count;
      badgeMobile.style.display = count > 0 ? 'flex' : 'none';
    }
    
    // Render list in modal
    const container = document.getElementById('cart-items-container');
    const formContainer = document.getElementById('cart-form-container');
    
    if (container) {
      if (count === 0) {
        container.innerHTML = `
          <div style="text-align:center; padding: 2rem 0; color: var(--text-muted);">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🛒</div>
            <p>Your quote request list is empty.</p>
          </div>
        `;
        if (formContainer) formContainer.style.display = 'none';
      } else {
        if (formContainer) formContainer.style.display = 'block';
        let html = '';
        quoteCart.forEach(item => {
          const imgUrl = item.image || '/static/images/placeholder.jpg';
          html += `
            <div class="cart-item-row">
              <img src="${imgUrl}" alt="${item.name}" class="cart-item-img">
              <div class="cart-item-info">
                <h5 class="cart-item-title">${item.name}</h5>
                <span class="cart-item-sku">SKU: ${item.sku}</span>
              </div>
              <button type="button" class="cart-item-remove" onclick="removeFromQuoteCart('${item.id}')" title="Remove item">&times;</button>
            </div>
          `;
        });
        container.innerHTML = html;
        
        // Update pre-filled message text in form
        const messageField = document.getElementById('cart-message');
        if (messageField) {
          let text = 'Hi, please send a price quote and availability details for the following products:\n';
          quoteCart.forEach(item => {
            text += `- ${item.name} (SKU: ${item.sku})\n`;
          });
          text += '\nThank you!';
          messageField.value = text;
        }
      }
    }
  };

  window.addToQuoteCart = function(id, name, sku, slug, subcategory_slug, image) {
    if (quoteCart.some(item => item.id === id)) {
      window.showCartToast(`"${name}" is already in your quote list.`);
      return;
    }
    
    quoteCart.push({ id, name, sku, slug, subcategory_slug, image });
    localStorage.setItem('quote_cart', JSON.stringify(quoteCart));
    window.updateCartUI();
    window.showCartToast(`Added "${name}" to quote request list!`);
  };

  window.removeFromQuoteCart = function(id) {
    quoteCart = quoteCart.filter(item => item.id !== id);
    localStorage.setItem('quote_cart', JSON.stringify(quoteCart));
    window.updateCartUI();
  };

  window.clearQuoteCart = function() {
    quoteCart = [];
    localStorage.setItem('quote_cart', JSON.stringify(quoteCart));
    window.updateCartUI();
  };

  window.handleCartEnquirySubmit = function(event, formEl) {
    event.preventDefault();
    
    const submitBtn = formEl.querySelector('button[type="submit"]');
    const alertEl = formEl.querySelector('.form-alert');
    
    if (submitBtn) submitBtn.disabled = true;
    if (alertEl) {
      alertEl.style.display = 'none';
      alertEl.className = 'alert';
    }
    
    const formData = new FormData(formEl);
    
    let productDetails = '';
    quoteCart.forEach((item, idx) => {
      productDetails += `${idx + 1}. ${item.name} (SKU: ${item.sku})\n`;
    });
    
    formData.append('product_name', 'Multiple Products Quote List');
    formData.append('interested_in', 'Multiple Showrooms');
    formData.append('type', 'quote_list');
    formData.append('items_json', JSON.stringify(quoteCart));
    formData.append('message', `[Quote Request List]\n${productDetails}\n[User Message]\n${formData.get('message')}`);
    
    fetch('/enquiry/submit', {
      method: 'POST',
      body: formData
    })
    .then(res => res.json())
    .then(data => {
      if (submitBtn) submitBtn.disabled = false;
      if (data.success) {
        if (alertEl) {
          alertEl.className = 'alert alert-success';
          alertEl.innerHTML = `<div>${data.message}</div>${data.whatsapp_url ? `<a href="${data.whatsapp_url}" target="_blank" rel="noopener noreferrer" class="btn btn-sm" style="background:#25D366; color:#fff; font-weight:700; display:inline-flex; align-items:center; gap:0.4rem; margin-top:0.6rem; text-decoration:none; padding:0.5rem 1rem; border-radius:6px;">💬 Open WhatsApp to Send Quote List</a>` : ''}`;
          alertEl.style.display = 'block';
        } else {
          alert(data.message);
        }
        formEl.reset();
        window.clearQuoteCart();
        
        if (data.whatsapp_url) {
          setTimeout(() => {
            try {
              window.open(data.whatsapp_url, '_blank');
            } catch(e) {}
          }, 600);
        }
        
        setTimeout(() => {
          window.closeModal('cart-modal');
        }, 3500);
      } else {
        const errText = data.errors ? Object.values(data.errors).join(', ') : (data.message || 'Submission failed');
        if (alertEl) {
          alertEl.className = 'alert alert-danger';
          alertEl.textContent = errText;
          alertEl.style.display = 'block';
        } else {
          alert(errText);
        }
      }
    })
    .catch(err => {
      if (submitBtn) submitBtn.disabled = false;
      alert('An error occurred. Please try again or contact us by phone.');
    });
  };

  window.updateCartUI();

  /* ──────────────────────────────────────────────────────────
     11. HOMEPAGE KALANJIAM PRODUCT CATEGORY FILTER
     ────────────────────────────────────────────────────────── */
  window.filterHomeCategory = function(storeSlug, btnEl) {
    document.querySelectorAll('.k-tab-btn').forEach(btn => btn.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');

    const cards = document.querySelectorAll('.k-prod-card');
    cards.forEach(card => {
      const category = card.getAttribute('data-category');
      if (storeSlug === 'all' || category === storeSlug) {
        card.style.display = 'flex';
      } else {
        card.style.display = 'none';
      }
    });
  };

  /* ──────────────────────────────────────────────────────────
     12. HOMEPAGE SHOWROOM SWITCHER TABS
     ────────────────────────────────────────────────────────── */
  window.switchShowroom = function(index, btnEl) {
    document.querySelectorAll('.showroom-tab-btn').forEach(btn => btn.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');

    document.querySelectorAll('.showroom-card-panel').forEach(panel => panel.classList.remove('active'));
    const targetPanel = document.getElementById(`showroom-panel-${index}`);
    if (targetPanel) {
      targetPanel.classList.add('active');
    }
  };

  /* ──────────────────────────────────────────────────────────
     13. BRAND LOGO LOCKUP ALIGNMENT (Top & Bottom Navbars)
     Aligns the right edge of SATHIK GROUPS with HARDWARES|PLUMBING|SANITARYWARE
     ────────────────────────────────────────────────────────── */
  function alignBrandLockups() {
    document.querySelectorAll('.brand-text').forEach(brand => {
      const name = brand.querySelector('.brand-name');
      const sub = brand.querySelector('.brand-sub');
      if (!name || !sub) return;

      name.style.letterSpacing = '';
      const subWidth = sub.getBoundingClientRect().width;
      const nameWidth = name.getBoundingClientRect().width;

      if (subWidth > 0 && nameWidth > 0 && Math.abs(subWidth - nameWidth) > 0.5) {
        const computed = window.getComputedStyle(name);
        const currentSpacing = parseFloat(computed.letterSpacing) || 0;
        const charCount = (name.textContent.trim().length - 1) || 12;
        const diff = subWidth - nameWidth;
        const adjustment = diff / charCount;
        name.style.letterSpacing = `${currentSpacing + adjustment}px`;
      }
    });
  }

  alignBrandLockups();
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(alignBrandLockups);
  }
  window.recordDirectQuoteClick = function(productName, sku, waUrl) {
    try {
      fetch('/quotations/record-click', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_name: productName,
          sku: sku,
          whatsapp_url: waUrl
        })
      }).catch(() => {});
    } catch(e) {}
  };
});


