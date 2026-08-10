/**
 * ============================================================================
 * XynaFaith Mobile
 * ============================================================================
 *
 * File:
 *      config.js
 *
 * Purpose:
 *      Central application configuration.
 *
 * Responsibilities:
 *      - Application metadata
 *      - API configuration
 *      - Network configuration
 *      - Mobile feature flags
 *      - Security configuration
 *
 * Notes:
 *      This file contains only static configuration values.
 *      No business logic should exist here.
 *
 * Author:
 *      Xynasoft
 *
 * ============================================================================
 */

"use strict";

/**
 * ============================================================================
 * Application Configuration
 * ============================================================================
 */

const XFConfig = Object.freeze({

    /**
     * ------------------------------------------------------------
     * Application Information
     * ------------------------------------------------------------
     */
    APP: Object.freeze({

        NAME: "XynaFaith",

        VERSION: "1.0.0",

        COMPANY: "Xynasoft",

        DESCRIPTION:
            "Powered by AI • Guided by Scripture • Led by Pastors"

    }),

    /**
     * ------------------------------------------------------------
     * API Configuration
     * ------------------------------------------------------------
     */
    API: Object.freeze({

        /**
         * Base API URL.
         *
         * Development:
         *      http://localhost:8000/api/v1
         *
         * Production:
         *      https://api.xynafaith.com/api/v1
         */
        BASE_URL:
            "http://localhost:8000/api/v1",

        REQUEST_TIMEOUT: 30000

    }),

    /**
     * ------------------------------------------------------------
     * Authentication
     * ------------------------------------------------------------
     */
    AUTH: Object.freeze({

        ACCESS_TOKEN_KEY:
            "access_token",

        REFRESH_TOKEN_KEY:
            "refresh_token",

        USER_KEY:
            "user",

        REMEMBER_DEVICE_KEY:
            "remember_device"

    }),

    /**
     * ------------------------------------------------------------
     * Application Settings
     * ------------------------------------------------------------
     */
    SETTINGS: Object.freeze({

        DEBUG: true,

        LOGGING: true,

        ENABLE_ANALYTICS: false,

        ENABLE_CRASH_REPORTING: false

    }),

    /**
     * ------------------------------------------------------------
     * Mobile Features
     * ------------------------------------------------------------
     */
    FEATURES: Object.freeze({

        BIOMETRICS: true,

        PUSH_NOTIFICATIONS: false,

        CAMERA: true,

        FILE_UPLOAD: true,

        OFFLINE_MODE: false,

        DARK_MODE: true,

        DEEP_LINKING: true

    })

});