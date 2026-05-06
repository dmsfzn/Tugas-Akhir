/* ── Halaman Analisis JS ── */
document.addEventListener('DOMContentLoaded', function() {

  /* Submit loading state */
  var form = document.getElementById('analysisForm');
  if (form) {
    form.addEventListener('submit', function() {
      var btn = document.getElementById('submitBtn');
      if (btn) {
        btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Processing...';
        btn.disabled = true;
      }
    });
  }

  /* Mini bar chart */
  var vals = [0.72, 0.88, 0.91, 0.65, 0.94, 0.83, 0.89];
  var el   = document.getElementById('confChart');
  if (el) {
    var max = Math.max.apply(null, vals);
    el.innerHTML = vals.map(function(v) {
      var h = Math.round((v / max) * 100);
      return '<div class="bar-col" style="height:' + h + '%;background:' +
        (v > 0.85 ? 'var(--accent)' : 'var(--bg-card-2)') + ';opacity:.9;" title="' +
        (v * 100).toFixed(0) + '%"></div>';
    }).join('');
  }
});

function clearInput() {
  var el = document.getElementById('inputText');
  if (el) el.value = '';
}

function handleBulkFile(inp) {
  if (inp.files && inp.files.length > 0) {
    showToast('File "' + inp.files[0].name + '" siap untuk diproses.', 'info');
  }
}
