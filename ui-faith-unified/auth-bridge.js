(() => {
  "use strict";

  const V1_KEY = "access_token";
  const V2_KEY = "xynafaith_v2_access_token";

  function clearStudioSession() {
    sessionStorage.removeItem(V2_KEY);
  }

  async function validateToken(value) {
    if (!value) return false;

    try {
      const response = await fetch("/auth/me", {
        headers: {
          Authorization: `Bearer ${value}`
        },
        cache: "no-store"
      });

      return response.ok;
    } catch {
      return false;
    }
  }

  async function synchronizeSession() {
    const value = localStorage.getItem(V1_KEY);

    if (!value) {
      clearStudioSession();
      return false;
    }

    const valid = await validateToken(value);

    if (localStorage.getItem(V1_KEY) !== value) {
      return false;
    }

    if (!valid) {
      clearStudioSession();
      return false;
    }

    sessionStorage.setItem(V2_KEY, value);
    return true;
  }

  function installLogoutBridge() {
    if (typeof window.logout !== "function") return;

    const originalLogout = window.logout;

    window.logout = async function (...args) {
      try {
        return await originalLogout.apply(this, args);
      } finally {
        clearStudioSession();
      }
    };
  }

  window.XynaFaithUnifiedAuth = {
    synchronizeSession,
    clearStudioSession
  };

  window.addEventListener("load", installLogoutBridge);
})();
