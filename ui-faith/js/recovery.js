// =====================================
// RECOVERY.JS
// STEP 1X
// STARTUP RECOVERY
// =====================================

(() => {

  // =====================================
  // SAFE JSON PARSE
  // =====================================
  window.safeParseUser =
    function () {

      try {

        const raw =
          localStorage.getItem(
            "user"
          );

        if (!raw) {
          return null;
        }

        return JSON.parse(raw);

      } catch (err) {

        console.error(
          "Bad user JSON:",
          err
        );

        localStorage.removeItem(
          "user"
        );

        return null;
      }
    };

  // =====================================
  // RESET SESSION
  // =====================================
  window.resetSession =
    function () {

      localStorage.removeItem(
        "access_token"
      );

      localStorage.removeItem(
        "user"
      );

      window.currentUser =
        null;
    };

})();