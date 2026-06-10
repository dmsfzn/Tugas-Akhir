/* app.js — Fungsi global MotorMind yang dipakai di semua halaman. */

'use strict';

/**
 * Tampilkan notifikasi toast di sudut layar.
 * @param {string} msg  - Pesan yang ditampilkan.
 * @param {string} type - Tipe toast: 'success' | 'danger' | 'warning' | 'info'.
 */
function showToast(msg, type) {
  type = type || 'info';
  const icons = {
    success: '<i class="bi bi-check-circle-fill" style="color:#22c55e"></i>',
    danger:  '<i class="bi bi-exclamation-circle-fill" style="color:#ef4444"></i>',
    warning: '<i class="bi bi-exclamation-triangle-fill" style="color:#fbbf24"></i>',
    info:    '<i class="bi bi-info-circle-fill" style="color:#818cf8"></i>',
  };
  const c = document.getElementById('toastContainer');
  if (!c) return;
  const t = document.createElement('div');
  t.className = 'mm-toast';
  t.innerHTML = (icons[type] || icons.info) + '<span>' + msg + '</span>';
  c.appendChild(t);
  setTimeout(function () { t.remove(); }, 4000);
}

/**
 * Tampilkan konfirmasi sebelum submit form hapus.
 * @param {string} formId - ID elemen <form> yang akan di-submit.
 */
function confirmDelete(formId) {
  if (confirm('Yakin ingin menghapus data ini?')) {
    document.getElementById(formId).submit();
  }
}

/**
 * Buka URL laporan di popup window terpusat.
 * @param {string} url - URL halaman laporan.
 */
function openReport(url) {
  var w    = Math.min(window.screen.width, 960);
  var h    = Math.min(window.screen.height, 800);
  var left = Math.round((window.screen.width  - w) / 2);
  var top  = Math.round((window.screen.height - h) / 2);
  window.open(
    url, '_blank',
    'width=' + w + ',height=' + h + ',left=' + left + ',top=' + top +
    ',scrollbars=yes,resizable=yes'
  );
}
/**
 * Terapkan atribut data-pct (lebar %), data-opacity, data-fsize, dan data-alpha
 * ke elemen yang sesuai sebagai style inline.
 * Memungkinkan Jinja2 menulis nilai dinamis ke data-*, bukan ke style="",
 * sehingga linter CSS tidak melihat ekspresi template di dalam atribut style.
 */
function applyDataWidths() {
  /* Bar / fill dengan lebar dan opasitas dinamis */
  document.querySelectorAll('[data-pct]').forEach(function(el) {
    el.style.width = el.getAttribute('data-pct') + '%';
    var op = el.getAttribute('data-opacity');
    if (op !== null) el.style.opacity = op;
  });

  /* Word-cloud span: ukuran font dan warna alpha dinamis */
  document.querySelectorAll('[data-fsize]').forEach(function(el) {
    el.style.fontFamily = "'Space Mono', monospace";
    el.style.fontSize   = el.getAttribute('data-fsize') + 'px';
    var alpha = el.getAttribute('data-alpha');
    if (alpha !== null) {
      el.style.color = 'rgba(249,115,22,' + alpha + ')';
    }
    el.style.cursor = 'default';
  });

  /* Elemen dengan background warna dari data-bg */
  document.querySelectorAll('[data-bg]').forEach(function(el) {
    el.style.background = el.getAttribute('data-bg');
  });
}

document.addEventListener('DOMContentLoaded', applyDataWidths);

/* Tandai nav-item aktif di sidebar sesuai URL halaman saat ini. */
(function highlightActive() {
  var path = window.location.pathname;
  document.querySelectorAll('.mm-sidebar .nav-item').forEach(function (link) {
    if (link.getAttribute('href') === path) {
      link.classList.add('active');
    }
  });
})();

/* Toggle Sidebar dengan persistensi state */
(function setupSidebarToggle() {
  const toggleBtn = document.getElementById('sidebarToggle');
  const wrapper = document.querySelector('.mm-wrapper');
  const sidebar = document.querySelector('.mm-sidebar');

  if (toggleBtn && wrapper && sidebar) {
    // Periksa status tersimpan di localStorage (default adalah collapsed/minim)
    const sidebarState = localStorage.getItem('sidebar-state');
    if (sidebarState === 'expanded') {
      wrapper.classList.add('sidebar-expanded');
    }

    toggleBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      wrapper.classList.toggle('sidebar-expanded');
      localStorage.setItem(
        'sidebar-state',
        wrapper.classList.contains('sidebar-expanded') ? 'expanded' : 'collapsed'
      );
    });

    // Sembunyikan/minimize sidebar di mobile ketika mengklik di luar sidebar
    document.addEventListener('click', function(e) {
      if (wrapper.classList.contains('sidebar-expanded')) {
        if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
          wrapper.classList.remove('sidebar-expanded');
          localStorage.setItem('sidebar-state', 'collapsed');
        }
      }
    });
  }
})();
