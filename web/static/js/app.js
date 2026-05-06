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

/* Tandai nav-item aktif di sidebar sesuai URL halaman saat ini. */
(function highlightActive() {
  var path = window.location.pathname;
  document.querySelectorAll('.mm-sidebar .nav-item').forEach(function (link) {
    if (link.getAttribute('href') === path) {
      link.classList.add('active');
    }
  });
})();
