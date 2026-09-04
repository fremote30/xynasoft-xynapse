/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Status Bar Service
 * ==========================================================
 *
 * Android 15+ uses edge-to-edge system bars.
 * Status bar background-color control is therefore not
 * available on modern Android.
 *
 * XynaFaith handles the top system inset through CSS:
 *
 *   env(safe-area-inset-top)
 *
 * This service is responsible primarily for status-bar
 * icon/text appearance.
 * ==========================================================
 */

(() => {

    "use strict";

    class StatusBarService {

        constructor() {

            this.initialized = false;

        }

        // =====================================================
        // Plugin
        // =====================================================

        getPlugin() {

            if (!window.Capacitor) {
                return null;
            }

            return Capacitor.Plugins?.StatusBar || null;

        }

        // =====================================================
        // Platform
        // =====================================================

        getPlatform() {

            try {

                return Capacitor.getPlatform?.() || "web";

            }

            catch (_) {

                return "web";

            }

        }

        // =====================================================
        // Initialize
        // =====================================================

        async initialize() {

            if (this.initialized) {
                return true;
            }

            console.log(
                "📱 Initializing Status Bar..."
            );

            const StatusBar =
                this.getPlugin();

            if (!StatusBar) {

                console.log(
                    "ℹ️ Status Bar unavailable in browser."
                );

                this.initialized = true;

                return true;
            }

            try {

                // XynaFaith currently uses a light header.
                // DARK = dark status-bar icons/text.
                await StatusBar.setStyle({
                    style: "DARK"
                });

                /*
                 * Background-color control is not available
                 * on Android 15+.
                 *
                 * iOS does not require this call because the
                 * web content/safe-area supplies the visual
                 * background.
                 */

                this.initialized = true;

                console.log(
                    "✅ Status Bar Ready"
                );

                return true;

            }

            catch (error) {

                console.warn(
                    "Status Bar initialization failed:",
                    error
                );

                // Do not prevent the mobile runtime from
                // starting if system-bar configuration fails.
                this.initialized = true;

                return false;
            }

        }

        // =====================================================
        // Light Application Theme
        // =====================================================

        async light() {

            const StatusBar =
                this.getPlugin();

            if (!StatusBar) {
                return false;
            }

            try {

                await StatusBar.setStyle({
                    style: "DARK"
                });

                return true;

            }

            catch (error) {

                console.warn(
                    "Status Bar light mode failed:",
                    error
                );

                return false;
            }

        }

        // =====================================================
        // Dark Application Theme
        // =====================================================

        async dark() {

            const StatusBar =
                this.getPlugin();

            if (!StatusBar) {
                return false;
            }

            try {

                await StatusBar.setStyle({
                    style: "LIGHT"
                });

                return true;

            }

            catch (error) {

                console.warn(
                    "Status Bar dark mode failed:",
                    error
                );

                return false;
            }

        }

    }

    window.XynaStatusBar =
        new StatusBarService();

})();
