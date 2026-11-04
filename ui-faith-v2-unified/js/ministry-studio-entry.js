
(() => {
  "use strict";

  function addMinistryStudioLink() {
    if (
      typeof window.getToken !== "function" ||
      !window.getToken()
    ) return;

    const nav = document.getElementById("topnav");

    if (!nav ||
        nav.querySelector('[data-v2-ministry-studio]')) {
      return;
    }

    const link = document.createElement("a");
    link.href = "#ministry-studio";
    link.textContent = "Ministry Studio";
    link.dataset.v2MinistryStudio = "true";

    link.addEventListener("click", event => {
      event.preventDefault();

      if (typeof window.navigate === "function") {
        window.navigate("ministry-studio");
      }
    });

    nav.appendChild(link);
  }

  document.addEventListener("DOMContentLoaded", () => {
    addMinistryStudioLink();

    const nav = document.getElementById("topnav");

    if (nav) {
      new MutationObserver(addMinistryStudioLink)
        .observe(nav, { childList: true });
    }
  });
})();
