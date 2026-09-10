/**
 * Contact timeline — loads history by phone on Log Call and Call Detail pages.
 */
(function () {
  function csrf() {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.content : '';
  }

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function renderTimeline(host, data) {
    if (!host) return;
    if (!data || (!data.contact && !(data.calls && data.calls.length))) {
      host.innerHTML = '<div class="ct-empty">No prior history for this number</div>';
      host.hidden = false;
      return;
    }
    var c = data.contact || {};
    var html = '';
    html += '<div class="ct-head">';
    html += '<div class="ct-title">';
    html += '<strong>' + escapeHtml(c.display_name || c.phone || 'Contact') + '</strong>';
    if (c.is_vip) html += ' <span class="badge" style="background:#f59e0b;color:#fff;">VIP</span>';
    html += '</div>';
    if (c.company || c.email) {
      html += '<div class="ct-sub">' +
        (c.company ? escapeHtml(c.company) : '') +
        (c.company && c.email ? ' · ' : '') +
        (c.email ? escapeHtml(c.email) : '') +
        '</div>';
    }
    html += '<div class="ct-sub">' + (data.total_calls || 0) + ' total call(s)</div>';
    html += '</div>';

    if (data.calls && data.calls.length) {
      html += '<div class="ct-list">';
      data.calls.slice(0, 8).forEach(function (call) {
        html += '<a class="ct-item" href="/calls/' + call.id + '">';
        html += '<div class="ct-item-top">';
        html += '<span class="ct-id">#' + call.id + '</span>';
        html += '<span class="badge status-' + String(call.status || '').toLowerCase().replace(/ /g, '-') + '">' + escapeHtml(call.status) + '</span>';
        html += '<span class="badge badge-' + String(call.priority || '').toLowerCase() + '">' + escapeHtml(call.priority) + '</span>';
        html += '</div>';
        if (call.reason) html += '<div class="ct-reason">' + escapeHtml(call.reason) + '</div>';
        if (call.date_logged) html += '<div class="ct-when">' + escapeHtml(String(call.date_logged).replace('T', ' ').slice(0, 16)) + '</div>';
        html += '</a>';
      });
      html += '</div>';
    }
    host.innerHTML = html;
    host.hidden = false;
  }

  function loadTimeline(phone, host) {
    if (!phone || phone.length < 5 || !host) return;
    fetch('/api/contacts/timeline?phone=' + encodeURIComponent(phone) + '&limit=10', {
      headers: { 'Accept': 'application/json', 'X-CSRFToken': csrf() },
      credentials: 'same-origin'
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j && j.ok) renderTimeline(host, j);
      })
      .catch(function () {});
  }

  document.addEventListener('DOMContentLoaded', function () {
    // Log call form — phone field
    var phoneInput = document.querySelector('input[name="phone_number"], #phone_number');
    var historyHost = document.getElementById('phoneHistory');
    if (phoneInput && historyHost) {
      var timer = null;
      phoneInput.addEventListener('input', function () {
        clearTimeout(timer);
        var v = (phoneInput.value || '').trim();
        if (v.length < 5) {
          historyHost.hidden = true;
          historyHost.innerHTML = '';
          return;
        }
        timer = setTimeout(function () { loadTimeline(v, historyHost); }, 350);
      });
      if ((phoneInput.value || '').trim().length >= 5) {
        loadTimeline(phoneInput.value.trim(), historyHost);
      }
    }

    // Call detail — inject timeline panel if phone is present
    var detailPhone = document.querySelector('[data-copy]');
    var detailGrid = document.querySelector('.detail-grid');
    if (detailPhone && detailGrid) {
      var phone = detailPhone.getAttribute('data-copy');
      if (phone) {
        var panel = document.createElement('div');
        panel.className = 'cl-card mb-3 ct-panel';
        panel.innerHTML = '<div class="cl-card-header">Contact timeline</div><div class="cl-card-body" id="detailContactTimeline"><div class="ct-empty">Loading…</div></div>';
        // Insert as first card in the right column if present, else after details
        var rightCol = detailGrid.children[1];
        if (rightCol) {
          rightCol.insertBefore(panel, rightCol.firstChild);
        } else {
          detailGrid.appendChild(panel);
        }
        loadTimeline(phone, document.getElementById('detailContactTimeline'));
      }
    }
  });
})();
