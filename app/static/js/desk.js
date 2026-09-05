/** Call desk: SLA, relative time, bulk select, shortcuts */
document.addEventListener('DOMContentLoaded', function () {
  function relTime(iso) {
    if (!iso) return '';
    var then = new Date(iso);
    if (isNaN(then.getTime())) return '';
    var sec = Math.floor((Date.now() - then.getTime()) / 1000);
    if (sec < 60) return 'just now';
    if (sec < 3600) return Math.floor(sec / 60) + 'm ago';
    if (sec < 86400) return Math.floor(sec / 3600) + 'h ago';
    if (sec < 86400 * 7) return Math.floor(sec / 86400) + 'd ago';
    return then.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }
  document.querySelectorAll('[data-rel-time]').forEach(function (el) {
    var iso = el.getAttribute('data-rel-time');
    if (iso) el.textContent = relTime(iso);
  });
  document.querySelectorAll('[data-sla]').forEach(function (el) {
    var iso = el.getAttribute('data-logged');
    var target = parseFloat(el.getAttribute('data-target-hours') || '24');
    if (!iso) return;
    var then = new Date(iso);
    if (isNaN(then.getTime())) return;
    var hours = (Date.now() - then.getTime()) / 3600000;
    var left = target - hours;
    el.classList.remove('ok', 'warning', 'overdue');
    if (left < 0) { el.classList.add('overdue'); el.textContent = Math.abs(Math.round(left)) + 'h over'; }
    else if (left < target * 0.25) { el.classList.add('warning'); el.textContent = Math.round(left) + 'h left'; }
    else { el.classList.add('ok'); el.textContent = Math.round(left) + 'h left'; }
  });

  var checkAll = document.getElementById('checkAll');
  var bulkBar = document.getElementById('bulkBar');
  var bulkCount = document.getElementById('bulkCount');
  function selectedIds() {
    return Array.prototype.map.call(document.querySelectorAll('.row-select:checked'), function (c) { return c.value; });
  }
  function refreshBulk() {
    var ids = selectedIds();
    if (bulkBar) bulkBar.classList.toggle('visible', ids.length > 0);
    if (bulkCount) bulkCount.textContent = ids.length;
  }
  if (checkAll) checkAll.addEventListener('change', function () {
    document.querySelectorAll('.row-select').forEach(function (c) { c.checked = checkAll.checked; });
    refreshBulk();
  });
  document.querySelectorAll('.row-select').forEach(function (c) {
    c.addEventListener('change', refreshBulk);
  });
  var bulkClear = document.getElementById('bulkClear');
  if (bulkClear) bulkClear.addEventListener('click', function () {
    document.querySelectorAll('.row-select, #checkAll').forEach(function (c) { c.checked = false; });
    refreshBulk();
  });
  document.querySelectorAll('[data-bulk-action]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var ids = selectedIds();
      if (!ids.length) return;
      if (window.clToast) window.clToast('info', ids.length + ' selected — bulk API ships in backend phase.');
    });
  });

  function openShortcuts() {
    var ov = document.getElementById('shortcutsOverlay');
    if (ov) ov.hidden = false;
  }
  function closeShortcuts() {
    var ov = document.getElementById('shortcutsOverlay');
    if (ov) ov.hidden = true;
  }
  document.querySelectorAll('[data-shortcuts-open]').forEach(function (b) {
    b.addEventListener('click', openShortcuts);
  });
  document.querySelectorAll('[data-shortcuts-close]').forEach(function (b) {
    b.addEventListener('click', closeShortcuts);
  });
  var shortcutsOv = document.getElementById('shortcutsOverlay');
  if (shortcutsOv) {
    shortcutsOv.addEventListener('click', function (e) {
      if (e.target === shortcutsOv) closeShortcuts();
    });
  }

  document.addEventListener('keydown', function (e) {
    var tag = (e.target && e.target.tagName) || '';
    var typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (e.target && e.target.isContentEditable);
    if (e.key === 'Escape') closeShortcuts();
    if (typing) return;
    if (e.key === '?' || (e.shiftKey && e.key === '/')) { e.preventDefault(); openShortcuts(); }
    if (e.key === 'c' || e.key === 'C') {
      var n = document.getElementById('btnNewCall');
      if (n) { e.preventDefault(); window.location.href = n.getAttribute('href'); }
    }
    if (e.key === '/') {
      var s = document.getElementById('inboxSearch');
      if (s) { e.preventDefault(); s.focus(); }
    }
  });
});
