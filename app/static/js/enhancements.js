/**
 * CallLog Pro enhancements:
 * - In-app notification centre (backed by /api/inbox)
 * - Server-side saved views (backed by /api/views)
 * - API token management helpers (used from Settings)
 */
(function () {
  function csrf() {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.content : '';
  }

  function api(path, opts) {
    opts = opts || {};
    var headers = Object.assign({
      'Accept': 'application/json',
      'X-CSRFToken': csrf()
    }, opts.headers || {});
    if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(opts.body);
    }
    return fetch(path, Object.assign({}, opts, { headers: headers, credentials: 'same-origin' }))
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, status: r.status, data: j }; }); });
  }

  function timeAgo(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    var sec = Math.floor((Date.now() - d.getTime()) / 1000);
    if (sec < 60) return 'just now';
    if (sec < 3600) return Math.floor(sec / 60) + 'm ago';
    if (sec < 86400) return Math.floor(sec / 3600) + 'h ago';
    return Math.floor(sec / 86400) + 'd ago';
  }

  // ---------------------------------------------------------------------------
  // Notification centre
  // ---------------------------------------------------------------------------
  function initNotifications() {
    var bell = document.getElementById('notifBell');
    var panel = document.getElementById('notifPanel');
    var list = document.getElementById('notifList');
    var badge = document.getElementById('notifBadge');
    if (!bell || !panel || !list) return;

    var open = false;

    function setBadge(n) {
      if (!badge) return;
      if (n > 0) {
        badge.hidden = false;
        badge.textContent = n > 99 ? '99+' : String(n);
      } else {
        badge.hidden = true;
        badge.textContent = '0';
      }
    }

    function renderItems(items) {
      if (!items || !items.length) {
        list.innerHTML = '<div class="notif-empty">No notifications yet</div>';
        return;
      }
      list.innerHTML = items.map(function (n) {
        var cls = n.is_read ? 'notif-item' : 'notif-item unread';
        var href = n.link_url || (n.call_id ? '/calls/' + n.call_id : '#');
        return (
          '<a class="' + cls + '" href="' + href + '" data-id="' + n.id + '">' +
            '<div class="notif-title">' + escapeHtml(n.title || '') + '</div>' +
            (n.body ? '<div class="notif-body">' + escapeHtml(n.body) + '</div>' : '') +
            '<div class="notif-meta">' +
              '<span class="notif-cat">' + escapeHtml(n.category || 'system') + '</span>' +
              '<span class="notif-when">' + timeAgo(n.created_at) + '</span>' +
            '</div>' +
          '</a>'
        );
      }).join('');

      list.querySelectorAll('.notif-item').forEach(function (el) {
        el.addEventListener('click', function () {
          var id = el.getAttribute('data-id');
          if (id) {
            api('/api/inbox/' + id + '/read', { method: 'POST' }).then(function () {
              refresh(false);
            });
          }
        });
      });
    }

    function escapeHtml(s) {
      return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    function refresh(showPanel) {
      api('/api/inbox?limit=25').then(function (res) {
        if (!res.ok || !res.data || !res.data.ok) return;
        setBadge(res.data.unread_count || 0);
        if (showPanel || open) renderItems(res.data.items || []);
      }).catch(function () {});
    }

    function togglePanel() {
      open = !open;
      panel.hidden = !open;
      if (open) {
        refresh(true);
        // Mark all visible as read after a short delay when opening
        setTimeout(function () {
          api('/api/inbox/read', { method: 'POST', body: {} }).then(function () {
            refresh(true);
          });
        }, 1200);
      }
    }

    bell.addEventListener('click', function (e) {
      e.stopPropagation();
      togglePanel();
    });

    document.addEventListener('click', function (e) {
      if (!open) return;
      if (panel.contains(e.target) || bell.contains(e.target)) return;
      open = false;
      panel.hidden = true;
    });

    // Initial + poll every 45s
    refresh(false);
    setInterval(function () { refresh(false); }, 45000);

    // Expose for other scripts
    window.clRefreshNotifications = function () { refresh(open); };
  }

  // ---------------------------------------------------------------------------
  // Server-side saved views (upgrades localStorage version)
  // ---------------------------------------------------------------------------
  function initSavedViews() {
    var host = document.getElementById('savedViews');
    var saveBtn = document.getElementById('btnSaveView');
    if (!host && !saveBtn) return;

    function render(views) {
      if (!host) return;
      host.querySelectorAll('.sv-chip, .sv-clear, .sv-server').forEach(function (n) { n.remove(); });
      (views || []).forEach(function (v) {
        var a = document.createElement('a');
        a.className = 'sv-chip sv-server' + (v.is_pinned ? ' pinned' : '');
        a.textContent = v.name;
        a.title = 'Server view';
        // Build URL from filters if possible; otherwise stay on current with data
        a.href = buildViewUrl(v.filters || {});
        var x = document.createElement('button');
        x.type = 'button';
        x.className = 'sv-x';
        x.innerHTML = '&times;';
        x.title = 'Delete view';
        x.addEventListener('click', function (e) {
          e.preventDefault();
          e.stopPropagation();
          api('/api/views/' + v.id, { method: 'DELETE' }).then(function (res) {
            if (res.ok) load();
          });
        });
        a.appendChild(x);
        host.appendChild(a);
      });
    }

    function buildViewUrl(filters) {
      var params = new URLSearchParams();
      if (filters.status) params.set('status', filters.status);
      if (filters.priority) params.set('priority', filters.priority);
      if (filters.department) params.set('department', filters.department);
      if (filters.tag) params.set('tag', filters.tag);
      if (filters.overdue) params.set('overdue', '1');
      if (filters.q) params.set('q', filters.q);
      if (filters.assigned_to) params.set('assigned_to', filters.assigned_to);
      var qs = params.toString();
      return '/calls/' + (qs ? '?' + qs : '');
    }

    function currentFilters() {
      var params = new URLSearchParams(location.search);
      var f = {};
      ['status', 'priority', 'department', 'tag', 'q', 'assigned_to'].forEach(function (k) {
        if (params.get(k)) f[k] = params.get(k);
      });
      if (params.get('overdue') === '1') f.overdue = true;
      return f;
    }

    function load() {
      api('/api/views').then(function (res) {
        if (res.ok && res.data && res.data.ok) {
          render(res.data.views || []);
        }
      }).catch(function () {});
    }

    if (saveBtn) {
      // Prefer server save; fall back silently if endpoint fails
      saveBtn.addEventListener('click', function (e) {
        // Let localStorage handler in wave11 also run if present; we take precedence
        var name = window.prompt('Name this view:', 'My filter');
        if (!name || !name.trim()) return;
        api('/api/views', {
          method: 'POST',
          body: {
            name: name.trim().slice(0, 80),
            filters: currentFilters(),
            is_pinned: true
          }
        }).then(function (res) {
          if (res.ok && res.data && res.data.ok) {
            if (window.clToast) window.clToast('success', 'View saved');
            load();
          } else if (window.clToast) {
            window.clToast('danger', (res.data && res.data.error) || 'Could not save view');
          }
        });
      }, true); // capture so we run early
    }

    load();
  }

  // ---------------------------------------------------------------------------
  // API token management (Settings page)
  // ---------------------------------------------------------------------------
  function initApiTokens() {
    var listEl = document.getElementById('apiTokenList');
    var form = document.getElementById('apiTokenForm');
    if (!listEl && !form) return;

    function loadTokens() {
      if (!listEl) return;
      api('/api/tokens').then(function (res) {
        if (!res.ok || !res.data || !res.data.ok) {
          listEl.innerHTML = '<p class="text-muted">Unable to load tokens.</p>';
          return;
        }
        var tokens = res.data.tokens || [];
        if (!tokens.length) {
          listEl.innerHTML = '<p class="text-muted mb-0">No API tokens yet.</p>';
          return;
        }
        listEl.innerHTML = tokens.map(function (t) {
          return (
            '<div class="token-row" data-id="' + t.id + '">' +
              '<div class="token-main">' +
                '<div class="token-name">' + escapeHtml(t.name) + '</div>' +
                '<div class="token-meta">' +
                  '<code>' + escapeHtml(t.prefix) + '…</code> · ' +
                  escapeHtml(t.scopes || 'read') +
                  (t.expires_at ? ' · expires ' + t.expires_at.slice(0, 10) : '') +
                  (t.is_active ? '' : ' · <span class="text-danger">revoked</span>') +
                '</div>' +
              '</div>' +
              (t.is_active ?
                '<button type="button" class="btn btn-sm btn-outline-danger token-revoke">Revoke</button>' :
                '') +
            '</div>'
          );
        }).join('');

        listEl.querySelectorAll('.token-revoke').forEach(function (btn) {
          btn.addEventListener('click', function () {
            var row = btn.closest('.token-row');
            var id = row && row.getAttribute('data-id');
            if (!id || !confirm('Revoke this token? It will stop working immediately.')) return;
            api('/api/tokens/' + id, { method: 'DELETE' }).then(function (r) {
              if (r.ok) loadTokens();
            });
          });
        });
      });
    }

    function escapeHtml(s) {
      return String(s || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var nameInput = document.getElementById('tokenName');
        var scopesInput = document.getElementById('tokenScopes');
        var daysInput = document.getElementById('tokenDays');
        var name = (nameInput && nameInput.value || '').trim();
        if (!name) {
          if (window.clToast) window.clToast('warning', 'Token name is required');
          return;
        }
        var body = {
          name: name,
          scopes: (scopesInput && scopesInput.value) || 'read,write'
        };
        if (daysInput && daysInput.value) body.expires_days = parseInt(daysInput.value, 10);

        api('/api/tokens', { method: 'POST', body: body }).then(function (res) {
          if (res.ok && res.data && res.data.ok && res.data.token) {
            var raw = res.data.token.token;
            var box = document.getElementById('tokenOnce');
            if (box) {
              box.hidden = false;
              box.querySelector('code').textContent = raw;
            }
            if (nameInput) nameInput.value = '';
            if (window.clToast) window.clToast('success', 'Token created — copy it now');
            loadTokens();
          } else if (window.clToast) {
            window.clToast('danger', (res.data && res.data.error) || 'Failed to create token');
          }
        });
      });
    }

    loadTokens();
  }

  document.addEventListener('DOMContentLoaded', function () {
    initNotifications();
    initSavedViews();
    initApiTokens();
  });
})();
