// =====================================
// GLOBAL ERROR HANDLER
// =====================================

(() => {

  // =========================
  // JS ERRORS
  // =========================
  window.onerror = function (
    message,
    source,
    line,
    column,
    error
  ) {

    console.error(
      "🔥 Global Error:",
      error || message
    );

    if (
      typeof showToast ===
      "function"
    ) {

            showToast(
        "Application error. Check console.",
        "error"
        );
    }

    return false;
  };

  // =========================
  // PROMISE ERRORS
  // =========================
  window.onunhandledrejection =
    function (event) {

    console.error(
      "🔥 Unhandled Promise:",
      event.reason
    );

    if (
      typeof showToast ===
      "function"
    ) {

      showToast(
        "Unexpected error",
        "error"
      );
    }
  };

})();