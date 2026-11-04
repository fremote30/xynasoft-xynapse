(() => {
  "use strict";

  const allowedRoutes = new Set([
    "home",
    "login",
    "register",
    "dashboard",
    "network"
  ]);

  function openRequestedRoute() {
    const route = window.location.hash.slice(1);

    if (!allowedRoutes.has(route)) return;
    if (typeof window.navigate !== "function") return;

    window.navigate(route);
  }

  window.addEventListener("load", openRequestedRoute);
  window.addEventListener("hashchange", openRequestedRoute);
})();
