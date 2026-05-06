/* dashboard-owner.js — Chart sentimen interaktif di dashboard owner. */

/* Data chart yang diambil dari API, disimpan di module scope untuk switch range. */
var chartData = [];

/** Fetch data dari API lalu render chart dengan range default 30 hari. */
async function loadChart() {
  try {
    chartData = await fetch('/api/chart/sentiment').then(function(r) { return r.json(); });
    renderChart(30);
  } catch(e) {}
}

/**
 * Render bar chart dari chartData dengan slice N hari terakhir.
 * @param {number} days - Jumlah hari yang ditampilkan (7 atau 30).
 */
function renderChart(days) {
  var el = document.getElementById('mainChart');
  if (!el) return;
  var slice = chartData.slice(-days);
  if (!slice.length) return;
  var max = Math.max.apply(null, slice.map(function(d) { return d.pos + d.neg; }));
  max = max || 1;
  el.innerHTML = slice.map(function(d) {
    var h     = Math.round(((d.pos + d.neg) / max) * 100);
    var isNeg = d.neg > d.pos;
    return '<div class="bar-col" style="height:' + Math.max(h, 4) + '%;background:' +
      (isNeg ? 'var(--negative)' : 'var(--accent)') + ';opacity:.75;" title="' +
      d.day + ': +' + d.pos + ' / -' + d.neg + '"></div>';
  }).join('');
}

/**
 * Ganti rentang tampilan chart (tombol 7d / 30d).
 * @param {number} days - Range hari yang dipilih.
 */
function switchRange(days) {
  var btn7  = document.getElementById('btn7d');
  var btn30 = document.getElementById('btn30d');
  if (btn7)  btn7.classList.toggle('active',  days === 7);
  if (btn30) btn30.classList.toggle('active', days === 30);
  renderChart(days);
}

document.addEventListener('DOMContentLoaded', function() {
  loadChart();
});
