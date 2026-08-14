// =====================================================
// XYNASOFT MOBILE RUNTIME
// bootstrap.js
//
// Initializes the mobile runtime.
//
// SAFE:
// Does not modify the existing application.
// Only exposes helper methods.
//
// =====================================================

(() => {

    console.log("🚀 Xynasoft Mobile Runtime");

    if (!window.XynaPlatform) {
        console.error("❌ config.js not loaded.");
        return;
    }

    if (!window.Assets) {
        console.error("❌ assets.js not loaded.");
        return;
    }

    console.log(
        "✅ Runtime Ready:",
        XynaPlatform.name
    );

})();