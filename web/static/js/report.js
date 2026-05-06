/**
 * report.js — Fungsi tombol aksi di semua halaman laporan (popup window).
 *
 * Juga bertugas menerapkan nilai lebar (width) dan opasitas dinamis
 * dari atribut data-* ke elemen bar/fill, agar template Jinja2 tidak
 * perlu menyisipkan ekspresi {{ }} langsung di dalam atribut style="",
 * yang akan memicu peringatan linter "Do not use empty rulesets".
 */

/** Cetak halaman laporan menggunakan dialog print browser. */
function doPrint() {
  window.print();
}

/** Tutup popup window laporan. */
function doClose() {
  window.close();
}

/**
 * Download data sebagai file CSV melalui redirect ke endpoint Flask.
 * @param {string} url - URL endpoint export CSV.
 */
function downloadCSV(url) {
  window.location.href = url;
}

/**
 * applyDataWidths()
 * Membaca atribut data-pct (lebar %) dan data-opacity (opsional) pada
 * setiap elemen bertanda [data-pct], lalu menerapkannya sebagai
 * style.width dan style.opacity. Dipanggil saat DOM siap.
 *
 * Digunakan agar nilai dinamis dari Jinja2 ditempatkan pada data-*
 * (bukan di dalam style=""), menghindari peringatan CSS linter.
 */
function applyDataWidths() {
  /* Bar / fill elemen dengan lebar dinamis */
  document.querySelectorAll('[data-pct]').forEach(function(el) {
    el.style.width = el.getAttribute('data-pct') + '%';
    var op = el.getAttribute('data-opacity');
    if (op !== null) el.style.opacity = op;
  });

  /* Word-cloud span: font-size dan warna dengan alpha dinamis */
  document.querySelectorAll('[data-fsize]').forEach(function(el) {
    el.style.fontFamily = "'Space Mono', monospace";
    el.style.fontSize   = el.getAttribute('data-fsize') + 'px';
    var alpha = el.getAttribute('data-alpha');
    if (alpha !== null) {
      el.style.color = 'rgba(249,115,22,' + alpha + ')';
    }
  });
}

document.addEventListener('DOMContentLoaded', applyDataWidths);
