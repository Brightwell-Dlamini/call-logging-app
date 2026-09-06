/** Wave 4: presence, note templates, resolve prompt, recent pages, bulk escalate */
(function () {
  var PRESENCE_KEY = 'cl-presence';
  var RECENT_KEY = 'cl-recent-pages';
  var TEMPLATES = [
    { label: 'Acknowledged', text: 'Acknowledged with caller. Investigating and will follow up.' },
    { label: 'Waiting on customer', text: 'Awaiting further information from the customer before proceeding.' },
    { label: 'Escalated internally', text: 'Escalated to the relevant internal team for specialised support.' },
    { label: 'Resolved on call', text: 'Issue resolved during the call. Customer confirmed understanding.' },
    { label: 'Callback scheduled', text: 'Callback scheduled with the customer for follow-up.' },
    { label: 'Password / access', text: 'Guided caller through access recovery steps. Access restored.' }
  ];

  function csrf() {
    return (document.querySelector('meta[name="csrf-token"]') || {}).content || '';
  }

  // Track recent pages for command palette
  try {
    var path = location.pathname + location.search;
    if (path && path !== '/login') {
      var recent = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
      recent = recent.filter(function (p) { return p !== path; });
      recent.unshift(path);
      localStorage.setItem(RECENT_KEY, JSON.stringify(recent.slice(0, 8)));
    }
  } catch (e) {}

  document.addEventListener('DOMContentLoaded', function () {
    // Presence selector
    var sel = document.getElementById('presenceSelect');
    if (sel) {
      try {
        var saved = localStorage.getItem(PRESENCE_KEY) || 'available';
        sel.value = saved;
        document.body.setAttribute('data-presence', saved);
      } catch (e) {}
      sel.addEventListener('change', function () {
        try { localStorage.setItem(PRESENCE_KEY, sel.value); } catch (e) {}
        document.body.setAttribute('data-presence', sel.value);
        if (window.clToast) window.clToast('info', 'Status: ' + sel.options[sel.selectedIndex].text);
      });
    }

    // Inject note templates near note textareas
    document.querySelectorAll('textarea[name="note"], textarea#note').forEach(function (ta) {
      if (ta.parentNode.querySelector('.note-templates')) return;
      var wrap = document.createElement('div');
      wrap.className = 'note-templates';
      wrap.innerHTML = '<span class="nt-label">Templates</span>';
      TEMPLATES.forEach(function (t) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'nt-chip';
        b.textContent = t.label;
        b.addEventListener('click', function () {
          ta.value = (ta.value ? ta.value + '\n' : '') + t.text;
          ta.focus();
        });
        wrap.appendChild(b);
      });
      ta.parentNode.insertBefore(wrap, ta);
    });

    // Gate resolve quick action — ask for resolution text
    document.body.addEventListener('click', function (e) {
      var q = e.target.closest('[data-quick="resolve"]');
      if (!q) return;
      // wave2 handles the click; we intercept first with capture by replacing handler
    }, true);
  });

  // Override resolve to require note (patch after wave2)
  document.addEventListener('DOMContentLoaded', function () {
    document.body.addEventListener('click', function (e) {
      var q = e.target.closest('[data-quick]');
      if (!q) return;
      var action = q.getAttribute('data-quick');
      if (action !== 'resolve') return;
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      var id = q.getAttribute('data-call-id');
      var resolution = window.prompt('Resolution summary (required):', 'Resolved with caller');
      if (!resolution || !resolution.trim()) {
        if (window.clToast) window.clToast('warning', 'Resolution required');
        return;
      }
      fetch('/api/calls/' + id + '/quick', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrf()
        },
        body: JSON.stringify({ action: 'resolve', resolution: resolution.trim() })
      }).then(function (r) { return r.json(); }).then(function (j) {
        if (j.ok) {
          if (window.clToast) window.clToast('success', 'Resolved');
          setTimeout(function () { location.reload(); }, 400);
        } else if (window.clToast) {
          window.clToast('error', j.error || 'Failed');
        }
      });
    }, true);

    // Bulk escalate
    document.querySelectorAll('[data-bulk-action="escalate"]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var ids = Array.prototype.map.call(
          document.querySelectorAll('.row-select:checked'),
          function (c) { return parseInt(c.value, 10); }
        );
        if (!ids.length) return;
        Promise.all(ids.map(function (id) {
          return fetch('/api/calls/' + id + '/quick', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrf()
            },
            body: JSON.stringify({ action: 'escalate' })
          });
        })).then(function () {
          if (window.clToast) window.clToast('success', 'Escalated ' + ids.length + ' call(s)');
          setTimeout(function () { location.reload(); }, 500);
        });
      });
    });

    // Expose recent pages for command palette consumers
    window.clRecentPages = function () {
      try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); } catch (e) { return []; }
    };
  });
})();
