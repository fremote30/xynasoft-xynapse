/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Utility Helpers
 * ==========================================================
 */

(() => {

    "use strict";

    window.MobileUtils = {

        delay(ms) {

            return new Promise(resolve => setTimeout(resolve, ms));

        },

        uuid() {

            return crypto.randomUUID();

        },

        timestamp() {

            return new Date().toISOString();

        },

        log(...args) {

            console.log("[XynaMobile]", ...args);

        }

    };

})();