/** Wave 7: draft autosave, S star, offline, unassigned badge, audit filter */
(function () {
  function csrf() {
    return (document.querySelector('meta[name="csrf-token"]') || {}).content || '';
  }

  document.addEventListener('DOMContentLoaded', function () {
    // Draft note autosave per call
    var noteTa = document.querySelector('textarea[name="note"]');
    var callMatch = location.pathname.match(/\/calls\/(\d+)/);
    if (noteTa && callMatch) {
      var key = 'cl-draft-note-' + callMatch[1];
      try {
        var saved = localStorage.getItem(key);
        if (saved && !noteTa.value) noteTa.value = saved;
      } catch (e) {}
      var saveT;
      noteTa.addEventListener('input', function () {
        clearTimeout(saveT);
        saveT = setTimeout(function () {
          try { localStorage.setItem(key, noteTa.value); } catch (e) {}
        }, 400);
      });
      var form = noteTa.closest('form');
      if (form) {
        form.addEventListener('submit', function () {
          try { localStorage.removeItem(key); } catch (e) {}
        });
      }
    }

    // Offline / online toasts
    window.addEventListener('offline', function () {
      if (window.clToast) window.clToast('warning', 'You are offline — changes may not save');
    });
    window.addEventListener('online', function () {
      if (window.clToast) window.clToast('success', 'Back online');
    });

    // Unassigned badge in nav
    var callsNav = document.querySelector('a.nav-item[href="/calls/"]') ||
      document.querySelector('a.nav-item[href*="/calls"]');
    if (callsNav) {
      fetch('/api/dashboard/stats')
        .then(function (r) { return r.json(); })
        .then(function (d) {
          var n = d.unassigned || 0;
          if (n > 0) {
            var badge = document.createElement('span');
            badge.className = 'nav-count-badge';
            badge.textContent = n > 99 ? '99+' : String(n);
            badge.title = n + ' unassigned';
            callsNav.appendChild(badge);
          }
        })
        .catch(function () {});
    }

    // S = star focused row
    document.addEventListener('keydown', function (e) {
      var tag = (e.target && e.target.tagName) || '';
      var typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (e.target && e.target.isContentEditable);
      if (typing || e.metaKey || e.ctrlKey) return;
      if (e.key !== 's' && e.key !== 'S') return;
      var focused = document.querySelector('.inbox-row.is-focused, .inbox-row.keyboard-focus, .inbox-row:focus');
      if (!focused) return;
      var id = focused.getAttribute('data-call-id');
      if (!id) return;
      e.preventDefault();
      var stars = [];
      try { stars = JSON.parse(localStorage.getItem('cl-stars') || '[]'); } catch (err) {}
      var idx = stars.indexOf(String(id));
      if (idx >= 0) stars.splice(idx, 1);
      else stars.push(String(id));
      try { localStorage.setItem('cl-stars', JSON.stringify(stars)); } catch (err) {}
      focused.classList.toggle('is-starred', idx < 0);
      if (window.clToast) window.clToast('info', idx < 0 ? 'Starred #' + id : 'Unstarred #' + id);
    });

    // Apply starred class on load
    try {
      var stars = JSON.parse(localStorage.getItem('cl-stars') || '[]');
      document.querySelectorAll('.inbox-row[data-call-id]').forEach(function (row) {
        if (stars.indexOf(String(row.getAttribute('data-call-id'))) >= 0) {
          row.classList.add('is-starred');
        }
      });
    } catch (e) {}

    // Audit log client filter
    var auditFilter = document.getElementById('auditFilter');
    if (auditFilter) {
      auditFilter.addEventListener('input', function () {
        var q = auditFilter.value.toLowerCase().trim();
        document.querySelectorAll('.table tbody tr').forEach(function (tr) {
          var text = tr.textContent.toLowerCase();
          tr.style.display = !q || text.indexOf(q) !== -1 ? '' : 'none';
        });
      });
    }

    // Round-robin button
    var rr = document.getElementById('btnRoundRobin');
    if (rr) {
      rr.addEventListener('click', function () {
        if (!confirm('Assign all unassigned open calls round-robin to active agents?')) return;
        fetch('/api/calls/round-robin', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf()
          },
          body: JSON.stringify({})
        }).then(function (r) { return r.json(); }).then(function (j) {
          if (j.ok) {
            if (window.clToast) window.clToast('success', 'Assigned ' + (j.assigned || 0) + ' call(s)');
            setTimeout(function () { location.reload(); }, 600);
          } else if (window.clToast) {
            window.clToast('error', j.error || 'Failed');
          }
        });
      });
    }
  });
})();
