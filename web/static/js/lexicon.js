/**
 * lexicon.js — UI logic untuk halaman Manajemen Lexicon.
 *
 * Bertanggung jawab atas:
 *  - Membuka / menutup modal Tambah & Edit kata
 *  - Sinkronisasi skor default saat kategori berubah
 *  - Menutup modal saat klik di luar area modal (backdrop)
 */

/* ──────────────────────────────────────────────────────────────
   syncScore(categorySelectId, scoreInputId)
   Mengatur nilai skor input secara otomatis berdasarkan kategori
   yang dipilih:  positif → +1.0 | negatif → -1.0
   ────────────────────────────────────────────────────────────── */
function syncScore(categorySelectId, scoreInputId) {
  var cat   = document.getElementById(categorySelectId);
  var score = document.getElementById(scoreInputId);
  if (!cat || !score) return;
  score.value = cat.value === 'positif' ? '1.0' : '-1.0';
}

/* ──────────────────────────────────────────────────────────────
   openAddModal()
   Mereset form terlebih dahulu lalu menyinkronkan skor default,
   kemudian menampilkan modal Tambah Kata.
   ────────────────────────────────────────────────────────────── */
function openAddModal() {
  /* Reset semua field form ke nilai awal */
  var form = document.querySelector('#addModal form');
  if (form) form.reset();

  /* Pastikan skor sesuai kategori awal setelah reset */
  syncScore('addCategory', 'addScore');

  var m = document.getElementById('addModal');
  if (m) m.style.display = 'flex';
}

/* ──────────────────────────────────────────────────────────────
   openEditModal(btn)
   Membaca data-id, data-word, data-score, data-category dari
   atribut data-* pada tombol Edit yang diklik, lalu mengisi
   field form modal dan menampilkannya.

   Menggunakan data-* agar nilai Jinja2 tidak ditulis langsung
   di dalam string onclick="..." (yang memicu peringatan JS linter).
   ────────────────────────────────────────────────────────────── */
function openEditModal(btn) {
  document.getElementById('editId').value       = btn.dataset.id;
  document.getElementById('editWord').value     = btn.dataset.word;
  document.getElementById('editScore').value    = btn.dataset.score;
  document.getElementById('editCategory').value = btn.dataset.category;

  var m = document.getElementById('editModal');
  if (m) m.style.display = 'flex';
}

/* ──────────────────────────────────────────────────────────────
   closeModal(id)
   Menutup modal dengan id tertentu dengan menyembunyikannya.
   ────────────────────────────────────────────────────────────── */
function closeModal(id) {
  var m = document.getElementById(id);
  if (m) m.style.display = 'none';
}

/* ──────────────────────────────────────────────────────────────
   DOMContentLoaded — Pasang event listeners setelah DOM siap
   ────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function() {

  /* Auto-sinkron skor saat kategori diubah di modal ADD */
  var addCat = document.getElementById('addCategory');
  if (addCat) {
    addCat.addEventListener('change', function() {
      syncScore('addCategory', 'addScore');
    });
  }

  /* Auto-sinkron skor saat kategori diubah di modal EDIT */
  var editCat = document.getElementById('editCategory');
  if (editCat) {
    editCat.addEventListener('change', function() {
      syncScore('editCategory', 'editScore');
    });
  }

  /* Tutup modal saat user mengklik area backdrop (luar modal) */
  document.querySelectorAll('.mm-modal-backdrop').forEach(function(el) {
    el.addEventListener('click', function(e) {
      if (e.target === this) this.style.display = 'none';
    });
  });
});
