/* history.js — Logika halaman Riwayat Analisis (pegawai). */

/**
 * Buka popup laporan semua analisis dengan filter yang sedang aktif di form.
 * Mengumpulkan nilai dari setiap input filter lalu meneruskannya sebagai query string.
 */
function openAllReport() {
  var form = document.getElementById('filterForm');
  if (!form) return;
  var params = new URLSearchParams({
    date_from : form.querySelector('[name=date_from]').value,
    date_to   : form.querySelector('[name=date_to]').value,
    sentiment : form.querySelector('[name=sentiment]').value,
    q         : form.querySelector('[name=q]').value
  });
  openReport('/report/all-analyses?' + params.toString());
}

/**
 * Render activity bar chart (7 hari terakhir) dari data API sentimen.
 * Bar lebih tinggi menunjukkan hari dengan lebih banyak analisis.
 */
async function renderActivity() {
  try {
    var data  = await fetch('/api/chart/sentiment').then(function(r) { return r.json(); });
    var chart = document.getElementById('actChart');
    if (!chart || !data.length) return;
    var max = Math.max.apply(null, data.map(function(d) { return d.pos + d.neg; }));
    max = max || 1;
    chart.innerHTML = data.slice(-7).map(function(d) {
      var total = d.pos + d.neg;
      var h     = Math.round((total / max) * 100);
      return '<div class="bar-col" style="height:' + Math.max(h, 4) + '%;background:var(--bg-card-2);border-top:2px solid ' +
        (total > max * 0.6 ? 'var(--accent)' : 'var(--text-3)') + ';" title="' + d.day + '"></div>';
    }).join('');
  } catch(e) {}
}

document.addEventListener('DOMContentLoaded', function() {
  renderActivity();
});
