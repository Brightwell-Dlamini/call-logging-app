/** Batch 4: filter pills, j/k nav, context menu, skeleton, coach, copy */
(function () {
  function qs(s, el) { return (el || document).querySelector(s); }
  function qsa(s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); }

  function buildFilterPills() {
    var host = qs('#filterPills');
    if (!host) return;
    var params = new URLSearchParams(window.location.search);
    var labels = {
      status: 'Status', priority: 'Priority', department: 'Dept',
      search: 'Search', assigned_to: 'Assignee', sort: 'Sort'
    };
    host.innerHTML = '';
    var count = 0;
    Object.keys(labels).forEach(function (key) {
      var val = params.get(key);
      if (!val) return;
      count++;
      var pill = document.createElement('span');
      pill.className = 'filter-pill';
      var display = key === 'assigned_to' ? 'Me' : val;
      pill.innerHTML = '<span></span><button type="button" aria-label="Remove">&times;</button>';
      pill.querySelector('span').textContent = labels[key] + ': ' + display;
      pill.querySelector('button').addEventListener('click', function () {
        params.delete(key);
        var q = params.toString();
        window.location.href = window.location.pathname + (q ? '?' + q : '');
      });
      host.appendChild(pill);
    });
    if (count > 0) {
      var clear = document.createElement('button');
      clear.type = 'button';
      clear.className = 'clear-all';
      clear.textContent = 'Clear all';
      clear.addEventListener('click', function () {
        window.location.href = window.location.pathname;
      });
      host.appendChild(clear);
    }
  }

  var focusIdx = -1;
  function rows() {
    return qsa('.inbox-list-wrap:not(.hidden) .inbox-row, #inboxListWrap:not(.hidden) .inbox-row');
  }
  function setFocus(i) {
    var r = rows();
    r.forEach(function (el) { el.classList.remove('kb-focus'); });
    if (i < 0 || i >= r.length) { focusIdx = -1; return; }
    focusIdx = i;
    r[i].classList.add('kb-focus');
    r[i].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  var menu = null;
  function ensureMenu() {
    if (menu) return menu;
    menu = document.createElement('div');
    menu.className = 'ctx-menu';
    menu.innerHTML =
      '<button type="button" data-act="preview"><i class="fas fa-panel-right"></i> Preview</button>' +
      '<button type="button" data-act="open"><i class="fas fa-up-right-from-square"></i> Open full</button>' +
      '<button type="button" data-act="copy-phone"><i class="fas fa-copy"></i> Copy phone</button>' +
      '<div class="ctx-sep"></div>' +
      '<button type="button" data-act="copy-id"><i class="fas fa-hashtag"></i> Copy call ID</button>';
    document.body.appendChild(menu);
    menu.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-act]');
      if (!btn || !menu._row) return;
      var act = btn.getAttribute('data-act');
      var row = menu._row;
      var id = row.getAttribute('data-call-id');
      var phone = (row.querySelector('.caller-phone') || {}).textContent || '';
      hideMenu();
      if (act === 'preview') row.click();
      else if (act === 'open' && id) window.location.href = '/calls/' + id;
      else if (act === 'copy-phone') copyText(phone.trim());
      else if (act === 'copy-id') copyText('#' + id);
    });
    return menu;
  }
  function showMenu(x, y, row) {
    var m = ensureMenu();
    m._row = row;
    m.classList.add('open');
    m.style.left = Math.min(x, window.innerWidth - 200) + 'px';
    m.style.top = Math.min(y, window.innerHeight - 180) + 'px';
  }
  function hideMenu() {
    if (menu) menu.classList.remove('open');
  }

  function copyText(text) {
    if (!text) return;
    function ok() { if (window.clToast) window.clToast('success', 'Copied: ' + text); }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(ok).catch(function () { fallbackCopy(text); ok(); });
    } else { fallbackCopy(text); ok(); }
  }
  function fallbackCopy(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch (e) {}
    ta.remove();
  }
  window.clCopy = copyText;

  function wireDrawerSkeleton() {
    var drawerContent = qs('#drawerContent');
    var overlay = qs('#drawerOverlay');
    if (!overlay || !drawerContent) return;
    var obs = new MutationObserver(function () {
      if (!overlay.hidden && drawerContent.textContent.indexOf('Loading') !== -1) {
        drawerContent.innerHTML =
          '<div class="drawer-skeleton">' +
          '<div class="skeleton skel-block"></div>' +
          '<div class="skeleton skel-line w60"></div>' +
          '<div class="skeleton skel-line w80"></div>' +
          '<div class="skeleton skel-line w40"></div>' +
          '<div class="skeleton skel-line w80"></div>' +
          '</div>';
      }
    });
    obs.observe(drawerContent, { childList: true, characterData: true, subtree: true });
  }

  function showCoach() {
    try { if (localStorage.getItem('cl-coach-v1')) return; } catch (e) { return; }
    if (!document.body.classList.contains('has-sidebar')) return;
    var tip = document.createElement('div');
    tip.className = 'coach-tip';
    tip.id = 'coachTip';
    tip.innerHTML =
      '<div class="coach-body">' +
      '<div class="coach-title">Power-user desk</div>' +
      '<div class="coach-text">Press <kbd>?</kbd> for shortcuts · <kbd>J</kbd>/<kbd>K</kbd> move inbox · <kbd>B</kbd> board · <kbd>W</kbd> workload · right-click a row for quick actions.</div>' +
      '<div class="coach-actions">' +
      '<button type="button" class="btn btn-primary btn-sm" id="coachDismiss">Got it</button>' +
      '</div></div>';
    document.body.appendChild(tip);
    qs('#coachDismiss', tip).addEventListener('click', function () {
      try { localStorage.setItem('cl-coach-v1', '1'); } catch (e) {}
      tip.hidden = true;
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    buildFilterPills();
    wireDrawerSkeleton();
    setTimeout(showCoach, 800);

    document.body.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-copy]');
      if (btn) {
        e.preventDefault();
        copyText(btn.getAttribute('data-copy'));
        btn.classList.add('copied');
        setTimeout(function () { btn.classList.remove('copied'); }, 1200);
      }
    });

    document.body.addEventListener('contextmenu', function (e) {
      var row = e.target.closest('.inbox-row');
      if (!row) return;
      e.preventDefault();
      showMenu(e.clientX, e.clientY, row);
    });
    document.addEventListener('click', hideMenu);

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') hideMenu();
      var tag = (e.target && e.target.tagName) || '';
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (e.target && e.target.isContentEditable)) return;
      var r = rows();
      if (!r.length) return;
      if (e.key === 'j' || e.key === 'J') {
        e.preventDefault();
        if (focusIdx < 0) setFocus(0);
        else setFocus(Math.min(focusIdx + 1, r.length - 1));
      } else if (e.key === 'k' || e.key === 'K') {
        e.preventDefault();
        setFocus(Math.max(focusIdx - 1, 0));
      } else if (e.key === 'Enter' && focusIdx >= 0 && r[focusIdx]) {
        e.preventDefault();
        r[focusIdx].click();
      } else if ((e.key === 'o' || e.key === 'O') && focusIdx >= 0 && r[focusIdx]) {
        var id = r[focusIdx].getAttribute('data-call-id');
        if (id) window.location.href = '/calls/' + id;
      }
    });
  });
})();
