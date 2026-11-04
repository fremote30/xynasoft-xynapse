// =====================================
// APP.JS
// FINAL CLEAN BOOTSTRAP
// =====================================

(() => {

  "use strict";

  // =====================================
  // SAFE SPA BOOTSTRAP
  // =====================================
  document.addEventListener("DOMContentLoaded", async () => {

    try {

      console.log("🚀 XynaFaith SPA Booting...");

      // =====================================
      // INITIALIZE MOBILE SDK
      // =====================================
      console.log("📱 Initializing Mobile SDK...");

      if (window.DeviceService) {
        await DeviceService.initialize();
      }

      if (window.StorageService) {
        await StorageService.initialize();
      }

      if (window.NetworkService) {
        await NetworkService.initialize();
      }

      if (window.NotificationService) {
        await NotificationService.initialize();
      }

      if (window.MobileAuthService) {
        await MobileAuthService.initialize();
      }

      if (window.MobileApi) {
        await MobileApi.initialize();
      }

      console.log("✅ Mobile SDK Ready");

      // =====================================
      // RESTORE USER
      // =====================================
      window.currentUser =
        typeof safeParseUser === "function"
          ? safeParseUser()
          : null;

      // =====================================
      // TOKEN RESTORE
      // =====================================
      const token = getToken();

      if (token) {

        try {

          await getCurrentUser();

        } catch (err) {

          console.error("Session restore failed:", err);

          // =====================================
          // RECOVER BAD SESSION
          // =====================================
          if (typeof resetSession === "function") {

            resetSession();

          } else {

            localStorage.removeItem("access_token");
            localStorage.removeItem("user");

            window.currentUser = null;

          }

        }

      }

      // =====================================
      // RESTORE PUSH DEVICE REGISTRATION
      // =====================================
      if (
        token &&
        window.NotificationService &&
        typeof NotificationService.syncToken === "function"
      ) {
        await NotificationService.syncToken();
      }

      // =====================================
      // NAVBAR
      // =====================================
      if (typeof renderNavbar === "function") {

        renderNavbar();

      }

      // =====================================
      // MOBILE DRAWER USER
      // =====================================
      if (typeof loadMobileDrawerUser === "function") {

        loadMobileDrawerUser();

      }

      // =====================================
      // AUTH + UI
      // =====================================
      if (typeof bindAuthForms === "function") {

        bindAuthForms();

      }

      if (typeof bindPasswordToggle === "function") {

        bindPasswordToggle();

      }

      // =====================================
      // GLOBAL CLICK EVENTS
      // =====================================
      document.addEventListener("click", (e) => {

        // =================================
        // UPGRADE TO PASTOR
        // =================================
        if (e.target.id === "upgradePastorBtn") {

          upgradeToPastor();

        }

      });

      // =====================================
      // START PAGE
      // =====================================
      let startPage = "home";

      if (token && window.currentUser) {

        startPage =
          window.currentUser.role === "member"
            ? "member-dashboard"
            : "dashboard";

      }

      // =====================================
      // START NAVIGATION
      // =====================================
      if (typeof navigate === "function") {

        await navigate(startPage);

      }

      console.log("✅ SPA Initialized");

    } catch (err) {

      console.error("🔥 SPA INIT FAILED:", err);

      const app = document.getElementById("app");

      if (app) {

        app.innerHTML = `
          <div style="padding:60px;text-align:center;">
            <h2>Application failed to load</h2>
            <p>Please refresh the page.</p>
          </div>
        `;

      }

    }

  });

})();