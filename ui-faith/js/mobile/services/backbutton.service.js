/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Back Button Service
 * ==========================================================
 */

(() => {

    "use strict";

    class BackButtonService {

        constructor() {

            this.initialized = false;

        }

        async initialize() {

            if (this.initialized) {
                return;
            }

            console.log("⬅️ Initializing Back Button Service...");

            if (!window.Capacitor) {

                this.initialized = true;
                return;

            }

            try {

                const { App } = Capacitor.Plugins;

                if (!App) {

                    console.warn("App plugin unavailable.");

                    this.initialized = true;
                    return;

                }

                App.addListener("backButton", ({ canGoBack }) => {

                    if (canGoBack) {

                        window.history.back();

                    } else {

                        console.log("Back button pressed on root screen.");

                        // Future enhancement:
                        // Show "Press back again to exit"

                    }

                });

                this.initialized = true;

                console.log("✅ Back Button Service Ready");

            }

            catch (error) {

                console.error(error);

            }

        }

    }

    window.BackButtonService =
        new BackButtonService();

})();