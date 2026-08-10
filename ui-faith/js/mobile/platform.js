/**
 * ============================================================================
 * File: platform.js
 *
 * Purpose:
 * Provides platform detection for XynaFaith Mobile.
 *
 * Responsibilities:
 * - Detect Browser
 * - Detect Android
 * - Detect iPhone/iPad
 * - Detect Capacitor
 *
 * Notes:
 * Every native service should use this module instead of performing
 * its own platform detection.
 * ============================================================================
 */

const XFPlatform = {

    /**
     * Returns true when running inside Capacitor.
     */
    isNative() {

        return !!window.Capacitor;

    },

    /**
     * Returns true when running in a standard web browser.
     */
    isWeb() {

        return !this.isNative();

    },

    /**
     * Returns the current platform.
     *
     * Returns:
     *  - android
     *  - ios
     *  - web
     */
    getPlatform() {

        if (!window.Capacitor) {

            return "web";

        }

        return window.Capacitor.getPlatform();

    }

};

window.XFPlatform = XFPlatform;