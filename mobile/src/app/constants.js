/**
 * ============================================================================
 * XynaFaith Mobile
 * ============================================================================
 *
 * File:
 *      constants.js
 *
 * Purpose:
 *      Shared application constants.
 *
 * Responsibilities:
 *      - Routes
 *      - Storage Keys
 *      - Events
 *      - Network Status
 *      - User Roles
 *
 * Author:
 *      Xynasoft
 *
 * ============================================================================
 */

"use strict";

const XFConstants = Object.freeze({

    /**
     * ------------------------------------------------------------
     * Application Routes
     * ------------------------------------------------------------
     */
    ROUTES: Object.freeze({

        SPLASH: "splash",

        LOGIN: "login",

        REGISTER: "register",

        HOME: "home",

        DASHBOARD: "dashboard",

        SERMON: "sermon",

        PRAYER: "prayer",

        NETWORK: "network",

        PROFILE: "profile",

        SETTINGS: "settings"

    }),

    /**
     * ------------------------------------------------------------
     * Storage Keys
     * ------------------------------------------------------------
     */
    STORAGE: Object.freeze({

        USER: "user",

        ACCESS_TOKEN: "access_token",

        REFRESH_TOKEN: "refresh_token",

        REMEMBER_DEVICE: "remember_device"

    }),

    /**
     * ------------------------------------------------------------
     * Network
     * ------------------------------------------------------------
     */
    NETWORK: Object.freeze({

        ONLINE: "online",

        OFFLINE: "offline"

    }),

    /**
     * ------------------------------------------------------------
     * Authentication
     * ------------------------------------------------------------
     */
    AUTH: Object.freeze({

        AUTHENTICATED: "authenticated",

        UNAUTHENTICATED: "unauthenticated"

    }),

    /**
     * ------------------------------------------------------------
     * User Roles
     * ------------------------------------------------------------
     */
    ROLES: Object.freeze({

        MEMBER: "member",

        PASTOR: "pastor",

        VERIFIED_PASTOR: "verified_pastor",

        ADMIN: "admin"

    })

});