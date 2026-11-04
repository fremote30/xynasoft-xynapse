

function scrollToTop(){

  window.scrollTo({
    top:0,
    behavior:"smooth"
  });

}

function toggleMobileSidebar(){

  const sidebar =
    document.querySelector(
      ".studio-sidebar"
    );

  sidebar.classList.toggle(
    "open"
  );

}

/* ===================================== */
/* ADVANCED TOGGLE */
/* ===================================== */
function initializeSermonPageV2() {

    const toggle =
      document.querySelector(
        ".advanced-toggle"
      );

    const panel =
      document.querySelector(
        ".advanced-panel"
      );

    if (panel) {

      panel.style.display = "none";

    }

    if (toggle && panel) {

      toggle.addEventListener(
        "click",
        () => {

          if (
            panel.style.display
            === "none"
          ) {

            panel.style.display =
              "block";

          } else {

            panel.style.display =
              "none";
          }

        }
      );
    }

    /* ================================= */
    /* FILE NAME DISPLAY */
    /* ================================= */
    const fileInput =
      document.getElementById(
        "sermonFile"
      );

    if (fileInput) {

      fileInput.addEventListener(
        "change",
        () => {

          const label =
            document.getElementById(
              "uploadFileName"
            );

          if (
            fileInput.files &&
            fileInput.files[0]
          ) {

            label.innerHTML =
              "📄 " +
              fileInput.files[0].name;

          } else {

            label.innerHTML =
              "No file selected";
          }

        }
      );
    }

}/* ===================================== */
/* REWRITE MODE */
/* ===================================== */
function activateRewriteMode(){

  // =============================
  // SHOW INFO PANEL
  // =============================
  const info =
    document.getElementById(
      "rewriteInfo"
    );

  if(info){

    info.style.display =
      "block";
  }

  // =============================
  // ACTIVATE TAB
  // =============================
  document
    .querySelectorAll(
      ".tab-btn"
    )

    .forEach(tab => {

      tab.classList.remove(
        "active"
      );

    });

  const rewriteTab =
    document.getElementById(
      "rewriteTab"
    );

  if(rewriteTab){

    rewriteTab.classList.add(
      "active"
    );
  }

}

/* ===================================== */
/* MULTIVERSE MODE */
/* ===================================== */
function activateMultiverseMode(){

  // =============================
  // HIDE REWRITE INFO
  // =============================
  const rewriteInfo =
    document.getElementById(
      "rewriteInfo"
    );

  if(rewriteInfo){

    rewriteInfo.style.display =
      "none";
  }

  // =============================
  // SHOW MULTIVERSE INFO
  // =============================
  const multiverseInfo =
    document.getElementById(
      "multiverseInfo"
    );

  if(multiverseInfo){

    multiverseInfo.style.display =
      "block";
  }

  // =============================
  // ACTIVE TAB
  // =============================
  document
    .querySelectorAll(
      ".tab-btn"
    )

    .forEach(tab => {

      tab.classList.remove(
        "active"
      );

    });

  const multiverseTab =
    document.getElementById(
      "multiverseTab"
    );

  if(multiverseTab){

    multiverseTab.classList.add(
      "active"
    );
  }

  // =============================
  // HIDE NORMAL OUTPUT
  // =============================
  const sermonOutput =
    document.getElementById(
      "sermonOutput"
    );

  if(sermonOutput){

    sermonOutput.style.display =
      "none";
  }

  // =============================
  // SHOW MULTIVERSE OUTPUT
  // =============================
  const multiverseOutput =
    document.getElementById(
      "multiverseOutput"
    );

  if(multiverseOutput){

    multiverseOutput.style.display =
      "block";
  }

}


// Rebind page-specific controls after SPA navigation.
window.initializeSermonPageV2 = initializeSermonPageV2;


/* SERMON STUDIO V2 — BATCH 18B */
function bindSermonWorkspaceV2() {
  const studio = document.querySelector(".studio-layout");
  if (!studio) return;

  const focusButton = studio.querySelector(".focus-btn");
  const xynivaPanel = studio.querySelector("#xynivaStudioPanel");
  const xynivaButton = studio.querySelector(
    ".sermon-v2-xyniva-toggle"
  );
  const collaborateButton = studio.querySelector(
    ".sermon-v2-collaborate"
  );

  // A fresh page starts in normal mode.
  studio.classList.remove("sermon-v2-focus");

  if (focusButton) {
    focusButton.setAttribute("aria-pressed", "false");
    focusButton.textContent = "🖥 Focus Mode";

    focusButton.onclick = function () {
      const enabled = studio.classList.toggle("sermon-v2-focus");
      focusButton.setAttribute("aria-pressed", String(enabled));
      focusButton.setAttribute(
        "aria-label",
        enabled ? "Exit Focus Mode" : "Enter Focus Mode"
      );
      focusButton.textContent = enabled
        ? "↩ Exit Focus"
        : "🖥 Focus Mode";
    };
  }

  if (xynivaPanel && xynivaButton) {
    xynivaPanel.classList.remove("sermon-v2-xyniva-collapsed");

    xynivaButton.onclick = function () {
      const collapsed = xynivaPanel.classList.toggle(
        "sermon-v2-xyniva-collapsed"
      );
      xynivaButton.setAttribute(
        "aria-expanded",
        String(!collapsed)
      );
      xynivaButton.setAttribute(
        "aria-label",
        collapsed
          ? "Expand Xyniva assistant"
          : "Collapse Xyniva assistant"
      );
      xynivaButton.textContent = collapsed ? "+" : "−";
    };
  }

  if (collaborateButton) {
    collaborateButton.onclick = function () {
      const section = studio.querySelector(
        "#collaborationSection"
      );

      const visible = section &&
        section.getClientRects().length > 0 &&
        getComputedStyle(section).visibility !== "hidden";

      if (visible) {
        section.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });
        return;
      }

      // Use the existing sharing workflow if it is available.
      if (typeof window.openPastorShareModal === "function") {
        window.openPastorShareModal();
      } else {
        console.info(
          "Collaboration is available for eligible sermons and pastors."
        );
      }
    };
  }
}

window.bindSermonWorkspaceV2 = bindSermonWorkspaceV2;


/* SERMON STUDIO V2 — BATCH 18C */
function bindSermonToolbarV2() {
  const studio = document.querySelector(".studio-layout");
  if (!studio) return;

  const toolbar = studio.querySelector(".sermon-v2-toolbar");
  if (!toolbar || toolbar.dataset.bound === "true") return;

  toolbar.dataset.bound = "true";

  const selectors = {
    save: "#saveSermonBtn",
    update: "#updateSermonBtn",
    pdf: 'button[onclick="exportPDF()"]',
    docx: 'button[onclick="exportDOCX()"]',
    share: 'button[onclick="openShareModal()"]',
    collaborate: ".sermon-v2-collaborate"
  };

  function permitted(element) {
    if (!element || element.disabled) return false;

    // Preserve existing role-based and action-based restrictions.
    if (element.closest(".pastor-only, .owner-only")) {
      const restricted = element.closest(
        ".pastor-only, .owner-only"
      );
      if (restricted && (
        restricted.hidden ||
        getComputedStyle(restricted).display === "none" ||
        getComputedStyle(restricted).visibility === "hidden"
      )) return false;
    }

    return true;
  }

  function refresh() {
    toolbar.querySelectorAll("[data-sermon-action]").forEach(button => {
      const action = button.dataset.sermonAction;
      const target = studio.querySelector(selectors[action]);

      button.disabled = !permitted(target);
      button.setAttribute(
        "aria-disabled",
        String(button.disabled)
      );
    });
  }

  toolbar.addEventListener("click", event => {
    const button = event.target.closest("[data-sermon-action]");
    if (!button || !toolbar.contains(button)) return;

    refresh();
    if (button.disabled) return;

    const target = studio.querySelector(
      selectors[button.dataset.sermonAction]
    );

    if (permitted(target)) target.click();
    refresh();
  });

  refresh();

  // Existing sermon code may change button state after loading.
  // Re-evaluate on interaction without replacing its handlers.
  studio.addEventListener("click", event => {
    if (!event.target.closest(".sermon-v2-toolbar")) {
      queueMicrotask(refresh);
    }
  });
}

window.bindSermonToolbarV2 = bindSermonToolbarV2;


/* SERMON STUDIO V2 — BATCH 19B */
function arrangeSermonWorkspaceV2() {
  const studio = document.querySelector(".studio-layout");
  if (!studio) return;

  const toolbar = studio.querySelector(".sermon-v2-toolbar");
  const focus = studio.querySelector(".main-actions");
  const toolbarHost = studio.querySelector("#sermonV2ToolbarHost");
  const focusHost = studio.querySelector("#sermonV2FocusHost");

  if (toolbar && toolbarHost &&
      toolbar.parentElement !== toolbarHost) {
    toolbarHost.appendChild(toolbar);
  }

  if (focus && focusHost &&
      focus.parentElement !== focusHost) {
    focusHost.appendChild(focus);
  }
}

window.arrangeSermonWorkspaceV2 = arrangeSermonWorkspaceV2;


/* SERMON STUDIO V2 — BATCH 19D */
function bindSermonPanelsV2() {
  const studio = document.querySelector(".studio-layout");
  if (!studio) return;

  const createButton = studio.querySelector("#sermonV2CreateToggle");
  const assistantButton = studio.querySelector("#sermonV2AssistantToggle");

  if (!createButton || !assistantButton) return;

  if (studio.dataset.panelsBound === "true") return;
  studio.dataset.panelsBound = "true";

  const desktop = window.matchMedia("(min-width: 1201px)");

  let createOpen = true;
  let assistantOpen = false;

  function render() {
    const active = desktop.matches;

    studio.classList.toggle(
      "sermon-v2-create-closed",
      active && !createOpen
    );

    studio.classList.toggle(
      "sermon-v2-assistant-closed",
      active && !assistantOpen
    );

    createButton.setAttribute(
      "aria-expanded",
      String(!active || createOpen)
    );

    assistantButton.setAttribute(
      "aria-expanded",
      String(!active || assistantOpen)
    );

    createButton.setAttribute(
      "aria-controls",
      "mobileInputsTab"
    );

    assistantButton.setAttribute(
      "aria-controls",
      "mobileActionsTab"
    );
  }

  createButton.addEventListener("click", () => {
    if (!desktop.matches) return;
    createOpen = !createOpen;
    render();
  });

  assistantButton.addEventListener("click", () => {
    if (!desktop.matches) return;
    assistantOpen = !assistantOpen;
    render();
  });

  if (desktop.addEventListener) {
    desktop.addEventListener("change", render);
  } else if (desktop.addListener) {
    desktop.addListener(render);
  }

  render();
}

window.bindSermonPanelsV2 = bindSermonPanelsV2;


/* SERMON STUDIO V2 — BATCH 19F */
function arrangeSermonMoreActionsV2() {
  const studio = document.querySelector(".studio-layout");
  if (!studio) return;

  const card = studio.querySelector(
    ".sermon-v2-secondary-actions"
  );

  const host = studio.querySelector(
    "#sermonV2MoreActionsHost"
  );

  if (!card || !host) return;

  if (card.parentElement !== host) {
    host.appendChild(card);
  }
}

window.arrangeSermonMoreActionsV2 =
  arrangeSermonMoreActionsV2;
