/**
 * CallLog Pro – shared client-side utilities
 */
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.alert-dismissible').forEach(function (alert) {
        setTimeout(function () {
            var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });

    document.querySelectorAll('[data-confirm]').forEach(function (el) {
        el.addEventListener('click', function (e) {
            if (!confirm(el.getAttribute('data-confirm'))) {
                e.preventDefault();
            }
        });
    });

    var toggle = document.getElementById('sidebarToggle');
    var backdrop = document.getElementById('sidebarBackdrop');
    function closeSidebar() {
        document.body.classList.remove('sidebar-open');
    }
    if (toggle) {
        toggle.addEventListener('click', function () {
            document.body.classList.toggle('sidebar-open');
        });
    }
    if (backdrop) {
        backdrop.addEventListener('click', closeSidebar);
    }
    document.querySelectorAll('.app-sidebar .nav-item').forEach(function (link) {
        link.addEventListener('click', function () {
            if (window.innerWidth <= 900) closeSidebar();
        });
    });
});
