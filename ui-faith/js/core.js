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
    const nav = document.getElementById("topnav");
    if (!nav) return;

    const user = window.currentUser;
    let page = window.currentPage || "home";

    if (page === "edit-profile" || page === "pastor-profile") {
      page = window.currentUser?.role === "member" ? "member-dashboard" : "dashboard";
    }

    // ================= GUEST NAV =================
    if (!user) {
      nav.innerHTML = `
        <button data-page="home" class="nav-link" onclick="navigate('home')">Home</button>
        <button data-page="network" class="nav-link" onclick="navigate('network')">Network</button>
        <button class="btn-secondary" onclick="navigate('login')">Login</button>
        <button class="btn-primary" onclick="navigate('register')">Register</button>
      `;
    }
    // ================= MEMBER NAV =================
    else if (user.role === "member") {
      nav.innerHTML = `
        <button data-page="home" class="nav-link" onclick="navigate('home')">Home</button>
        <button data-page="member-dashboard" class="nav-link" onclick="navigate('member-dashboard')">Dashboard</button>
         <button data-page="sermon" class="nav-link" onclick="navigate('sermon')">Sermon Studio</button>
        <button data-page="mysermons" class="nav-link" onclick="navigate('mysermons')">My Sermons</button>
        <button data-page="network" class="nav-link" onclick="navigate('network')">Network</button>
        <button class="btn-secondary" onclick="typeof logout === 'function' && logout()">Logout</button>
      `;
    }
    // ================= PASTOR / ADMIN NAV =================
    else {
      const adminLink = user.role === "admin"
        ? `<button data-page="admin-approvals" class="nav-link" onclick="navigate('admin-approvals')">Admin</button>`
        : "";
      nav.innerHTML = `
        <button data-page="home" class="nav-link" onclick="navigate('home')">Home</button>
        <button data-page="dashboard" class="nav-link" onclick="navigate('dashboard')">Dashboard</button>
        ${adminLink}
        <button data-page="sermon" class="nav-link" onclick="navigate('sermon')">Sermon Studio</button>
        <button data-page="mysermons" class="nav-link" onclick="navigate('mysermons')">My Sermons</button>
        <button data-page="network" class="nav-link" onclick="navigate('network')">Network</button>
        <button class="btn-secondary" onclick="typeof logout === 'function' && logout()">Logout</button>
      `;
    }

    document.querySelectorAll(".nav-link").forEach(link => link.classList.remove("nav-active"));
    const active = nav.querySelector(`[data-page="${page}"]`);
    if (active) active.classList.add("nav-active");
  }


  function renderMobileDrawer() {
    const drawerLinks = document.querySelector(".mobile-drawer-links");
    if (!drawerLinks) return;

    const user = window.currentUser;
    drawerLinks.innerHTML = "";

    if (!user) {
        // Guest links
        drawerLinks.innerHTML = `
            <button onclick="navigate('home')">🏠 Home</button>
            <button onclick="navigate('network')">🌐 Network</button>
            <button onclick="navigate('login')">🔑 Login</button>
            <button onclick="navigate('register')">📝 Register</button>
        `;
    } else if (user.role === "member") {
        // Member links
        drawerLinks.innerHTML = `
            <button onclick="navigate('home')">🏠 Home</button>
            <button onclick="navigate('member-dashboard')">📊 Dashboard</button>
            <button onclick="navigate('sermon')">✍️ Sermon Studio</button>
            <button onclick="navigate('mysermons')">📚 My Sermons</button>
            <button onclick="navigate('network')">🌐 Network</button>
            <button onclick="logout()">🧱 Logout</button>
        `;
    } else {
        // Pastor / Admin
        const adminBtn = user.role === "admin"
            ? `<button onclick="navigate('admin-approvals')">👑 Admin</button>` 
            : "";
        drawerLinks.innerHTML = `
            <button onclick="navigate('home')">🏠 Home</button>
            <button onclick="navigate('dashboard')">📊 Dashboard</button>
            ${adminBtn}
            <button onclick="navigate('sermon')">✍️ Sermon Studio</button>
            <button onclick="navigate('mysermons')">📚 My Sermons</button>
            <button onclick="navigate('network')">🌐 Network</button>
            <button onclick="navigate('settings')">⚙️ Settings</button>
            <button onclick="logout()">🧱 Logout</button>
        `;
    }
}
  // =====================================
  // MOBILE MENU
  // =====================================
  //function toggleMobileMenu() {
    //const nav = document.getElementById("topnav");
    //if (!nav) return;
    //nav.classList.toggle("mobile-open");
  //}

  // =====================================
// MOBILE DRAWER TOGGLE
// =====================================
window.toggleMobileMenu = function () {
    const drawer = document.getElementById("mobileDrawer");
    if (!drawer) return;

    drawer.classList.toggle("open");
};

    // =====================================
  // MOBILE DRAWER
  // =====================================
function loadMobileDrawerUser() {
    const nameElem = document.getElementById("mobileDrawerUserName");
    const roleElem = document.getElementById("mobileDrawerUserRole");
    const user = window.currentUser;

    if (nameElem) {
        nameElem.textContent = user?.name || "Guest";
    }

    if (roleElem) {
        roleElem.textContent = user?.role
            ? user.role.charAt(0).toUpperCase() + user.role.slice(1)
            : "";
    }

    // 🔹 Ensure drawer links match user state
    if (typeof renderMobileDrawer === "function") {
        renderMobileDrawer();
    }
}

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
      document.getElementById(
        "mobileDrawer"
      );

    const btn =
      document.getElementById(
        "mobileMenuBtn"
      );

    if (
      !drawer ||
      !btn
    ) return;

    if (
      !drawer.contains(e.target) &&
      !btn.contains(e.target)
    ) {

      drawer.classList.remove(
        "open"
      );
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
  window.safeRun = safeRun;
  window.bindPasswordToggle = bindPasswordToggle;
  window.renderNavbar = renderNavbar;
  window.toggleMobileMenu = toggleMobileMenu;
  window.loadMobileDrawerUser = loadMobileDrawerUser;
})();