(function () {
    'use strict';

    function gettext(message) {
        return typeof window.gettext === 'function' ? window.gettext(message) : message;
    }

    function ngettext(singular, plural, count) {
        if (typeof window.ngettext === 'function') return window.ngettext(singular, plural, count);
        return count === 1 ? singular : plural;
    }

    function localizeDigits(value) {
        return typeof window.ahaarLocalizeDigits === 'function'
            ? window.ahaarLocalizeDigits(value)
            : String(value);
    }

    function interpolate(format, values) {
        if (typeof window.ahaarInterpolate === 'function') {
            return window.ahaarInterpolate(format, values);
        }
        const result = format.replace(/%\((\w+)\)[sd]/g, function (match, key) {
            return Object.prototype.hasOwnProperty.call(values, key) ? String(values[key]) : match;
        });
        return localizeDigits(result);
    }

    const root = document.documentElement;
    const navToggle = document.getElementById('mobileNavToggle');
    const mainNav = document.getElementById('mainNav');
    const themeMenu = document.getElementById('themeMenu');
    const themeToggle = document.getElementById('themeToggle');
    const THEME_KEY = 'ahaar_theme_preference';
    const darkQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const themeModeLabels = {
        light: gettext('Light'),
        dark: gettext('Dark'),
        system: gettext('System')
    };

    function closeNav(restoreFocus) {
        if (!mainNav || !navToggle) return;
        const wasOpen = mainNav.classList.contains('open');
        const shouldRestoreFocus = restoreFocus && wasOpen && mainNav.contains(document.activeElement);
        mainNav.classList.remove('open');
        navToggle.setAttribute('aria-expanded', 'false');
        navToggle.setAttribute('aria-label', gettext('Open navigation'));
        document.body.classList.remove('menu-open');
        if (shouldRestoreFocus) navToggle.focus();
    }

    const menuCloseTimers = new WeakMap();
    const animatedMenuSelector = '.nav-dropdown, .account-menu';

    function isAnimatedMenu(menu) {
        return Boolean(menu && menu.matches(animatedMenuSelector));
    }

    function openAnimatedMenu(menu) {
        if (!isAnimatedMenu(menu)) return;
        const closeTimer = menuCloseTimers.get(menu);
        if (closeTimer) {
            window.clearTimeout(closeTimer);
            menuCloseTimers.delete(menu);
        }
        menu.classList.remove('is-closing');
        menu.setAttribute('open', '');
    }

    function closeAnimatedMenu(menu) {
        if (!menu || !menu.open) return;
        if (!isAnimatedMenu(menu)) {
            menu.removeAttribute('open');
            return;
        }
        if (menu.classList.contains('is-closing')) return;
        menu.classList.add('is-closing');
        const delay = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 180;
        const closeTimer = window.setTimeout(function () {
            menu.removeAttribute('open');
            menu.classList.remove('is-closing');
            menuCloseTimers.delete(menu);
        }, delay);
        menuCloseTimers.set(menu, closeTimer);
    }

    function closeMenus(except) {
        document.querySelectorAll('details[open]').forEach(function (menu) {
            if (menu !== except) closeAnimatedMenu(menu);
        });
    }

    if (navToggle && mainNav) {
        navToggle.addEventListener('click', function () {
            const open = !mainNav.classList.contains('open');
            mainNav.classList.toggle('open', open);
            navToggle.setAttribute('aria-expanded', String(open));
            navToggle.setAttribute('aria-label', open ? gettext('Close navigation') : gettext('Open navigation'));
            document.body.classList.toggle('menu-open', open);
            if (open) {
                closeMenus();
                const firstItem = mainNav.querySelector('a[href], summary');
                if (firstItem) {
                    window.setTimeout(function () {
                        if (mainNav.classList.contains('open')) firstItem.focus({ preventScroll: true });
                    }, 60);
                }
            }
        });
    }

    document.addEventListener('click', function (event) {
        const menu = event.target.closest('details');
        if (menu) {
            if (event.target.closest('summary') && isAnimatedMenu(menu)) {
                event.preventDefault();
                if (menu.open && !menu.classList.contains('is-closing')) {
                    closeAnimatedMenu(menu);
                } else {
                    closeMenus(menu);
                    openAnimatedMenu(menu);
                }
                return;
            }
            closeMenus(menu);
            const mobileExploreMenu = window.innerWidth <= 900 && menu.classList.contains('nav-dropdown');
            if (!mobileExploreMenu || event.target.closest('a[href]')) closeNav();
        } else if (!event.target.closest('.main-nav')) {
            closeMenus();
            if (!event.target.closest('.nav-actions')) closeNav();
        } else if (event.target.closest('a[href]')) {
            closeNav(true);
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape') return;
        const openMenu = document.querySelector('details[open]');
        const menuHadFocus = openMenu && openMenu.contains(document.activeElement);
        closeMenus();
        closeNav(true);
        if (menuHadFocus && openMenu && !mainNav?.contains(openMenu)) {
            const summary = openMenu.querySelector('summary');
            if (summary) summary.focus();
        }
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
        if (themeToggle) {
            const label = interpolate(
                gettext('Choose color theme (current: %(mode)s)'),
                { mode: themeModeLabels[safeMode] }
            );
            themeToggle.setAttribute('aria-label', label);
            themeToggle.title = label;
        }
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

    function handleSystemThemeChange() {
        if (storedTheme() === 'system') applyTheme('system');
    }
    if (typeof darkQuery.addEventListener === 'function') {
        darkQuery.addEventListener('change', handleSystemThemeChange);
    } else if (typeof darkQuery.addListener === 'function') {
        darkQuery.addListener(handleSystemThemeChange);
    }
    applyTheme(storedTheme());

    document.querySelectorAll('.alert-close').forEach(function (button) {
        button.addEventListener('click', function () {
            const alert = button.closest('.alert');
            if (alert) alert.remove();
        });
    });

    function fieldGroup(field) {
        return field.closest('.form-group, fieldset, .rating-form');
    }

    function fieldLabel(field) {
        if (field.labels && field.labels.length) return field.labels[0].textContent.trim();
        if (field.getAttribute('aria-label')) return field.getAttribute('aria-label');
        return (field.name || gettext('This field')).replace(/_/g, ' ').replace(/^\w/, function (letter) {
            return letter.toUpperCase();
        });
    }

    function addDescription(field, id) {
        if (!id) return;
        const descriptions = (field.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
        if (!descriptions.includes(id)) field.setAttribute('aria-describedby', descriptions.concat(id).join(' '));
    }

    function setFieldInvalid(field, invalid) {
        const group = fieldGroup(field);
        if (!field) return;
        field.setAttribute('aria-invalid', String(invalid));
        if (field.type === 'radio' && field.name) {
            Array.from(field.form.elements).filter(function (item) {
                return item.name === field.name && item.type === 'radio';
            }).forEach(function (item) { item.setAttribute('aria-invalid', String(invalid)); });
        }
        if (group) {
            const hasInvalid = Array.from(group.querySelectorAll('[aria-invalid="true"]')).length > 0;
            group.classList.toggle('is-invalid', hasInvalid);
        }
    }

    function invalidFields(form) {
        const fields = [];
        const radioGroups = new Set();
        Array.from(form.querySelectorAll('input, select, textarea')).forEach(function (field) {
            if (!field.willValidate || field.validity.valid) return;
            if (field.type === 'radio') {
                if (radioGroups.has(field.name)) return;
                radioGroups.add(field.name);
            }
            fields.push(field);
        });
        return fields;
    }

    function reportInvalidFields(form) {
        const fields = invalidFields(form);
        fields.forEach(function (field) { setFieldInvalid(field, true); });
        if (!fields.length) return;

        let summary = form.querySelector('[data-form-summary]');
        if (!summary) {
            summary = document.createElement('div');
            summary.className = 'form-summary hidden';
            summary.setAttribute('data-form-summary', '');
            summary.setAttribute('role', 'alert');
            summary.setAttribute('tabindex', '-1');
            const token = form.querySelector('[name="csrfmiddlewaretoken"]');
            form.insertBefore(summary, token ? token.nextSibling : form.firstChild);
        }
        summary.replaceChildren();
        const title = document.createElement('strong');
        title.textContent = gettext('Please check the highlighted fields.');
        const list = document.createElement('ul');
        fields.forEach(function (field) {
            const item = document.createElement('li');
            item.textContent = interpolate(
                            gettext('%(field)s: %(error)s'),
                            { field: fieldLabel(field), error: field.validationMessage }
                        );
            list.appendChild(item);
        });
        summary.append(title, list);
        summary.classList.remove('hidden');
        fields[0].focus();
    }

    function associateServerErrors(form) {
        form.querySelectorAll('.errorlist').forEach(function (errors) {
            let fields = [];
            const group = errors.closest('.form-group, fieldset');
            if (group) fields = Array.from(group.querySelectorAll('input, select, textarea'));
            const match = errors.id.match(/^id_(.+)_error$/);
            if (match) {
                fields = Array.from(form.elements).filter(function (field) { return field.name === match[1]; });
            }
            if (!fields.length) return;
            if (!errors.id) errors.id = 'form-errors-' + Math.random().toString(36).slice(2, 10);
            fields.forEach(function (field) {
                field.dataset.serverError = 'true';
                field.dataset.serverErrorId = errors.id;
                field.dataset.serverErrorValue = field.type === 'radio' ? String(field.checked) : field.value;
                setFieldInvalid(field, true);
                addDescription(field, errors.id);
            });
        });
    }

    function clearServerError(field) {
        const relatedFields = field.type === 'radio' && field.name
            ? Array.from(field.form.elements).filter(function (item) {
                return item.name === field.name && item.type === 'radio';
            })
            : [field];

        relatedFields.forEach(function (item) {
            const errorId = item.dataset.serverErrorId;
            const error = errorId ? document.getElementById(errorId) : null;
            if (error) error.remove();
            if (errorId) {
                const descriptions = (item.getAttribute('aria-describedby') || '').split(/\s+/).filter(function (id) {
                    return id && id !== errorId;
                });
                if (descriptions.length) item.setAttribute('aria-describedby', descriptions.join(' '));
                else item.removeAttribute('aria-describedby');
            }
            delete item.dataset.serverError;
            delete item.dataset.serverErrorId;
            delete item.dataset.serverErrorValue;
            setFieldInvalid(item, Boolean(item.validity && !item.validity.valid));
        });

        const summary = field.form.querySelector('[data-form-summary]');
        if (summary && !field.form.querySelector('.errorlist') && !field.form.querySelector('[aria-invalid="true"]')) {
            summary.classList.add('hidden');
        }
    }

    document.querySelectorAll('form').forEach(function (form) {
        associateServerErrors(form);
        let validationPending = false;
        form.addEventListener('invalid', function (event) {
            event.preventDefault();
            setFieldInvalid(event.target, true);
            if (validationPending) return;
            validationPending = true;
            window.setTimeout(function () {
                validationPending = false;
                reportInvalidFields(form);
            }, 0);
        }, true);

        form.addEventListener('input', function (event) {
            const field = event.target;
            if (!field.validity) return;
            if (field.dataset.serverError === 'true') {
                const changed = field.type === 'radio'
                    ? String(field.checked) !== field.dataset.serverErrorValue
                    : field.value !== field.dataset.serverErrorValue;
                if (!changed) return;
                clearServerError(field);
            }
            if (field.validity.valid) setFieldInvalid(field, false);
        });
        form.addEventListener('change', function (event) {
            const field = event.target;
            if (!field.validity) return;
            if (field.dataset.serverError === 'true') {
                const changed = field.type === 'radio'
                    ? String(field.checked) !== field.dataset.serverErrorValue
                    : field.value !== field.dataset.serverErrorValue;
                if (!changed) return;
                clearServerError(field);
            }
            if (field.validity.valid) setFieldInvalid(field, false);
        });

        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                reportInvalidFields(form);
                return;
            }
            const submitter = event.submitter || form.querySelector('[data-confirm]');
            const confirmation = submitter ? submitter.dataset.confirm : '';
            if (confirmation && !window.confirm(confirmation)) {
                event.preventDefault();
                return;
            }
            const button = submitter && submitter.matches('button[type="submit"], input[type="submit"]')
                ? submitter
                : form.querySelector('button[type="submit"], input[type="submit"]');
            if (!button || button.disabled || button.dataset.noLoading === 'true') return;
            button.disabled = true;
            button.classList.add('loading');
            form.setAttribute('aria-busy', 'true');
            if (button.tagName === 'BUTTON') {
                button.dataset.originalText = button.innerHTML;
                button.textContent = gettext('Please wait…');
            }
            window.setTimeout(function () {
                button.disabled = false;
                button.classList.remove('loading');
                form.removeAttribute('aria-busy');
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
        document.querySelectorAll('.filter-btn').forEach(function (item) {
            const active = item === button;
            item.classList.toggle('active', active);
            item.setAttribute('aria-pressed', String(active));
        });
        let visible = 0;
        document.querySelectorAll('.ngo-food-card').forEach(function (card) {
            const matches = filter === 'all' || card.dataset.category === filter || (filter === 'expiring' && card.dataset.expiring === 'yes');
            card.hidden = !matches;
            if (matches) visible += 1;
        });
        const count = document.getElementById('postCount');
        if (count) {
                    count.textContent = interpolate(
                        ngettext('%(count)s food post available', '%(count)s food posts available', visible),
                        { count: visible }
                    );
                }
        const empty = document.getElementById('noResults');
        if (empty) empty.classList.toggle('hidden', visible !== 0);
    };

    document.querySelectorAll('.filter-btn[data-filter]').forEach(function (button) {
        button.setAttribute('aria-pressed', String(button.classList.contains('active')));
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
        const activeTab = tabs.find(function (tab) {
            return tab.classList.contains('active') || tab.getAttribute('aria-selected') === 'true';
        }) || tabs[0];
        tabs.forEach(function (tab) { tab.tabIndex = tab === activeTab ? 0 : -1; });
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
                element.textContent = gettext('Expired');
                element.classList.add('expiry-red');
                return;
            }
            const hours = Math.floor(remaining / 3600000);
            const minutes = Math.floor((remaining % 3600000) / 60000);
            if (hours > 0) {
                const hourText = interpolate(ngettext('%(count)s hour', '%(count)s hours', hours), { count: hours });
                const minuteText = interpolate(ngettext('%(count)s minute', '%(count)s minutes', minutes), { count: minutes });
                element.textContent = interpolate(gettext('Expires in %(time)s'), { time: hourText + ' ' + minuteText });
            } else {
                element.textContent = interpolate(
                    ngettext('Expires in %(count)s minute', 'Expires in %(count)s minutes', minutes),
                    { count: minutes }
                );
            }
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
            button.setAttribute('aria-label', show ? gettext('Hide password') : gettext('Show password'));
            button.setAttribute('aria-pressed', String(show));
            button.querySelector('use').setAttribute('href', show ? '#i-eye' : '#i-eye-off');
        });
    });

    function updateRoleDescription() {
        const selected = document.querySelector('input[name="role"]:checked') || document.getElementById('id_role');
        const description = document.getElementById('roleDescription');
        if (!selected || !description) return;
        const descriptions = {
            donor: gettext('Share surplus food from your home, business, or community event.'),
            ngo: gettext('Find food donations and request support for your community.'),
            volunteer: gettext('Accept delivery tasks and help food reach people safely.')
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
            if (output) output.textContent = localizeDigits(ratingValue(form) + ' / 5');
        });
    });

    document.querySelectorAll('input[type="file"][data-preview]').forEach(function (input) {
        input.addEventListener('change', function () {
            const preview = document.getElementById(input.dataset.preview);
            const placeholder = document.getElementById(input.dataset.placeholder);
            const upload = input.closest('.file-upload');
            if (!input.files || !input.files[0]) return;
            if (upload) {
                const name = upload.querySelector('strong');
                const detail = upload.querySelector('small');
                const size = input.files[0].size / 1024;
                if (name) name.textContent = input.files[0].name;
                if (detail) detail.textContent = size > 1024
                    ? interpolate(gettext('%(size)s MB · selected'), { size: (size / 1024).toFixed(1) })
                    : interpolate(gettext('%(size)s KB · selected'), { size: Math.max(1, Math.round(size)) });
            }
            if (!preview) return;
            if (preview.dataset.objectUrl) URL.revokeObjectURL(preview.dataset.objectUrl);
            if (!('originalSrc' in preview.dataset)) {
                preview.dataset.originalSrc = preview.getAttribute('src') || '';
            }
            const originalSrc = preview.dataset.originalSrc;
            const url = URL.createObjectURL(input.files[0]);
            preview.dataset.objectUrl = url;
            preview.src = url;
            preview.classList.remove('hidden');
            if (placeholder) placeholder.classList.add('hidden');
            preview.onload = function () {
                URL.revokeObjectURL(url);
                delete preview.dataset.objectUrl;
            };
            preview.onerror = function () {
                URL.revokeObjectURL(url);
                delete preview.dataset.objectUrl;
                if (originalSrc) {
                    preview.src = originalSrc;
                } else {
                    preview.removeAttribute('src');
                    preview.classList.add('hidden');
                    if (placeholder) placeholder.classList.remove('hidden');
                }
                const detail = upload ? upload.querySelector('small') : null;
                if (detail) detail.textContent = gettext('Could not preview this image. Choose a valid image file.');
            };
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

    function setLocationButtonState(button, label, disabled) {
        if (!button) return;
        const text = button.querySelector('[data-location-label]');
        if (text) text.textContent = label;
        button.disabled = disabled;
        button.setAttribute('aria-busy', String(disabled));
    }

    window.detectLocation = function () {
        const button = document.getElementById('detectLocationBtn');
        const status = document.getElementById('locationStatus');
        if (!navigator.geolocation) {
            showLocationError(gettext('Location is not supported by this browser. Enter your address manually.'));
            return;
        }
        setLocationButtonState(button, gettext('Locating…'), true);
        if (status) { status.textContent = gettext('Requesting your location…'); status.className = 'form-hint'; }
        navigator.geolocation.getCurrentPosition(function (position) {
            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;
            const latInput = document.getElementById('id_latitude');
            const lngInput = document.getElementById('id_longitude');
            const locationInput = document.getElementById('id_location');
            if (latInput) latInput.value = latitude.toFixed(6);
            if (lngInput) lngInput.value = longitude.toFixed(6);
            if (status) {
                status.textContent = interpolate(
                                    gettext('Location captured: %(latitude)s, %(longitude)s. Add a nearby landmark for volunteers.'),
                                    { latitude: latitude.toFixed(5), longitude: longitude.toFixed(5) }
                                );
                status.className = 'location-coords';
            }
            setLocationButtonState(button, gettext('Use my location'), false);
            window.dispatchEvent(new CustomEvent('ahaar:location', { detail: { latitude: latitude, longitude: longitude } }));
            if (locationInput && !locationInput.value) locationInput.focus();
        }, function () {
            setLocationButtonState(button, gettext('Use my location'), false);
            showLocationError(gettext('Could not access your location. Allow location permission or enter the address manually.'));
        }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 });
    };

    const protectedTextSelector = 'script, style, textarea, input';
    const localizableAttributes = ['title', 'alt', 'placeholder', 'aria-label', 'aria-valuetext'];

    function localizeTextTree(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            if (node.parentElement && node.parentElement.closest(protectedTextSelector)) return;
            const localized = localizeDigits(node.nodeValue);
            if (localized !== node.nodeValue) node.nodeValue = localized;
            return;
        }
        if (node.nodeType !== Node.ELEMENT_NODE || node.matches(protectedTextSelector)) return;
        localizableAttributes.forEach(function (attribute) {
            if (!node.hasAttribute(attribute)) return;
            const current = node.getAttribute(attribute);
            const localized = localizeDigits(current);
            if (localized !== current) node.setAttribute(attribute, localized);
        });
        Array.from(node.childNodes).forEach(localizeTextTree);
    }

    if (root.lang === 'bn' && 'MutationObserver' in window) {
        localizeTextTree(document.body);
        const numberObserver = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.type === 'attributes') {
                    const current = mutation.target.getAttribute(mutation.attributeName) || '';
                    const localized = localizeDigits(current);
                    if (localized !== current) mutation.target.setAttribute(mutation.attributeName, localized);
                    return;
                }
                mutation.addedNodes.forEach(localizeTextTree);
                if (mutation.type === 'characterData') localizeTextTree(mutation.target);
            });
        });
        numberObserver.observe(document.body, {
            childList: true,
            subtree: true,
            characterData: true,
            attributes: true,
            attributeFilter: localizableAttributes
        });
    }

    window.animateCounter = function (element) {
        const target = Number(element.dataset.count || element.textContent);
        if (!Number.isFinite(target) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        const start = performance.now();
        function tick(now) {
            const progress = Math.min((now - start) / 900, 1);
            const value = Math.floor(target * (1 - Math.pow(1 - progress, 3))).toLocaleString(
                document.documentElement.lang || undefined
            );
            element.textContent = localizeDigits(value);
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
