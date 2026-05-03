/* ── Halaman Lexicon JS ── */

function openAddModal() {
  var m = document.getElementById('addModal');
  if (m) m.style.display = 'flex';
}

function openEditModal(id, word, score, category) {
  document.getElementById('editId').value       = id;
  document.getElementById('editWord').value     = word;
  document.getElementById('editScore').value    = score;
  document.getElementById('editCategory').value = category;
  var m = document.getElementById('editModal');
  if (m) m.style.display = 'flex';
}

function closeModal(id) {
  var m = document.getElementById(id);
  if (m) m.style.display = 'none';
}

document.addEventListener('DOMContentLoaded', function() {
  /* Close on backdrop click */
  document.querySelectorAll('.mm-modal-backdrop').forEach(function(el) {
    el.addEventListener('click', function(e) {
      if (e.target === this) this.style.display = 'none';
    });
  });
});
