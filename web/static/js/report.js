/* report.js — Fungsi tombol aksi di semua halaman laporan (popup window). */

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
