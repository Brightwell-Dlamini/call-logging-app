/**
 * CallLog Pro – command palette, theme, drawer, toasts
 */
(function () {
  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  function applyTheme(mode) {
    var root = document.documentElement;
    root.setAttribute('data-theme', mode);
    try { localStorage.setItem('cl-theme', mode); } catch (e) {}
    var dark = mode === 'dark' || (mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    root.classList.toggle('theme-dark', dark);
    document.querySelectorAll('[data-theme-set]').forEach(function (btn) {
      btn.classList.toggle('active', btn.getAttribute('data-theme-set') === mode);
    });
    var icon = document.querySelector('[data-theme-cycle] i');
    if (icon) icon.className = dark ? 'fas fa-sun' : 'fas fa-moon';
  }
  function currentTheme() {
    try { return localStorage.getItem('cl-theme') || 'system'; } catch (e) { return 'system'; }
  }

  var COMMANDS = [];
  function buildCommands() {
    COMMANDS = [
      { label: 'Dashboard', href: '/', icon: 'fa-border-all', keywords: 'home' },
      { label: 'Calls', href: '/calls/', icon: 'fa-phone', keywords: 'inbox list' },
      { label: 'Log call', href: '/calls/new', icon: 'fa-plus', keywords: 'create new' },
      { label: 'Reports', href: '/reports/', icon: 'fa-chart-simple', keywords: 'analytics' },
      { label: 'Settings', href: '/settings', icon: 'fa-gear', keywords: 'profile theme' },
      { label: 'Admin overview', href: '/admin/', icon: 'fa-sliders', keywords: 'admin' },
      { label: 'Users', href: '/admin/users', icon: 'fa-users', keywords: 'admin' },
      { label: 'Departments', href: '/admin/departments', icon: 'fa-building', keywords: 'admin' },
      { label: 'Audit log', href: '/admin/activities', icon: 'fa-clock-rotate-left', keywords: 'admin' },
      { label: 'Toggle theme', action: 'theme', icon: 'fa-moon', keywords: 'dark light' }
    ];
  }

  function openCmd() {
    var ov = document.getElementById('cmdOverlay');
    if (!ov) return;
    ov.hidden = false;
    var input = document.getElementById('cmdInput');
    input.value = '';
    renderCmd('');
    setTimeout(function () { input.focus(); }, 10);
  }
  function closeCmd() {
    var ov = document.getElementById('cmdOverlay');
    if (ov) ov.hidden = true;
  }
  function renderCmd(q) {
    var list = document.getElementById('cmdList');
    if (!list) return;
    var qq = (q || '').toLowerCase().trim();
    var items = COMMANDS.filter(function (c) {
      if (!qq) return true;
      return (c.label + ' ' + (c.keywords || '')).toLowerCase().indexOf(qq) !== -1;
    });
    if (!items.length) {
      list.innerHTML = '<li class="cmd-empty">No matches</li>';
      return;
    }
    list.innerHTML = items.map(function (c, i) {
      return '<li><button type="button" class="' + (i === 0 ? 'active' : '') + '" data-idx="' + i + '">' +
        '<i class="fas ' + c.icon + '"></i><span>' + c.label + '</span></button></li>';
    }).join('');
    list.querySelectorAll('button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        runCmd(items[parseInt(btn.getAttribute('data-idx'), 10)]);
      });
    });
  }
  function runCmd(c) {
    closeCmd();
    if (!c) return;
    if (c.action === 'theme') {
      var modes = ['light', 'dark', 'system'];
      applyTheme(modes[(modes.indexOf(currentTheme()) + 1) % modes.length]);
      return;
    }
    if (c.href) window.location.href = c.href;
  }

  function openDrawer(url) {
    var ov = document.getElementById('drawerOverlay');
    var content = document.getElementById('drawerContent');
    if (!ov || !content) {
      window.location.href = url.replace('?partial=1', '').replace('&partial=1', '');
      return;
    }
    content.innerHTML = '<div class="drawer-loading">Loading…</div>';
    ov.hidden = false;
    fetch(url, { headers: { 'X-Partial': '1', 'Accept': 'text/html' } })
      .then(function (r) { return r.text(); })
      .then(function (html) {
        content.innerHTML = html;
        content.querySelectorAll('[data-drawer-close]').forEach(function (btn) {
          btn.addEventListener('click', closeDrawer);
        });
      })
      .catch(function () {
        content.innerHTML = '<div class="drawer-loading">Failed to load. <a href="' + url.replace('partial=1', '') + '">Open full page</a></div>';
      });
  }
  function closeDrawer() {
    var ov = document.getElementById('drawerOverlay');
    if (ov) ov.hidden = true;
  }

  function showToast(cat, msg) {
    var stack = document.getElementById('toastStack');
    if (!stack) return;
    var el = document.createElement('div');
    el.className = 'cl-toast ' + (cat || 'info');
    var icon = { success: 'fa-circle-check', danger: 'fa-circle-xmark', warning: 'fa-triangle-exclamation', info: 'fa-circle-info' }[cat] || 'fa-circle-info';
    el.innerHTML = '<i class="fas ' + icon + ' toast-icon"></i><div class="toast-msg"></div><button type="button" class="toast-close" aria-label="Close">&times;</button>';
    el.querySelector('.toast-msg').textContent = msg;
    el.querySelector('.toast-close').addEventListener('click', function () { dismissToast(el); });
    stack.appendChild(el);
    setTimeout(function () { dismissToast(el); }, 4500);
  }
  function dismissToast(el) {
    if (!el || !el.parentNode) return;
    el.classList.add('out');
    setTimeout(function () { el.remove(); }, 180);
  }
  window.clToast = showToast;

  ready(function () {
    var flash = document.getElementById('flashToasts');
    if (flash) {
      flash.querySelectorAll('[data-toast-msg]').forEach(function (n) {
        showToast(n.getAttribute('data-toast-cat'), n.getAttribute('data-toast-msg'));
      });
    }

    document.querySelectorAll('[data-confirm]').forEach(function (el) {
      el.addEventListener('click', function (e) {
        if (!confirm(el.getAttribute('data-confirm'))) e.preventDefault();
      });
    });

    var toggle = document.getElementById('sidebarToggle');
    var backdrop = document.getElementById('sidebarBackdrop');
    function closeSidebar() { document.body.classList.remove('sidebar-open'); }
    if (toggle) toggle.addEventListener('click', function () { document.body.classList.toggle('sidebar-open'); });
    if (backdrop) backdrop.addEventListener('click', closeSidebar);
    document.querySelectorAll('.app-sidebar .nav-item').forEach(function (link) {
      link.addEventListener('click', function () {
        if (window.innerWidth <= 900) closeSidebar();
      });
    });

    applyTheme(currentTheme());
    document.querySelectorAll('[data-theme-set]').forEach(function (btn) {
      btn.addEventListener('click', function () { applyTheme(btn.getAttribute('data-theme-set')); });
    });
    document.querySelectorAll('[data-theme-cycle]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var modes = ['light', 'dark', 'system'];
        applyTheme(modes[(modes.indexOf(currentTheme()) + 1) % modes.length]);
      });
    });
    try {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
        if (currentTheme() === 'system') applyTheme('system');
      });
    } catch (e) {}

    buildCommands();
    document.querySelectorAll('[data-cmd-open]').forEach(function (b) {
      b.addEventListener('click', openCmd);
    });
    var cmdInput = document.getElementById('cmdInput');
    if (cmdInput) {
      cmdInput.addEventListener('input', function () { renderCmd(cmdInput.value); });
      cmdInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          var active = document.querySelector('#cmdList button.active');
          if (active) active.click();
        }
      });
    }
    var cmdOverlay = document.getElementById('cmdOverlay');
    if (cmdOverlay) {
      cmdOverlay.addEventListener('click', function (e) {
        if (e.target === cmdOverlay) closeCmd();
      });
    }

    document.body.addEventListener('click', function (e) {
      var openEl = e.target.closest('[data-drawer-open]');
      if (openEl) {
        e.preventDefault();
        openDrawer(openEl.getAttribute('data-drawer-open'));
      }
    });
    var drawerOverlay = document.getElementById('drawerOverlay');
    if (drawerOverlay) {
      drawerOverlay.addEventListener('click', function (e) {
        if (e.target === drawerOverlay) closeDrawer();
      });
    }

    document.addEventListener('keydown', function (e) {
      var meta = e.metaKey || e.ctrlKey;
      if (meta && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        var ov = document.getElementById('cmdOverlay');
        if (ov && !ov.hidden) closeCmd(); else openCmd();
      }
      if (e.key === 'Escape') {
        closeCmd();
        closeDrawer();
      }
    });
  });
})();
