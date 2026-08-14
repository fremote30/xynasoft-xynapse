// =====================================================
// XYNASOFT MOBILE RUNTIME
// bootstrap.js
//
// Initializes the Xynasoft Mobile Runtime.
//
// SAFE:
// - Does NOT modify the existing SPA.
// - Initializes available mobile services.
// - Continues running even if one service fails.
// - Serves as the single entry point for the mobile SDK.
//
// =====================================================

(() => {

    "use strict";

    console.log("");
    console.log("========================================");
    console.log("🚀 Xynasoft Mobile Runtime");
    console.log("========================================");

    // -------------------------------------------------
    // Verify Core Runtime
    // -------------------------------------------------

    if (!window.XynaPlatform) {

        console.error("❌ config.js not loaded.");

        return;

    }

    if (!window.Assets) {

        console.error("❌ assets.js not loaded.");

        return;

    }

    console.log("✅ Platform:", XynaPlatform.name);

    // -------------------------------------------------
    // Safe Service Initializer
    // -------------------------------------------------

    async function initializeService(name, service) {

        if (!service) {

            console.warn(`⚠ ${name} not found.`);

            return;

        }

        if (typeof service.initialize !== "function") {

            console.warn(`⚠ ${name} has no initialize() method.`);

            return;

        }

        try {

            await service.initialize();

            console.log(`✅ ${name} initialized`);

        }

        catch (error) {

            console.error(`❌ ${name} failed to initialize`, error);

        }

    }

    // -------------------------------------------------
    // Initialize Mobile SDK
    // -------------------------------------------------

    async function initializeMobileServices() {

        console.log("");
        console.log("Initializing Mobile Services...");
        console.log("");

        await initializeService(
            "Splash Service",
            window.XynaSplash
        );

        await initializeService(
            "Status Bar",
            window.XynaStatusBar
        );

        await initializeService(
            "Keyboard Service",
            window.KeyboardService
        );

        await initializeService(
            "Back Button Service",
            window.BackButtonService
        );
        await initializeService(
            "Device Service",
            window.DeviceService
        );

        await initializeService(
            "Storage Service",
            window.StorageService
        );

        await initializeService(
            "Network Service",
            window.NetworkService
        );

        await initializeService(
            "Camera Service",
            window.CameraService
        );

        await initializeService(
            "Share Service",
            window.ShareService
        );

        await initializeService(
            "Notification Service",
            window.NotificationService
        );

        await initializeService(
            "Authentication Service",
            window.MobileAuthService
        );

        await initializeService(
            "API Service",
            window.MobileApi
        );

        console.log("");
        console.log("========================================");
        console.log("✅ Mobile Runtime Ready");
        console.log("========================================");
        console.log("");

    }

    // -------------------------------------------------
    // Start Runtime
    // -------------------------------------------------

    document.addEventListener("DOMContentLoaded", async () => {

        if (window.XynaSplash) {

            await XynaSplash.show();

        }
        await initializeMobileServices();

        if (window.XynaSplash) {

            setTimeout(async () => {

                await XynaSplash.hide();

            }, 900);

        }

    });

})();