/** Wave 10: P pending, filter collapse, recent callers, critical chime, shift summary */
(function () {
  function csrf() {
    return (document.querySelector('meta[name="csrf-token"]') || {}).content || '';
  }

  var CHIME_KEY = 'cl-critical-chime';
  var FILTER_KEY = 'cl-filters-collapsed';
  var RECENT_KEY = 'cl-recent-callers';

  function playChime() {
    try {
      if (localStorage.getItem(CHIME_KEY) !== '1') return;
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      var ctx = new Ctx();
      var o = ctx.createOscillator();
      var g = ctx.createGain();
      o.type = 'sine';
      o.frequency.value = 880;
      g.gain.value = 0.04;
      o.connect(g);
      g.connect(ctx.destination);
      o.start();
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
      o.stop(ctx.currentTime + 0.28);
    } catch (e) {}
  }

  document.addEventListener('DOMContentLoaded', function () {
    // Critical chime toggle
    var chime = document.getElementById('criticalChimeToggle');
    if (chime) {
      try { chime.checked = localStorage.getItem(CHIME_KEY) === '1'; } catch (e) {}
      chime.addEventListener('change', function () {
        try { localStorage.setItem(CHIME_KEY, chime.checked ? '1' : '0'); } catch (e) {}
        if (chime.checked) playChime();
        if (window.clToast) window.clToast('info', chime.checked ? 'Critical chime on' : 'Critical chime off');
      });
    }

    // Chime if critical rows present on load
    if (document.querySelector('.inbox-row.is-critical')) playChime();

    // Filter bar collapse
    var filterBar = document.querySelector('.filter-bar');
    var filterToggle = document.getElementById('toggleFilters');
    if (filterBar && filterToggle) {
      try {
        if (localStorage.getItem(FILTER_KEY) === '1') filterBar.classList.add('is-collapsed');
      } catch (e) {}
      filterToggle.addEventListener('click', function () {
        filterBar.classList.toggle('is-collapsed');
        try {
          localStorage.setItem(FILTER_KEY, filterBar.classList.contains('is-collapsed') ? '1' : '0');
        } catch (e) {}
      });
    }

    // Shift summary strip
    var shift = document.getElementById('shiftSummary');
    if (shift) {
      fetch('/api/dashboard/stats')
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d.ok) return;
          shift.innerHTML =
            '<span><strong>' + (d.my_open || 0) + '</strong> my open</span>' +
            '<span><strong>' + (d.resolved_today || 0) + '</strong> resolved today</span>' +
            '<span><strong>' + (d.unassigned || 0) + '</strong> unassigned</span>' +
            (d.sla_breach ? '<span class="shift-risk"><strong>' + d.sla_breach + '</strong> SLA risk</span>' : '');
          shift.hidden = false;
        })
        .catch(function () {});
    }

    // Remember recent callers on new-call submit
    var newForm = document.querySelector('form[action*="/calls/new"], form#newCallForm');
    if (!newForm) {
      // try by page path
      if (location.pathname.indexOf('/calls/new') === 0) {
        newForm = document.querySelector('form');
      }
    }
    if (newForm && location.pathname.indexOf('/calls/new') === 0) {
      newForm.addEventListener('submit', function () {
        var nameEl = newForm.querySelector('[name="caller_name"]');
        var phoneEl = newForm.querySelector('[name="phone_number"]');
        if (!nameEl || !phoneEl) return;
        var entry = {
          name: (nameEl.value || '').trim(),
          phone: (phoneEl.value || '').trim(),
          at: Date.now()
        };
        if (!entry.name || !entry.phone) return;
        var list = [];
        try { list = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); } catch (e) {}
        list = list.filter(function (x) { return x.phone !== entry.phone; });
        list.unshift(entry);
        list = list.slice(0, 8);
        try { localStorage.setItem(RECENT_KEY, JSON.stringify(list)); } catch (e) {}
      });

      // Render recent chips
      var host = document.getElementById('recentCallers');
      if (host) {
        var list = [];
        try { list = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); } catch (e) {}
        if (list.length) {
          host.innerHTML = '<span class="recent-label">Recent</span>';
          list.forEach(function (x) {
            var b = document.createElement('button');
            b.type = 'button';
            b.className = 'recent-chip';
            b.textContent = x.name.split(' ')[0] + ' · ' + x.phone.slice(-4);
            b.title = x.name + ' ' + x.phone;
            b.addEventListener('click', function () {
              var n = newForm.querySelector('[name="caller_name"]');
              var p = newForm.querySelector('[name="phone_number"]');
              if (n) n.value = x.name;
              if (p) {
                p.value = x.phone;
                p.dispatchEvent(new Event('input', { bubbles: true }));
                p.dispatchEvent(new Event('change', { bubbles: true }));
              }
            });
            host.appendChild(b);
          });
          host.hidden = false;
        }
      }
    }

    // Keyboard P = pending focused
    document.addEventListener('keydown', function (e) {
      var tag = (e.target && e.target.tagName) || '';
      var typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (e.target && e.target.isContentEditable);
      if (typing || e.metaKey || e.ctrlKey) return;
      if (e.key !== 'p' && e.key !== 'P') return;
      var focused = document.querySelector('.inbox-row.is-focused, .inbox-row.keyboard-focus, .inbox-row:focus');
      if (!focused) return;
      var id = focused.getAttribute('data-call-id');
      if (!id) return;
      e.preventDefault();
      var reason = window.prompt('Pending reason (optional):', 'Awaiting callback');
      if (reason === null) return;
      fetch('/api/calls/' + id + '/quick', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
        body: JSON.stringify({ action: 'pending', reason: reason || '' })
      }).then(function (r) { return r.json(); }).then(function (j) {
        if (j.ok) {
          if (window.clToast) window.clToast('info', 'Marked #' + id + ' pending');
          setTimeout(function () { location.reload(); }, 400);
        }
      });
    });
  });
})();
