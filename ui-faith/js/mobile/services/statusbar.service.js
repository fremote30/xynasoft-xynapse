/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Status Bar Service
 * ==========================================================
 */

(() => {

    "use strict";

    class StatusBarService {

        constructor() {

            this.initialized = false;

        }

        // =====================================================
        // Initialize
        // =====================================================

        async initialize() {

            if (this.initialized) {
                return;
            }

            console.log("📱 Initializing Status Bar...");

            this.initialized = true;

            if (!window.Capacitor) {

                console.log("ℹ️ Running in browser.");

                return;

            }

            try {

                const { StatusBar } =
                    Capacitor.Plugins;

                if (!StatusBar) {

                    console.warn("StatusBar plugin unavailable.");

                    return;

                }

                // ---------------------------------
                // Default Launch Style
                // ---------------------------------

                await StatusBar.setStyle({

                    style: "DARK"

                });

                await StatusBar.setBackgroundColor({

                    color: "#ffffff"

                });

                console.log("✅ Status Bar Ready");

            }

            catch (error) {

                console.warn(
                    "StatusBar initialization failed:",
                    error
                );

            }

        }

        // =====================================================
        // Light Theme
        // =====================================================

        async light() {

            if (!window.Capacitor) return;

            try {

                const { StatusBar } =
                    Capacitor.Plugins;

                await StatusBar.setStyle({

                    style: "DARK"

                });

                await StatusBar.setBackgroundColor({

                    color: "#ffffff"

                });

            }

            catch (e) {

                console.warn(e);

            }

        }

        // =====================================================
        // Dark Theme
        // =====================================================

        async dark() {

            if (!window.Capacitor) return;

            try {

                const { StatusBar } =
                    Capacitor.Plugins;

                await StatusBar.setStyle({

                    style: "LIGHT"

                });

                await StatusBar.setBackgroundColor({

                    color: "#121212"

                });

            }

            catch (e) {

                console.warn(e);

            }

        }

    }

    window.XynaStatusBar =
        new StatusBarService();

})();