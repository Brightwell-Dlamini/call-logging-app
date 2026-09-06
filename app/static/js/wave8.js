/** Wave 8: A claim, N next, starred filter, on-call timer, progress bar, celebration */
(function () {
  function csrf() {
    return (document.querySelector('meta[name="csrf-token"]') || {}).content || '';
  }

  // Top progress bar on internal nav
  var bar = document.createElement('div');
  bar.id = 'navProgress';
  bar.className = 'nav-progress';
  document.documentElement.appendChild(bar);
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href]');
    if (!a) return;
    var href = a.getAttribute('href') || '';
    if (!href || href.charAt(0) === '#' || href.indexOf('javascript:') === 0) return;
    if (a.target === '_blank' || e.metaKey || e.ctrlKey) return;
    if (href.charAt(0) === '/' || href.indexOf(location.origin) === 0) {
      bar.classList.add('active');
    }
  });

  document.addEventListener('DOMContentLoaded', function () {
    // Starred filter chip
    var starChip = document.getElementById('filterStarred');
    if (starChip) {
      starChip.addEventListener('click', function (e) {
        e.preventDefault();
        var stars = [];
        try { stars = JSON.parse(localStorage.getItem('cl-stars') || '[]'); } catch (err) {}
        document.querySelectorAll('.inbox-row[data-call-id]').forEach(function (row) {
          var id = String(row.getAttribute('data-call-id'));
          var show = stars.indexOf(id) >= 0;
          row.style.display = show ? '' : 'none';
        });
        document.querySelectorAll('.preset-chips a, .quick-filters .chip').forEach(function (c) {
          c.classList.remove('active');
        });
        starChip.classList.add('active');
        if (window.clToast) window.clToast('info', 'Showing starred only (client filter)');
      });
    }

    // On-call timer when presence is on_call
    var timerEl = document.getElementById('onCallTimer');
    var presence = document.getElementById('presenceSelect');
    var timerStart = null;
    var timerIv = null;
    function stopTimer() {
      if (timerIv) clearInterval(timerIv);
      timerIv = null;
      timerStart = null;
      if (timerEl) { timerEl.hidden = true; timerEl.textContent = ''; }
    }
    function startTimer() {
      if (!timerEl) return;
      timerStart = Date.now();
      timerEl.hidden = false;
      function tick() {
        var s = Math.floor((Date.now() - timerStart) / 1000);
        var m = Math.floor(s / 60);
        var sec = s % 60;
        timerEl.textContent = m + ':' + (sec < 10 ? '0' : '') + sec;
      }
      tick();
      if (timerIv) clearInterval(timerIv);
      timerIv = setInterval(tick, 1000);
    }
    if (presence) {
      if (presence.value === 'on_call') startTimer();
      presence.addEventListener('change', function () {
        if (presence.value === 'on_call') startTimer();
        else stopTimer();
      });
    }

    // Clear queue celebration
    var empty = document.querySelector('.empty-state');
    var openRows = document.querySelectorAll('.inbox-row[data-status="Open"], .inbox-row[data-status="In Progress"]');
    if (empty && location.pathname.indexOf('/calls') === 0 && !document.querySelector('.inbox-row')) {
      try {
        if (sessionStorage.getItem('cl-celebrated') !== '1') {
          sessionStorage.setItem('cl-celebrated', '1');
          if (window.clToast) window.clToast('success', 'Queue clear — nice work');
        }
      } catch (e) {}
    }

    // Claim next unassigned
    var claimNext = document.getElementById('btnClaimNext');
    if (claimNext) {
      claimNext.addEventListener('click', function () {
        claimNext.disabled = true;
        fetch('/api/calls/claim-next', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
          body: JSON.stringify({})
        }).then(function (r) { return r.json(); }).then(function (j) {
          if (j.ok && j.call_id) {
            if (window.clToast) window.clToast('success', 'Claimed #' + j.call_id);
            setTimeout(function () { window.location.href = '/calls/' + j.call_id; }, 400);
          } else {
            claimNext.disabled = false;
            if (window.clToast) window.clToast('info', j.message || 'No unassigned calls');
          }
        }).catch(function () { claimNext.disabled = false; });
      });
    }

    // Keyboard A = claim focused, N = claim next
    document.addEventListener('keydown', function (e) {
      var tag = (e.target && e.target.tagName) || '';
      var typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (e.target && e.target.isContentEditable);
      if (typing || e.metaKey || e.ctrlKey) return;
      var k = e.key.toLowerCase();

      if (k === 'a') {
        var focused = document.querySelector('.inbox-row.is-focused, .inbox-row.keyboard-focus, .inbox-row:focus');
        if (!focused) return;
        var id = focused.getAttribute('data-call-id');
        if (!id) return;
        e.preventDefault();
        fetch('/api/calls/' + id + '/quick', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
          body: JSON.stringify({ action: 'claim' })
        }).then(function (r) { return r.json(); }).then(function (j) {
          if (j.ok) {
            if (window.clToast) window.clToast('success', 'Claimed #' + id);
            setTimeout(function () { location.reload(); }, 400);
          }
        });
      }

      if (k === 'n') {
        e.preventDefault();
        var btn = document.getElementById('btnClaimNext');
        if (btn) btn.click();
        else {
          fetch('/api/calls/claim-next', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
            body: JSON.stringify({})
          }).then(function (r) { return r.json(); }).then(function (j) {
            if (j.ok && j.call_id) {
              if (window.clToast) window.clToast('success', 'Claimed #' + j.call_id);
              setTimeout(function () { window.location.href = '/calls/' + j.call_id; }, 400);
            } else if (window.clToast) {
              window.clToast('info', j.message || 'No unassigned calls');
            }
          });
        }
      }
    });
  });
})();
