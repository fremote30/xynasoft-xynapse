/**
 * ============================================================================
 * XynaFaith Mobile Framework
 * ============================================================================
 *
 * File:
 *      index.js
 *
 * Purpose:
 *      Registers and exposes the XynaFaith Mobile Framework.
 *
 * Responsibilities:
 *      - Register framework services
 *      - Create a single global XF namespace
 *      - Prevent global namespace pollution
 *
 * Author:
 *      Xynasoft
 *
 * ============================================================================
 */

(function () {

    "use strict";

    /**
     * Prevent accidental re-registration.
     */
    if (window.XF) {

        console.warn("XF Mobile Framework already initialized.");

        return;

    }

    /**
     * Global XynaFaith Mobile Framework.
     */
    window.XF = {

        /**
         * Framework configuration.
         */
        Config: XFConfig,

        /**
         * Central logging service.
         */
        Logger: XFLogger,

        /**
         * Platform detection.
         */
        Platform: XFPlatform,

        /**
         * Secure storage.
         */
        Storage: XFStorage,

        /**
         * Authentication service.
         */
        Auth: XFAuth,

        /**
         * Session manager.
         */
        Session: XFSession,

        /**
         * Device information.
         */
        Device: XFDevice,

        /**
         * Network monitoring.
         */
        Network: XFNetwork,

        /**
         * Camera service.
         */
        Camera: XFCamera,

        /**
         * Native sharing.
         */
        Share: XFShare,

        /**
         * Push notifications.
         */
        Notifications: XFNotifications,

        /**
         * Biometrics.
         */
        Biometrics: XFBiometrics

    };

    console.info("XynaFaith Mobile Framework loaded.");

})();