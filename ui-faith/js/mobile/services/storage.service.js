/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Storage Service
 * ----------------------------------------------------------
 * Purpose:
 * Centralized storage manager for XynaFaith.
 *
 * Current Backend:
 * - Browser Local Storage
 *
 * Future:
 * - Capacitor Preferences
 * - Secure Storage
 * - Encrypted Storage
 * ==========================================================
 */

(() => {

    "use strict";

    class StorageService {

        constructor() {

            this.initialized = false;

        }

        // =====================================================
        // Initialize
        // =====================================================

        async initialize() {

            if (this.initialized) {
                return true;
            }

            console.log("💾 Initializing Storage Service...");

            this.initialized = true;

            console.log("✅ Storage Service Ready");

            return true;

        }

        // =====================================================
        // Save
        // =====================================================

        async set(key, value) {

            try {

                localStorage.setItem(
                    key,
                    JSON.stringify(value)
                );

                return true;

            } catch (error) {

                console.error(
                    "StorageService.set() failed:",
                    error
                );

                return false;

            }

        }

        // =====================================================
        // Read
        // =====================================================

        async get(key) {

            try {

                const value = localStorage.getItem(key);

                if (value === null) {
                    return null;
                }

                return JSON.parse(value);

            } catch (error) {

                console.error(
                    "StorageService.get() failed:",
                    error
                );

                return null;

            }

        }

        // =====================================================
        // Remove
        // =====================================================

        async remove(key) {

            try {

                localStorage.removeItem(key);

                return true;

            } catch (error) {

                console.error(
                    "StorageService.remove() failed:",
                    error
                );

                return false;

            }

        }

        // =====================================================
        // Clear
        // =====================================================

        async clear() {

            try {

                localStorage.clear();

                return true;

            } catch (error) {

                console.error(
                    "StorageService.clear() failed:",
                    error
                );

                return false;

            }

        }

        // =====================================================
        // Exists
        // =====================================================

        exists(key) {

            return localStorage.getItem(key) !== null;

        }

        // =====================================================
        // Keys
        // =====================================================

        keys() {

            return Object.keys(localStorage);

        }

        // =====================================================
        // Count
        // =====================================================

        count() {

            return localStorage.length;

        }

    }

    window.StorageService = new StorageService();

})();