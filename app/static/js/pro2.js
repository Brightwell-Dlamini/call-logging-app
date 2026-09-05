/** Pro batch 2: board view, saved views, critical sound */
(function () {
  function qs(s, el) { return (el || document).querySelector(s); }
  function qsa(s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); }

  function soundEnabled() {
    try { return localStorage.getItem('cl-sound') !== 'off'; } catch (e) { return true; }
  }
  function setSound(v) {
    try { localStorage.setItem('cl-sound', v); } catch (e) {}
    qsa('[data-sound-set]').forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-sound-set') === v);
    });
  }
  function playCriticalChime() {
    if (!soundEnabled()) return;
    try {
      var ctx = new (window.AudioContext || window.webkitAudioContext)();
      var o = ctx.createOscillator();
      var g = ctx.createGain();
      o.type = 'sine';
      o.frequency.value = 880;
      g.gain.value = 0.04;
      o.connect(g); g.connect(ctx.destination);
      o.start();
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
      o.stop(ctx.currentTime + 0.4);
      setTimeout(function () { ctx.close(); }, 500);
    } catch (e) {}
  }

  var SV_KEY = 'cl-saved-views';
  function loadViews() {
    try { return JSON.parse(localStorage.getItem(SV_KEY) || '[]'); } catch (e) { return []; }
  }
  function saveViews(arr) {
    try { localStorage.setItem(SV_KEY, JSON.stringify(arr.slice(0, 8))); } catch (e) {}
  }
  function currentQuery() { return window.location.search || ''; }
  function renderSavedViews() {
    var host = qs('#savedViews');
    if (!host) return;
    var views = loadViews();
    host.innerHTML = '';
    var sp = document.createElement('span');
    sp.className = 'sv-label';
    sp.textContent = 'Views';
    host.appendChild(sp);
    views.forEach(function (v, i) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'sv-chip' + (v.q === currentQuery() ? ' active' : '');
      b.innerHTML = '<span></span><i class="fas fa-xmark sv-x"></i>';
      b.querySelector('span').textContent = v.name;
      b.addEventListener('click', function (e) {
        if (e.target.classList.contains('sv-x')) {
          e.stopPropagation();
          var next = loadViews();
          next.splice(i, 1);
          saveViews(next);
          renderSavedViews();
          return;
        }
        window.location.href = window.location.pathname + (v.q || '');
      });
      host.appendChild(b);
    });
  }

  var STATUSES = ['Open', 'In Progress', 'Pending', 'Resolved', 'Closed'];
  function renderBoard() {
    var wrap = qs('#boardWrap');
    var dataEl = qs('#boardData');
    if (!wrap || !dataEl) return;
    var data = [];
    try { data = JSON.parse(dataEl.textContent || '[]'); } catch (e) { data = []; }
    wrap.innerHTML = '';
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
        var priClass = 'badge-' + (c.priority || 'medium').toLowerCase();
        card.innerHTML =
          '<div class="bc-top"><span class="bc-id">#' + c.id + '</span><span class="badge ' + priClass + '">' + c.priority + '</span></div>' +
          '<div class="bc-name"></div><div class="bc-reason"></div><div class="bc-foot"></div>';
        card.querySelector('.bc-name').textContent = c.name;
        card.querySelector('.bc-reason').textContent = c.reason || '';
        var foot = card.querySelector('.bc-foot');
        if (c.dept) {
          var d = document.createElement('span');
          d.className = 'badge status-pending';
          d.textContent = c.dept;
          foot.appendChild(d);
        }
        if (c.assignee) {
          var a = document.createElement('span');
          a.style.fontSize = '0.7rem';
          a.style.color = 'var(--cl-text-muted)';
          a.textContent = c.assignee.split(' ')[0];
          foot.appendChild(a);
        }
        body.appendChild(card);
      });
      if (!items.length) {
        var empty = document.createElement('div');
        empty.style.cssText = 'font-size:0.75rem;color:var(--cl-text-muted);padding:8px;text-align:center;';
        empty.textContent = 'Empty';
        body.appendChild(empty);
      }
      wrap.appendChild(col);
    });
  }

  function setView(mode) {
    var board = qs('#boardWrap');
    var list = qs('#inboxListWrap');
    qsa('[data-view]').forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-view') === mode);
    });
    if (mode === 'board') {
      if (board) { board.classList.add('visible'); renderBoard(); }
      if (list) list.classList.add('hidden');
      try { localStorage.setItem('cl-view', 'board'); } catch (e) {}
    } else {
      if (board) board.classList.remove('visible');
      if (list) list.classList.remove('hidden');
      try { localStorage.setItem('cl-view', 'list'); } catch (e) {}
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    setSound(soundEnabled() ? 'on' : 'off');
    qsa('[data-sound-set]').forEach(function (b) {
      b.addEventListener('click', function () {
        setSound(b.getAttribute('data-sound-set'));
        if (b.getAttribute('data-sound-set') === 'on') playCriticalChime();
      });
    });
    if (document.querySelector('.crit-banner') || document.querySelector('.urgency-dot.critical')) {
      try {
        if (!sessionStorage.getItem('cl-chimed') && soundEnabled()) {
          sessionStorage.setItem('cl-chimed', '1');
          setTimeout(playCriticalChime, 600);
        }
      } catch (e) {}
    }

    renderSavedViews();
    var saveBtn = qs('#btnSaveView');
    if (saveBtn) {
      saveBtn.addEventListener('click', function () {
        var name = prompt('Name this view', 'My filter');
        if (!name) return;
        var views = loadViews();
        views.unshift({ name: name.trim().slice(0, 24), q: currentQuery() });
        saveViews(views);
        renderSavedViews();
        if (window.clToast) window.clToast('success', 'View saved');
      });
    }

    qsa('[data-view]').forEach(function (b) {
      b.addEventListener('click', function () { setView(b.getAttribute('data-view')); });
    });
    try {
      if (localStorage.getItem('cl-view') === 'board' && qs('#boardWrap')) setView('board');
    } catch (e) {}

    document.addEventListener('keydown', function (e) {
      var tag = (e.target && e.target.tagName) || '';
      var typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (e.target && e.target.isContentEditable);
      if (typing) return;
      if (e.key === 'b' || e.key === 'B') {
        if (!qs('#boardWrap')) return;
        var board = qs('#boardWrap');
        setView(board && board.classList.contains('visible') ? 'list' : 'board');
      }
    });
  });
})();
