/* MotorMind Report JS */

/* Cetak halaman */
function doPrint() {
  window.print();
}

/* Tutup popup */
function doClose() {
  window.close();
}

/* Download CSV — redirect ke endpoint */
function downloadCSV(url) {
  window.location.href = url;
}

/* Set dynamic styles from data attributes */
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('[data-width]').forEach(function(el) {
    el.style.width = el.getAttribute('data-width');
  });
  document.querySelectorAll('[data-opacity]').forEach(function(el) {
    el.style.opacity = el.getAttribute('data-opacity');
  });
  document.querySelectorAll('[data-size]').forEach(function(el) {
    el.style.fontSize = el.getAttribute('data-size');
  });
  document.querySelectorAll('[data-color]').forEach(function(el) {
    el.style.color = el.getAttribute('data-color');
  });
});
