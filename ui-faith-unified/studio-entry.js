(() => {
  "use strict";

  const V1_KEY = "access_token";
  const V2_KEY = "xynafaith_v2_access_token";

  async function prepareStudioSession() {
    const currentToken = localStorage.getItem(V1_KEY);

    if (!currentToken) {
      sessionStorage.removeItem(V2_KEY);
      return;
    }

    try {
      const response = await fetch("/auth/me", {
        headers: {
          Authorization: `Bearer ${currentToken}`
        },
        cache: "no-store"
      });

      if (
        response.ok &&
        localStorage.getItem(V1_KEY) === currentToken
      ) {
        sessionStorage.setItem(V2_KEY, currentToken);
      } else {
        sessionStorage.removeItem(V2_KEY);
      }
    } catch {
      sessionStorage.removeItem(V2_KEY);
    }
  }

  window.XynaFaithStudioEntry = {
    prepareStudioSession
  };
})();
