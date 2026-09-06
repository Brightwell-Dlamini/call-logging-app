/** Wave 9: E escalate, auto-refresh, activity poll, copy filter URL, time-spent on resolve */
(function () {
  function csrf() {
    return (document.querySelector('meta[name="csrf-token"]') || {}).content || '';
  }

  var REFRESH_KEY = 'cl-auto-refresh';
  var ACT_KEY = 'cl-last-activity-id';

  document.addEventListener('DOMContentLoaded', function () {
    // Auto-refresh toggle
    var ar = document.getElementById('autoRefreshToggle');
    if (ar) {
      try {
        if (localStorage.getItem(REFRESH_KEY) === '1') ar.checked = true;
      } catch (e) {}
      ar.addEventListener('change', function () {
        try { localStorage.setItem(REFRESH_KEY, ar.checked ? '1' : '0'); } catch (e) {}
        if (window.clToast) window.clToast('info', ar.checked ? 'Auto-refresh on (60s)' : 'Auto-refresh off');
      });
      setInterval(function () {
        try {
          if (localStorage.getItem(REFRESH_KEY) !== '1') return;
        } catch (e) { return; }
        if (document.hidden) return;
        // only on calls list
        if (location.pathname.indexOf('/calls') === 0 && location.pathname.indexOf('/calls/') === -1) {
          location.reload();
        }
      }, 60000);
    }

    // Copy current filter URL
    var copyUrl = document.getElementById('btnCopyFilters');
    if (copyUrl) {
      copyUrl.addEventListener('click', function () {
        var url = location.href;
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(url).then(function () {
            if (window.clToast) window.clToast('success', 'Filter URL copied');
          });
        } else {
          prompt('Copy this URL', url);
        }
      });
    }

    // Poll notifications for new activity toast
    var lastId = null;
    try { lastId = localStorage.getItem(ACT_KEY); } catch (e) {}
    function pollActivity() {
      if (document.hidden) return;
      fetch('/api/notifications')
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d.ok || !d.items || !d.items.length) return;
          var newest = d.items[0];
          var nid = String(newest.id);
          if (lastId && nid !== lastId) {
            if (window.clToast) {
              window.clToast('info', (newest.title || 'New activity') + (newest.body ? ' — ' + newest.body : ''));
            }
          }
          lastId = nid;
          try { localStorage.setItem(ACT_KEY, nid); } catch (e) {}
        })
        .catch(function () {});
    }
    if (document.body.classList.contains('has-sidebar')) {
      setTimeout(pollActivity, 3000);
      setInterval(pollActivity, 45000);
    }

    // Keyboard E = escalate focused
    document.addEventListener('keydown', function (e) {
      var tag = (e.target && e.target.tagName) || '';
      var typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (e.target && e.target.isContentEditable);
      if (typing || e.metaKey || e.ctrlKey) return;
      if (e.key !== 'e' && e.key !== 'E') return;
      var focused = document.querySelector('.inbox-row.is-focused, .inbox-row.keyboard-focus, .inbox-row:focus');
      if (!focused) return;
      var id = focused.getAttribute('data-call-id');
      if (!id) return;
      e.preventDefault();
      fetch('/api/calls/' + id + '/quick', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
        body: JSON.stringify({ action: 'escalate' })
      }).then(function (r) { return r.json(); }).then(function (j) {
        if (j.ok) {
          if (window.clToast) window.clToast('warning', 'Escalated #' + id + ' to Critical');
          setTimeout(function () { location.reload(); }, 400);
        }
      });
    });
  });

  // Enhance R-resolve path: also ask time spent (hook after wave6)
  // Intercept resolve quick buttons for time spent
  document.addEventListener('DOMContentLoaded', function () {
    document.body.addEventListener('click', function (e) {
      var q = e.target.closest('[data-quick="resolve"]');
      if (!q || q.getAttribute('data-w9') === '1') return;
      // Let existing handlers run; we add time_spent via a secondary listener after resolve
      // Instead wrap: prevent and do full flow with time spent
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      var id = q.getAttribute('data-call-id');
      if (!id) return;
      var resolution = window.prompt('Resolution summary:', 'Resolved with caller');
      if (!resolution || !resolution.trim()) return;
      var mins = window.prompt('Time spent (minutes, optional):', '');
      var csat = window.prompt('Satisfaction 1–5 (optional):', '');
      var body = { action: 'resolve', resolution: resolution.trim() };
      if (mins && /^\d+$/.test(mins.trim())) body.time_spent = parseInt(mins.trim(), 10);
      if (csat && /^[1-5]$/.test(csat.trim())) body.satisfaction = parseInt(csat.trim(), 10);
      fetch('/api/calls/' + id + '/quick', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
        body: JSON.stringify(body)
      }).then(function (r) { return r.json(); }).then(function (j) {
        if (j.ok) {
          if (window.clToast) window.clToast('success', 'Resolved #' + id);
          setTimeout(function () { location.reload(); }, 400);
        }
      });
    }, true);
  });
})();
