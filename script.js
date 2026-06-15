// Nav scroll effect
const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {
  nav.classList.toggle('scrolled', window.scrollY > 20);
}, { passive: true });

// Mobile toggle
document.getElementById('mobileToggle').addEventListener('click', () => {
  const links = document.querySelector('.nav-links');
  const cta = document.querySelector('.nav-cta');
  if (links) {
    const open = links.style.display === 'flex';
    links.style.cssText = open ? '' : 'display:flex;flex-direction:column;position:fixed;top:70px;left:0;right:0;background:rgba(8,10,15,0.97);padding:24px;gap:20px;border-bottom:1px solid rgba(255,255,255,0.07);backdrop-filter:blur(20px);z-index:99;';
  }
});

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const target = document.querySelector(a.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});

// Reveal on scroll (IntersectionObserver)
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      const siblings = [...entry.target.parentElement.querySelectorAll('[data-reveal]')];
      const idx = siblings.indexOf(entry.target);
      setTimeout(() => {
        entry.target.classList.add('revealed');
      }, idx * 80);
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll('[data-reveal]').forEach(el => revealObserver.observe(el));

// Animated counter for stats
function animateCounter(el, target, duration = 1800) {
  const start = performance.now();
  const update = (time) => {
    const progress = Math.min((time - start) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.floor(ease * target).toLocaleString();
    if (progress < 1) requestAnimationFrame(update);
    else el.textContent = target.toLocaleString();
  };
  requestAnimationFrame(update);
}

const statsObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      document.querySelectorAll('.stat-num').forEach(el => {
        animateCounter(el, parseInt(el.dataset.target));
      });
      statsObserver.disconnect();
    }
  });
}, { threshold: 0.5 });
const statsEl = document.querySelector('.hero-stats');
if (statsEl) statsObserver.observe(statsEl);

// Animate progress bars when workflow section enters view
const barObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.querySelectorAll('.bar-fill').forEach(bar => {
        bar.classList.add('animated');
      });
      barObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.3 });
const workflowEl = document.querySelector('.workflow-steps');
if (workflowEl) barObserver.observe(workflowEl);

// Subtle parallax on hero glow elements
let ticking = false;
window.addEventListener('scroll', () => {
  if (!ticking) {
    requestAnimationFrame(() => {
      const y = window.scrollY;
      document.querySelectorAll('.hero-glow').forEach((glow, i) => {
        glow.style.transform = `translateY(${y * (0.05 + i * 0.03)}px)`;
      });
      ticking = false;
    });
    ticking = true;
  }
}, { passive: true });

// Cursor-following glow on feature cards
document.querySelectorAll('.feature-card, .price-card, .testi-card').forEach(card => {
  card.addEventListener('mousemove', e => {
    const rect = card.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    card.style.setProperty('--mx', `${x}%`);
    card.style.setProperty('--my', `${y}%`);
  });
});

// Gallery hover: show all overlays on touch
if ('ontouchstart' in window) {
  document.querySelectorAll('.gi-overlay').forEach(el => {
    el.style.opacity = '1';
  });
}
