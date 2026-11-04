/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Notification Service
 * ==========================================================
 *
 * Handles native push registration, device-token syncing,
 * notification receipt, notification taps, and logout cleanup.
 */

(() => {

    "use strict";

    class NotificationService {

        constructor() {
            this.initialized = false;
            this.listenersRegistered = false;
            this.token = null;
        }

        // =====================================================
        // Initialize
        // =====================================================

        async initialize() {

            if (this.initialized) {
                return true;
            }

            console.log("🔔 Initializing Notification Service...");

            if (!window.Capacitor) {
                console.log("ℹ Browser mode.");
                this.initialized = true;
                return true;
            }

            try {

                const { PushNotifications } =
                    Capacitor.Plugins;

                if (!PushNotifications) {
                    console.warn("Push plugin unavailable.");
                    return false;
                }

                /*
                 * Register listeners BEFORE native registration
                 * so the FCM/APNs token event cannot be missed.
                 */
                await this.registerListeners();

                const granted =
                    await this.requestPermission();

                this.initialized = true;

                if (!granted) {
                    return false;
                }

                console.log("✅ Notification Service Ready");

                return true;

            } catch (error) {

                console.error(
                    "Notification initialization failed:",
                    error
                );

                return false;
            }
        }

        // =====================================================
        // Permission + Native Registration
        // =====================================================

        async requestPermission() {

            const { PushNotifications } =
                Capacitor.Plugins;

            let permission =
                await PushNotifications.checkPermissions();

            if (permission.receive === "prompt") {

                permission =
                    await PushNotifications.requestPermissions();
            }

            if (permission.receive !== "granted") {

                console.warn(
                    "Notification permission denied."
                );

                return false;
            }

            await PushNotifications.register();

            return true;
        }

        // =====================================================
        // Listeners
        // =====================================================

        async registerListeners() {

            if (this.listenersRegistered) {
                return;
            }

            const { PushNotifications } =
                Capacitor.Plugins;

            await PushNotifications.addListener(
                "registration",
                async token => {

                    this.token = token.value;

                    console.log(
                        "📲 Push token registered"
                    );

                    /*
                     * If login has already completed this will
                     * bind immediately. Otherwise auth.js/app.js
                     * will call syncToken() again later.
                     */
                    await this.syncToken();
                }
            );

            await PushNotifications.addListener(
                "registrationError",
                error => {

                    console.error(
                        "Push registration error:",
                        error
                    );
                }
            );

            await PushNotifications.addListener(
                "pushNotificationReceived",
                notification => {

                    console.log(
                        "🔔 Notification received",
                        notification
                    );
                }
            );

            await PushNotifications.addListener(
                "pushNotificationActionPerformed",
                action => {

                    console.log(
                        "👉 Notification opened",
                        action
                    );

                    this.routeNotification(action);
                }
            );

            this.listenersRegistered = true;
        }

        // =====================================================
        // Platform
        // =====================================================

        getPlatform() {

            if (window.XynaPlatform?.isAndroid) {
                return "android";
            }

            if (window.XynaPlatform?.isIOS) {
                return "ios";
            }

            return null;
        }

        // =====================================================
        // Sync Token To XynaFaith Backend
        // =====================================================

        async syncToken() {

            if (!this.token) {
                return false;
            }

            const platform =
                this.getPlatform();

            if (!platform) {
                return false;
            }

            const accessToken =
                typeof getToken === "function"
                    ? getToken()
                    : null;

            if (!accessToken) {

                console.log(
                    "ℹ Push token waiting for authenticated session."
                );

                return false;
            }

            try {

                const response =
                    await apiFetch(
                        "/api/v1/devices/push-token",
                        {
                            method: "POST",
                            body: JSON.stringify({
                                token: this.token,
                                platform
                            })
                        }
                    );

                if (!response.ok) {

                    const detail =
                        await response.text();

                    throw new Error(
                        detail ||
                        "Push token registration failed"
                    );
                }

                console.log(
                    "✅ Push device linked to user"
                );

                return true;

            } catch (error) {

                console.error(
                    "Push token sync failed:",
                    error
                );

                return false;
            }
        }

        // =====================================================
        // Deactivate Token Before Logout
        // =====================================================

        async unregisterToken() {

            if (!this.token) {
                return true;
            }

            const platform =
                this.getPlatform();

            const accessToken =
                typeof getToken === "function"
                    ? getToken()
                    : null;

            if (!platform || !accessToken) {
                return false;
            }

            try {

                const response =
                    await apiFetch(
                        "/api/v1/devices/push-token",
                        {
                            method: "DELETE",
                            body: JSON.stringify({
                                token: this.token,
                                platform
                            })
                        }
                    );

                if (!response.ok) {

                    console.warn(
                        "Push token deactivation failed."
                    );

                    return false;
                }

                console.log(
                    "✅ Push device deactivated"
                );

                return true;

            } catch (error) {

                console.error(
                    "Push token deactivation error:",
                    error
                );

                return false;
            }
        }

        // =====================================================
        // Notification Routing
        // =====================================================

        routeNotification(action) {

            const data =
                action?.notification?.data ||
                action?.notification?.notification?.data ||
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
        // Current Native Token
        // =====================================================

        getToken() {
            return this.token;
        }
    }

    window.NotificationService =
        new NotificationService();

})();
