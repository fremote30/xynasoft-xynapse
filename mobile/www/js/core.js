(() => {

  window.currentUser = window.currentUser || null;

// =====================================
// SERMON LIBRARY PAGINATION
// =====================================
window.SERMONS_PER_PAGE = 10;
window.currentSermonPage = 1;

  // =====================================
  // SAFE RUNNER
  // =====================================
  function safeRun(fn, label = "function") {
    try { fn(); } catch (err) { console.error(`❌ ${label} failed:`, err); }
  }

  // =====================================
  // PASSWORD TOGGLE
  // =====================================
  function bindPasswordToggle() {
    setTimeout(() => {
      document.querySelectorAll(".toggle").forEach(toggle => {
        toggle.onclick = () => {
          const input = toggle.previousElementSibling;
          if (!input) return;
          input.type = input.type === "password" ? "text" : "password";
        };
      });
    }, 100);
  }

// =====================================
// RENDER NAVBAR
// =====================================
function renderNavbar() {

  const nav =
    document.getElementById("topnav");

  if (!nav) {
    return;
  }

  const user =
    window.currentUser;

  let page =
    window.currentPage || "home";

  if (
    page === "edit-profile" ||
    page === "pastor-profile"
  ) {
    page =
      window.currentUser?.role === "member"
        ? "member-dashboard"
        : "dashboard";
  }

  // =====================================
  // SAFE ATTRIBUTE VALUE
  // =====================================
  const escapeAttribute = value =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll('"', "&quot;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");

  const savedSearch =
    window.currentSearchQuery ||
    localStorage.getItem(
      "xynafaith_search_query"
    ) ||
    "";

  // =====================================
  // INLINE ICONS
  // =====================================
  const icons = {

    search: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle
          cx="11"
          cy="11"
          r="7"
        ></circle>

        <path
          d="M20 20l-3.5-3.5"
        ></path>
      </svg>
    `,

    home: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          d="M3 11.5 12 4l9 7.5"
        ></path>

        <path
          d="M5.5 10.5V20h13v-9.5"
        ></path>

        <path
          d="M9.5 20v-6h5v6"
        ></path>
      </svg>
    `,

    dashboard: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <rect
          x="3"
          y="3"
          width="7"
          height="7"
          rx="1"
        ></rect>

        <rect
          x="14"
          y="3"
          width="7"
          height="7"
          rx="1"
        ></rect>

        <rect
          x="3"
          y="14"
          width="7"
          height="7"
          rx="1"
        ></rect>

        <rect
          x="14"
          y="14"
          width="7"
          height="7"
          rx="1"
        ></rect>
      </svg>
    `,

    admin: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          d="M12 3 5 6v5c0 4.8 2.9 8.1 7 10 4.1-1.9 7-5.2 7-10V6l-7-3Z"
        ></path>

        <path
          d="m9 12 2 2 4-4"
        ></path>
      </svg>
    `,

    sermon: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          d="M4 5.5A3.5 3.5 0 0 1 7.5 2H11v17H7.5A3.5 3.5 0 0 0 4 22Z"
        ></path>

        <path
          d="M20 5.5A3.5 3.5 0 0 0 16.5 2H13v17h3.5A3.5 3.5 0 0 1 20 22Z"
        ></path>
      </svg>
    `,

    network: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle
          cx="12"
          cy="8"
          r="3"
        ></circle>

        <circle
          cx="5"
          cy="17"
          r="2.5"
        ></circle>

        <circle
          cx="19"
          cy="17"
          r="2.5"
        ></circle>

        <path
          d="M10 10.5 6.5 14.5"
        ></path>

        <path
          d="m14 10.5 3.5 4"
        ></path>
      </svg>
    `,

    login: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          d="M10 17l5-5-5-5"
        ></path>

        <path
          d="M15 12H3"
        ></path>

        <path
          d="M14 3h6v18h-6"
        ></path>
      </svg>
    `,

    register: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle
          cx="9"
          cy="8"
          r="4"
        ></circle>

        <path
          d="M2.5 21c.7-4.2 3-6.5 6.5-6.5s5.8 2.3 6.5 6.5"
        ></path>

        <path
          d="M19 8v6"
        ></path>

        <path
          d="M16 11h6"
        ></path>
      </svg>
    `,

    logout: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          d="M14 8l4 4-4 4"
        ></path>

        <path
          d="M18 12H7"
        ></path>

        <path
          d="M10 4H4v16h6"
        ></path>
      </svg>
    `
  };

  // =====================================
  // SEARCH BAR
  // =====================================
  const searchBar = `
    <div class="navbar-search">

      <span class="navbar-search-icon">
        ${icons.search}
      </span>

      <input
        id="globalSearch"
        class="navbar-search-input"
        type="search"
        placeholder="Search XynaFaith"
        autocomplete="off"
        aria-label="Search XynaFaith"
        value="${escapeAttribute(savedSearch)}"
      >

      <button
        id="globalSearchButton"
        class="navbar-search-submit"
        type="button"
        aria-label="Submit search"
        title="Search"
      >
        Search
      </button>

    </div>
  `;

  // =====================================
  // REUSABLE NAV ITEM
  // =====================================
  const navItem = (
    targetPage,
    label,
    icon,
    extraClass = ""
  ) => `
    <button
      type="button"
      data-page="${targetPage}"
      class="nav-link ${extraClass}"
      onclick="navigate('${targetPage}')"
      title="${label}"
    >
      <span class="nav-icon">
        ${icon}
      </span>

      <span class="nav-label">
        ${label}
      </span>
    </button>
  `;

  // =====================================
  // GUEST NAV
  // =====================================
  if (!user) {

    nav.innerHTML = `
      ${searchBar}

      <div class="navbar-links">

        ${navItem(
          "home",
          "Home",
          icons.home
        )}

        ${navItem(
          "network",
          "Network",
          icons.network
        )}

        ${navItem(
          "login",
          "Login",
          icons.login,
          "guest-nav-link"
        )}

        ${navItem(
          "register",
          "Register",
          icons.register,
          "guest-nav-link"
        )}

      </div>
    `;
  }

  // =====================================
  // MEMBER NAV
  // =====================================
  else if (
    user.role === "member"
  ) {

    nav.innerHTML = `
      ${searchBar}

      <div class="navbar-links">

        ${navItem(
          "home",
          "Home",
          icons.home
        )}

        ${navItem(
          "member-dashboard",
          "Dashboard",
          icons.dashboard
        )}

        ${navItem(
          "sermon",
          "Sermon Studio",
          icons.sermon
        )}

        ${navItem(
          "mysermons",
          "My Sermons",
          icons.sermon
        )}

        ${navItem(
          "network",
          "Network",
          icons.network
        )}

        <button
          type="button"
          class="nav-link"
          onclick="
            typeof logout === 'function'
            && logout()
          "
          title="Logout"
        >
          <span class="nav-icon">
            ${icons.logout}
          </span>

          <span class="nav-label">
            Logout
          </span>
        </button>

      </div>
    `;
  }

  // =====================================
  // PASTOR / ADMIN NAV
  // =====================================
  else {

    const adminLink =
      user.role === "admin"
        ? navItem(
            "admin-approvals",
            "Admin",
            icons.admin
          )
        : "";

    nav.innerHTML = `
      ${searchBar}

      <div class="navbar-links">

        ${navItem(
          "home",
          "Home",
          icons.home
        )}

        ${navItem(
          "dashboard",
          "Dashboard",
          icons.dashboard
        )}

        ${adminLink}

        ${navItem(
          "sermon",
          "Sermon Studio",
          icons.sermon
        )}

        ${navItem(
          "mysermons",
          "My Sermons",
          icons.sermon
        )}

        ${navItem(
          "network",
          "Network",
          icons.network
        )}

        <button
          type="button"
          class="nav-link"
          onclick="
            typeof logout === 'function'
            && logout()
          "
          title="Logout"
        >
          <span class="nav-icon">
            ${icons.logout}
          </span>

          <span class="nav-label">
            Logout
          </span>
        </button>

      </div>
    `;
  }

  // =====================================
  // ACTIVE PAGE
  // =====================================
  nav
    .querySelectorAll(".nav-link")
    .forEach(link => {
      link.classList.remove(
        "nav-active"
      );
    });

  const active =
    nav.querySelector(
      `[data-page="${page}"]`
    );

  if (active) {
    active.classList.add(
      "nav-active"
    );
  }
  // Refresh mobile drawer
  loadMobileDrawerUser();

}

// =====================================
// RENDER MOBILE DRAWER
// =====================================
function renderMobileDrawer() {

  const drawerLinks =
    document.getElementById(
      "mobileDrawerLinks"
    ) ||
    document.querySelector(
      ".mobile-drawer-links"
    );

  if (!drawerLinks) {
    return;
  }

  const user =
    window.currentUser;

  const drawerItem = (
    page,
    icon,
    label
  ) => `
    <button
      type="button"
      class="mobile-drawer-link"
      data-page="${page}"
      onclick="
        if (
          typeof window.closeMobileMenu ===
          'function'
        ) {
          window.closeMobileMenu();
        }

        navigate('${page}');
      "
    >
      <span
        class="mobile-drawer-link-icon"
        aria-hidden="true"
      >
        ${icon}
      </span>

      <span class="mobile-drawer-link-label">
        ${label}
      </span>
    </button>
  `;

  const logoutItem = `
    <button
      type="button"
      class="
        mobile-drawer-link
        mobile-drawer-logout
      "
      onclick="
        if (
          typeof window.closeMobileMenu ===
          'function'
        ) {
          window.closeMobileMenu();
        }

        if (
          typeof logout ===
          'function'
        ) {
          logout();
        }
      "
    >
      <span
        class="mobile-drawer-link-icon"
        aria-hidden="true"
      >
        🚪
      </span>

      <span class="mobile-drawer-link-label">
        Logout
      </span>
    </button>
  `;

  // =====================================
  // GUEST DRAWER
  // =====================================
  if (!user) {

    drawerLinks.innerHTML = `
      <div class="mobile-drawer-section">

        ${drawerItem(
          "home",
          "🏠",
          "Home"
        )}

        ${drawerItem(
          "search",
          "🔍",
          "Search"
        )}

        ${drawerItem(
          "network",
          "🌍",
          "Discover"
        )}

      </div>

      <div class="mobile-drawer-divider"></div>

      <div class="mobile-drawer-section">

        ${drawerItem(
          "login",
          "🔑",
          "Login"
        )}

        ${drawerItem(
          "register",
          "✍️",
          "Create Account"
        )}

      </div>
    `;

    return;
  }

  // =====================================
  // MEMBER DRAWER
  // =====================================
  if (user.role === "member") {

    drawerLinks.innerHTML = `
      <div class="mobile-drawer-section">

        ${drawerItem(
          "mysermons",
          "📚",
          "My Sermons"
        )}

        ${drawerItem(
          "network",
          "🌍",
          "Discover"
        )}

        ${drawerItem(
          "prayer",
          "🙏",
          "Prayer Activity"
        )}

        ${drawerItem(
          "edit-member-profile",
          "👤",
          "My Profile"
        )}

      </div>

      <div class="mobile-drawer-divider"></div>

      <div class="mobile-drawer-section">
        ${logoutItem}
      </div>
    `;

    return;
  }

  // =====================================
  // ADMIN LINK
  // =====================================
  const adminItem =
    user.role === "admin"
      ? drawerItem(
          "admin-approvals",
          "🛡️",
          "Administration"
        )
      : "";

  // =====================================
  // PASTOR / ADMIN DRAWER
  // =====================================
  drawerLinks.innerHTML = `
    <div class="mobile-drawer-section">

      ${drawerItem(
        "mysermons",
        "📚",
        "My Sermons"
      )}

      ${drawerItem(
        "network",
        "🌍",
        "Discover"
      )}

      ${drawerItem(
        "prayer",
        "🙏",
        "Prayer Activity"
      )}

      ${drawerItem(
        "edit-profile",
        "👤",
        "My Profile"
      )}

      ${adminItem}

    </div>

    <div class="mobile-drawer-divider"></div>

    <div class="mobile-drawer-section">
      ${logoutItem}
    </div>
  `;
}


// =====================================
// RENDER MOBILE BOTTOM NAVIGATION
// =====================================
function renderMobileBottomNav() {

  const bottomNav =
    document.getElementById(
      "mobileBottomNav"
    );

  if (!bottomNav) {
    return;
  }

  const user =
    window.currentUser;

  const currentPage =
    window.currentPage || "home";


  // =====================================
  // CREATE BOTTOM NAV ITEM
  // =====================================
  const bottomNavItem = ({
    route,
    label,
    icon,
    activePages = [],
    extraClass = ""
  }) => {

    const isActive =
      activePages.includes(
        currentPage
      );

    return `
      <button
        type="button"
        class="
          mobile-bottom-nav-item
          ${extraClass}
          ${isActive
            ? "active nav-active"
            : ""}
        "
        data-page="${route}"
        onclick="
          if (
            typeof window.closeMobileMenu ===
            'function'
          ) {
            window.closeMobileMenu();
          }

          navigate('${route}');
        "
        aria-label="${label}"
        ${
          isActive
            ? 'aria-current="page"'
            : ""
        }
      >

        <span
          class="mobile-bottom-nav-icon"
          aria-hidden="true"
        >
          ${icon}
        </span>

        <span
          class="mobile-bottom-nav-label"
        >
          ${label}
        </span>

      </button>
    `;
  };


  // =====================================
  // SVG ICONS
  // =====================================
  const icons = {

    home: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
        focusable="false"
      >
        <path d="M3 11.5 12 4l9 7.5"></path>
        <path d="M5.5 10.5V21h13V10.5"></path>
        <path d="M9.5 21v-6h5v6"></path>
      </svg>
    `,

    dashboard: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
        focusable="false"
      >
        <rect
          x="3"
          y="3"
          width="7"
          height="7"
          rx="1"
        ></rect>

        <rect
          x="14"
          y="3"
          width="7"
          height="7"
          rx="1"
        ></rect>

        <rect
          x="3"
          y="14"
          width="7"
          height="7"
          rx="1"
        ></rect>

        <rect
          x="14"
          y="14"
          width="7"
          height="7"
          rx="1"
        ></rect>
      </svg>
    `,

    search: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
        focusable="false"
      >
        <circle
          cx="11"
          cy="11"
          r="7"
        ></circle>

        <path d="M20 20l-3.5-3.5"></path>
      </svg>
    `,

    studio: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
        focusable="false"
      >
        <path
          d="
            M4 5.5
            A3.5 3.5 0 0 1 7.5 2
            H11
            V19
            H7.5
            A3.5 3.5 0 0 0 4 22
            Z
          "
        ></path>

        <path
          d="
            M20 5.5
            A3.5 3.5 0 0 0 16.5 2
            H13
            V19
            H16.5
            A3.5 3.5 0 0 1 20 22
            Z
          "
        ></path>
      </svg>
    `,

    network: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
        focusable="false"
      >
        <circle
          cx="12"
          cy="7"
          r="3"
        ></circle>

        <circle
          cx="5"
          cy="17"
          r="2.5"
        ></circle>

        <circle
          cx="19"
          cy="17"
          r="2.5"
        ></circle>

        <path d="M10 9.5 6.5 14.5"></path>
        <path d="M14 9.5 17.5 14.5"></path>
      </svg>
    `,

    profile: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
        focusable="false"
      >
        <circle
          cx="12"
          cy="8"
          r="4"
        ></circle>

        <path d="M4 21c1-4.5 4-7 8-7s7 2.5 8 7"></path>
      </svg>
    `,

    register: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
        focusable="false"
      >
        <circle
          cx="9"
          cy="8"
          r="4"
        ></circle>

        <path d="M2.5 21c.8-4.5 3.5-7 6.5-7"></path>
        <path d="M17 10v8"></path>
        <path d="M13 14h8"></path>
      </svg>
    `,

    login: `
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
        focusable="false"
      >
        <path d="M14 4h5a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-5"></path>
        <path d="M10 8l4 4-4 4"></path>
        <path d="M14 12H3"></path>
      </svg>
    `

  };


  // =====================================
  // GUEST NAVIGATION
  // =====================================
  if (!user) {

    bottomNav.dataset.items = "4";

    bottomNav.innerHTML = `

      ${bottomNavItem({
        route: "home",
        label: "Home",
        icon: icons.home,
        activePages: [
          "home"
        ]
      })}


      ${bottomNavItem({
        route: "search",
        label: "Search",
        icon: icons.search,
        activePages: [
          "search"
        ]
      })}


      ${bottomNavItem({
        route: "network",
        label: "Network",
        icon: icons.network,
        activePages: [
          "network",
          "pastor-profile"
        ]
      })}


      ${bottomNavItem({
        route: "login",
        label: "Login",
        icon: icons.login,
        activePages: [
          "login",
          "register",
          "forgot-password",
          "reset-password"
        ]
      })}

    `;

    return;
  }


  // =====================================
  // AUTHENTICATED USER ROUTES
  // =====================================
  bottomNav.dataset.items = "5";


  const dashboardRoute =
    user.role === "member"
      ? "member-dashboard"
      : "dashboard";


  const profileRoute =
    user.role === "member"
      ? "edit-member-profile"
      : "edit-profile";


  // =====================================
  // AUTHENTICATED NAVIGATION
  // =====================================
  bottomNav.innerHTML = `

    ${bottomNavItem({
      route: "home",
      label: "Home",
      icon: icons.home,
      activePages: [
        "home"
      ]
    })}


    ${bottomNavItem({
      route: dashboardRoute,
      label: "Dashboard",
      icon: icons.dashboard,
      activePages: [
        "dashboard",
        "member-dashboard",
        "admin-approvals"
      ]
    })}


    ${bottomNavItem({
      route: "search",
      label: "Search",
      icon: icons.search,
      activePages: [
        "search"
      ]
    })}


    ${bottomNavItem({
      route: "sermon",
      label: "Studio",
      icon: icons.studio,
      activePages: [
        "sermon",
        "mysermons",
        "shared-sermons",
        "sermon-collaboration"
      ]
    })}


    ${bottomNavItem({
      route: "network",
      label: "Network",
      icon: icons.network,
      activePages: [
        "network",
        "pastor-profile"
      ]
    })}

  `;
}

// =====================================
// SET MOBILE DRAWER STATE
// =====================================
function setMobileMenuState(isOpen) {
  const drawer =
    document.getElementById("mobileDrawer");

  const overlay =
    document.getElementById("mobileDrawerOverlay");

  const menuButton =
    document.getElementById("mobileMenuBtn");

  if (!drawer) {
    return;
  }

  drawer.classList.toggle("open", isOpen);

  if (overlay) {
    overlay.classList.toggle("open", isOpen);
    overlay.setAttribute(
      "aria-hidden",
      String(!isOpen)
    );
  }

  document.body.classList.toggle(
    "drawer-open",
    isOpen
  );

  drawer.setAttribute(
    "aria-hidden",
    String(!isOpen)
  );

  if (menuButton) {
    menuButton.setAttribute(
      "aria-expanded",
      String(isOpen)
    );

    menuButton.setAttribute(
      "aria-label",
      isOpen
        ? "Close navigation menu"
        : "Open navigation menu"
    );
  }
}

// =====================================
// TOGGLE MOBILE DRAWER
// =====================================
window.toggleMobileMenu = function () {
  const drawer =
    document.getElementById("mobileDrawer");

  if (!drawer) {
    return;
  }

  const isOpen =
    drawer.classList.contains("open");

  setMobileMenuState(!isOpen);
};

// =====================================
// CLOSE MOBILE DRAWER
// =====================================
window.closeMobileMenu = function () {
  setMobileMenuState(false);
};

// =====================================
// LOAD MOBILE DRAWER USER
// =====================================
function loadMobileDrawerUser() {

    const nameElem =
        document.getElementById("mobileDrawerUserName");

    const roleElem =
        document.getElementById("mobileDrawerUserRole");

    const user =
        window.currentUser;

    // -------------------------
    // Guest
    // -------------------------
    if (!user) {

        if (nameElem)
            nameElem.textContent = "Welcome";

        if (roleElem)
            roleElem.textContent = "Guest";

        renderMobileDrawer();
        renderMobileBottomNav();

        return;
    }

    // -------------------------
    // Display Name
    // -------------------------
    const displayName =
        user.name ||
        user.full_name ||
        user.username ||
        "User";

    if (nameElem)
        nameElem.textContent = displayName;

    // -------------------------
    // Display Role
    // -------------------------
    let role = "";

    switch (user.role) {

        case "admin":
            role = "Administrator";
            break;

        case "pastor":
            role = "Pastor";
            break;

        case "member":
            role = "Member";
            break;

        default:
            role = user.role || "";
    }

    if (roleElem)
        roleElem.textContent = role;

    // -------------------------
    // Refresh drawer
    // -------------------------
    renderMobileDrawer();
    renderMobileBottomNav();
}

// =====================================
// OPEN MOBILE SEARCH
// =====================================
window.openMobileSearch = function () {

  if (
    typeof window.closeMobileMenu ===
    "function"
  ) {
    window.closeMobileMenu();
  }

  navigate("search");
};


    // =====================================
  // AI Disclaimer
  // =====================================
window.showAIDisclaimer = function () {

  alert(
`XynaFaith is an AI-assisted ministry platform.

The platform is designed to support pastors, ministry leaders, and churches—not replace pastoral leadership, biblical discernment, theological study, or the guidance of the Holy Spirit.

All AI-generated content should be reviewed, verified, and prayerfully considered before use in ministry settings.`
  );

};
// =====================================
// CLOSE MOBILE DRAWER WHEN CLICKING OUTSIDE
// =====================================
document.addEventListener(
    "click",
    (e) => {

        const drawer =
            document.getElementById("mobileDrawer");

        const btn =
            document.getElementById("mobileMenuBtn");

        if (!drawer || !btn)
            return;

        if (
            !drawer.contains(e.target) &&
            !btn.contains(e.target)
        ) {

            window.closeMobileMenu();

        }

    }
);

// =====================================
  // Helper Function
  // =====================================
window.safeSermonText = function(content) {

  if (!content) return "Saved sermon";

  // already string
  if (typeof content === "string") return content;

  // object handling (AI sermons)
  if (typeof content === "object") {

    return (
      content.introduction ||
      content.content ||
      content.summary ||
      content.application ||
      content.points?.[0] ||
      content.title ||
      "Saved sermon"
    );
  }

  return "Saved sermon";
};

// =====================================
// GLOBAL EXPORTS
// =====================================
window.safeRun =
  safeRun;

window.bindPasswordToggle =
  bindPasswordToggle;

window.renderNavbar =
  renderNavbar;

window.renderMobileDrawer =
  renderMobileDrawer;

window.renderMobileBottomNav =
  renderMobileBottomNav;

window.loadMobileDrawerUser =
  loadMobileDrawerUser;

})();