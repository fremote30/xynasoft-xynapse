/**
 * ============================================================================
 * File: storage.js
 *
 * Purpose:
 * Provides a unified storage API.
 *
 * Browser:
 * - localStorage
 *
 * Native:
 * - Capacitor Secure Storage (future)
 *
 * ============================================================================
 */

const XFStorage = {

    /**
     * Save a value.
     */
    save(key, value) {

        localStorage.setItem(key, JSON.stringify(value));

    },

    /**
     * Retrieve a value.
     */
    get(key) {

        const value = localStorage.getItem(key);

        return value ? JSON.parse(value) : null;

    },

    /**
     * Remove a value.
     */
    remove(key) {

        localStorage.removeItem(key);

    }

};