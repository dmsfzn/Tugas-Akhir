/* lexicon.js — Modal CRUD kata lexicon di halaman Lexicon (pegawai). */

/** Tampilkan modal tambah kata baru. */
function openAddModal() {
  var m = document.getElementById('addModal');
  if (m) m.style.display = 'flex';
}

/**
 * Isi field form edit lalu tampilkan modal edit.
 * @param {number} id       - ID kata lexicon.
 * @param {string} word     - Kata yang akan diedit.
 * @param {number} score    - Skor sentimen saat ini.
 * @param {string} category - Kategori: 'positif' | 'negatif'.
 */
function openEditModal(id, word, score, category) {
  document.getElementById('editId').value       = id;
  document.getElementById('editWord').value     = word;
  document.getElementById('editScore').value    = score;
  document.getElementById('editCategory').value = category;
  var m = document.getElementById('editModal');
  if (m) m.style.display = 'flex';
}

/** Tutup modal berdasarkan ID elemen backdrop. */
function closeModal(id) {
  var m = document.getElementById(id);
  if (m) m.style.display = 'none';
}

document.addEventListener('DOMContentLoaded', function() {
  /* Tutup modal ketika user mengklik area backdrop di luar konten modal. */
  document.querySelectorAll('.mm-modal-backdrop').forEach(function(el) {
    el.addEventListener('click', function(e) {
      if (e.target === this) this.style.display = 'none';
    });
  });
});
