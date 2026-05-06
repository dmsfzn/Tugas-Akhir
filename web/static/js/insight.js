/* ── Halaman Insight JS ── */

document.addEventListener('DOMContentLoaded', function() {
  /* Render negative trend chart from inline data */
  var dataEl = document.getElementById('negTrendData');
  var el     = document.getElementById('negTrend');
  if (!dataEl || !el) return;

  try {
    var data = JSON.parse(dataEl.textContent);
    if (!data || !data.length) {
      el.innerHTML = '<span style="font-size:11px;color:var(--text-3);">Tidak ada data tren</span>';
      return;
    }
    var max = Math.max.apply(null, data.map(function(d) { return d.cnt; }));
    max = max || 1;
    el.innerHTML = data.map(function(d) {
      var h = Math.round((d.cnt / max) * 100);
      return '<div class="bar-col" style="height:' + Math.max(h, 4) + '%;background:' +
        (h > 70 ? 'var(--negative)' : 'rgba(249,115,22,.4)') + ';border-radius:3px 3px 0 0;" title="Minggu ' + d.wk + ': ' + d.cnt + ' negatif"></div>';
    }).join('');
  } catch(e) {}
});
