/**
 * ============================================================================
 * XynaFaith Mobile
 * ============================================================================
 *
 * File:
 *      logger.js
 *
 * Purpose:
 *      Central logging framework for the XynaFaith Mobile application.
 *
 * Responsibilities:
 *      • Standardize application logging
 *      • Provide log levels
 *      • Timestamp every log entry
 *      • Support future remote logging
 *      • Support production log filtering
 *
 * Notes:
 *      All framework and application modules should log through XF.Logger.
 *      Direct calls to console.log(), console.warn(), and console.error()
 *      should be avoided outside of this file.
 *
 * Author:
 *      Xynasoft
 *
 * ============================================================================
 */

"use strict";

/**
 * ============================================================================
 * Logger
 * ============================================================================
 */
const XFLogger = {

    /**
     * Enable or disable logging.
     *
     * @type {boolean}
     */
    enabled: true,

    /**
     * Current log level.
     *
     * debug | info | warn | error
     *
     * @type {string}
     */
    level: "debug",

    /**
     * Supported log levels.
     */
    levels: Object.freeze({

        debug: 1,

        info: 2,

        warn: 3,

        error: 4

    }),

    /**
     * ------------------------------------------------------------------------
     * Return timestamp.
     *
     * @returns {string}
     * ------------------------------------------------------------------------
     */
    timestamp() {

        return new Date().toISOString();

    },

    /**
     * ------------------------------------------------------------------------
     * Determine whether a log level is enabled.
     *
     * @param {string} level
     *
     * @returns {boolean}
     * ------------------------------------------------------------------------
     */
    shouldLog(level) {

        return this.levels[level] >= this.levels[this.level];

    },

    /**
     * ------------------------------------------------------------------------
     * Debug
     *
     * @param {...*} args
     * ------------------------------------------------------------------------
     */
    debug(...args) {

        if (!this.enabled || !this.shouldLog("debug")) {

            return;

        }

        console.debug(

            `[DEBUG] ${this.timestamp()}`,

            ...args

        );

    },

    /**
     * ------------------------------------------------------------------------
     * Information
     *
     * @param {...*} args
     * ------------------------------------------------------------------------
     */
    info(...args) {

        if (!this.enabled || !this.shouldLog("info")) {

            return;

        }

        console.info(

            `[INFO] ${this.timestamp()}`,

            ...args

        );

    },

    /**
     * ------------------------------------------------------------------------
     * Warning
     *
     * @param {...*} args
     * ------------------------------------------------------------------------
     */
    warn(...args) {

        if (!this.enabled || !this.shouldLog("warn")) {

            return;

        }

        console.warn(

            `[WARN] ${this.timestamp()}`,

            ...args

        );

    },

    /**
     * ------------------------------------------------------------------------
     * Error
     *
     * @param {...*} args
     * ------------------------------------------------------------------------
     */
    error(...args) {

        if (!this.enabled || !this.shouldLog("error")) {

            return;

        }

        console.error(

            `[ERROR] ${this.timestamp()}`,

            ...args

        );

    },

    /**
     * ------------------------------------------------------------------------
     * Enable logging.
     * ------------------------------------------------------------------------
     */
    enable() {

        this.enabled = true;

    },

    /**
     * ------------------------------------------------------------------------
     * Disable logging.
     * ------------------------------------------------------------------------
     */
    disable() {

        this.enabled = false;

    },

    /**
     * ------------------------------------------------------------------------
     * Set log level.
     *
     * @param {string} level
     * ------------------------------------------------------------------------
     */
    setLevel(level) {

        if (!this.levels[level]) {

            throw new Error(`Invalid log level: ${level}`);

        }

        this.level = level;

    }

};

/**
 * ============================================================================
 * Register Logger
 * ============================================================================
 */

window.XF = window.XF || {};

window.XF.Logger = XFLogger;