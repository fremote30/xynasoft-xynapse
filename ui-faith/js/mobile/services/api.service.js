/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * API Service
 * ----------------------------------------------------------
 * Purpose:
 * Centralized HTTP client for XynaFaith.
 *
 * Responsibilities:
 * - GET / POST / PUT / DELETE
 * - Authorization headers
 * - JSON serialization
 * - Request timeout
 * - Error handling
 * - Future token refresh
 * ==========================================================
 */

(() => {

    "use strict";

    class ApiService {

        constructor() {

            this.initialized = false;

            this.timeout = 30000;

            this.baseUrl =
                window.XynaPlatform?.isMobile
                    ? "https://xynafaith.com"
                    : "";

        }

        // =====================================================
        // Initialize
        // =====================================================

        async initialize() {

            if (this.initialized) {
                return true;
            }

            console.log("🌍 Initializing API Service...");

            this.initialized = true;

            console.log("✅ API Service Ready");

            return true;

        }

        // =====================================================
        // Configure Base URL
        // =====================================================

        setBaseUrl(url) {

            this.baseUrl = url;

        }

        // =====================================================
        // Authorization Header
        // =====================================================

        authHeaders() {

            const token = localStorage.getItem("access_token");

            return token
                ? {
                    Authorization: `Bearer ${token}`
                  }
                : {};

        }

        // =====================================================
        // Default Headers
        // =====================================================

        headers(extra = {}) {

            return {

                "Content-Type": "application/json",

                ...this.authHeaders(),

                ...extra

            };

        }

        // =====================================================
        // GET
        // =====================================================

        async get(url) {

            const response = await fetch(

                this.baseUrl + url,

                {

                    headers: this.headers()

                }

            );

            return response;

        }

        // =====================================================
        // POST
        // =====================================================

        async post(url, body = {}) {

            const response = await fetch(

                this.baseUrl + url,

                {

                    method: "POST",

                    headers: this.headers(),

                    body: JSON.stringify(body)

                }

            );

            return response;

        }

        // =====================================================
        // PUT
        // =====================================================

        async put(url, body = {}) {

            const response = await fetch(

                this.baseUrl + url,

                {

                    method: "PUT",

                    headers: this.headers(),

                    body: JSON.stringify(body)

                }

            );

            return response;

        }

        // =====================================================
        // DELETE
        // =====================================================

        async delete(url, body = null) {

            const options = {

                method: "DELETE",

                headers: this.headers()

            };

            if (body !== null) {
                options.body =
                    JSON.stringify(body);
            }

            const response = await fetch(

                this.baseUrl + url,

                options

            );

            return response;

        }

    }

    window.MobileApi = new ApiService();

})();