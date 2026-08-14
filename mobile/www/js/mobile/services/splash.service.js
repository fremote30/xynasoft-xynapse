/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Splash Service
 * ==========================================================
 */

(() => {

    "use strict";

    class SplashService {

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

            console.log("🚀 Initializing Splash Screen...");

            this.initialized = true;

            console.log("✅ Splash Service Ready");

        }

        // =====================================================
        // Show
        // =====================================================

        async show() {

            if (!window.Capacitor) {
                return;
            }

            try {

                const { SplashScreen } =
                    Capacitor.Plugins;

                if (SplashScreen) {

                    await SplashScreen.show({
                        autoHide: false
                    });

                }

            }

            catch (e) {

                console.warn(e);

            }

        }

        // =====================================================
        // Hide
        // =====================================================

        async hide() {

            if (!window.Capacitor) {
                return;
            }

            try {

                const { SplashScreen } =
                    Capacitor.Plugins;

                if (SplashScreen) {

                    await SplashScreen.hide();

                }

            }

            catch (e) {

                console.warn(e);

            }

        }

    }

    window.XynaSplash =
        new SplashService();

})();