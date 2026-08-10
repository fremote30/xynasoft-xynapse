/**
 * ============================================================================
 * XynaFaith Mobile
 * ============================================================================
 *
 * File:
 *      formatters.js
 *
 * Purpose:
 *      Central formatting library used throughout the XynaFaith Mobile
 *      application.
 *
 * Responsibilities:
 *      • Format dates
 *      • Format times
 *      • Format numbers
 *      • Format file sizes
 *      • Format phone numbers
 *      • Format user names
 *      • Format scripture references
 *      • Format relative time
 *
 * Notes:
 *      All formatting logic should live here.
 *
 * Author:
 *      Xynasoft
 *
 * ============================================================================
 */

"use strict";

/**
 * ============================================================================
 * Formatting Library
 * ============================================================================
 */
const XFFormatter = {

    /**
     * ------------------------------------------------------------------------
     * Format a date.
     *
     * Example:
     *      August 10, 2026
     * ------------------------------------------------------------------------
     */
    date(value) {

        if (!value) {

            return "";

        }

        return new Date(value).toLocaleDateString(undefined, {

            year: "numeric",

            month: "long",

            day: "numeric"

        });

    },

    /**
     * ------------------------------------------------------------------------
     * Format time.
     *
     * Example:
     *      3:45 PM
     * ------------------------------------------------------------------------
     */
    time(value) {

        if (!value) {

            return "";

        }

        return new Date(value).toLocaleTimeString([], {

            hour: "numeric",

            minute: "2-digit"

        });

    },

    /**
     * ------------------------------------------------------------------------
     * Format date and time.
     * ------------------------------------------------------------------------
     */
    dateTime(value) {

        if (!value) {

            return "";

        }

        return new Date(value).toLocaleString();

    },

    /**
     * ------------------------------------------------------------------------
     * Format number with commas.
     * ------------------------------------------------------------------------
     */
    number(value) {

        return Number(value).toLocaleString();

    },

    /**
     * ------------------------------------------------------------------------
     * Format percentage.
     * ------------------------------------------------------------------------
     */
    percentage(value, decimals = 0) {

        return `${Number(value).toFixed(decimals)}%`;

    },

    /**
     * ------------------------------------------------------------------------
     * Format file size.
     * ------------------------------------------------------------------------
     */
    fileSize(bytes) {

        if (!bytes) {

            return "0 Bytes";

        }

        const units = [

            "Bytes",

            "KB",

            "MB",

            "GB",

            "TB"

        ];

        let size = bytes;

        let unit = 0;

        while (size >= 1024 && unit < units.length - 1) {

            size /= 1024;

            unit++;

        }

        return `${size.toFixed(1)} ${units[unit]}`;

    },

    /**
     * ------------------------------------------------------------------------
     * Format phone number.
     * ------------------------------------------------------------------------
     */
    phone(phone) {

        if (!phone) {

            return "";

        }

        const digits = phone.replace(/\D/g, "");

        if (digits.length !== 10) {

            return phone;

        }

        return `(${digits.slice(0,3)}) ${digits.slice(3,6)}-${digits.slice(6)}`;

    },

    /**
     * ------------------------------------------------------------------------
     * Format display name.
     * ------------------------------------------------------------------------
     */
    displayName(user) {

        if (!user) {

            return "Guest";

        }

        return (

            user.full_name ||

            user.name ||

            user.username ||

            "Guest"

        );

    },

    /**
     * ------------------------------------------------------------------------
     * Generate avatar initials.
     * ------------------------------------------------------------------------
     */
    initials(name) {

        if (!name) {

            return "G";

        }

        return name

            .trim()

            .split(/\s+/)

            .map(word => word[0])

            .join("")

            .substring(0, 2)

            .toUpperCase();

    },

    /**
     * ------------------------------------------------------------------------
     * Format scripture reference.
     * ------------------------------------------------------------------------
     */
    scripture(reference) {

        if (!reference) {

            return "";

        }

        return reference.trim();

    },

    /**
     * ------------------------------------------------------------------------
     * Truncate long text.
     * ------------------------------------------------------------------------
     */
    truncate(text, max = 100) {

        if (!text) {

            return "";

        }

        if (text.length <= max) {

            return text;

        }

        return text.substring(0, max) + "...";

    },

    /**
     * ------------------------------------------------------------------------
     * Capitalize first letter.
     * ------------------------------------------------------------------------
     */
    capitalize(text) {

        if (!text) {

            return "";

        }

        return text.charAt(0).toUpperCase() +

            text.slice(1);

    }

};

/**
 * ============================================================================
 * Register Formatter
 * ============================================================================
 */

window.XF = window.XF || {};

window.XF.Formatter = XFFormatter;