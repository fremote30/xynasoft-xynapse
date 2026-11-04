/**
 * ================================================================
 * XYNASOFT MOBILE SDK
 * ----------------------------------------------------------------
 * File:
 * device.service.js
 *
 * Purpose:
 * Centralized access to device information and platform detection.
 *
 * Used By:
 * - Camera Service
 * - Authentication Service
 * - Notification Service
 * - Network Service
 * - XynAssist
 *
 * Author:
 * Xynasoft
 * ================================================================
 */

(() => {

    "use strict";

    class DeviceService {

        constructor() {

            this.initialized = false;

            this.deviceInfo = null;

        }

        /**
         * ------------------------------------------------------------
         * Initialize Device Service
         * ------------------------------------------------------------
         */
        async initialize() {

            if (this.initialized) {
                return this.deviceInfo;
            }

            console.log("📱 Initializing Device Service...");

            try {

                if (window.Capacitor) {

                    const platform = Capacitor.getPlatform();

                    this.deviceInfo = {

                        platform,

                        isNative: Capacitor.isNativePlatform(),

                        isAndroid: platform === "android",

                        isIOS: platform === "ios",

                        isWeb: platform === "web",

                        online: navigator.onLine,

                        initialized: true

                    };

                } else {

                    this.deviceInfo = {

                        platform: "web",

                        isNative: false,

                        isAndroid: false,

                        isIOS: false,

                        isWeb: true,

                        online: navigator.onLine,

                        initialized: true

                    };

                }

                this.initialized = true;

                console.log("✅ Device Service Ready");

                console.table(this.deviceInfo);

                return this.deviceInfo;

            } catch (error) {

                console.error("❌ Device initialization failed", error);

                return null;

            }

        }

        //-------------------------------------------------------------
        // Platform
        //-------------------------------------------------------------

        platform() {

            return this.deviceInfo?.platform ?? "web";

        }

        isNative() {

            return this.deviceInfo?.isNative ?? false;

        }

        isAndroid() {

            return this.deviceInfo?.isAndroid ?? false;

        }

        isIOS() {

            return this.deviceInfo?.isIOS ?? false;

        }

        isWeb() {

            return this.deviceInfo?.isWeb ?? true;

        }

        //-------------------------------------------------------------
        // Network
        //-------------------------------------------------------------

        isOnline() {

            return navigator.onLine;

        }

        //-------------------------------------------------------------
        // Screen
        //-------------------------------------------------------------

        width() {

            return window.innerWidth;

        }

        height() {

            return window.innerHeight;

        }

        isMobileWidth() {

            return window.innerWidth < 768;

        }

        //-------------------------------------------------------------
        // Safe Area
        //-------------------------------------------------------------

        safeAreaInsets() {

            return {

                top: getComputedStyle(document.documentElement)
                    .getPropertyValue("env(safe-area-inset-top)"),

                bottom: getComputedStyle(document.documentElement)
                    .getPropertyValue("env(safe-area-inset-bottom)"),

                left: getComputedStyle(document.documentElement)
                    .getPropertyValue("env(safe-area-inset-left)"),

                right: getComputedStyle(document.documentElement)
                    .getPropertyValue("env(safe-area-inset-right)")

            };

        }

        //-------------------------------------------------------------
        // Summary
        //-------------------------------------------------------------

        summary() {

            return {

                platform: this.platform(),

                native: this.isNative(),

                online: this.isOnline(),

                width: this.width(),

                height: this.height(),

                mobile: this.isMobileWidth()

            };

        }

    }

    window.DeviceService = new DeviceService();

})();