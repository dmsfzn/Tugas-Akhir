/* dashboard-pegawai.js — Chart tren sentimen di dashboard pegawai. */

/**
 * Ambil data dari API /api/chart/sentiment dan render bar chart tren 14 hari.
 * Warna bar: biru (positif dominan) atau merah (negatif dominan).
 */
async function renderTrend() {
  try {
    var data  = await fetch('/api/chart/sentiment').then(function(r) { return r.json(); });
    var chart = document.getElementById('trendChart');
    if (!data.length) return;
    var maxVal = Math.max.apply(null, data.map(function(d) { return d.pos + d.neg; }));
    maxVal = maxVal || 1;
    chart.innerHTML = data.slice(-14).map(function(d) {
      var pct   = Math.round(((d.pos + d.neg) / maxVal) * 100);
      var isNeg = d.neg > d.pos;
      return '<div class="bar-col" style="height:' + Math.max(pct, 4) + '%;background:' +
        (isNeg ? 'var(--negative)' : 'var(--accent)') + ';opacity:.8;" title="' +
        d.day + ': ' + d.pos + ' pos, ' + d.neg + ' neg"></div>';
    }).join('');
  } catch(e) {
    var chart = document.getElementById('trendChart');
    if (chart) chart.innerHTML = '<span class="text-dimmer" style="font-size:11px;">Tidak ada data chart</span>';
  }
}

document.addEventListener('DOMContentLoaded', function() {
  renderTrend();
});
