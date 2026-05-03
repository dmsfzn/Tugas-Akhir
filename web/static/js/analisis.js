/* Halaman Analisis JS */
document.addEventListener('DOMContentLoaded', function() {

  /* Submit loading state:
     Prevents multiple submissions and shows a loading spinner on the button when clicked. */
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

  /* Mini bar chart logic:
     Dynamically renders a small bar chart in the bottom right corner showing confidence distributions. */
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

  /* Set dynamic width for confidence bar from data attribute to avoid CSS linter errors */
  var confBars = document.querySelectorAll('.confidence-fill[data-width]');
  confBars.forEach(function(bar) {
    bar.style.width = bar.getAttribute('data-width');
  });
});

/* Clears the main text input area when the Clear button is clicked */
function clearInput() {
  var el = document.getElementById('inputText');
  if (el) el.value = '';
}

/* Handles the bulk file upload button selection (Currently just a UI stub) */
function handleBulkFile(inp) {
  if (inp.files && inp.files.length > 0) {
    showToast('File "' + inp.files[0].name + '" siap untuk diproses.', 'info');
  }
}
