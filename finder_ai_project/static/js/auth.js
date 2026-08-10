/* ═══════════════════════════════════════════════════════════════════════
   AUTH.JS  —  Finder AI  —  Splash + Login + Signup Modal Tickets
   ═══════════════════════════════════════════════════════════════════════ */

/* ─── SPLASH SCREEN ─────────────────────────────────────────────────── */
(function () {
  const splash   = document.getElementById('splashScreen');
  const shell    = document.getElementById('authShell');
  const startBtn = document.getElementById('splashStartBtn') || document.getElementById('landingStartBtn');
  const loginBtn = document.getElementById('landingLoginBtn');

  if (!splash || !startBtn) return;

  function leaveLanding(destination) {
    const isAuth = startBtn.dataset.authenticated === 'true';
    splash.classList.add('is-hiding');

    setTimeout(() => {
      splash.remove();
      if (isAuth && destination !== 'login') {
        const goto = shell ? shell.dataset.goto : null;
        window.location.href = goto || '/app/';
      } else {
        if (shell) {
          shell.hidden = false;
          shell.querySelector('input')?.focus();
        }
      }
    }, 580);
  }

  startBtn.addEventListener('click', () => leaveLanding('start'));
  loginBtn?.addEventListener('click', () => leaveLanding('login'));
})();

/* ─── SIGNUP MODAL CONTROLLER ────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {

  /* ── DOM references ── */
  const openBtn    = document.getElementById('openSignupModalBtn');
  const overlay    = document.getElementById('signupModalOverlay');
  const modal      = document.getElementById('signupModal');
  const closeBtn   = document.getElementById('closeSignupModalBtn');
  const viewport   = document.getElementById('ticketViewport');
  const progressFill = document.getElementById('signupProgressFill');
  const progressBar  = document.getElementById('signupProgressBar');
  const backBtn    = document.getElementById('modalBackBtn');
  const nextBtn    = document.getElementById('modalNextBtn');
  const submitBtn  = document.getElementById('modalSubmitBtn');
  const dots       = Array.from(document.querySelectorAll('.modal-step-dot'));
  const tickets    = Array.from(document.querySelectorAll('.signup-ticket'));
  const signupForm = document.getElementById('signupForm');

  if (!overlay || !openBtn) return;

  const TOTAL = tickets.length;  // 4 tickets
  let current = 0;

  /* ── OPEN MODAL ──────────────────────────────────────────────────── */
  openBtn.addEventListener('click', () => {
    overlay.hidden = false;
    overlay.classList.remove('is-closing');
    document.body.style.overflow = 'hidden';
    // Focus first input of ticket 0 after animation
    setTimeout(() => {
      const firstInput = tickets[0]?.querySelector('input');
      firstInput?.focus();
    }, 420);
  });

  /* ── CLOSE MODAL ─────────────────────────────────────────────────── */
  function closeModal() {
    overlay.classList.add('is-closing');
    document.body.style.overflow = '';
    setTimeout(() => {
      overlay.hidden = true;
      overlay.classList.remove('is-closing');
      // Reset to first ticket
      goToTicket(0, false);
    }, 280);
  }

  closeBtn.addEventListener('click', closeModal);

  // Click outside modal body to close
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeModal();
  });

  // Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !overlay.hidden) closeModal();
  });

  /* ── NAVIGATE TO TICKET ──────────────────────────────────────────── */
  function goToTicket(index, animate = true) {
    current = Math.max(0, Math.min(TOTAL - 1, index));

    // Slide viewport
    viewport.style.transform = `translateX(-${current * 100}%)`;

    // Update progress bar (25% per ticket)
    const pct = Math.round(((current + 1) / TOTAL) * 100);
    progressFill.style.width = pct + '%';
    progressBar.setAttribute('aria-valuenow', pct);

    // Update dots
    dots.forEach((dot, i) => {
      dot.classList.toggle('is-active', i === current);
      dot.classList.toggle('is-done',   i < current);
    });

    // Show/hide nav buttons
    backBtn.hidden   = current === 0;
    nextBtn.hidden   = current === TOTAL - 1;
    submitBtn.hidden = current !== TOTAL - 1;

    // Scroll ticket back to top
    if (animate) {
      tickets[current]?.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      tickets[current]?.scrollTo({ top: 0 });
    }

    // Focus first interactive element
    if (animate) {
      setTimeout(() => {
        tickets[current]?.querySelector('input, button')?.focus();
      }, 440);
    }
  }

  /* ── VALIDATION PER TICKET ────────────────────────────────────────── */
  function validateCurrentTicket() {
    const ticket = tickets[current];

    if (current === 0) {
      // Ticket 1: validate real form inputs
      const formInputs = Array.from(
        signupForm.querySelectorAll('input:not([type=hidden])')
      );
      for (const input of formInputs) {
        if (!input.checkValidity()) {
          input.reportValidity();
          input.focus();
          return false;
        }
      }
      // Check password match
      const pwd    = document.getElementById('signupPassword');
      const pwdCfm = document.getElementById('t1PasswordConfirm');
      if (pwd && pwdCfm && pwd.value !== pwdCfm.value) {
        pwdCfm.setCustomValidity('Les mots de passe ne correspondent pas.');
        pwdCfm.reportValidity();
        pwdCfm.setCustomValidity('');
        pwdCfm.focus();
        return false;
      }
      return true;
    }

    if (current === 1) {
      // Ticket 2: job_role required + at least 1 goal
      const jobInput = document.getElementById('t2JobRole');
      if (!jobInput?.value.trim()) {
        jobInput?.focus();
        showTicketError(ticket, 'Veuillez indiquer votre métier pour continuer.');
        return false;
      }
      const goalsChecked = ticket.querySelectorAll('[data-group="goals"]:checked');
      if (goalsChecked.length === 0) {
        showTicketError(ticket, 'Choisissez au moins un objectif pour continuer.');
        return false;
      }
      return true;
    }

    if (current === 2) {
      // Ticket 3: at least 1 source + 1 budget
      const sourcesChecked = ticket.querySelectorAll('[data-group="research_sources"]:checked');
      if (sourcesChecked.length === 0) {
        showTicketError(ticket, 'Sélectionnez au moins une source préférée.');
        return false;
      }
      const budgetChecked = ticket.querySelector('[data-group="budget_preference"]:checked');
      if (!budgetChecked) {
        showTicketError(ticket, 'Choisissez une préférence de budget.');
        return false;
      }
      return true;
    }

    // Ticket 3 (index 3): result_style is preselected (balanced by default) → always valid
    return true;
  }

  /* ── INLINE ERROR HELPER ──────────────────────────────────────────── */
  function showTicketError(ticket, message) {
    // Remove any existing error
    ticket.querySelector('.ticket-inline-error')?.remove();
    const err = document.createElement('p');
    err.className = 'ticket-inline-error';
    err.textContent = message;
    // Insert after ticket-header
    const header = ticket.querySelector('.ticket-header');
    header?.insertAdjacentElement('afterend', err);
    setTimeout(() => err.remove(), 4000);
  }

  /* ── COLLECT & SYNC HIDDEN FIELDS ────────────────────────────────── */
  function syncHiddenFields() {
    // Ticket 2
    const jobInput  = document.getElementById('t2JobRole');
    const expInput  = document.getElementById('t2ExpLevel');
    document.getElementById('h_job_role').value         = jobInput?.value  || '';
    document.getElementById('h_experience_level').value = expInput?.value  || '';

    // Goals (multi-checkbox → comma-separated)
    const goalsVals = Array.from(
      document.querySelectorAll('[data-group="goals"]:checked')
    ).map(c => c.value);
    document.getElementById('h_goals').value = goalsVals.join(',');

    // Ticket 3
    const srcVals = Array.from(
      document.querySelectorAll('[data-group="research_sources"]:checked')
    ).map(c => c.value);
    document.getElementById('h_research_sources').value = srcVals.join(',');

    const stackVals = Array.from(
      document.querySelectorAll('[data-group="technology_stack"]:checked')
    ).map(c => c.value);
    document.getElementById('h_technology_stack').value = stackVals.join(',');

    const budgetEl = document.querySelector('[data-group="budget_preference"]:checked');
    document.getElementById('h_budget_preference').value = budgetEl?.value || '';

    // Ticket 4
    const styleEl = document.querySelector('[data-group="result_style"]:checked');
    document.getElementById('h_result_style').value      = styleEl?.value || 'balanced';
    document.getElementById('h_preferred_language').value = document.getElementById('t4Lang')?.value  || '';
    document.getElementById('h_watch_frequency').value    = document.getElementById('t4Freq')?.value  || '';
  }

  /* ── NAV BUTTONS ──────────────────────────────────────────────────── */
  nextBtn?.addEventListener('click', () => {
    if (!validateCurrentTicket()) return;
    syncHiddenFields();
    goToTicket(current + 1);
  });

  backBtn?.addEventListener('click', () => {
    goToTicket(current - 1);
  });

  submitBtn?.addEventListener('click', () => {
    if (!validateCurrentTicket()) return;
    syncHiddenFields();
    submitBtn.disabled = true;
    submitBtn.textContent = 'Création en cours…';
    signupForm.requestSubmit();
  });

  /* ── PASSWORD STRENGTH HINT ─────────────────────────────────────── */
  const passwordInput = document.getElementById('signupPassword');
  const passwordHint  = document.getElementById('passwordHint');

  passwordInput?.addEventListener('input', () => {
    const v = passwordInput.value;
    const strong = v.length >= 10 && /[A-Z]/.test(v) && /\d/.test(v) && /[^A-Za-z0-9]/.test(v);
    if (!v) {
      passwordHint.textContent = 'Utilisez au moins 8 caractères, avec lettres, chiffres et symbole si possible.';
      passwordHint.classList.remove('is-strong');
    } else if (strong) {
      passwordHint.textContent = '✓ Mot de passe solide.';
      passwordHint.classList.add('is-strong');
    } else {
      passwordHint.textContent = 'Ajoutez une majuscule, un chiffre et un symbole pour le renforcer.';
      passwordHint.classList.remove('is-strong');
    }
  });

  /* ── INITIAL STATE ────────────────────────────────────────────────── */
  goToTicket(0, false);
});
