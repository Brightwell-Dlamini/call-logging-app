/**
 * Lightweight change-feed polling for board and inbox auto-refresh.
 */
(function () {
  var POLL_MS = 20000;
  var lastRevision = null;
  var lastServerTime = null;
  var timer = null;

  function csrf() {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.content : '';
  }

  function shouldWatch() {
    // Board or calls list pages
    if (document.getElementById('boardColumns')) return true;
    if (document.querySelector('.inbox-table, #callsTable, .calls-list, [data-realtime="calls"]')) return true;
    if (location.pathname.indexOf('/board') === 0) return true;
    if (location.pathname === '/calls/' || location.pathname === '/calls') return true;
    return false;
  }

  function showBanner(msg) {
    var existing = document.getElementById('rtRefreshBanner');
    if (existing) {
      existing.querySelector('span').textContent = msg;
      existing.hidden = false;
      return;
    }
    var bar = document.createElement('div');
    bar.id = 'rtRefreshBanner';
    bar.className = 'rt-refresh-banner';
    bar.innerHTML = '<span></span> <button type="button" class="btn btn-sm btn-primary">Refresh</button>';
    bar.querySelector('span').textContent = msg;
    bar.querySelector('button').addEventListener('click', function () {
      location.reload();
    });
    var main = document.getElementById('mainContent') || document.body;
    main.insertBefore(bar, main.firstChild);
  }

  function poll() {
    if (document.hidden) return;
    var url = '/api/feed/changes';
    if (lastServerTime) url += '?since=' + encodeURIComponent(lastServerTime);
    fetch(url, {
      headers: { 'Accept': 'application/json', 'X-CSRFToken': csrf() },
      credentials: 'same-origin'
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) return;
        if (j.server_time) lastServerTime = j.server_time;
        if (lastRevision === null) {
          lastRevision = j.revision;
          return;
        }
        if (j.revision && j.revision !== lastRevision && j.has_changes) {
          lastRevision = j.revision;
          var parts = [];
          if (j.updated_calls) parts.push(j.updated_calls + ' updated');
          if (j.new_activities) parts.push(j.new_activities + ' activities');
          showBanner('Board/inbox changed (' + (parts.join(', ') || 'updates') + ').');
          if (window.clRefreshNotifications) window.clRefreshNotifications();
        } else if (j.revision) {
          lastRevision = j.revision;
        }
      })
      .catch(function () {});
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (!shouldWatch()) return;
    // Seed
    poll();
    timer = setInterval(poll, POLL_MS);
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) poll();
    });
  });
})();
