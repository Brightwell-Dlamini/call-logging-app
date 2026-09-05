/** System upgrades: live command search, phone history lookup */
(function () {
  function debounce(fn, ms) {
    var t;
    return function () {
      var args = arguments, ctx = this;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(ctx, args); }, ms);
    };
  }

  // Live search in command palette
  document.addEventListener('DOMContentLoaded', function () {
    var input = document.getElementById('cmdInput');
    var list = document.getElementById('cmdList');
    if (!input || !list) return;

    var runSearch = debounce(function (q) {
      if (!q || q.length < 2) return;
      fetch('/api/search?q=' + encodeURIComponent(q))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var html = '';
          (data.calls || []).forEach(function (c) {
            html += '<li class="cmd-item" data-href="' + c.url + '">' +
              '<span class="cmd-item-title">#' + c.id + ' ' + c.caller + '</span>' +
              '<span class="cmd-item-meta">' + c.status + ' · ' + c.priority + '</span></li>';
          });
          (data.users || []).forEach(function (u) {
            html += '<li class="cmd-item" data-href="/calls/?search=' + encodeURIComponent(u.name) + '">' +
              '<span class="cmd-item-title">' + u.name + '</span>' +
              '<span class="cmd-item-meta">' + u.role + '</span></li>';
          });
          if (html) {
            list.insertAdjacentHTML('afterbegin', html);
            list.querySelectorAll('.cmd-item[data-href]').forEach(function (li) {
              li.addEventListener('click', function () {
                window.location.href = li.getAttribute('data-href');
              });
            });
          }
        })
        .catch(function () {});
    }, 220);

    input.addEventListener('input', function () {
      runSearch(input.value.trim());
    });
  });

  // Phone history while logging a call
  document.addEventListener('DOMContentLoaded', function () {
    var phone = document.querySelector('#logCallForm input[name="phone_number"]');
    if (!phone) return;
    var box = document.createElement('div');
    box.id = 'phoneHistory';
    box.className = 'phone-history';
    box.hidden = true;
    phone.parentNode.appendChild(box);

    var lookup = debounce(function (val) {
      if (!val || val.replace(/\D/g, '').length < 6) {
        box.hidden = true;
        return;
      }
      fetch('/api/phone-lookup?phone=' + encodeURIComponent(val))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var matches = data.matches || [];
          if (!matches.length) { box.hidden = true; return; }
          box.innerHTML = '<strong>Prior history</strong> for this number:<ul class="mb-0 mt-1">' +
            matches.map(function (m) {
              return '<li><a href="/calls/' + m.id + '">#' + m.id + '</a> ' +
                m.caller + ' · ' + m.status + ' · ' + m.date + '</li>';
            }).join('') + '</ul>';
          box.hidden = false;
        })
        .catch(function () {});
    }, 300);

    phone.addEventListener('input', function () { lookup(phone.value.trim()); });
  });
})();
