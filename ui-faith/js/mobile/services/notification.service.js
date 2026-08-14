/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Notification Service
 * ==========================================================
 */

(() => {

    "use strict";

    class NotificationService {

        constructor() {

            this.initialized = false;

            this.token = null;

        }

        // =====================================================
        // Initialize
        // =====================================================

        async initialize() {

            if (this.initialized) {
                return;
            }

            console.log("🔔 Initializing Notification Service...");

            this.initialized = true;

            if (!window.Capacitor) {

                console.log("ℹ Browser mode.");

                return;

            }

            try {

                const { PushNotifications } =
                    Capacitor.Plugins;

                if (!PushNotifications) {

                    console.warn("Push plugin unavailable.");

                    return;

                }

                await this.requestPermission();

                this.registerListeners();

                console.log("✅ Notification Service Ready");

            }

            catch (error) {

                console.error(error);

            }

        }

        // =====================================================
        // Permission
        // =====================================================

        async requestPermission() {

            const { PushNotifications } =
                Capacitor.Plugins;

            const permission =
                await PushNotifications.requestPermissions();

            if (permission.receive !== "granted") {

                console.warn("Notification permission denied.");

                return false;

            }

            await PushNotifications.register();

            return true;

        }

        // =====================================================
        // Listeners
        // =====================================================

        registerListeners() {

            const { PushNotifications } =
                Capacitor.Plugins;

            // -----------------------------------------

            PushNotifications.addListener(

                "registration",

                token => {

                    this.token = token.value;

                    console.log(
                        "📲 Push Token:",
                        token.value
                    );

                }

            );

            // -----------------------------------------

            PushNotifications.addListener(

                "registrationError",

                error => {

                    console.error(error);

                }

            );

            // -----------------------------------------

            PushNotifications.addListener(

                "pushNotificationReceived",

                notification => {

                    console.log(
                        "🔔 Notification Received",
                        notification
                    );

                }

            );

            // -----------------------------------------

            PushNotifications.addListener(

                "pushNotificationActionPerformed",

                notification => {

                    console.log(
                        "👉 Notification Clicked",
                        notification
                    );

                    this.routeNotification(notification);

                }

            );

        }

        // =====================================================
        // Router
        // =====================================================

        routeNotification(notification) {

            const data =
                notification.notification?.data ||
                {};

            switch (data.type) {

                case "prayer":

                    navigate?.("prayer");

                    break;

                case "sermon":

                    navigate?.("sermon");

                    break;

                case "member":

                    navigate?.("member-profile");

                    break;

                case "dashboard":

                    navigate?.("dashboard");

                    break;

                default:

                    navigate?.("home");

            }

        }

        // =====================================================
        // Token
        // =====================================================

        getToken() {

            return this.token;

        }

    }

    window.NotificationService =
        new NotificationService();

})();