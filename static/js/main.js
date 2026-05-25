// main.js — students will add JavaScript here as features are built

// Mobile nav hamburger toggle
(function () {
    const btn = document.getElementById('nav-hamburger');
    const menu = document.getElementById('nav-mobile-menu');
    if (!btn || !menu) return;

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
})();
