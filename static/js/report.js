/* ═══════════════════════════════════════════════════════════════
   MotorMind — report.js
   Shared JavaScript for ALL printable popup report pages.
   ═══════════════════════════════════════════════════════════════ */

'use strict';

/* ── PRINT ─────────────────────────────────────────────────────── */
function doPrint() {
  window.print();
}

/* ── CLOSE WINDOW ──────────────────────────────────────────────── */
function doClose() {
  if (window.history.length > 1) {
    window.close();
  } else {
    window.close();
  }
}

/* ── CONFIDENCE BAR — animate fill on load ─────────────────────── */
function animateConfBars() {
  document.querySelectorAll('.conf-fill[data-width]').forEach(el => {
    const w = el.getAttribute('data-width');
    /* small delay so transition is visible */
    setTimeout(() => { el.style.width = w + '%'; }, 120);
  });
}

/* ── WORD BAR — animate fill on load ──────────────────────────── */
function animateWordBars() {
  document.querySelectorAll('.word-bar-fill[data-width]').forEach(el => {
    const w = el.getAttribute('data-width');
    setTimeout(() => { el.style.width = w + '%'; }, 180);
  });
}

/* ── STACKED BAR — animate on load ─────────────────────────────── */
function animateTrendBars() {
  document.querySelectorAll('.bar-seg-pos[data-width], .bar-seg-neg[data-width]').forEach(el => {
    const w = el.getAttribute('data-width');
    setTimeout(() => { el.style.width = w + '%'; }, 200);
  });
}

/* ── TABLE STRIPE — zebra for print colour ──────────────────────── */
function ensureTableStripe() {
  document.querySelectorAll('.report-table tbody tr:nth-child(even) td').forEach(td => {
    /* already handled by CSS, this is a safety override for WebKit print */
    td.style.webkitPrintColorAdjust = 'exact';
  });
}

/* ── KEYBOARD SHORTCUTS ────────────────────────────────────────── */
function initKeyboardShortcuts() {
  document.addEventListener('keydown', function (e) {
    /* Ctrl/Cmd + P → print */
    if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
      /* let browser handle it naturally — no override needed */
      return;
    }
    /* Escape → close */
    if (e.key === 'Escape') {
      doClose();
    }
  });
}

/* ── TOOLBAR SCROLL SHADOW ─────────────────────────────────────── */
function initToolbarShadow() {
  const toolbar = document.querySelector('.report-toolbar');
  if (!toolbar) return;
  window.addEventListener('scroll', function () {
    toolbar.style.boxShadow = window.scrollY > 4
      ? '0 2px 12px rgba(0,0,0,.35)'
      : 'none';
  }, { passive: true });
}

/* ── RESPONSIVE TABLE — collapse columns on tiny screens ─────────── */
function initResponsiveTable() {
  if (window.innerWidth <= 480) {
    /* hide columns marked .hide-mobile (handled by CSS, but ensure aria) */
    document.querySelectorAll('.hide-mobile').forEach(el => {
      el.setAttribute('aria-hidden', 'true');
    });
  }
}

/* ── INIT ──────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {
  animateConfBars();
  animateWordBars();
  animateTrendBars();
  ensureTableStripe();
  initKeyboardShortcuts();
  initToolbarShadow();
  initResponsiveTable();
});
