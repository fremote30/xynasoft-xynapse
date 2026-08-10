/**
 * ============================================================================
 * XynaFaith Mobile
 * ============================================================================
 *
 * File:
 *      validators.js
 *
 * Purpose:
 *      Central validation library used throughout the XynaFaith Mobile
 *      application.
 *
 * Responsibilities:
 *      • Validate user input
 *      • Standardize validation rules
 *      • Reduce duplicate validation logic
 *      • Provide reusable validation methods
 *
 * Notes:
 *      This file should be the ONLY source of validation logic.
 *
 * Author:
 *      Xynasoft
 *
 * ============================================================================
 */

"use strict";

/**
 * ============================================================================
 * Validation Library
 * ============================================================================
 */
const XFValidator = {

    /**
     * ------------------------------------------------------------------------
     * Determine whether a value exists.
     *
     * @param {*} value
     *
     * @returns {boolean}
     * ------------------------------------------------------------------------
     */
    required(value) {

        if (value === null || value === undefined) {

            return false;

        }

        return String(value).trim().length > 0;

    },

    /**
     * ------------------------------------------------------------------------
     * Validate an email address.
     *
     * @param {string} email
     *
     * @returns {boolean}
     * ------------------------------------------------------------------------
     */
    email(email) {

        if (!this.required(email)) {

            return false;

        }

        const pattern =
            /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        return pattern.test(email.trim());

    },

    /**
     * ------------------------------------------------------------------------
     * Validate password length.
     *
     * Default minimum is 8 characters.
     *
     * @param {string} password
     * @param {number} minLength
     *
     * @returns {boolean}
     * ------------------------------------------------------------------------
     */
    password(password, minLength = 8) {

        if (!this.required(password)) {

            return false;

        }

        return password.length >= minLength;

    },

    /**
     * ------------------------------------------------------------------------
     * Validate strong password.
     *
     * Requires:
     *
     * • Uppercase
     * • Lowercase
     * • Number
     * • Special Character
     *
     * @param {string} password
     *
     * @returns {boolean}
     * ------------------------------------------------------------------------
     */
    strongPassword(password) {

        if (!this.password(password)) {

            return false;

        }

        const pattern =
            /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).+$/;

        return pattern.test(password);

    },

    /**
     * ------------------------------------------------------------------------
     * Validate minimum length.
     *
     * @param {string} value
     * @param {number} min
     *
     * @returns {boolean}
     * ------------------------------------------------------------------------
     */
    minLength(value, min) {

        if (!this.required(value)) {

            return false;

        }

        return value.trim().length >= min;

    },

    /**
     * ------------------------------------------------------------------------
     * Validate maximum length.
     *
     * @param {string} value
     * @param {number} max
     *
     * @returns {boolean}
     * ------------------------------------------------------------------------
     */
    maxLength(value, max) {

        if (!this.required(value)) {

            return false;

        }

        return value.trim().length <= max;

    },

    /**
     * ------------------------------------------------------------------------
     * Validate phone number.
     *
     * Accepts digits, spaces, parentheses,
     * plus sign and hyphens.
     *
     * @param {string} phone
     *
     * @returns {boolean}
     * ------------------------------------------------------------------------
     */
    phone(phone) {

        if (!this.required(phone)) {

            return false;

        }

        const pattern =
            /^[0-9+\-()\s]{7,20}$/;

        return pattern.test(phone);

    },

    /**
     * ------------------------------------------------------------------------
     * Validate URL.
     *
     * @param {string} url
     *
     * @returns {boolean}
     * ------------------------------------------------------------------------
     */
    url(url) {

        if (!this.required(url)) {

            return false;

        }

        try {

            new URL(url);

            return true;

        }

        catch {

            return false;

        }

    },

    /**
     * ------------------------------------------------------------------------
     * Validate image file.
     *
     * @param {File} file
     *
     * @returns {boolean}
     * ------------------------------------------------------------------------
     */
    image(file) {

        if (!file) {

            return false;

        }

        return file.type.startsWith("image/");

    },

    /**
     * ------------------------------------------------------------------------
     * Validate uploaded file size.
     *
     * Default:
     *      10 MB
     *
     * @param {File} file
     * @param {number} maxSize
     *
     * @returns {boolean}
     * ------------------------------------------------------------------------
     */
    fileSize(file, maxSize = 10 * 1024 * 1024) {

        if (!file) {

            return false;

        }

        return file.size <= maxSize;

    },

    /**
     * ------------------------------------------------------------------------
     * Validate scripture reference.
     *
     * Examples:
     *
     * John 3:16
     * Psalm 23
     * Romans 8:28
     *
     * @param {string} scripture
     *
     * @returns {boolean}
     * ------------------------------------------------------------------------
     */
    scripture(scripture) {

        if (!this.required(scripture)) {

            return false;

        }

        const pattern =
            /^[1-3]?\s?[A-Za-z]+\s+\d+(:\d+)?(-\d+)?$/;

        return pattern.test(scripture.trim());

    }

};

/**
 * ============================================================================
 * Register Validator
 * ============================================================================
 */

window.XF = window.XF || {};

window.XF.Validator = XFValidator;