/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Authentication Service
 * ----------------------------------------------------------
 * Purpose:
 * Centralized authentication manager for XynaFaith Mobile.
 *
 * Responsibilities:
 * - Session management
 * - Login state
 * - Logout
 * - Token management
 * - Future biometric authentication
 * - Future token refresh
 * ==========================================================
 */

(() => {

    "use strict";

    class AuthService {

        constructor() {

            this.initialized = false;

            this.user = null;

        }

        // =====================================================
        // Initialize
        // =====================================================

        async initialize() {

            if (this.initialized) {
                return true;
            }

            console.log("🔐 Initializing Authentication Service...");

            this.initialized = true;

            console.log("✅ Authentication Service Ready");

            return true;

        }

        // =====================================================
        // Token Management
        // =====================================================

        getToken() {

            return localStorage.getItem("access_token");

        }

        async saveToken(token) {

            localStorage.setItem(
                "access_token",
                token
            );

            return true;

        }

        async removeToken() {

            localStorage.removeItem(
                "access_token"
            );

            return true;

        }

        hasToken() {

            return !!this.getToken();

        }

        // =====================================================
        // User Management
        // =====================================================

        getUser() {

            return this.user;

        }

        setUser(user) {

            this.user = user;

        }

        clearUser() {

            this.user = null;

        }

        isAuthenticated() {

            return this.hasToken();

        }

        // =====================================================
        // Logout
        // =====================================================

        async logout() {

            await this.removeToken();

            this.clearUser();

            localStorage.removeItem("user");

            console.log("👋 User logged out");

            return true;

        }

        // =====================================================
        // Biometric Login
        // =====================================================

        async biometricLogin() {

            console.log(
                "🔐 Biometric authentication will be implemented in Phase 2."
            );

            return false;

        }

        // =====================================================
        // Token Refresh
        // =====================================================

        async refreshToken() {

            console.log(
                "🔄 Token refresh will be implemented in a future release."
            );

            return false;

        }

    }

    window.MobileAuthService = new AuthService();

})();