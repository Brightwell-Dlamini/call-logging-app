/** Wave 2: notifications, bulk assign, stars, drawer quick actions, filter presets */
(function () {
  function csrf() {
    return (document.querySelector('meta[name="csrf-token"]') || {}).content || '';
  }

  // Notification bell
  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('notifBell');
    var panel = document.getElementById('notifPanel');
    var list = document.getElementById('notifList');
    var badge = document.getElementById('notifBadge');
    if (!btn || !panel) return;

    function loadNotifs() {
      fetch('/api/notifications')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var items = data.items || [];
          if (badge) {
            badge.textContent = items.length > 9 ? '9+' : String(items.length);
            badge.hidden = items.length === 0;
          }
          if (!list) return;
          if (!items.length) {
            list.innerHTML = '<div class="notif-empty">No recent activity</div>';
            return;
          }
          list.innerHTML = items.map(function (n) {
            return '<a class="notif-item" href="' + n.url + '">' +
              '<div class="notif-title">' + n.title + '</div>' +
              '<div class="notif-body">' + n.body + '</div></a>';
          }).join('');
        })
        .catch(function () {});
    }

    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      panel.hidden = !panel.hidden;
      if (!panel.hidden) loadNotifs();
    });
    document.addEventListener('click', function () { panel.hidden = true; });
    panel.addEventListener('click', function (e) { e.stopPropagation(); });
    loadNotifs();
  });

  // Bulk assign
  document.addEventListener('DOMContentLoaded', function () {
    var sel = document.getElementById('bulkAssignSelect');
    if (!sel) return;
    sel.addEventListener('change', function () {
      var agentId = sel.value;
      if (!agentId) return;
      var ids = Array.prototype.map.call(
        document.querySelectorAll('.row-select:checked'),
        function (c) { return parseInt(c.value, 10); }
      );
      if (!ids.length) {
        if (window.clToast) window.clToast('warning', 'Select calls first');
        sel.value = '';
        return;
      }
      fetch('/calls/bulk', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrf(),
          'Accept': 'application/json'
        },
        body: JSON.stringify({ ids: ids, action: 'assign', assigned_to: parseInt(agentId, 10) })
      }).then(function (r) { return r.json(); }).then(function (j) {
        if (j.ok) {
          if (window.clToast) window.clToast('success', j.message || 'Assigned');
          setTimeout(function () { location.reload(); }, 400);
        } else if (window.clToast) {
          window.clToast('error', j.error || 'Failed');
        }
        sel.value = '';
      });
    });
  });

  // Drawer quick actions + stars (delegated)
  document.body.addEventListener('click', function (e) {
    var q = e.target.closest('[data-quick]');
    if (q) {
      e.preventDefault();
      var action = q.getAttribute('data-quick');
      var id = q.getAttribute('data-call-id');
      fetch('/api/calls/' + id + '/quick', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrf()
        },
        body: JSON.stringify({ action: action })
      }).then(function (r) { return r.json(); }).then(function (j) {
        if (j.ok) {
          if (window.clToast) window.clToast('success', action.charAt(0).toUpperCase() + action.slice(1) + 'd');
          setTimeout(function () { location.reload(); }, 450);
        } else if (window.clToast) {
          window.clToast('error', j.error || 'Failed');
        }
      });
    }

    var star = e.target.closest('[data-star-id]');
    if (star) {
      e.preventDefault();
      e.stopPropagation();
      var sid = star.getAttribute('data-star-id');
      var stars = [];
      try { stars = JSON.parse(localStorage.getItem('cl-stars') || '[]'); } catch (err) {}
      var i = stars.indexOf(sid);
      if (i >= 0) stars.splice(i, 1);
      else stars.push(sid);
      try { localStorage.setItem('cl-stars', JSON.stringify(stars)); } catch (err) {}
      var icon = star.querySelector('i');
      if (icon) {
        icon.className = stars.indexOf(sid) >= 0 ? 'fas fa-star' : 'far fa-star';
      }
      if (window.clToast) window.clToast('info', stars.indexOf(sid) >= 0 ? 'Starred' : 'Unstarred');
    }
  });

  // Reflect stars on list rows
  document.addEventListener('DOMContentLoaded', function () {
    var stars = [];
    try { stars = JSON.parse(localStorage.getItem('cl-stars') || '[]'); } catch (e) {}
    document.querySelectorAll('[data-call-id]').forEach(function (row) {
      if (stars.indexOf(row.getAttribute('data-call-id')) >= 0) {
        row.classList.add('is-starred');
      }
    });
  });
})();
