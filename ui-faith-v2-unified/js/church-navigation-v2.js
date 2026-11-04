(() => {
  "use strict";

  const views = Object.freeze({
    home: ["churchHomeSection"],
    community: ["churchCommunitySection"],
    prayer: ["churchPrayerSection"],
    testimonies: ["churchTestimonySection"],
    management: [
      "churchOperationsSection",
      "churchPeopleSection",
      "churchPastoralCareWorkspace"
    ]
  });

  const $ = (id) => document.getElementById(id);

  let activeView = "home";
  let authorizedViews = new Set();

  function getSections(view) {
    return (views[view] || [])
      .map((id) => $(id))
      .filter(Boolean);
  }

  function applyView(view) {
    const content = $("churchSpaceContent");
    const navigation = $("churchSpaceNavigation");

    if (!content || !navigation) return false;
    if (!authorizedViews.has(view)) return false;

    activeView = view;

    Object.entries(views).forEach(([name, ids]) => {
      ids.forEach((id) => {
        const section = $(id);
        if (!section) return;

        section.classList.toggle(
          "xf-church-view-inactive",
          name !== view
        );
      });
    });

    navigation.querySelectorAll("[data-church-view]")
      .forEach((button) => {
        const selected = button.dataset.churchView === view;

        if (selected) {
          button.setAttribute("aria-current", "page");
        } else {
          button.removeAttribute("aria-current");
        }
      });

    return true;
  }

  function initialize(context) {
    const content = $("churchSpaceContent");
    const navigation = $("churchSpaceNavigation");

    if (!content || !navigation || content.hidden) return false;

    const capabilities = context?.capabilities || {};
    const permissions = context?.permissions || [];

    const canManage =
      Boolean(capabilities.can_view_members) ||
      Boolean(capabilities.can_manage_pastoral_care) ||
      (
        Array.isArray(permissions) &&
        permissions.includes("groups.manage")
      );

    authorizedViews = new Set([
      "home",
      "community",
      "prayer",
      "testimonies"
    ]);

    if (canManage) {
      authorizedViews.add("management");
    }

    const managementButton = navigation.querySelector(
      '[data-church-view="management"]'
    );

    if (managementButton) {
      managementButton.hidden = !canManage;
    }

    if (!navigation.dataset.churchNavigationBound) {
      navigation.addEventListener("click", (event) => {
        const button = event.target.closest(
          "[data-church-view]"
        );

        if (!button || !navigation.contains(button)) return;

        const view = button.dataset.churchView;
        if (!authorizedViews.has(view)) return;

        applyView(view);
      });

      navigation.dataset.churchNavigationBound = "1";
    }

    return applyView("home");
  }

  function reset() {
    authorizedViews.clear();
    activeView = "home";

    Object.values(views).flat().forEach((id) => {
      $(id)?.classList.remove("xf-church-view-inactive");
    });

    const navigation = $("churchSpaceNavigation");
    if (navigation) {
      const management = navigation.querySelector(
        '[data-church-view="management"]'
      );
      if (management) management.hidden = true;
    }
  }

  window.XynaFaithChurchNavigationV2 = Object.freeze({
    initialize,
    applyView,
    reset
  });
})();
