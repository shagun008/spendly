// main.js — students will add JavaScript here as features are built

// Desktop user dropdown toggle
(function () {
    const trigger = document.getElementById('nav-user-trigger');
    const dropdown = document.getElementById('nav-user-dropdown');
    if (!trigger || !dropdown) return;

    function closeDropdown() {
        dropdown.classList.remove('is-open');
        dropdown.setAttribute('aria-hidden', 'true');
        trigger.setAttribute('aria-expanded', 'false');
    }

    trigger.addEventListener('click', function (e) {
        e.stopPropagation();
        const isOpen = dropdown.classList.toggle('is-open');
        dropdown.setAttribute('aria-hidden', isOpen ? 'false' : 'true');
        trigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    // Click outside to close
    document.addEventListener('click', function (e) {
        if (!dropdown.contains(e.target) && !trigger.contains(e.target)) {
            closeDropdown();
        }
    });

    // Escape to close
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && dropdown.classList.contains('is-open')) {
            closeDropdown();
            trigger.focus();
        }
    });
})();

// Mobile nav toggle — supports both hamburger and user icon when logged in
(function () {
    const btn = document.getElementById('nav-hamburger');
    const menu = document.getElementById('nav-mobile-menu');
    if (!btn || !menu) return;

    // Detect if we're in "logged-in" mode by checking for the data attribute
    const isUserMode = btn.dataset.userMode === 'true';

    function setOpen(open) {
        menu.classList.toggle('is-open', open);
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        btn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
        menu.setAttribute('aria-hidden', open ? 'false' : 'true');
    }

    btn.addEventListener('click', function () {
        const open = menu.classList.toggle('is-open');
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        btn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
        menu.setAttribute('aria-hidden', open ? 'false' : 'true');
    });

    // Close menu when a link inside it is clicked
    menu.addEventListener('click', function (e) {
        if (e.target.tagName === 'A') {
            menu.classList.remove('is-open');
            btn.setAttribute('aria-expanded', 'false');
            menu.setAttribute('aria-hidden', 'true');
        }
    });

    // If logged in, swap hamburger icon for user icon
    if (isUserMode) {
        // Replace the three spans with a user icon
        btn.innerHTML = '';
        const icon = document.createElement('i');
        icon.setAttribute('data-lucide', 'user');
        icon.classList.add('nav-hamburger-user-icon');
        btn.appendChild(icon);
        btn.classList.add('nav-user-icon-btn');
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }
})();
