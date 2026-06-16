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

    home:
      "/faith/pages/home.html",

    login:
      "/faith/pages/login.html",

    register:
      "/faith/pages/register.html",

    dashboard:
      "/faith/pages/dashboard.html",

    network:
      "/faith/pages/network.html",

    sermon:
      "/faith/pages/sermon.html",

    "member-dashboard":
      "/faith/pages/member-dashboard.html",

    mysermons:
      "/faith/pages/my-sermons.html",

    "edit-profile":
      "/faith/pages/edit-profile.html",

    "admin-approvals":
      "/faith/pages/admin-approvals.html",

    "pastor-profile":
      "/faith/pages/pastor-profile.html"
  };

  // =====================================
  // PROTECTED ROUTES
  // =====================================
  window.protectedRoutes = [

    "dashboard",

    "sermon",

    "network",

    "member-dashboard",

    "mysermons"
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

    const requestId =
      ++__navRequestId;

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
    // CLEANUP PREVIOUS PAGE
    // =====================================
    runPageCleanup();

    try {

      // =====================================
      // AUTH CHECK
      // =====================================
      const token =
        typeof getToken ===
        "function"

          ? getToken()

          : null;

      if (
        protectedRoutes.includes(
          page
        ) &&
        !token
      ) {

        page = "login";
      }

      // =====================================
      // ROLE GUARDS
      // =====================================
      let user =
        window.currentUser;

      if (!user) {

        const storedRole =
          localStorage.getItem(
            "userRole"
          );

        if (storedRole) {

          user = {
            role: storedRole
          };

          window.currentUser =
            user;
        }
      }

      // =====================================
      // MEMBER BLOCK
      // =====================================
      if (user) {

        if (
          user.role === "member" &&
          ["dashboard"]
            .includes(page)
        ) {

          page =
            "member-dashboard";
        }

        // =====================================
        // PASTOR BLOCK
        // =====================================
        if (
          user.role === "pastor" &&
          page ===
          "member-dashboard"
        ) {

          page = "dashboard";
        }
      }

      // =====================================
      // FIND ROUTE
      // =====================================
      const route =
        routes[page];

      if (!route) {

        const app =
          $("app");

        if (app) {

          app.innerHTML =
            `
              <div style="padding:60px;text-align:center;">
                <h2>Page not found</h2>
              </div>
            `;
        }

        return;
      }

      // =====================================
      // SET CURRENT PAGE
      // =====================================
      window.currentPage =
        page;

      // =====================================
      // CLOSE MOBILE MENU
      // =====================================
      const nav =
        document.getElementById(
          "topnav"
        );

      if (nav) {

        nav.classList.remove(
          "mobile-open"
        );
      }

      // =====================================
      // FETCH PAGE
      // =====================================
      const res =
        await fetch(route);

      if (!res.ok) {

        throw new Error(
          `Failed to load route: ${route}`
        );
      }

      if (
        requestId !==
        __navRequestId
      ) {
        return;
      }

              const html =
        await res.text();

      if (
        !html ||
        html.trim().length === 0
      ) {

        throw new Error(
          `Empty HTML returned for ${page}`
        );
      }

      if (
        requestId !==
        __navRequestId
      ) {
        return;
      }

      // =====================================
      // APP CONTAINER
      // =====================================
      const app =
        $("app");

      if (!app) {

        throw new Error(
          "#app container missing"
        );
      }

      // =====================================
      // INJECT PAGE
      // =====================================
            console.log(
          "✅ Injecting page:",
          page
        );

        console.log(
          "📄 HTML length:",
          html.length
        );

        app.innerHTML = html;

      // =====================================
      // REFRESH USER
      // =====================================
      if (
        typeof getCurrentUser ===
        "function"
      ) {

        try {

          const latestUser =
            await getCurrentUser();

          if (latestUser) {

            window.currentUser =
              latestUser;
          }

        } catch (err) {

          console.error(
            "User refresh failed:",
            err
          );
        }
      }

        // =====================================
        // SET CURRENT PAGE
        // =====================================
        window.currentPage =
          page;
      // =====================================
      // NAVBAR
      // =====================================
      if (
        typeof renderNavbar ===
        "function"
      ) {

        renderNavbar();
      }

      // =====================================
      // AUTH FORMS
      // =====================================
      safeRun(
        () => bindAuthForms(),
        "auth"
      );

      safeRun(
        () => bindPasswordToggle(),
        "password"
      );

      if (
      typeof bindSermonStudio ===
      "function"
    ) {

      safeRun(
        () => bindSermonStudio(),
        "sermon"
      );
    }

      // =====================================
      // PAGE LOADERS
      // =====================================

      // DASHBOARD
      if (page === "dashboard") {

        await loadUserInfo();

        await loadDashboard();

        loadTopSermons();

        loadAIInsights();

        startDashboardAutoRefresh();
      }

      // MEMBER DASHBOARD
      if (
        page ===
        "member-dashboard"
      ) {

        await loadUserInfo();

        await loadMemberDashboard();

        startDashboardAutoRefresh();
      }

      // NETWORK
      if (page === "network") {

        await loadUserInfo();

        await loadNetworkPage();
      }

      if (page ==="admin-approvals") {

          await loadUserInfo();

          await loadPastorApplications();
      }

      // SERMON
      if (page === "sermon") {

        await loadUserInfo();

        loadSelectedSermon();
      }

      // MY SERMONS
      // MY SERMONS
      if (page === "mysermons") {

        await loadUserInfo();

        await waitForElement(
          "sermonList"
        );

        await loadMySermons();

        // Shared sermons are pastor-only
        if (
          window.currentUser &&
          window.currentUser.role === "pastor"
        ) {

          await loadSharedSermons();
        }
      }

      // EDIT PROFILE
      if (
        page ===
        "edit-profile"
      ) {

        await loadUserInfo();

        await loadProfilePage();
      }

      // PASTOR PROFILE
      if (
        page ===
        "pastor-profile"
      ) {

        await loadUserInfo();

        await loadPastorProfilePage();
      }

      console.log(
        `✅ Loaded page: ${page}`
      );

    } catch (err) {

            console.error(
        "🔥 Navigation crash:",
        err
      );

      console.error(
        "Failed page:",
        page
      );

      const app =
        $("app");

      if (app) {

        app.innerHTML = `

          <div
            style="
              padding:60px;
              text-align:center;
            "
          >

            <h2>
              Error loading page
            </h2>

            <p>
              ${err.message}
            </p>

          </div>

        `;
      }

    } finally {

      window.isNavigating =
        false;
    }
  }

  // =====================================
  // GLOBAL EXPORT
  // =====================================
  window.navigate =
    navigate;

})();