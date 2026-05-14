(function () {
    const navToggle = document.getElementById("navToggle");
    const navMenu = document.getElementById("navMenu");
    const themeSwitcher = document.getElementById("themeSwitcher");
    const themeToggleBtn = document.getElementById("themeToggle");
    const userMenu = document.getElementById("userMenu");
    const userMenuToggle = document.getElementById("userMenuToggle");

    function closeUserMenu() {
        if (!userMenu) return;
        userMenu.classList.remove("open");
        if (typeof userMenu.removeAttribute === "function") {
            userMenu.removeAttribute("open");
        }
        if (userMenuToggle) {
            userMenuToggle.setAttribute("aria-expanded", "false");
        }
    }

    function closeThemeMenu() {
        if (!themeSwitcher || !themeToggleBtn) return;
        themeSwitcher.classList.remove("open");
        themeToggleBtn.setAttribute("aria-expanded", "false");
    }

    function closeNav() {
        if (!navToggle || !navMenu) return;
        navMenu.classList.remove("open");
        navToggle.setAttribute("aria-expanded", "false");
        closeUserMenu();
    }

    if (navToggle && navMenu) {
        navToggle.addEventListener("click", function (event) {
            event.stopPropagation();
            closeThemeMenu();
            closeUserMenu();
            const isOpen = navMenu.classList.toggle("open");
            navToggle.setAttribute("aria-expanded", String(isOpen));
        });
    }

    if (themeToggleBtn && themeSwitcher) {
        themeToggleBtn.addEventListener("click", function (event) {
            event.stopPropagation();
            closeUserMenu();
            const isOpen = themeSwitcher.classList.toggle("open");
            themeToggleBtn.setAttribute("aria-expanded", String(isOpen));
        });
    }

    if (userMenuToggle && userMenu) {
        const toggleUserMenu = function (event) {
            event.preventDefault();
            event.stopPropagation();
            closeThemeMenu();
            const isOpen = !(userMenu.classList.contains("open") || userMenu.hasAttribute("open"));
            userMenu.classList.toggle("open", isOpen);
            if (isOpen) {
                userMenu.setAttribute("open", "");
            } else {
                userMenu.removeAttribute("open");
            }
            userMenuToggle.setAttribute("aria-expanded", String(isOpen));
        };

        userMenuToggle.addEventListener("click", toggleUserMenu);
        userMenuToggle.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === " ") {
                toggleUserMenu(event);
            }
        });
    }

    document.addEventListener("click", function (event) {
        if (
            navMenu &&
            navToggle &&
            navMenu.classList.contains("open") &&
            !navMenu.contains(event.target) &&
            !navToggle.contains(event.target)
        ) {
            closeNav();
        }

        if (
            themeSwitcher &&
            themeSwitcher.classList.contains("open") &&
            !themeSwitcher.contains(event.target)
        ) {
            closeThemeMenu();
        }

        if (
            userMenu &&
            userMenu.classList.contains("open") &&
            !userMenu.contains(event.target)
        ) {
            closeUserMenu();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") return;
        closeNav();
        closeThemeMenu();
        closeUserMenu();
    });

    const THEME_KEY = "ahaar_theme_preference";
    const themeOptions = document.querySelectorAll(".theme-option");
    const prefersDarkQuery = window.matchMedia
        ? window.matchMedia("(prefers-color-scheme: dark)")
        : null;

    function getStoredThemeMode() {
        try {
            const value = localStorage.getItem(THEME_KEY);
            if (value === "light" || value === "dark" || value === "system") {
                return value;
            }
        } catch (error) {
            return "system";
        }
        return "system";
    }

    function resolveTheme(mode) {
        if (mode === "light" || mode === "dark") return mode;
        if (prefersDarkQuery && prefersDarkQuery.matches) return "dark";
        return "light";
    }

    function getThemeIcon(mode) {
        if (mode === "light") return "\u2600";
        if (mode === "dark") return "\u263E";
        return resolveTheme(mode) === "dark" ? "\u25D1" : "\u25D0";
    }

    function updateThemeUI(mode) {
        themeOptions.forEach(function (btn) {
            const isActive = btn.dataset.themeValue === mode;
            btn.classList.toggle("active", isActive);
            btn.setAttribute("aria-pressed", String(isActive));
        });

        if (!themeToggleBtn) return;
        themeToggleBtn.textContent = getThemeIcon(mode);
        themeToggleBtn.setAttribute("aria-label", "Theme settings: " + mode);
        themeToggleBtn.setAttribute("title", "Theme: " + mode);
    }

    function applyThemeMode(mode) {
        const safeMode = mode === "light" || mode === "dark" || mode === "system" ? mode : "system";
        const resolvedTheme = resolveTheme(safeMode);
        document.documentElement.setAttribute("data-theme-mode", safeMode);
        document.documentElement.setAttribute("data-theme", resolvedTheme);
        updateThemeUI(safeMode);
    }

    window.setThemeMode = function (mode) {
        try {
            localStorage.setItem(THEME_KEY, mode);
        } catch (error) {
            // Ignore storage errors (private mode / disabled storage)
        }
        applyThemeMode(mode);
    };

    themeOptions.forEach(function (btn) {
        btn.addEventListener("click", function (event) {
            event.stopPropagation();
            const mode = btn.dataset.themeValue;
            window.setThemeMode(mode);
            closeThemeMenu();
        });
    });

    if (prefersDarkQuery) {
        const onSystemThemeChange = function () {
            if (getStoredThemeMode() === "system") {
                applyThemeMode("system");
            }
        };

        if (typeof prefersDarkQuery.addEventListener === "function") {
            prefersDarkQuery.addEventListener("change", onSystemThemeChange);
        } else if (typeof prefersDarkQuery.addListener === "function") {
            prefersDarkQuery.addListener(onSystemThemeChange);
        }
    }

    applyThemeMode(getStoredThemeMode());

    document.querySelectorAll("form").forEach(function (form) {
        form.addEventListener("submit", function () {
            const submitBtn = form.querySelector(
                "button[type='submit'], input[type='submit']"
            );
            if (!submitBtn || submitBtn.dataset.noLoading === "true") return;
            if (submitBtn.disabled) return;

            submitBtn.disabled = true;
            submitBtn.classList.add("loading");
            if (submitBtn.tagName === "BUTTON") {
                if (!submitBtn.dataset.originalText) {
                    submitBtn.dataset.originalText = submitBtn.textContent.trim();
                }
                submitBtn.textContent = "Please wait...";
            } else {
                if (!submitBtn.dataset.originalText) {
                    submitBtn.dataset.originalText = submitBtn.value;
                }
                submitBtn.value = "Please wait...";
            }
        });
    });

    function closeAlert(alertEl) {
        if (!alertEl) return;
        alertEl.classList.add("is-closing");
        window.setTimeout(function () {
            alertEl.remove();
        }, 320);
    }

    document.querySelectorAll(".alert-close").forEach(function (btn) {
        btn.addEventListener("click", function () {
            closeAlert(btn.closest(".alert"));
        });
    });

    document.querySelectorAll(".alert").forEach(function (alertEl) {
        window.setTimeout(function () {
            closeAlert(alertEl);
        }, 6000);
    });

    window.switchTab = function (btn) {
        if (!btn) return;
        const target = btn.dataset.target;
        if (!target) return;

        const scope =
            btn.closest("[data-tab-container]") ||
            btn.closest("section") ||
            document;
        scope.querySelectorAll(".tab-btn").forEach(function (tabBtn) {
            tabBtn.classList.remove("active");
        });
        btn.classList.add("active");

        scope.querySelectorAll(".tab-panel").forEach(function (panel) {
            panel.classList.remove("active");
            panel.style.display = "none";
        });

        const targetPanel = scope.querySelector(target) || document.querySelector(target);
        if (targetPanel) {
            targetPanel.classList.add("active");
            targetPanel.style.display = "block";
        }
    };

    window.filterPosts = function (type, btn) {
        const cards = document.querySelectorAll(".ngo-food-card");
        let visibleCount = 0;
        cards.forEach(function (card) {
            const category = (card.dataset.category || "").toLowerCase();
            const expiring = (card.dataset.expiring || "no").toLowerCase();

            let visible = false;
            if (type === "all") {
                visible = true;
            } else if (type === "expiring") {
                visible = expiring === "yes";
            } else {
                visible = category === String(type).toLowerCase();
            }
            card.style.display = visible ? "" : "none";
            if (visible) visibleCount += 1;
        });

        if (btn) {
            const parent = btn.parentElement || document;
            parent.querySelectorAll(".filter-btn").forEach(function (sibling) {
                sibling.classList.remove("active");
            });
            btn.classList.add("active");
        }

        const postCountEl = document.getElementById("postCount");
        if (postCountEl) {
            postCountEl.textContent = visibleCount + " food post(s) available";
        }

        const noResults = document.getElementById("noResults");
        if (noResults) {
            if (visibleCount === 0 && cards.length > 0) {
                noResults.classList.remove("hidden");
            } else {
                noResults.classList.add("hidden");
            }
        }
    };

    function formatCountdown(ms) {
        const totalMinutes = Math.floor(ms / 60000);
        const days = Math.floor(totalMinutes / 1440);
        const hours = Math.floor((totalMinutes % 1440) / 60);
        const minutes = totalMinutes % 60;

        if (days > 0) return days + "d " + hours + "h left";
        if (hours > 0) return hours + "h " + minutes + "m left";
        return Math.max(minutes, 0) + "m left";
    }

    window.updateCountdowns = function () {
        const now = Date.now();
        document.querySelectorAll("[data-expiry]").forEach(function (el) {
            const raw = el.dataset.expiry;
            const expiryMs = new Date(raw).getTime();
            if (!raw || Number.isNaN(expiryMs)) return;

            const diff = expiryMs - now;
            const hours = diff / 3600000;
            const card = el.closest(".ngo-food-card");

            el.classList.remove("time-green", "time-amber", "time-red");

            if (diff <= 0) {
                el.textContent = "Expired";
                el.classList.add("time-red");
                if (card) card.dataset.expiring = "yes";
                return;
            }

            el.textContent = formatCountdown(diff);
            if (hours > 6) {
                el.classList.add("time-green");
                if (card) card.dataset.expiring = "no";
            } else if (hours >= 1) {
                el.classList.add("time-amber");
                if (card) card.dataset.expiring = "yes";
            } else {
                el.classList.add("time-red");
                if (card) card.dataset.expiring = "yes";
            }
        });
    };

    const imageInput = document.getElementById("id_image");
    if (imageInput) {
        imageInput.addEventListener("change", function (event) {
            const file = event.target.files && event.target.files[0];
            const previewImg = document.getElementById("previewImg");
            const previewPlaceholder = document.getElementById("previewPlaceholder");

            if (!file || !previewImg) return;

            const reader = new FileReader();
            reader.onload = function (loadEvent) {
                previewImg.src = loadEvent.target.result;
                previewImg.classList.remove("hidden");
                if (previewPlaceholder) previewPlaceholder.classList.add("hidden");
            };
            reader.readAsDataURL(file);
        });
    }

    function setPasswordToggleState(btn, isVisible) {
        if (!btn) return;
        btn.classList.toggle("is-visible", isVisible);
        btn.setAttribute("aria-pressed", String(isVisible));
        btn.setAttribute("aria-label", isVisible ? "Hide password" : "Show password");
    }

    window.togglePass = function (inputId, btn) {
        const input = document.getElementById(inputId);
        if (!input) return;

        const toText = input.type === "password";
        input.type = toText ? "text" : "password";
        setPasswordToggleState(btn, toText);
    };

    document.querySelectorAll(".password-toggle").forEach(function (toggleBtn) {
        setPasswordToggleState(toggleBtn, false);
    });

    const loginToggle = document.getElementById("togglePassword");
    const loginPassword = document.getElementById("password");
    if (loginToggle && loginPassword) {
        loginToggle.addEventListener("click", function (event) {
            event.preventDefault();
            window.togglePass("password", loginToggle);
        });
    }

    window.updateRoleDescription = function (value) {
        const roleBox = document.getElementById("roleDescription");
        if (!roleBox) return;

        const descriptions = {
            donor: "Donor: Share surplus food and help reduce waste.",
            ngo: "NGO: Browse available donations and request food for people in need.",
            volunteer: "Volunteer: Accept deliveries and confirm handover with OTP.",
        };

        if (descriptions[value]) {
            roleBox.textContent = descriptions[value];
            roleBox.style.display = "block";
        } else {
            roleBox.textContent = "";
            roleBox.style.display = "none";
        }
    };

    window.animateCounter = function (el, target) {
        const finalValue = Number(target);
        if (!el || Number.isNaN(finalValue)) return;

        const duration = 1200;
        const start = 0;
        let startTime = null;

        function step(timestamp) {
            if (!startTime) startTime = timestamp;
            const progress = Math.min((timestamp - startTime) / duration, 1);
            const current = Math.floor(start + (finalValue - start) * progress);
            el.textContent = current.toLocaleString();
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        }
        window.requestAnimationFrame(step);
    };

    function clearLocationError() {
        const existing = document.getElementById("locationError");
        if (existing) existing.remove();
    }

    window.showLocationError = function (msg) {
        const input = document.getElementById("id_location");
        if (!input) return;

        let errorEl = document.getElementById("locationError");
        if (!errorEl) {
            errorEl = document.createElement("p");
            errorEl.id = "locationError";
            errorEl.className = "location-error";
            const wrapper = input.closest(".location-field-wrapper");
            if (wrapper && wrapper.parentNode) {
                wrapper.parentNode.insertBefore(errorEl, wrapper.nextSibling);
            } else if (input.parentNode) {
                input.parentNode.insertBefore(errorEl, input.nextSibling);
            }
        }
        errorEl.textContent = msg;
    };

    function buildOpenStreetMapEmbed(lat, lng, zoomPadding) {
        const delta = zoomPadding || 0.01;
        const latNum = Number(lat);
        const lngNum = Number(lng);
        const left = (lngNum - delta).toFixed(6);
        const bottom = (latNum - delta).toFixed(6);
        const right = (lngNum + delta).toFixed(6);
        const top = (latNum + delta).toFixed(6);
        return (
            '<iframe title="Location map" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="https://www.openstreetmap.org/export/embed.html?bbox=' +
            left +
            "%2C" +
            bottom +
            "%2C" +
            right +
            "%2C" +
            top +
            "&layer=mapnik&marker=" +
            lat +
            "%2C" +
            lng +
            '"></iframe>'
        );
    }

    window.detectLocation = function () {
        const btn = document.getElementById("detectLocationBtn");
        const locationInput = document.getElementById("id_location");
        const latInput = document.getElementById("id_latitude");
        const lngInput = document.getElementById("id_longitude");
        const mapPreview = document.getElementById("locationMapPreview");
        const coords = document.getElementById("locationCoords");

        if (!locationInput) return;

        function setBtnLoading(isLoading) {
            if (!btn) return;
            btn.disabled = isLoading;
            btn.classList.toggle("loading", isLoading);
            btn.textContent = isLoading ? "Detecting..." : "Detect Location";
        }

        clearLocationError();
        setBtnLoading(true);

        if (!navigator.geolocation) {
            setBtnLoading(false);
            window.showLocationError("Geolocation is not supported by this browser.");
            return;
        }

        navigator.geolocation.getCurrentPosition(
            async function (position) {
                const lat = position.coords.latitude.toFixed(6);
                const lng = position.coords.longitude.toFixed(6);

                if (latInput) latInput.value = lat;
                if (lngInput) lngInput.value = lng;

                let addressText = lat + ", " + lng;
                try {
                    const url =
                        "https://nominatim.openstreetmap.org/reverse?lat=" +
                        lat +
                        "&lon=" +
                        lng +
                        "&format=json&addressdetails=1";
                    const response = await fetch(url, {
                        headers: {
                            Accept: "application/json",
                        },
                    });
                    if (!response.ok) {
                        throw new Error("Reverse geocoding failed");
                    }

                    const data = await response.json();
                    const address = data.address || {};
                    const locality = address.city || address.town || address.village || "";
                    const area = address.neighbourhood || address.suburb || "";
                    const roadLine = [address.house_number, address.road]
                        .filter(Boolean)
                        .join(" ");

                    const parts = [roadLine, area, locality, address.county].filter(Boolean);
                    addressText = parts.join(", ") || data.display_name || addressText;
                } catch (error) {
                    window.showLocationError(
                        "Location detected, but address lookup failed. Coordinates were saved."
                    );
                }

                locationInput.value = addressText;

                if (coords) {
                    coords.style.display = "block";
                    coords.textContent = "Latitude: " + lat + " | Longitude: " + lng;
                }

                if (mapPreview) {
                    mapPreview.style.display = "block";
                    mapPreview.innerHTML = buildOpenStreetMapEmbed(lat, lng, 0.01);
                }

                if (btn) {
                    btn.disabled = false;
                    btn.classList.remove("loading");
                    btn.classList.add("btn-primary");
                    btn.textContent = "Location Set";
                }
            },
            function (error) {
                setBtnLoading(false);
                let message = "Unable to detect location.";
                if (error.code === error.PERMISSION_DENIED) {
                    message =
                        "Location permission denied. Please allow access and try again.";
                } else if (error.code === error.POSITION_UNAVAILABLE) {
                    message = "Location information is unavailable right now.";
                } else if (error.code === error.TIMEOUT) {
                    message = "Location request timed out. Please try again.";
                }
                window.showLocationError(message);
            },
            {
                enableHighAccuracy: true,
                timeout: 12000,
            }
        );
    };

    document.querySelectorAll("[data-target]").forEach(function (counter) {
        if (counter.dataset.animated === "yes") return;
        counter.dataset.animated = "yes";
        window.animateCounter(counter, counter.dataset.target);
    });

    document.querySelectorAll(".bar-fill").forEach(function (bar) {
        const finalWidth = bar.style.width || bar.dataset.width || "0%";
        bar.dataset.width = finalWidth;
        bar.style.width = "0";
    });
    window.setTimeout(function () {
        document.querySelectorAll(".bar-fill").forEach(function (bar) {
            bar.style.width = bar.dataset.width || "0%";
        });
    }, 400);

    window.updateCountdowns();
    window.setInterval(window.updateCountdowns, 60000);
})();
