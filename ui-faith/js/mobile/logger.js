/**
 * ============================================================================
 * File: logger.js
 *
 * Purpose:
 * Central logging utility.
 *
 * Responsibilities:
 * - Information logs
 * - Warning logs
 * - Error logs
 *
 * Notes:
 * Logging can be disabled through XFConfig.
 * ============================================================================
 */

const XFLogger = {

    info(message) {

        if (!XFConfig.enableLogging) return;

        console.log("[INFO]", message);

    },

    warn(message) {

        if (!XFConfig.enableLogging) return;

        console.warn("[WARN]", message);

    },

    error(message) {

        console.error("[ERROR]", message);

    }

};