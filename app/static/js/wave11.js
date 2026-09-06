/** Wave 11: O reopen, saved views, note templates, SLA countdown, bulk assign */
(function () {
  function csrf() {
    return (document.querySelector('meta[name="csrf-token"]') || {}).content || '';
  }

  var VIEWS_KEY = 'cl-saved-views';
  var TEMPLATES = [
    'Customer confirmed details; proceeding.',
    'Left voicemail; awaiting callback.',
    'Escalated to supervisor for approval.',
    'Sent follow-up email with reference number.',
    'Resolved with customer on the line.',
    'Pending third-party / external vendor.',
  ];

  document.addEventListener('DOMContentLoaded', function () {
    // Saved views
    var host = document.getElementById('savedViews');
    var saveBtn = document.getElementById('btnSaveView');
    function loadViews() {
      var views = [];
      try { views = JSON.parse(localStorage.getItem(VIEWS_KEY) || '[]'); } catch (e) {}
      if (!host) return;
      host.querySelectorAll('.sv-chip, .sv-clear').forEach(function (n) { n.remove(); });
      views.forEach(function (v, i) {
        var a = document.createElement('a');
        a.href = v.url;
        a.className = 'sv-chip';
        a.textContent = v.name;
        a.title = v.url;
        var x = document.createElement('button');
        x.type = 'button';
        x.className = 'sv-x';
        x.innerHTML = '&times;';
        x.title = 'Remove';
        x.addEventListener('click', function (e) {
          e.preventDefault();
          e.stopPropagation();
          views.splice(i, 1);
          try { localStorage.setItem(VIEWS_KEY, JSON.stringify(views)); } catch (err) {}
          loadViews();
        });
        a.appendChild(x);
        host.appendChild(a);
      });
    }
    if (host) loadViews();
    if (saveBtn) {
      saveBtn.addEventListener('click', function () {
        var name = window.prompt('Name this view:', 'My filter');
        if (!name || !name.trim()) return;
        var views = [];
        try { views = JSON.parse(localStorage.getItem(VIEWS_KEY) || '[]'); } catch (e) {}
        views.push({ name: name.trim().slice(0, 40), url: location.href });
        views = views.slice(-12);
        try { localStorage.setItem(VIEWS_KEY, JSON.stringify(views)); } catch (e) {}
        loadViews();
        if (window.clToast) window.clToast('success', 'View saved');
      });
    }

    // Note templates
    var noteTa = document.querySelector('textarea[name="note"]');
    var tplHost = document.getElementById('noteTemplates');
    if (noteTa && tplHost) {
      TEMPLATES.forEach(function (t) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'note-tpl';
        b.textContent = t.length > 36 ? t.slice(0, 34) + '…' : t;
        b.title = t;
        b.addEventListener('click', function () {
          noteTa.value = (noteTa.value ? noteTa.value + '\n' : '') + t;
          noteTa.focus();
          noteTa.dispatchEvent(new Event('input', { bubbles: true }));
        });
        tplHost.appendChild(b);
      });
    }

    // Live SLA countdown on detail
    var slaEl = document.getElementById('slaCountdown');
    if (slaEl) {
      var logged = slaEl.getAttribute('data-logged');
      var status = slaEl.getAttribute('data-status') || '';
      var priority = slaEl.getAttribute('data-priority') || 'Medium';
      if (logged && ['Resolved', 'Closed'].indexOf(status) === -1) {
        var limits = { Critical: 2, High: 8, Medium: 24, Low: 48 };
        var limitH = limits[priority] || 24;
        function tick() {
          var start = new Date(logged).getTime();
          if (isNaN(start)) return;
          var elapsedH = (Date.now() - start) / 3600000;
          var left = limitH - elapsedH;
          var abs = Math.abs(left);
          var h = Math.floor(abs);
          var m = Math.floor((abs - h) * 60);
          if (left >= 0) {
            slaEl.textContent = h + 'h ' + m + 'm remaining';
            slaEl.className = 'sla-countdown ' + (left < limitH * 0.25 ? 'warn' : 'ok');
          } else {
            slaEl.textContent = h + 'h ' + m + 'm over SLA';
            slaEl.className = 'sla-countdown breach';
          }
        }
        tick();
        setInterval(tick, 30000);
      } else if (slaEl) {
        slaEl.textContent = 'Closed';
        slaEl.className = 'sla-countdown ok';
      }
    }

    // Bulk assign to agent
    var bulkAssign = document.getElementById('bulkAssignSelect');
    if (bulkAssign) {
      fetch('/api/users')
        .then(function (r) { return r.json(); })
        .then(function (users) {
          if (!Array.isArray(users)) return;
          users.forEach(function (u) {
            if (['Agent', 'Manager', 'Admin'].indexOf(u.role) === -1) return;
            var o = document.createElement('option');
            o.value = u.id;
            o.textContent = u.name;
            bulkAssign.appendChild(o);
          });
        })
        .catch(function () {});

      bulkAssign.addEventListener('change', function () {
        var aid = bulkAssign.value;
        if (!aid) return;
        var ids = Array.prototype.map.call(
          document.querySelectorAll('.row-select:checked'),
          function (c) { return c.value; }
        );
        if (!ids.length) {
          bulkAssign.value = '';
          if (window.clToast) window.clToast('info', 'Select calls first');
          return;
        }
        fetch('/calls/bulk', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
          body: JSON.stringify({ ids: ids, action: 'assign', assigned_to: parseInt(aid, 10) })
        }).then(function (r) { return r.json(); }).then(function (j) {
          if (j.ok) {
            if (window.clToast) window.clToast('success', j.message || 'Assigned');
            setTimeout(function () { location.reload(); }, 500);
          } else if (window.clToast) {
            window.clToast('error', j.error || 'Failed');
          }
          bulkAssign.value = '';
        });
      });
    }

    // Keyboard O = reopen focused
    document.addEventListener('keydown', function (e) {
      var tag = (e.target && e.target.tagName) || '';
      var typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (e.target && e.target.isContentEditable);
      if (typing || e.metaKey || e.ctrlKey) return;
      if (e.key !== 'o' && e.key !== 'O') return;
      var focused = document.querySelector('.inbox-row.is-focused, .inbox-row.keyboard-focus, .inbox-row:focus');
      if (!focused) return;
      var id = focused.getAttribute('data-call-id');
      if (!id) return;
      e.preventDefault();
      fetch('/api/calls/' + id + '/quick', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
        body: JSON.stringify({ action: 'reopen' })
      }).then(function (r) { return r.json(); }).then(function (j) {
        if (j.ok) {
          if (window.clToast) window.clToast('info', 'Reopened #' + id);
          setTimeout(function () { location.reload(); }, 400);
        }
      });
    });
  });
})();
