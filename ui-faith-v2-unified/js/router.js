// =====================================
// ROUTER.JS
// STEP 1N — ROUTER EXTRACTION
// =====================================

(() => {

  // =====================================
  // SHORTCUT
  // =====================================
  const $ = (id) =>
    document.getElementById(id);

  // =====================================
  // ROUTES
  // =====================================
  window.routes = {
    "ministry-studio":
      "/ui-faith-v2-unified/pages/ministry-studio.html",

    home:
      "/ui-faith-v2-unified/pages/home.html",

    login:
      "/ui-faith-v2-unified/pages/login.html",

    register:
      "/ui-faith-v2-unified/pages/register.html",

    dashboard:
      "/ui-faith-v2-unified/pages/dashboard.html",

    network:
      "/ui-faith-v2-unified/pages/network.html",

    sermon:
      "/ui-faith-v2-unified/pages/sermon.html",

    "sermon-series":
      "/ui-faith-v2-unified/pages/sermon-series.html",

    "bible-study":
      "/ui-faith-v2-unified/pages/bible-study.html",

    devotional:
      "/ui-faith-v2-unified/pages/devotional.html",

    "church-space":
      "/ui-faith-v2-unified/pages/church-space.html",

    xyniva:
      "/ui-faith-v2-unified/pages/xyniva.html",

    "reading-plans":
      "/ui-faith-v2-unified/pages/reading-plans.html",

    "sermon-notes":
      "/ui-faith-v2-unified/pages/sermon-notes.html",

    "member-dashboard":
      "/ui-faith-v2-unified/pages/member-dashboard.html",

    mysermons:
      "/ui-faith-v2-unified/pages/my-sermons.html",

    "edit-profile":
      "/ui-faith-v2-unified/pages/edit-profile.html",

    "edit-member-profile":
      "/ui-faith-v2-unified/pages/edit-member-profile.html",

    "admin-approvals":
      "/ui-faith-v2-unified/pages/admin-approvals.html",

    prayer:
      "/ui-faith-v2-unified/pages/prayer.html",

    "pastor-profile":
      "/ui-faith-v2-unified/pages/pastor-profile.html",

    search:
      "/ui-faith-v2-unified/pages/search.html"
  };

  // =====================================
  // PROTECTED ROUTES
  // =====================================
window.protectedRoutes = [
    "ministry-studio",

    "dashboard",

    "sermon",

    "sermon-series",

    "bible-study",

    "devotional",

    "church-space",

    "xyniva",

    "network",

    "reading-plans",
    "sermon-notes",
    "member-dashboard",

    "edit-member-profile",

    "prayer",

    "mysermons",

    "search"
];

  // =====================================
  // CLEANUP TASKS
  // =====================================
  window.pageCleanupTasks =
    window.pageCleanupTasks || [];

  // =====================================
  // NAVIGATION STATE
  // =====================================
  window.isNavigating = false;

  window.__navigationStack =
    window.__navigationStack || [];

  window.__isBackNavigation = false;

  let __navRequestId = 0;

  // =====================================
  // SAFE RUNNER
  // =====================================
  function safeRun(
    fn,
    label = "function"
  ) {

    try {

      fn();

    } catch (err) {

      console.error(
        `❌ ${label} failed:`,
        err
      );
    }
  }

  // =====================================
  // WAIT FOR ELEMENT
  // =====================================
  async function waitForElement(
    elementId,
    timeout = 3000
  ) {

    const start =
      Date.now();

    while (
      Date.now() - start <
      timeout
    ) {

      const element =
        document.getElementById(
          elementId
        );

      if (element) {
        return element;
      }

      await new Promise(resolve =>
        setTimeout(resolve, 50)
      );
    }

    return null;
  }

  window.waitForElement =
    waitForElement;

  // =====================================
  // PAGE CLEANUP
  // =====================================
  function runPageCleanup() {

    try {

      window.pageCleanupTasks
        .forEach(task => {

          try {

            task();

          } catch (err) {

            console.error(
              "Cleanup task failed:",
              err
            );
          }
        });

    } finally {

      window.pageCleanupTasks = [];
    }
  }

  // =====================================
  // CLEAR DASHBOARD INTERVAL
  // =====================================
  if (
    window.dashboardInterval
  ) {

    clearInterval(
      window.dashboardInterval
    );
  }

  // =====================================
  // MAIN NAVIGATION
  // =====================================
async function navigate(page) {

  const requestId = ++__navRequestId;

  const previousPage =
    window.currentPage || null;

  // =====================================
  // PREVENT DOUBLE NAVIGATION
  // =====================================
  if (
    window.isNavigating &&
    window.currentPage === page
  ) {
    return;
  }

  window.isNavigating = true;

  // =====================================
  // GLOBAL NAV STATE TRACKING (NEW)
  // =====================================
  window.__navState = {
    page,
    requestId,
    timestamp: Date.now()
  };

  // =====================================
// CLEANUP PREVIOUS PAGE
// =====================================
 runPageCleanup();

// =====================================
// STOP PAGE AUTO-REFRESHERS
// =====================================

// Dashboard auto refresh
if (window.dashboardInterval) {
  clearInterval(window.dashboardInterval);
}

// Prayer Wall live updates
if (typeof window.stopPrayerLiveUpdates === "function") {
  window.stopPrayerLiveUpdates();
}

try {

    // =====================================
    // AUTH CHECK
    // =====================================
    const token =
      typeof getToken === "function"
        ? getToken()
        : null;

    if (
      protectedRoutes.includes(page) &&
      !token
    ) {
      page = "login";
    }

    // =====================================
    // ROLE GUARDS
    // =====================================
    let user = window.currentUser;

    if (!user) {
      const storedRole = localStorage.getItem("userRole");

      if (storedRole) {
        user = { role: storedRole };
        window.currentUser = user;
      }
    }

    if (user) {

      if (user.role === "member" && page === "dashboard") {
        page = "member-dashboard";
      }

      if (user.role === "pastor" && page === "member-dashboard") {
        page = "dashboard";
      }

      if (
        page === "admin-approvals" &&
        user.role !== "admin"
      ) {
        page =
          user.role === "member"
            ? "member-dashboard"
            : "dashboard";
      }
    }

    // =====================================
    // FIND ROUTE
    // MOBILE SAFE
    // =====================================

    let route = routes[page];

    if (window.Assets && route) {

        if (route.startsWith("/ui-faith-v2-unified/pages/")) {

            route = Assets.page(
                route.replace("/ui-faith-v2-unified/pages/", "")
            );

        }

    }
    if (!route) {
      const app = $("app");

      if (app) {
        app.innerHTML = `
          <div style="padding:60px;text-align:center;">
            <h2>Page not found</h2>
          </div>
        `;
      }

      return;
    }

    // =====================================
    // SET CURRENT PAGE (IMPORTANT FIX ADDED HERE)
    // =====================================
    window.currentPage = page;

    // 🔥 RESET PAGE STATE FLAGS (CRITICAL FIX)
    window.__mySermonsLoading = false;
    window.__mySermonsLoaded = false;

    // =====================================
    // CLOSE MOBILE MENU
    // =====================================
    const nav = document.getElementById("topnav");

    if (nav) {
      nav.classList.remove("mobile-open");
    }

    // =====================================
    // FETCH PAGE
    // =====================================
    const res = await fetch(route);

    if (!res.ok) {
      throw new Error(`Failed to load route: ${route}`);
    }

    if (requestId !== __navRequestId) return;

    const html = await res.text();

    if (!html || html.trim().length === 0) {
      throw new Error(`Empty HTML returned for ${page}`);
    }

    if (requestId !== __navRequestId) return;

    // =====================================
    // INJECT PAGE
    // =====================================
    const app = $("app");

    if (!app) {
      throw new Error("#app container missing");
    }

    console.log("✅ Injecting page:", page);
    app.innerHTML = html;

    // =====================================
    // REFRESH USER
    // =====================================
    if (typeof getCurrentUser === "function") {
      try {
        const latestUser = await getCurrentUser();

        if (latestUser) {
          window.currentUser = latestUser;
        }
      } catch (err) {
        console.error("User refresh failed:", err);
      }
    }

    window.currentPage = page;

    // =====================================
    // SPA NAVIGATION HISTORY
    // =====================================
    if (
      !window.__isBackNavigation &&
      previousPage &&
      previousPage !== page
    ) {
      window.__navigationStack.push(
        previousPage
      );

      // Keep history bounded.
      if (
        window.__navigationStack.length >
        30
      ) {
        window.__navigationStack.shift();
      }
    }

    window.__isBackNavigation = false;

    // =====================================
    // NAVBAR
    // =====================================
    if (typeof renderNavbar === "function") {
      renderNavbar();
    }

    if (typeof refreshPrayerNotifications === "function") {
      await refreshPrayerNotifications();
    }
    // =====================================
    // AUTH FORMS
    // =====================================
    safeRun(() => bindAuthForms(), "auth");
    safeRun(() => bindPasswordToggle(), "password");
    safeRun(() => bindLoginIdentityFlow(), "login-identity");
    safeRun(() => bindPhoneLoginFlow(), "phone-login");
    safeRun(() => bindRegisterIdentityFlow(), "register-identity");
    safeRun(() => bindPhoneRegisterFlow(), "phone-register");

    if (typeof bindSermonStudio === "function") {
      safeRun(() => bindSermonStudio(), "sermon");
    }

    if (page === "ministry-studio") {
      if (typeof window.initUnifiedMinistryStudio !== "function") {
        throw new Error("Ministry Studio module unavailable");
      }
      await window.initUnifiedMinistryStudio();
    }

    // =====================================
    // PAGE LOADERS
    // =====================================

    if (page === "dashboard") {
      await loadUserInfo();
      await loadDashboard();
      loadTopSermons();
      loadAIInsights();
      startDashboardAutoRefresh();
    }

    if (page === "reading-plans") {
      await window.initMemberReadingPlansV2();
    }

    if (page === "sermon-notes") {
      await window.initMemberSermonNotesV2();
    }

    if (page === "member-dashboard") {
      await loadUserInfo();
      await loadMemberDashboard();
      startDashboardAutoRefresh();
    }

    if (page === "network") {
      await loadUserInfo();
      await loadNetworkPage();
    }

    if (page === "church-space") {
      await loadUserInfo();

      if (
        typeof window.loadChurchSpace ===
        "function"
      ) {
        await window.loadChurchSpace();
      }
    }

    if (page === "edit-member-profile") {
        await loadUserInfo();
        await loadMemberProfilePage();
    }

    if (page === "admin-approvals") {
      await loadUserInfo();
      await loadPastorApplications();
    }

    if (page === "xyniva") {
      await loadUserInfo();

      if (
        typeof window.bindXyniva ===
        "function"
      ) {
        window.bindXyniva();
      }
    }

    if (page === "sermon") {
      if (
        typeof window.initializeSermonPageV2 ===
        "function"
      ) {
        window.initializeSermonPageV2();
          if (typeof window.bindSermonWorkspaceV2 === "function") {
            window.bindSermonWorkspaceV2();
            if (typeof window.bindSermonToolbarV2 === "function") {
              window.bindSermonToolbarV2();
              if (typeof window.arrangeSermonWorkspaceV2 === "function") {
                window.arrangeSermonWorkspaceV2();
                if (typeof window.arrangeSermonMoreActionsV2 === "function") {
                  window.arrangeSermonMoreActionsV2();
                }
                if (typeof window.bindSermonPanelsV2 === "function") {
                  window.bindSermonPanelsV2();
                }
              }
            }
          }
      }

      await loadUserInfo();

      if (
        !window.__openingSavedSermon &&
        typeof window.loadSelectedSermon ===
          "function"
      ) {
        await window.loadSelectedSermon();
      }

      if (
        typeof window.bindXynivaStudio ===
          "function"
      ) {
        window.bindXynivaStudio();
      }
    }
    // =====================================
    // MY SERMONS (FIXED SAFETY)
    // =====================================
    // MY SERMONS
    if (page === "mysermons") {

      console.log("🔥 ENTERED MYSERMONS");

      await loadUserInfo();

      await waitForElement("sermonList");

      // =====================================
      // IGNORE STALE NAVIGATION CALLS
      // =====================================
      const nav = window.__navState;

      if (!nav || nav.page !== "mysermons") {
        console.log("⏭ Skipping stale mysermons load");
        return;
      }

      // =====================================
      // PREVENT DOUBLE LOAD
      // =====================================
      if (window.__mySermonsLoaded) {

        console.log(
          "⏭ My sermons already loaded"
        );

        // still allow shared sermons
        if (
          window.currentUser &&
          window.currentUser.role !== "member"
        ) {

          console.log(
            "🔥 Loading shared sermons (cached page)"
          );

          await loadSharedSermons();
        }

        return;
      }

      console.log("🔥 Loading My Sermons");

      await loadMySermons();

      window.__mySermonsLoaded = true;

      console.log(
        "🔥 USER:",
        window.currentUser
      );

      if (
        window.currentUser &&
        window.currentUser.role !== "member"
      ) {

        console.log(
          "🔥 Loading Shared Sermons"
        );

        await loadSharedSermons();

      } else {

        console.log(
          "⏭ Shared sermons skipped. Role:",
          window.currentUser?.role
        );
      }
    }

    if (page === "edit-profile") {
      await loadUserInfo();
      await loadProfilePage();
    }

    if (page === "pastor-profile") {
      await loadUserInfo();
      await loadPastorProfilePage();
    }

    if (page === "prayer") {
      await loadUserInfo();

      if (typeof loadPrayerWall === "function") {
        await loadPrayerWall();
      }
    }

    // =====================================
    // SEARCH
    // PREMIUM SPA SAFE LOADER
    // =====================================
    if (page === "search") {

        await loadUserInfo();

        // Wait for search.js initialization
        let attempts = 0;

        while (
            typeof window.loadSearchPage !== "function" &&
            attempts < 50
        ) {

            await new Promise(resolve =>
                setTimeout(resolve,100)
            );

            attempts++;
        }


        if (
            typeof window.loadSearchPage === "function"
        ) {

            const query =
              window.currentSearchQuery ||
              localStorage.getItem(
                  "xynafaith_search_query"
              ) ||
              "";


            console.log(
                "🔎 Loading search:",
                query
            );


            await window.loadSearchPage(
                query
            );


        } else {

            console.error(
                "❌ Search module unavailable"
            );

        }
    }

    console.log(`✅ Loaded page: ${page}`);

  } catch (err) {

    console.error("🔥 Navigation crash:", err);

    const app = $("app");

    if (app) {
      app.innerHTML = `
        <div style="padding:60px;text-align:center;">
          <h2>Error loading page</h2>
          <p>${err.message}</p>
        </div>
      `;
    }

  } finally {
    window.isNavigating = false;
  }
}

  // =====================================
  // GLOBAL EXPORT
  // =====================================
  window.navigate =
    navigate;

})();