/** Batch 3: density, workload board, viewing presence */
(function () {
  function qs(s, el) { return (el || document).querySelector(s); }
  function qsa(s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); }

  function applyDensity(mode) {
    document.documentElement.classList.toggle('density-compact', mode === 'compact');
    try { localStorage.setItem('cl-density', mode); } catch (e) {}
    qsa('[data-density]').forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-density') === mode);
    });
  }
  function currentDensity() {
    try { return localStorage.getItem('cl-density') || 'comfortable'; } catch (e) { return 'comfortable'; }
  }

  function renderWorkload() {
    var wrap = qs('#workloadWrap');
    var dataEl = qs('#boardData');
    if (!wrap || !dataEl) return;
    var data = [];
    try { data = JSON.parse(dataEl.textContent || '[]'); } catch (e) { data = []; }
    var groups = {};
    data.forEach(function (c) {
      var key = c.assignee || 'Unassigned';
      if (!groups[key]) groups[key] = [];
      groups[key].push(c);
    });
    var names = Object.keys(groups).sort(function (a, b) {
      if (a === 'Unassigned') return 1;
      if (b === 'Unassigned') return -1;
      return groups[b].length - groups[a].length;
    });
    var maxLoad = Math.max(1, Math.max.apply(null, names.map(function (n) { return groups[n].length; }).concat([1])));
    wrap.innerHTML = '';
    names.forEach(function (name) {
      var items = groups[name];
      var openCount = items.filter(function (c) {
        return c.status !== 'Resolved' && c.status !== 'Closed';
      }).length;
      var col = document.createElement('div');
      col.className = 'wl-col';
      var pct = Math.round((items.length / maxLoad) * 100);
      var heavy = openCount >= 3;
      col.innerHTML =
        '<div class="wl-col-header">' +
          '<span class="wl-avatar"></span>' +
          '<div style="flex:1;min-width:0">' +
            '<div class="wl-name"></div>' +
            '<div class="wl-meta"></div>' +
            '<div class="wl-load' + (heavy ? ' heavy' : '') + '"><span style="width:' + pct + '%"></span></div>' +
          '</div>' +
        '</div>' +
        '<div class="wl-body"></div>';
      col.querySelector('.wl-avatar').textContent = (name === 'Unassigned' ? '?' : name.charAt(0)).toUpperCase();
      col.querySelector('.wl-name').textContent = name;
      col.querySelector('.wl-meta').textContent = items.length + ' call' + (items.length !== 1 ? 's' : '') + ' · ' + openCount + ' open';
      var body = col.querySelector('.wl-body');
      items.forEach(function (c) {
        var card = document.createElement('div');
        card.className = 'board-card' + (c.priority === 'Critical' && c.status !== 'Resolved' && c.status !== 'Closed' ? ' is-critical' : '');
        card.setAttribute('data-drawer-open', c.partial);
        card.innerHTML =
          '<div class="bc-top"><span class="bc-id">#' + c.id + '</span>' +
          '<span class="badge status-' + (c.status || '').toLowerCase().replace(/\s+/g, '-') + '">' + c.status + '</span></div>' +
          '<div class="bc-name"></div>' +
          '<div class="bc-foot"><span class="badge badge-' + (c.priority || 'medium').toLowerCase() + '">' + c.priority + '</span></div>';
        card.querySelector('.bc-name').textContent = c.name;
        body.appendChild(card);
      });
      wrap.appendChild(col);
    });
  }

  function setView(mode) {
    var board = qs('#boardWrap');
    var list = qs('#inboxListWrap');
    var work = qs('#workloadWrap');
    qsa('[data-view]').forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-view') === mode);
    });
    if (board) board.classList.toggle('visible', mode === 'board');
    if (work) work.classList.toggle('visible', mode === 'workload');
    if (list) list.classList.toggle('hidden', mode === 'board' || mode === 'workload');
    if (mode === 'board' && board) {
      var dataEl = qs('#boardData');
      if (dataEl) {
        try {
          var data = JSON.parse(dataEl.textContent || '[]');
          var STATUSES = ['Open', 'In Progress', 'Pending', 'Resolved', 'Closed'];
          board.innerHTML = '';
          STATUSES.forEach(function (st) {
            var items = data.filter(function (c) { return c.status === st; });
            var col = document.createElement('div');
            col.className = 'board-col';
            col.innerHTML = '<div class="board-col-header"><span></span><span class="count"></span></div><div class="board-col-body"></div>';
            col.querySelector('.board-col-header span').textContent = st;
            col.querySelector('.count').textContent = items.length;
            var body = col.querySelector('.board-col-body');
            items.forEach(function (c) {
              var card = document.createElement('div');
              card.className = 'board-card' + (c.priority === 'Critical' && st !== 'Resolved' && st !== 'Closed' ? ' is-critical' : '');
              card.setAttribute('data-drawer-open', c.partial);
              card.innerHTML = '<div class="bc-top"><span class="bc-id">#' + c.id + '</span><span class="badge badge-' + (c.priority||'').toLowerCase() + '">' + c.priority + '</span></div><div class="bc-name"></div>';
              card.querySelector('.bc-name').textContent = c.name;
              body.appendChild(card);
            });
            board.appendChild(col);
          });
        } catch (e) {}
      }
    }
    if (mode === 'workload') renderWorkload();
    try { localStorage.setItem('cl-view', mode); } catch (e) {}
  }

  var channel = null;
  try { channel = new BroadcastChannel('calllog-presence'); } catch (e) {}
  var myId = Math.random().toString(36).slice(2, 8);
  var viewingCall = null;
  var othersOnCall = {};

  function broadcastViewing(callId) {
    viewingCall = callId;
    if (channel && callId) {
      channel.postMessage({ type: 'viewing', callId: String(callId), agent: myId, name: document.body.getAttribute('data-agent-name') || 'Agent' });
    }
  }
  function broadcastLeft() {
    if (channel && viewingCall) {
      channel.postMessage({ type: 'left', callId: String(viewingCall), agent: myId, name: document.body.getAttribute('data-agent-name') || 'Agent' });
    }
    viewingCall = null;
  }
  function showPresence(callId) {
    var host = qs('#drawerContent');
    if (!host) return;
    var existing = qs('.presence-banner', host);
    var names = othersOnCall[callId] || [];
    if (!names.length) {
      if (existing) existing.remove();
      return;
    }
    if (!existing) {
      existing = document.createElement('div');
      existing.className = 'presence-banner';
      existing.innerHTML = '<span class="pulse"></span><span class="presence-text"></span>';
      var body = qs('.drawer-body', host) || host;
      body.insertBefore(existing, body.firstChild);
    }
    existing.querySelector('.presence-text').textContent =
      names.join(', ') + (names.length === 1 ? ' is' : ' are') + ' also viewing this call';
  }

  if (channel) {
    channel.onmessage = function (ev) {
      var msg = ev.data || {};
      if (!msg.callId || msg.agent === myId) return;
      if (msg.type === 'viewing') {
        if (!othersOnCall[msg.callId]) othersOnCall[msg.callId] = [];
        if (othersOnCall[msg.callId].indexOf(msg.name) === -1) {
          othersOnCall[msg.callId].push(msg.name);
        }
        if (viewingCall && String(viewingCall) === String(msg.callId)) showPresence(msg.callId);
        if (viewingCall && String(viewingCall) === String(msg.callId) && channel) {
          channel.postMessage({ type: 'viewing', callId: String(viewingCall), agent: myId, name: document.body.getAttribute('data-agent-name') || 'Agent' });
        }
      }
      if (msg.type === 'left') {
        if (othersOnCall[msg.callId]) {
          othersOnCall[msg.callId] = othersOnCall[msg.callId].filter(function (n) { return n !== msg.name; });
          showPresence(msg.callId);
        }
      }
    };
  }

  document.addEventListener('DOMContentLoaded', function () {
    applyDensity(currentDensity());
    qsa('[data-density]').forEach(function (b) {
      b.addEventListener('click', function () { applyDensity(b.getAttribute('data-density')); });
    });

    qsa('[data-view]').forEach(function (b) {
      b.addEventListener('click', function (e) {
        e.stopImmediatePropagation();
        setView(b.getAttribute('data-view'));
      }, true);
    });
    try {
      var saved = localStorage.getItem('cl-view');
      if (saved === 'board' || saved === 'workload') setView(saved);
    } catch (e) {}

    var drawer = qs('#drawerOverlay');
    if (drawer) {
      var obs = new MutationObserver(function () {
        if (drawer.hidden) {
          broadcastLeft();
          return;
        }
        var title = qs('.drawer-title', drawer);
        if (title) {
          var m = title.textContent.match(/#(\d+)/);
          if (m) {
            broadcastViewing(m[1]);
            showPresence(m[1]);
          }
        }
      });
      obs.observe(drawer, { attributes: true, childList: true, subtree: true });
    }
    window.addEventListener('beforeunload', broadcastLeft);

    document.addEventListener('keydown', function (e) {
      var tag = (e.target && e.target.tagName) || '';
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if (e.key === 'd' || e.key === 'D') {
        applyDensity(currentDensity() === 'compact' ? 'comfortable' : 'compact');
      }
      if (e.key === 'w' || e.key === 'W') {
        if (qs('#workloadWrap')) setView('workload');
      }
    });
  });
})();
