/** Wave 5: focus mode, reopen, pending reason, idle reminder, aging rows, cmd extras */
(function () {
  var FOCUS_KEY = 'cl-focus-mode';

  function csrf() {
    return (document.querySelector('meta[name="csrf-token"]') || {}).content || '';
  }

  function applyFocus(on) {
    document.body.classList.toggle('focus-mode', !!on);
    try { localStorage.setItem(FOCUS_KEY, on ? '1' : '0'); } catch (e) {}
    var btn = document.getElementById('focusToggle');
    if (btn) {
      btn.classList.toggle('active', !!on);
      btn.title = on ? 'Exit focus mode' : 'Focus mode (hide charts)';
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    try {
      if (localStorage.getItem(FOCUS_KEY) === '1') applyFocus(true);
    } catch (e) {}

    var ft = document.getElementById('focusToggle');
    if (ft) {
      ft.addEventListener('click', function () {
        applyFocus(!document.body.classList.contains('focus-mode'));
        if (window.clToast) {
          window.clToast('info', document.body.classList.contains('focus-mode') ? 'Focus mode on' : 'Focus mode off');
        }
      });
    }

    // F = focus mode (when not typing)
    document.addEventListener('keydown', function (e) {
      var tag = (e.target && e.target.tagName) || '';
      var typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (e.target && e.target.isContentEditable);
      if (typing || e.metaKey || e.ctrlKey) return;
      if (e.key === 'f' || e.key === 'F') {
        e.preventDefault();
        applyFocus(!document.body.classList.contains('focus-mode'));
      }
    });

    // Aging visual on rows with data-rel-time / data-logged
    document.querySelectorAll('.inbox-row[data-call-id]').forEach(function (row) {
      var rel = row.querySelector('[data-rel-time]');
      if (!rel) return;
      var iso = rel.getAttribute('data-rel-time');
      if (!iso) return;
      var then = new Date(iso);
      if (isNaN(then.getTime())) return;
      var hours = (Date.now() - then.getTime()) / 3600000;
      if (hours >= 48) row.classList.add('age-hot');
      else if (hours >= 24) row.classList.add('age-warm');
    });

    // Idle reminder after 25 minutes of no interaction
    var last = Date.now();
    ['mousemove', 'keydown', 'click', 'scroll'].forEach(function (ev) {
      document.addEventListener(ev, function () { last = Date.now(); }, { passive: true });
    });
    setInterval(function () {
      if (Date.now() - last > 25 * 60 * 1000) {
        if (window.clToast) window.clToast('warning', 'Still there? Your session is idle — save any draft notes.');
        last = Date.now(); // only once per idle stretch
      }
    }, 60000);

    // Enrich command palette with board + recent
    if (typeof window !== 'undefined') {
      window.clExtraCommands = function () {
        var extras = [
          { label: 'Board', href: '/board/', icon: 'fa-columns', keywords: 'kanban status' },
          { label: 'My queue', href: '/board/mine', icon: 'fa-inbox', keywords: 'assigned claim' },
          { label: 'Workload', href: '/board/workload', icon: 'fa-chart-bar', keywords: 'capacity agents' },
          { label: 'Toggle focus mode', action: 'focus', icon: 'fa-eye', keywords: 'distraction free' }
        ];
        try {
          var recent = JSON.parse(localStorage.getItem('cl-recent-pages') || '[]');
          recent.slice(0, 5).forEach(function (p, i) {
            extras.push({
              label: 'Recent: ' + p,
              href: p,
              icon: 'fa-clock',
              keywords: 'recent history '
 + i
            });
          });
        } catch (e) {}
        return extras;
      };
    }
  });

  // Capture-phase handlers for pending / reopen
  document.addEventListener('DOMContentLoaded', function () {
    document.body.addEventListener('click', function (e) {
      var q = e.target.closest('[data-quick]');
      if (!q) return;
      var action = q.getAttribute('data-quick');
      var id = q.getAttribute('data-call-id');

      if (action === 'pending') {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        var reason = window.prompt('Why is this pending?', 'Awaiting customer response');
        if (!reason || !reason.trim()) {
          if (window.clToast) window.clToast('warning', 'Reason required');
          return;
        }
        fetch('/api/calls/' + id + '/quick', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
          body: JSON.stringify({ action: 'pending', resolution: reason.trim() })
        }).then(function (r) { return r.json(); }).then(function (j) {
          if (j.ok) {
            if (window.clToast) window.clToast('success', 'Marked pending');
            setTimeout(function () { location.reload(); }, 400);
          }
        });
      }

      if (action === 'reopen') {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        fetch('/api/calls/' + id + '/quick', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
          body: JSON.stringify({ action: 'reopen' })
        }).then(function (r) { return r.json(); }).then(function (j) {
          if (j.ok) {
            if (window.clToast) window.clToast('success', 'Reopened');
            setTimeout(function () { location.reload(); }, 400);
          }
        });
      }

      if (action === 'focus') {
        e.preventDefault();
        applyFocus(!document.body.classList.contains('focus-mode'));
      }
    }, true);
  });
})();
