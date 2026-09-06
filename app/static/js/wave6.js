/** Wave 6: sidebar collapse, live relative times, phone history, R to resolve, CSAT */
(function () {
  var SIDEBAR_KEY = 'cl-sidebar-collapsed';

  function csrf() {
    return (document.querySelector('meta[name="csrf-token"]') || {}).content || '';
  }

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

  function refreshRelTimes() {
    document.querySelectorAll('[data-rel-time]').forEach(function (el) {
      var iso = el.getAttribute('data-rel-time');
      if (iso) el.textContent = relTime(iso);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    // Sidebar collapse
    try {
      if (localStorage.getItem(SIDEBAR_KEY) === '1') {
        document.body.classList.add('sidebar-collapsed');
      }
    } catch (e) {}
    var collapseBtn = document.getElementById('sidebarCollapse');
    if (collapseBtn) {
      collapseBtn.addEventListener('click', function () {
        document.body.classList.toggle('sidebar-collapsed');
        try {
          localStorage.setItem(SIDEBAR_KEY, document.body.classList.contains('sidebar-collapsed') ? '1' : '0');
        } catch (e) {}
      });
    }

    // Live relative times every 60s
    refreshRelTimes();
    setInterval(refreshRelTimes, 60000);

    // Phone history on log call form
    var phoneInput = document.querySelector('#logCallForm input[name="phone_number"]');
    var histBox = document.getElementById('phoneHistory');
    var nameInput = document.querySelector('#logCallForm input[name="caller_name"]');
    if (phoneInput && histBox) {
      var t = null;
      phoneInput.addEventListener('input', function () {
        clearTimeout(t);
        var v = phoneInput.value.trim();
        if (v.length < 5) {
          histBox.hidden = true;
          histBox.innerHTML = '';
          return;
        }
        t = setTimeout(function () {
          fetch('/api/phone-lookup?phone=' + encodeURIComponent(v))
            .then(function (r) { return r.json(); })
            .then(function (data) {
              var matches = data.matches || [];
              if (!matches.length) {
                histBox.hidden = false;
                histBox.innerHTML = '<div class="ph-empty">No prior calls for this number</div>';
                return;
              }
              // Prefill name if empty
              if (nameInput && !nameInput.value && matches[0].caller) {
                nameInput.value = matches[0].caller;
              }
              histBox.hidden = false;
              histBox.innerHTML = '<div class="ph-title"><i class="fas fa-clock-rotate-left"></i> Prior calls (' + matches.length + ')</div>' +
                matches.map(function (m) {
                  return '<a class="ph-row" href="/calls/' + m.id + '">' +
                    '<span class="ph-id">#' + m.id + '</span>' +
                    '<span class="ph-meta">' + (m.date || '') + ' · ' + (m.status || '') + '</span>' +
                    '<span class="ph-reason">' + (m.reason || '').replace(/</g, '&lt;') + '</span></a>';
                }).join('');
            })
            .catch(function () {});
        }, 350);
      });
    }

    // R = resolve focused inbox row
    document.addEventListener('keydown', function (e) {
      var tag = (e.target && e.target.tagName) || '';
      var typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (e.target && e.target.isContentEditable);
      if (typing || e.metaKey || e.ctrlKey) return;
      if (e.key !== 'r' && e.key !== 'R') return;
      var focused = document.querySelector('.inbox-row.is-focused, .inbox-row:focus');
      if (!focused) focused = document.querySelector('.inbox-row.keyboard-focus');
      if (!focused) return;
      var id = focused.getAttribute('data-call-id');
      if (!id) return;
      e.preventDefault();
      var resolution = window.prompt('Resolution summary:', 'Resolved with caller');
      if (!resolution || !resolution.trim()) return;
      var csat = window.prompt('Satisfaction 1–5 (optional, Enter to skip):', '');
      var body = { action: 'resolve', resolution: resolution.trim() };
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
    });
  });

  // Enhance resolve quick action to ask CSAT (after wave4)
  document.addEventListener('DOMContentLoaded', function () {
    document.body.addEventListener('click', function (e) {
      var q = e.target.closest('[data-quick="resolve"]');
      if (!q) return;
      // wave4 already handles resolve with prompt; we only add CSAT if not intercepted
      // Use a custom attribute once handled
    }, true);
  });
})();
