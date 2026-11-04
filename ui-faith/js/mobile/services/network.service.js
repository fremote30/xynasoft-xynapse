/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Network Service
 * ----------------------------------------------------------
 * Purpose:
 * Centralized network monitoring.
 *
 * Responsibilities:
 * - Online/offline detection
 * - Network status
 * - Future sync queue
 * - Future background sync
 * ==========================================================
 */

(() => {

    "use strict";

    class NetworkService {

        constructor() {

            this.initialized = false;

            this.online = navigator.onLine;

            this.listeners = [];

        }

        // =====================================================
        // Initialize
        // =====================================================

            async initialize() {

                if (this.initialized) {
                    return true;
                }

                console.log("🌐 Initializing Network Service...");

                this.online = navigator.onLine;

                window.addEventListener(
                    "online",
                    () => this.updateStatus(true)
                );

                window.addEventListener(
                    "offline",
                    () => this.updateStatus(false)
                );

                // =====================================
                // NETWORK BANNER
                // =====================================

                this.addListener((online) => {

                    if (!window.NetworkBanner) {
                        return;
                    }

                    if (online) {
                        NetworkBanner.hide();
                    } else {
                        NetworkBanner.show();
                    }

                });

                this.initialized = true;

                console.log("✅ Network Service Ready");

                return true;

            }

        // =====================================================
        // Status
        // =====================================================

        updateStatus(status) {

            this.online = status;

            console.log(

                status
                    ? "🟢 Network Connected"
                    : "🔴 Network Disconnected"

            );

            this.notifyListeners();

        }

        // =====================================================
        // Listeners
        // =====================================================

        addListener(callback) {

            if (typeof callback === "function") {

                this.listeners.push(callback);

            }

        }

        notifyListeners() {

            this.listeners.forEach(callback => {

                try {

                    callback(this.online);

                }

                catch (error) {

                    console.error(error);

                }

            });

        }

        // =====================================================
        // Public API
        // =====================================================

        isOnline() {

            return this.online;

        }

        isOffline() {

            return !this.online;

        }

        status() {

            return {

                online: this.online,

                timestamp: new Date().toISOString()

            };

        }

    }

    window.NetworkService = new NetworkService();

})();