/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Back Button Service
 * ==========================================================
 *
 * Android back-button priority:
 *
 * 1. Close mobile drawer.
 * 2. Return through XynaFaith SPA navigation history.
 * 3. Return to Home when on an inner page.
 * 4. Exit only when already on Home/root.
 */

(() => {

    "use strict";

    class BackButtonService {

        constructor() {
            this.initialized = false;
        }

        async initialize() {

            if (this.initialized) {
                return true;
            }

            console.log(
                "⬅️ Initializing Back Button Service..."
            );

            if (!window.Capacitor) {
                this.initialized = true;
                return true;
            }

            try {

                const { App } =
                    Capacitor.Plugins;

                if (!App) {

                    console.warn(
                        "App plugin unavailable."
                    );

                    this.initialized = true;

                    return false;
                }

                await App.addListener(
                    "backButton",
                    async () => {

                        // =============================
                        // 1. CLOSE MOBILE DRAWER
                        // =============================

                        const drawer =
                            document.getElementById(
                                "mobileDrawer"
                            );

                        if (
                            drawer?.classList.contains(
                                "open"
                            )
                        ) {

                            window.closeMobileMenu?.();

                            return;
                        }

                        // =============================
                        // 2. SPA HISTORY
                        // =============================

                        const stack =
                            window.__navigationStack ||
                            [];

                        while (stack.length) {

                            const previousPage =
                                stack.pop();

                            if (
                                previousPage &&
                                previousPage !==
                                    window.currentPage
                            ) {

                                window.__isBackNavigation =
                                    true;

                                await window.navigate?.(
                                    previousPage
                                );

                                return;
                            }
                        }

                        // =============================
                        // 3. RETURN TO HOME
                        // =============================

                        const currentPage =
                            window.currentPage ||
                            "home";

                        if (currentPage !== "home") {

                            window.__isBackNavigation =
                                true;

                            await window.navigate?.(
                                "home"
                            );

                            return;
                        }

                        // =============================
                        // 4. EXIT APP FROM ROOT
                        // =============================

                        console.log(
                            "⬅️ Back pressed on Home — exiting app."
                        );

                        await App.exitApp();
                    }
                );

                this.initialized = true;

                console.log(
                    "✅ Back Button Service Ready"
                );

                return true;

            } catch (error) {

                console.error(
                    "Back Button Service failed:",
                    error
                );

                return false;
            }
        }
    }

    window.BackButtonService =
        new BackButtonService();

})();
