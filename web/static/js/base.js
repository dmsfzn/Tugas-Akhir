/* MotorMind Base JS */

/* Toast notification */
function showToast(msg, type) {
  type = type || 'info';
  var icons = {
    success: '<i class="bi bi-check-circle-fill" style="color:#22c55e"></i>',
    danger:  '<i class="bi bi-exclamation-circle-fill" style="color:#ef4444"></i>',
    warning: '<i class="bi bi-exclamation-triangle-fill" style="color:#fbbf24"></i>',
    info:    '<i class="bi bi-info-circle-fill" style="color:#818cf8"></i>'
  };
  var c = document.getElementById('toastContainer');
  if (!c) return;
  var t = document.createElement('div');
  t.className = 'mm-toast';
  t.innerHTML = (icons[type] || icons.info) + '<span>' + msg + '</span>';
  c.appendChild(t);
  setTimeout(function() { t.remove(); }, 4000);
}

/* Konfirmasi hapus */
function confirmDelete(formId) {
  if (confirm('Yakin ingin menghapus data ini?')) {
    document.getElementById(formId).submit();
  }
}

/* Buka popup laporan */
function openReport(url) {
  window.open(url, '_blank', 'width=960,height=780,scrollbars=yes,resizable=yes');
}
