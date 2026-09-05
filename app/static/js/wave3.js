/** Wave 3: health badge, B/Q/W navigation, notif auto-refresh, copy buttons */
(function () {
  document.addEventListener('DOMContentLoaded', function () {
    // Health badge
    var badge = document.getElementById('healthBadge');
    if (badge) {
      fetch('/health')
        .then(function (r) { return r.json(); })
        .then(function (d) {
          badge.classList.add(d.database === 'ok' ? 'ok' : 'bad');
          badge.title = (d.backend || '') + ' · ' + (d.database || '');
          badge.setAttribute('aria-label', 'System ' + (d.status || 'unknown'));
        })
        .catch(function () { badge.classList.add('bad'); });
    }

    // Keyboard: B board, Q queue, W workload, T theme already elsewhere
    document.addEventListener('keydown', function (e) {
      var tag = (e.target && e.target.tagName) || '';
      var typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (e.target && e.target.isContentEditable);
      if (typing || e.metaKey || e.ctrlKey || e.altKey) return;
      var k = e.key.toLowerCase();
      if (k === 'b') { e.preventDefault(); window.location.href = '/board/'; }
      if (k === 'q') { e.preventDefault(); window.location.href = '/board/mine'; }
      if (k === 'w') { e.preventDefault(); window.location.href = '/board/workload'; }
    });

    // Copy buttons
    document.body.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-copy]');
      if (!btn) return;
      var text = btn.getAttribute('data-copy');
      if (!text) return;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () {
          if (window.clToast) window.clToast('success', 'Copied');
        });
      }
    });

    // Notif auto-refresh every 90s
    setInterval(function () {
      var badgeEl = document.getElementById('notifBadge');
      if (!badgeEl) return;
      fetch('/api/notifications')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var n = (data.items || []).length;
          badgeEl.textContent = n > 9 ? '9+' : String(n);
          badgeEl.hidden = n === 0;
        })
        .catch(function () {});
    }, 90000);

    // Restore star icons on detail page
    var stars = [];
    try { stars = JSON.parse(localStorage.getItem('cl-stars') || '[]'); } catch (err) {}
    document.querySelectorAll('[data-star-id]').forEach(function (el) {
      var id = el.getAttribute('data-star-id');
      var icon = el.querySelector('i');
      if (icon && stars.indexOf(id) >= 0) icon.className = 'fas fa-star';
    });
  });
})();
