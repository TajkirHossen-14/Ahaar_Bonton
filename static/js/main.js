(function () {
    'use strict';

    const root = document.documentElement;
    const navToggle = document.getElementById('mobileNavToggle');
    const mainNav = document.getElementById('mainNav');
    const themeMenu = document.getElementById('themeMenu');
    const THEME_KEY = 'ahaar_theme_preference';
    const darkQuery = window.matchMedia('(prefers-color-scheme: dark)');

    function closeNav() {
        if (!mainNav || !navToggle) return;
        mainNav.classList.remove('open');
        navToggle.setAttribute('aria-expanded', 'false');
        navToggle.setAttribute('aria-label', 'Open navigation');
        document.body.classList.remove('menu-open');
    }

    function closeMenus(except) {
        document.querySelectorAll('details[open]').forEach(function (menu) {
            if (menu !== except) menu.removeAttribute('open');
        });
    }

    if (navToggle && mainNav) {
        navToggle.addEventListener('click', function () {
            const open = !mainNav.classList.contains('open');
            mainNav.classList.toggle('open', open);
            navToggle.setAttribute('aria-expanded', String(open));
            navToggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
            document.body.classList.toggle('menu-open', open);
            if (open) closeMenus();
        });
    }

    document.addEventListener('click', function (event) {
        const menu = event.target.closest('details');
        if (menu) {
            closeMenus(menu);
            if (window.innerWidth <= 900) closeNav();
        } else if (!event.target.closest('.main-nav')) {
            closeMenus();
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape') return;
        closeMenus();
        closeNav();
    });

    window.addEventListener('resize', function () {
        if (window.innerWidth > 900) closeNav();
    });

    function storedTheme() {
        try {
            const value = localStorage.getItem(THEME_KEY);
            return ['light', 'dark', 'system'].includes(value) ? value : 'system';
        } catch (error) {
            return 'system';
        }
    }

    function resolvedTheme(mode) {
        if (mode === 'light' || mode === 'dark') return mode;
        return darkQuery.matches ? 'dark' : 'light';
    }

    function applyTheme(mode) {
        const safeMode = ['light', 'dark', 'system'].includes(mode) ? mode : 'system';
        root.dataset.themeMode = safeMode;
        root.dataset.theme = resolvedTheme(safeMode);
        document.querySelectorAll('[data-theme-value]').forEach(function (button) {
            const active = button.dataset.themeValue === safeMode;
            button.classList.toggle('active', active);
            button.setAttribute('aria-pressed', String(active));
        });
        const themeMeta = document.querySelector('meta[name="theme-color"]');
        if (themeMeta) themeMeta.content = root.dataset.theme === 'dark' ? '#101a15' : '#176b45';
    }

    window.setThemeMode = function (mode) {
        try { localStorage.setItem(THEME_KEY, mode); } catch (error) { /* Storage is optional. */ }
        applyTheme(mode);
    };

    document.querySelectorAll('[data-theme-value]').forEach(function (button) {
        button.addEventListener('click', function () {
            window.setThemeMode(button.dataset.themeValue);
            if (themeMenu) themeMenu.removeAttribute('open');
        });
    });

    darkQuery.addEventListener('change', function () {
        if (storedTheme() === 'system') applyTheme('system');
    });
    applyTheme(storedTheme());

    document.querySelectorAll('.alert-close').forEach(function (button) {
        button.addEventListener('click', function () {
            const alert = button.closest('.alert');
            if (alert) alert.remove();
        });
    });

    document.querySelectorAll('form').forEach(function (form) {
        form.addEventListener('submit', function (event) {
            const submitter = event.submitter || form.querySelector('[data-confirm]');
            const confirmation = submitter ? submitter.dataset.confirm : '';
            if (confirmation && !window.confirm(confirmation)) {
                event.preventDefault();
                return;
            }
            const button = form.querySelector('button[type="submit"], input[type="submit"]');
            if (!button || button.disabled || button.dataset.noLoading === 'true') return;
            if (!form.checkValidity()) return;
            button.disabled = true;
            button.classList.add('loading');
            if (button.tagName === 'BUTTON') {
                button.dataset.originalText = button.innerHTML;
                button.textContent = 'Please wait…';
            }
            window.setTimeout(function () {
                button.disabled = false;
                button.classList.remove('loading');
                if (button.tagName === 'BUTTON' && button.dataset.originalText) {
                    button.innerHTML = button.dataset.originalText;
                }
            }, 8000);
        });
    });

    window.switchTab = function (button) {
        const container = button.closest('[data-tab-container]') || document;
        const targetId = button.dataset.target;
        const target = targetId ? document.querySelector(targetId) : null;
        if (!target) return;
        container.querySelectorAll('.tab-btn').forEach(function (item) {
            item.classList.toggle('active', item === button);
            item.setAttribute('aria-selected', String(item === button));
            item.tabIndex = item === button ? 0 : -1;
        });
        container.querySelectorAll('.tab-panel').forEach(function (panel) {
            panel.classList.toggle('active', panel === target);
            panel.hidden = panel !== target;
        });
        target.classList.add('active');
        target.hidden = false;
    };

    window.filterPosts = function (filter, button) {
        if (!button) {
            button = Array.from(document.querySelectorAll('.filter-btn[data-filter]')).find(function (item) {
                return item.dataset.filter === filter;
            });
        }
        document.querySelectorAll('.filter-btn').forEach(function (item) { item.classList.toggle('active', item === button); });
        let visible = 0;
        document.querySelectorAll('.ngo-food-card').forEach(function (card) {
            const matches = filter === 'all' || card.dataset.category === filter || (filter === 'expiring' && card.dataset.expiring === 'yes');
            card.hidden = !matches;
            if (matches) visible += 1;
        });
        const count = document.getElementById('postCount');
        if (count) count.textContent = visible + ' food post' + (visible === 1 ? '' : 's') + ' available';
        const empty = document.getElementById('noResults');
        if (empty) empty.classList.toggle('hidden', visible !== 0);
    };

    document.querySelectorAll('.filter-btn[data-filter]').forEach(function (button) {
        button.addEventListener('click', function () {
            window.filterPosts(button.dataset.filter, button);
        });
    });

    document.querySelectorAll('.tab-btn[data-target]').forEach(function (button) {
        button.addEventListener('click', function () {
            window.switchTab(button);
        });
    });
    document.querySelectorAll('.tab-panel:not(.active)').forEach(function (panel) {
        panel.hidden = true;
    });
    document.querySelectorAll('.tab-bar').forEach(function (tabBar) {
        const tabs = Array.from(tabBar.querySelectorAll('.tab-btn[data-target]'));
        tabs.forEach(function (tab, index) { tab.tabIndex = index === 0 ? 0 : -1; });
        tabBar.addEventListener('keydown', function (event) {
            if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
            const current = tabs.indexOf(document.activeElement);
            if (current < 0) return;
            event.preventDefault();
            let next = current;
            if (event.key === 'ArrowRight') next = (current + 1) % tabs.length;
            if (event.key === 'ArrowLeft') next = (current - 1 + tabs.length) % tabs.length;
            if (event.key === 'Home') next = 0;
            if (event.key === 'End') next = tabs.length - 1;
            tabs[next].focus();
            window.switchTab(tabs[next]);
        });
    });

    document.querySelectorAll('[data-expiry]').forEach(function (element) {
        const expiry = new Date(element.dataset.expiry).getTime();
        function update() {
            const remaining = expiry - Date.now();
            if (remaining <= 0) {
                element.textContent = 'Expired';
                element.classList.add('expiry-red');
                return;
            }
            const hours = Math.floor(remaining / 3600000);
            const minutes = Math.floor((remaining % 3600000) / 60000);
            element.textContent = hours > 0 ? 'Expires in ' + hours + 'h ' + minutes + 'm' : 'Expires in ' + minutes + 'm';
        }
        update();
        window.setInterval(update, 60000);
    });

    document.querySelectorAll('.password-toggle').forEach(function (button) {
        button.addEventListener('click', function () {
            const input = document.getElementById(button.dataset.target);
            if (!input) return;
            const show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            button.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
            button.setAttribute('aria-pressed', String(show));
            button.querySelector('use').setAttribute('href', show ? '#i-eye-off' : '#i-eye');
        });
    });

    function updateRoleDescription() {
        const selected = document.querySelector('input[name="role"]:checked') || document.getElementById('id_role');
        const description = document.getElementById('roleDescription');
        if (!selected || !description) return;
        const descriptions = {
            donor: 'Share surplus food from your home, business, or community event.',
            ngo: 'Find food donations and request support for your community.',
            volunteer: 'Accept delivery tasks and help food reach people safely.'
        };
        description.textContent = descriptions[selected.value] || '';
    }
    window.updateRoleDescription = updateRoleDescription;
    const roleInputs = document.querySelectorAll('input[name="role"]');
    if (roleInputs.length) {
        roleInputs.forEach(function (input) { input.addEventListener('change', updateRoleDescription); });
        updateRoleDescription();
    }

    function ratingValue(form) {
        const checked = form.querySelector('input[name="score"]:checked');
        return checked ? checked.value : '0';
    }

    window.selectStar = function (value) {
        const form = document.querySelector('.rating-form[data-rating-active="true"]');
        if (!form) return;
        const input = form.querySelector('input[name="score"][value="' + value + '"]');
        if (input) {
            input.checked = true;
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }
    };

    document.querySelectorAll('.rating-form').forEach(function (form) {
        const output = form.querySelector('.rating-value');
        form.addEventListener('change', function () {
            if (output) output.textContent = ratingValue(form) + ' / 5';
        });
    });

    document.querySelectorAll('input[type="file"][data-preview]').forEach(function (input) {
        input.addEventListener('change', function () {
            const preview = document.getElementById(input.dataset.preview);
            const placeholder = document.getElementById(input.dataset.placeholder);
            if (!preview || !input.files || !input.files[0]) return;
            const url = URL.createObjectURL(input.files[0]);
            preview.src = url;
            preview.classList.remove('hidden');
            if (placeholder) placeholder.classList.add('hidden');
            preview.onload = function () { URL.revokeObjectURL(url); };
        });
    });

    function showLocationError(message) {
        const status = document.getElementById('locationStatus');
        if (status) {
            status.textContent = message;
            status.className = 'form-error';
        }
    }
    window.showLocationError = showLocationError;

    window.detectLocation = function () {
        const button = document.getElementById('detectLocationBtn');
        const status = document.getElementById('locationStatus');
        if (!navigator.geolocation) {
            showLocationError('Location is not supported by this browser. Enter your address manually.');
            return;
        }
        if (button) { button.disabled = true; button.textContent = 'Locating…'; }
        if (status) { status.textContent = 'Requesting your location…'; status.className = 'form-hint'; }
        navigator.geolocation.getCurrentPosition(function (position) {
            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;
            const latInput = document.getElementById('id_latitude');
            const lngInput = document.getElementById('id_longitude');
            const locationInput = document.getElementById('id_location');
            if (latInput) latInput.value = latitude.toFixed(6);
            if (lngInput) lngInput.value = longitude.toFixed(6);
            if (status) {
                status.textContent = 'Location captured: ' + latitude.toFixed(5) + ', ' + longitude.toFixed(5) + '. Add a nearby landmark for volunteers.';
                status.className = 'location-coords';
            }
            if (button) { button.disabled = false; button.textContent = 'Use My Location'; }
            window.dispatchEvent(new CustomEvent('ahaar:location', { detail: { latitude: latitude, longitude: longitude } }));
            if (!locationInput.value) locationInput.focus();
        }, function () {
            if (button) { button.disabled = false; button.textContent = 'Use My Location'; }
            showLocationError('Could not access your location. Allow location permission or enter the address manually.');
        }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 });
    };

    window.animateCounter = function (element) {
        const target = Number(element.dataset.count || element.textContent);
        if (!Number.isFinite(target) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        const start = performance.now();
        function tick(now) {
            const progress = Math.min((now - start) / 900, 1);
            element.textContent = Math.floor(target * (1 - Math.pow(1 - progress, 3))).toLocaleString();
            if (progress < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    };

    const observer = 'IntersectionObserver' in window ? new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                window.animateCounter(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: .4 }) : null;
    document.querySelectorAll('[data-counter]').forEach(function (element) {
        if (observer) observer.observe(element); else window.animateCounter(element);
    });
})();
