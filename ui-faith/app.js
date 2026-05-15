(() => {

  const $ = (id) => document.getElementById(id);

  // =========================
  // ROUTES
  // =========================
const routes = {
  home: "/faith/pages/home.html",
  login: "/faith/pages/login.html",
  register: "/faith/pages/register.html",
  dashboard: "/faith/pages/dashboard.html",
  network: "/faith/pages/network.html",
  sermon: "/faith/pages/sermon.html",
  "member-dashboard": "/faith/pages/member-dashboard.html", // ✅ FIXED
  mysermons: "/faith/pages/my-sermons.html",
  "edit-profile": "/faith/pages/edit-profile.html",
  "pastor-profile": "/faith/pages/pastor-profile.html"
};


const protectedRoutes = [
  "dashboard",
  "sermon",
  "network",
  "member-dashboard", // ✅ ADD THIS
  "mysermons"
];

  let currentUser = null;
  let __navRequestId = 0;

  function isAuthenticated() {
    return !!localStorage.getItem("access_token");
  }

  function safeRun(fn, label = "function") {
    try { fn(); }
    catch (err) { console.error(`❌ ${label} failed:`, err); }
  }
 // =========================
// 🔔 TOAST
// =========================
window.showToast = function (message, type = "success") {

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerText = message;

  document.body.appendChild(toast);

  setTimeout(() => toast.classList.add("show"), 50);

  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
};

function handleAuthSuccess(data) {
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  
  localStorage.setItem("userRole", data.user.role);
  localStorage.setItem("user",JSON.stringify(data.user));
  window.currentUser = data.user;

  if (typeof renderNavbar === "function") renderNavbar();

  if (data.user.role === "member") {
    navigate("member-dashboard");
  } else {
    navigate("dashboard");
  }

  showToast(`Welcome ${data.user.name} 👋`, "success");
}

  // =========================
  // 🔥 STEP-FRONTEND: API FETCH (AUTO REFRESH)
  // =========================
// =========================
// API FETCH (TOKEN-AWARE + REFRESH)
// =========================
async function apiFetch(url, options = {}) {
  try {
    const token = localStorage.getItem("access_token");

    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    // First attempt
    let res = await fetch(url, { ...options, headers });

    // If unauthorized → try refresh
    if (res.status === 401) {
      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) {
        logout();
        return res;
      }

      const refreshRes = await fetch("/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (refreshRes.ok) {
        const data = await refreshRes.json();
        localStorage.setItem("access_token", data.access_token);

        // Retry original request
        const retryHeaders = {
          "Content-Type": "application/json",
          ...(options.headers || {}),
          Authorization: `Bearer ${data.access_token}`,
        };
        return fetch(url, { ...options, headers: retryHeaders });
      } else {
        logout();
        return res;
      }
    }

    return res;
  } catch (err) {
    console.error("❌ apiFetch error:", err);
    throw err;
  }
}

  // =========================
  // so it doesn’t keep running:
  // =========================

    if (window.dashboardInterval) {
    clearInterval(window.dashboardInterval);
  }
  // =========================
  // NAVIGATION
  // =========================
// =========================
// GLOBAL NAVIGATION FUNCTION
// =========================
//let __navRequestId = 0;
async function navigate(page) {
  const requestId = ++__navRequestId;

  // =========================
  // 🔐 AUTH CHECK
  // =========================
  const token = localStorage.getItem("access_token");

  if (protectedRoutes.includes(page) && !token) {
    page = "login";
  }

  // =========================
  // 🔥 HARD ROLE SYNC
  // =========================
  let user = window.currentUser;

  if (!user) {
    const storedRole = localStorage.getItem("userRole");
    if (storedRole) {
      user = { role: storedRole };
      window.currentUser = user;
    }
  }

  // =========================
  // 👤 ROLE GUARD
  // =========================
  if (user) {
    // ❌ MEMBER trying to access pastor routes
    if (user.role === "member" && ["dashboard", "sermon"].includes(page)) {
      console.warn("🚫 Member blocked from:", page);
      page = "member-dashboard";
    }

    // ❌ PASTOR trying to access member dashboard
    if (user.role === "pastor" && page === "member-dashboard") {
      console.warn("🚫 Pastor blocked from member dashboard");
      page = "dashboard";
    }
  }

  try {
    const route = routes[page];

    if (!route) {
      $("app").innerHTML = "<h2>Page not found</h2>";
      return;
    }

    // =========================
    // SET CURRENT PAGE FOR ACTIVE NAV
    // =========================
    window.currentPage = page;

    const res = await fetch(route);
    if (requestId !== __navRequestId) return;

    const html = await res.text();
    if (requestId !== __navRequestId) return;

    $("app").innerHTML = html;

    // =========================
    // 🔁 FORCE ROLE BEFORE NAVBAR
    // =========================
    const storedRole = localStorage.getItem("userRole");

    if (!window.currentUser && storedRole) {
      window.currentUser = { role: storedRole };
    }

    const latestUser = await getCurrentUser();
    if (latestUser) window.currentUser = latestUser;

    // ✅ NOW SAFE TO RENDER NAVBAR
    renderNavbar();

    // =========================
    // SAFE INIT
    // =========================
    safeRun(() => bindAuthForms(), "auth");
    safeRun(() => bindPasswordToggle(), "password");
    safeRun(() => bindSermonStudio(), "sermon");

    // =========================
    // 📊 PASTOR DASHBOARD
    // =========================
    if (page === "dashboard") {
      await loadUserInfo();
      await loadDashboard();
      loadTopSermons();
      loadAIInsights();
      startDashboardAutoRefresh();
    }

    // =========================
    // 👥 MEMBER DASHBOARD
    // =========================
    if (page === "member-dashboard") {
      await loadUserInfo();
      await loadMemberDashboard();
      startDashboardAutoRefresh();
    }

    // =========================
    // 🌐 NETWORK PAGE
    // =========================
    if (page === "network") {
      await loadUserInfo();
      await loadNetworkPage();
    }

    // =========================
    // ✍️ SERMON STUDIO
    // =========================
    if (page === "sermon") {
      await loadUserInfo();
      loadSelectedSermon();
    }

    // =========================
    // EDIT PROFILE
    // =========================
    if (page === "edit-profile") {
      await loadUserInfo();
      await loadProfilePage();
    }

    // =========================
    // 👤 PUBLIC PASTOR PROFILE
    // =========================
    if (page === "pastor-profile") {
      await loadUserInfo();
      await loadPastorProfilePage();
    }

  } catch (err) {
    console.error("🔥 Navigation crash:", err);
    $("app").innerHTML = `<h2>Error loading page</h2>`;
  }
}
 
  function openSermon(id) {
     // Save selected sermon
     localStorage.setItem("selected_sermon_id", id);

     // Navigate to sermon page
     navigate("sermon");
  }

  async function loadSelectedSermon() {
      const id = localStorage.getItem("selected_sermon_id");

      if (!id) return;

      try {
          const res = await apiFetch(`/sermon/${id}`);
          const data = await res.json();

          // 🔥 Inject into your editor/output
          if ($("sermonOutput")) {
               $("sermonOutput").innerHTML = `
               <h2>${data.title}</h2>
               <div>${data.content}</div>
           `;
          }

    } catch (err) {
    console.error("Load sermon error:", err);
  }
}
  window.navigate = navigate;

  // =========================
  // 🔥 UPDATED: USE apiFetch
  // =========================
async function getCurrentUser() {
  try {
    const token = localStorage.getItem("access_token");
    if (!token) return null;

    const res = await apiFetch("/auth/me");
    if (!res.ok) return null;

    const user = await res.json();
    window.currentUser = user; // ✅ Store globally
    localStorage.setItem("userRole", user.role); // persist role
    return user;
  } catch (err) {
    console.error("❌ getCurrentUser error:", err);
    return null;
  }
}

// =========================
// AUTH FORMS
// =========================
function bindAuthForms() {

  const loginForm = $("loginForm");
  if (loginForm) {
    loginForm.onsubmit = async (e) => {
      e.preventDefault();

      const errorEl = $("loginError");
      if (errorEl) errorEl.style.display = "none";

      try {
        const res = await apiFetch("/auth/login", {
          method: "POST",
          body: JSON.stringify({
            email: $("email").value,
            password: $("password").value
          })
        });

        const data = await res.json();

        if (!res.ok) {
          showToast(data.detail || "Invalid login credentials", "error");
          if (errorEl) {
            errorEl.innerText = data.detail || "Login failed";
            errorEl.style.display = "block";
          }
          return;
        }
        handleAuthSuccess(data);

      } catch (err) {
        console.error("Login error:", err);
        if (errorEl) {
          errorEl.innerText = "Something went wrong";
          errorEl.style.display = "block";
        }
        showToast("Login failed", "error");
      }
    };
  }

  const registerForm = $("registerForm");
  if (registerForm) {
    registerForm.onsubmit = async (e) => {
      e.preventDefault();

      const errorEl = $("registerError");
      if (errorEl) errorEl.style.display = "none";

      const password = $("password").value;
      const confirm = $("confirmPassword").value;

      if (password !== confirm) {
        if (errorEl) {
          errorEl.innerText = "Passwords do not match";
          errorEl.style.display = "block";
        }
        return;
      }

      try {
        const res = await apiFetch("/auth/register", {
          method: "POST",
          body: JSON.stringify({
            name: $("name").value,
            email: $("email").value,
            password,
            
          })
        });

        if (!res.ok) {
          const data = await res.json();
          if (errorEl) {
            errorEl.innerText = data.detail || "Registration failed";
            errorEl.style.display = "block";
          }
          showToast(data.detail || "Registration failed", "error");
          return;
        }

        // Auto-login after registration
        const loginRes = await apiFetch("/auth/login", {
          method: "POST",
          body: JSON.stringify({
            email: $("email").value,
            password
          })
        });

        const loginData = await loginRes.json();

         handleAuthSuccess(loginData);
      } catch (err) {
        console.error("Registration error:", err);
        if (errorEl) {
          errorEl.innerText = "Something went wrong";
          errorEl.style.display = "block";
        }
        showToast("Registration failed", "error");
      }
    };
  }
}

// =========================
// PASSWORD TOGGLE (SHOW/HIDE)
// =========================
function bindPasswordToggle() {
  setTimeout(() => {
    document.querySelectorAll(".toggle").forEach(toggle => {
      toggle.onclick = () => {
        const input = toggle.previousElementSibling;
        input.type = input.type === "password" ? "text" : "password";
      };
    });
  }, 100);
}

// =========================
// SPA INIT
// =========================
/*document.addEventListener("DOMContentLoaded", async () => {
  // Render navbar on first load
  renderNavbar();

  // Populate currentUser if token exists
  await getCurrentUser();

  // Bind auth forms
  bindAuthForms();
  bindPasswordToggle();

  // Default page load
  if (typeof navigate === "function") navigate("home");
});*/
 

  function updateNavbar(user) {
    const nav = document.querySelector(".nav-links");
    if (!nav) return;

    if (user) {
      nav.innerHTML = `
        <a onclick="navigate('home')">Home</a>
        <a onclick="navigate('dashboard')">Dashboard</a>
        <a onclick="navigate('network')">Network</a>
        <button onclick="logout()">Logout</button>
      `;
    } else {
      nav.innerHTML = `
        <a onclick="navigate('home')">Home</a>
        <a onclick="navigate('login')">Login</a>
        <a onclick="navigate('register')">Register</a>
      `;
    }
  }


  // =========================
// DASHBOARD LOADER FUNCTION
// =========================

async function loadDashboard() {
  try {
    // =========================
    // WELCOME USER
    // =========================
    const user = window.currentUser;
    if (user) {
      const heroTitle = document.querySelector(".hero-title");
      if (heroTitle) heroTitle.innerHTML = `Welcome back, <span class="highlight">${user.name}</span>!`;

      const heroSub = document.querySelector(".hero-sub");
      if (heroSub) heroSub.textContent = "Manage your sermons and lead your congregation.";
    }

    // =========================
    // SUMMARY METRICS
    // =========================
    const summaryRes = await apiFetch("/api/v1/dashboard/summary");
    if (!summaryRes.ok) throw new Error("Summary fetch failed");
    const summary = await summaryRes.json();

    $("sermonCount") && ($("sermonCount").innerText = summary.total_sermons ?? 0);
    $("memberCount") && ($("memberCount").innerText = summary.total_members ?? 0);
    if ($("engagementRate")) {
      const rate = summary.engagement ?? 0;
      $("engagementRate").style.width = rate + "%";
      $("engagementRate").textContent = rate + "%";
    }

    // =========================
    // RECENT SERMONS
    // =========================
    const recentContainer = $("recentSermons");
    if (recentContainer) recentContainer.innerHTML = `<p>Loading...</p>`;
    const recentRes = await apiFetch("/api/v1/dashboard/recent-sermons");
    if (recentRes.ok) {
      const recent = await recentRes.json();
      if (recentContainer) {
        recentContainer.innerHTML = recent.length
          ? recent.map(s => `<div class="sermon-item clickable" onclick="openSermon(${s.id})">
              <h4>${s.title}</h4>
              <p>${formatDate(s.created_at)}</p>
              <span>Shares: ${s.shares ?? 0}</span>
            </div>`).join("")
          : `<p>No recent sermons</p>`;
      }
    }

    // =========================
    // TOP SERMONS
    // =========================
    const topContainer = $("topSermons");
    if (topContainer) topContainer.innerHTML = `<p>Loading...</p>`;
    try {
      const topRes = await apiFetch("/api/v1/dashboard/top-sermons");
      if (topRes.ok) {
        const topSermons = await topRes.json();
        if (topContainer) {
          topContainer.innerHTML = topSermons.length
            ? topSermons.map((s, i) => `<p class="${i===0?'highlighted-item':''}"><strong>${s.title}</strong><br>Shares: ${s.shares ?? 0}</p>`).join("")
            : `<p>No top sermons yet</p>`;
        }
      }
    } catch (e) { topContainer && (topContainer.innerHTML = `<p>Failed to load top sermons</p>`); }

    // =========================
    // AI INSIGHTS
    // =========================
    const aiContainer = $("aiInsights");
    if (aiContainer) aiContainer.innerHTML = `<p>Analyzing...</p>`;
    try {
      const insightsRes = await apiFetch("/api/v1/dashboard/insights");
      if (insightsRes.ok) {
        const insights = await insightsRes.json();
        if (aiContainer) {
          aiContainer.innerHTML = insights.length
            ? insights.map((i, idx) => `<p class="${idx===0?'highlighted-item':''}">${i.message}</p>`).join("")
            : `<p>No insights yet</p>`;
        }
      }
    } catch (e) { aiContainer && (aiContainer.innerHTML = `<p>Failed to load insights</p>`); }

    // =========================
    // PRAYER WALL
    // =========================
    const prayerContainer = $("prayerWall");
    if (prayerContainer) prayerContainer.innerHTML = `<p>Loading recent prayers...</p>`;
    try {
      const prayerRes = await apiFetch("/api/v1/dashboard/recent-prayers");
      if (prayerRes.ok) {
        const prayers = await prayerRes.json();
        prayerContainer.innerHTML = prayers.length
          ? prayers.map(p => `<div class="prayer-item">
              <strong>${p.user_name}</strong> <span class="timestamp">(${formatDate(p.created_at)})</span>: ${p.message}
            </div>`).join("")
          : `<p>No prayers yet</p>`;
      }
    } catch (e) { prayerContainer && (prayerContainer.innerHTML = `<p>Failed to load prayers</p>`); }

  } catch (err) {
    console.error("❌ Dashboard load error:", err);
    showToast?.("Failed to load dashboard data", "error");
  }
}

// =========================
//MEMBER LOAD FUNCTION
// =========================
async function loadMemberDashboard() {

  try {

    const user = window.currentUser;

    if (!user) return;

    // =========================
    // USER NAME
    // =========================
    const nameEl = document.getElementById(
      "userName"
    );

    if (nameEl) {
      nameEl.textContent = user.name;
    }

    // =========================
    // SUMMARY
    // =========================
    const summaryRes = await apiFetch(
      "/api/v1/dashboard/summary"
    );

    if (summaryRes.ok) {

      const summary = await summaryRes.json();

      // =========================
      // SERMON COUNT
      // =========================
      if ($("sermonCount")) {

        $("sermonCount").innerText =
          summary.total_sermons ?? 0;
      }

      // =========================
      // FOLLOWING COUNT
      // =========================
      if ($("memberCount")) {

        $("memberCount").innerText =
          summary.total_members ?? 0;
      }

      // =========================
      // ENGAGEMENT
      // =========================
      const engagement =
        summary.engagement ?? 0;

      if ($("engagementRate")) {

        $("engagementRate").textContent =
          `${engagement}%`;
      }

      if ($("engagementFill")) {

        $("engagementFill").style.width =
          `${engagement}%`;
      }
    }

    // =========================
    // MEMBER FEED
    // =========================
    await loadMemberFeed();

    // =========================
    // TOP SERMONS
    // =========================
    const topRes = await apiFetch(
      "/api/v1/dashboard/top-sermons"
    );

    if (topRes.ok) {

      const data = await topRes.json();

      if ($("topSermons")) {

        $("topSermons").innerHTML =
          data.length

            ? data.map((s, i) => `

              <div
                class="
                  sermon-item
                  ${i === 0 ? "highlighted" : ""}
                "
              >

                <strong>
                  ${s.title}
                </strong>

              </div>

            `).join("")

            : `
              <p>No sermons yet</p>
            `;
      }
    }

    // =========================
    // AI INSIGHTS
    // =========================
    const aiRes = await apiFetch(
      "/api/v1/dashboard/insights"
    );

    if (aiRes.ok) {

      const insights = await aiRes.json();

      if ($("aiInsights")) {

        $("aiInsights").innerHTML =
          insights.length

            ? insights.map((i, idx) => `

              <div
                class="
                  insight-item
                  ${idx === 0 ? "highlighted" : ""}
                "
              >

                ${i.message}

              </div>

            `).join("")

            : `
              <p>No insights available</p>
            `;
      }
    }

    // =========================
    // PRAYER WALL
    // =========================
    const prayerRes = await apiFetch(
      "/api/v1/dashboard/member-prayers"
    );

    if (prayerRes.ok) {

      const prayers = await prayerRes.json();

      if ($("prayerWall")) {

        $("prayerWall").innerHTML =
          prayers.length

            ? prayers.map(p => `

              <div class="prayer-item">

                <strong>
                  ${p.user_name}
                </strong>

                <small>
                  ${formatDate(p.created_at)}
                </small>

                <p>
                  ${p.message}
                </p>

              </div>

            `).join("")

            : `
              <p>No prayers yet</p>
            `;
      }
    }

  } catch (err) {

    console.error(
      "Member dashboard error:",
      err
    );

    showToast?.(
      "Failed to load dashboard",
      "error"
    );
  }
}
// =========================
// CHART RENDERING FUNCTION
// =========================

function renderChart(chartData) {
  const ctx = document.getElementById("sermonChart").getContext("2d");

  return new Chart(ctx, {
    type: "line",
    data: {
      labels: chartData.labels,
      datasets: [{
        label: "Sermons Created",
        data: chartData.data,
        borderWidth: 2,
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  });
}

  // =========================
// MEMBER DASHBOARD LOADER FUNCTION
// =========================

async function loadMemberFeed() {

  try {

    // =========================
    // LOAD FOLLOW-BASED FEED
    // =========================
    const res = await apiFetch(
      "/api/v1/pastors/feed"
    );

    if (!res.ok) {
      throw new Error(
        "Failed to load member feed"
      );
    }

    const data = await res.json();

    const container = $("memberFeed");

    if (!container) return;

    // =========================
    // EMPTY FEED
    // =========================
    if (!data.length) {

      container.innerHTML = `

        <div class="feature-card">

          <h3>
            Your feed is empty
          </h3>

          <p>
            Follow pastors from the Network page
            to personalize your feed.
          </p>

          <button
            class="btn-primary"
            onclick="navigate('network')"
          >
            Explore Network
          </button>

        </div>

      `;

      return;
    }

    // =========================
    // RENDER FEED
    // =========================
    container.innerHTML = data.map(s => `

      <div
        class="feature-card sermon-feed-card"
      >

        <h3>
          ${s.title}
        </h3>

        <small>
          By ${s.pastor_name}
          •
          ${formatDate(s.created_at)}
        </small>

        <p>
          ${(s.content || "").substring(0, 200)}...
        </p>

        <button
          class="btn-secondary"
          onclick="openSermon(${s.id})"
        >
          Read Sermon
        </button>

      </div>

    `).join("");

  } catch (err) {

    console.error(
      "Feed error:",
      err
    );

    const container = $("memberFeed");

    if (container) {

      container.innerHTML = `

        <div class="feature-card">

          <h3>
            Unable to load feed
          </h3>

          <p>
            Please try again later.
          </p>

        </div>

      `;
    }
  }
}


async function loadNetworkPage() {

  try {

    // =========================
    // LOAD TOP SERMONS
    // =========================
    await loadTopSermons();

    // =========================
    // LOAD AI INSIGHTS
    // =========================
    await loadAIInsights();

    // =========================
    // LOAD PASTORS
    // =========================
    await loadPastors();

    // =========================
    // LOAD SUMMARY STATS
    // =========================
    const summaryRes = await apiFetch(
      "/api/v1/dashboard/summary"
    );

    if (summaryRes.ok) {

      const summary = await summaryRes.json();

      // =========================
      // TOTAL SERMONS
      // =========================
      if ($("sermonCount")) {

        $("sermonCount").innerText =
          summary.total_sermons ?? 0;
      }

      // =========================
      // TOTAL MEMBERS
      // =========================
      if ($("memberCount")) {

        $("memberCount").innerText =
          summary.total_members ?? 0;
      }
    }

    // =========================
    // LOAD PRAYER WALL
    // =========================
    const prayerRes = await apiFetch(
      "/api/v1/dashboard/recent-prayers"
    );

    if (prayerRes.ok) {

      const prayers = await prayerRes.json();

      if ($("prayerWall")) {

        $("prayerWall").innerHTML =
          prayers.length

            ? prayers.map(p => `

              <div class="prayer-item">

                <strong>
                  ${p.user_name}
                </strong>

                <small>
                  ${formatDate(p.created_at)}
                </small>

                <p>
                  ${p.message}
                </p>

              </div>

            `).join("")

            : `
              <p>
                No prayer activity yet
              </p>
            `;
      }
    }

  } catch (err) {

    console.error(
      "Network page error:",
      err
    );

    showToast?.(
      "Failed to load network page",
      "error"
    );
  }
}

async function loadPastors() {

  try {

    const res = await apiFetch(
      "/api/v1/pastors"
    );

    if (!res.ok) {
      throw new Error(
        "Failed to load pastors"
      );
    }

    const pastors = await res.json();

    const container = $("pastorGrid");

    if (!container) return;

    // =========================
    // EMPTY STATE
    // =========================
    if (!pastors.length) {

      container.innerHTML = `
        <div class="feature-card">
          <h3>No pastors yet</h3>
          <p>Pastors will appear here.</p>
        </div>
      `;

      return;
    }

    // =========================
    // RENDER PASTORS
    // =========================
    container.innerHTML = pastors.map(pastor => `

      <div class="feature-card pastor-card clickable" onclick="openPastorProfile(${pastor.id})">
        <div class="icon">⛪</div>

        <h3>${pastor.name}</h3>

        <p>
          ${pastor.followers} followers
        </p>

        <button
          class="${
            pastor.is_following
              ? 'btn-secondary'
              : 'btn-primary'
          }"

          onclick="
            ${
              pastor.is_following
                ? `unfollowPastor(${pastor.id})`
                : `followPastor(${pastor.id})`
            }
          "
        >
          ${
            pastor.is_following
              ? "Following"
              : "Follow"
          }
        </button>

      </div>

    `).join("");

  } catch (err) {

    console.error(
      "Pastor load error:",
      err
    );
  }
}

// =========================
// FOLLOW PASTOR
// =========================
window.followPastor = async function (pastorId) {

  try {

    const res = await apiFetch(
      `/api/v1/pastors/${pastorId}/follow`,
      {
        method: "POST"
      }
    );

    const data = await res.json();

    if (!res.ok) {
      throw new Error(
        data.detail || "Failed to follow pastor"
      );
    }

    // =========================
    // SUCCESS
    // =========================
    showToast(
      "Pastor followed successfully",
      "success"
    );

    // =========================
    // RELOAD PASTORS
    // =========================
    await loadPastors();

  } catch (err) {

    console.error(
      "Follow pastor error:",
      err
    );

    showToast(
      err.message || "Follow failed",
      "error"
    );
  }
};


// =========================
// UNFOLLOW PASTOR
// =========================
window.unfollowPastor = async function (pastorId) {

  try {

    const res = await apiFetch(
      `/api/v1/pastors/${pastorId}/unfollow`,
      {
        method: "DELETE"
      }
    );

    const data = await res.json();

    if (!res.ok) {
      throw new Error(
        data.detail || "Failed to unfollow pastor"
      );
    }

    // =========================
    // SUCCESS
    // =========================
    showToast(
      "Pastor unfollowed",
      "success"
    );

    // =========================
    // RELOAD
    // =========================
    await loadPastors();

  } catch (err) {

    console.error(
      "Unfollow pastor error:",
      err
    );

    showToast(
      err.message || "Unfollow failed",
      "error"
    );
  }
};

// =========================
// PROFILE PAGE
// =========================
async function loadProfilePage() {

  try {

    const res = await apiFetch(
      "/api/v1/pastor-profile/me"
    );

    if (!res.ok) {
      throw new Error(
        "Failed to load profile"
      );
    }

    const profile = await res.json();

    // =========================
    // LOAD DATA
    // =========================
    if ($("profileBio")) {
      $("profileBio").value =
        profile.bio || "";
    }

    if ($("churchName")) {
      $("churchName").value =
        profile.church_name || "";
    }

    if ($("ministryFocus")) {
      $("ministryFocus").value =
        profile.ministry_focus || "";
    }

    if ($("profileLocation")) {
      $("profileLocation").value =
        profile.location || "";
    }

    if ($("profileWebsite")) {
      $("profileWebsite").value =
        profile.website || "";
    }

    // =========================
    // SAVE HANDLER
    // =========================
    const form = $("profileForm");

    if (form) {

      form.onsubmit = async (e) => {

        e.preventDefault();

        try {

          const saveRes = await apiFetch(
            "/api/v1/pastor-profile/me",
            {
              method: "PUT",

              body: JSON.stringify({
                bio: $("profileBio")?.value,
                church_name: $("churchName")?.value,
                ministry_focus: $("ministryFocus")?.value,
                location: $("profileLocation")?.value,
                website: $("profileWebsite")?.value
              })
            }
          );

          const data = await saveRes.json();

          if (!saveRes.ok) {
            throw new Error(
              data.detail || "Save failed"
            );
          }

          showToast?.(
            "Profile updated successfully",
            "success"
          );

        } catch (err) {

          console.error(
            "Profile save error:",
            err
          );

          showToast?.(
            err.message || "Save failed",
            "error"
          );
        }
      };
    }

  } catch (err) {

    console.error(
      "Profile page error:",
      err
    );

    showToast?.(
      "Failed to load profile",
      "error"
    );
  }
}

async function loadPastorProfilePage() {

  try {

    const pastorId =
      localStorage.getItem(
        "selected_pastor_id"
      );

    if (!pastorId) {
      return;
    }

    // =========================
    // LOAD PROFILE
    // =========================
    const res = await apiFetch(
      `/api/v1/pastor-profile/${pastorId}`
    );

    if (!res.ok) {

      throw new Error(
        "Failed to load profile"
      );
    }

    const profile = await res.json();

    // =========================
    // PROFILE INFO
    // =========================
    if ($("pastorName")) {

      $("pastorName").textContent =
        profile.name || "Pastor";
    }

    if ($("pastorBio")) {

      $("pastorBio").textContent =
        profile.bio || "Ministry profile";
    }

    if ($("churchNameView")) {

      $("churchNameView").textContent =
        profile.church_name || "—";
    }

    if ($("ministryFocusView")) {

      $("ministryFocusView").textContent =
        profile.ministry_focus || "—";
    }

    if ($("locationView")) {

      $("locationView").textContent =
        profile.location || "—";
    }

    if ($("followersView")) {

      $("followersView").textContent =
        profile.followers || 0;
    }

    // =========================
    // SERMONS
    // =========================
    const sermonsContainer =
      $("pastorSermons");

    if (sermonsContainer) {

      sermonsContainer.innerHTML =
        profile.sermons?.length

          ? profile.sermons.map(s => `

            <div
              class="
                feature-card
                clickable
              "

              onclick="
                openSermon(${s.id})
              "
            >

              <h3>
                ${s.title}
              </h3>

              <small>
                ${formatDate(s.created_at)}
              </small>

            </div>

          `).join("")

          : `
            <p>
              No sermons yet
            </p>
          `;
    }

  } catch (err) {

    console.error(
      "Pastor profile error:",
      err
    );

    showToast?.(
      "Failed to load profile",
      "error"
    );
  }
}
// =========================
// LOGOUT
// =========================
window.logout = async function () {

  try {

    await fetch("/auth/logout", {
      method: "POST",

      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify({
        refresh_token: localStorage.getItem("refresh_token")
      })
    });

  } catch (err) {

    console.error("Logout error:", err);
  }

  // =========================
  // STOP AUTO REFRESH
  // =========================
  if (window.dashboardInterval) {
    clearInterval(window.dashboardInterval);
  }

  // =========================
  // CLEAR STORAGE
  // =========================
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("userRole");
  localStorage.removeItem("user");

  // =========================
  // CLEAR USER
  // =========================
  window.currentUser = null;

  // =========================
  // UPDATE NAVBAR
  // =========================
  if (typeof renderNavbar === "function") {
    renderNavbar();
  }

  // =========================
  // REDIRECT
  // =========================
  navigate("home");

  // =========================
  // TOAST
  // =========================
  showToast(
    "Logged out successfully",
    "success"
  );
};
  // =========================
  // 🔥 UPDATED: USE apiFetch
  // =========================
  function bindSermonStudio() {
    if (!$("userInput")) return;

    window.generateSermon = async function () {

      const output = $("sermonOutput");
      output.innerHTML = "Generating...";

      try {
        const res = await apiFetch("/api/v1/faith/sermon", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            input: $("userInput").value
          })
        });

        const data = await res.json();

        output.innerHTML = `
          <h3>${data.title || "Sermon"}</h3>
          <p>${data.introduction || ""}</p>
        `;

      } catch {
        output.innerHTML = "Error generating sermon";
      }
    };
  }

async function loadUserInfo() {
  try {
    const user = await getCurrentUser();

    if (!user) return;

    // Save globally
    window.currentUser = user;

    if ($("userName")) {
      $("userName").textContent = user.name;
    }

  } catch (e) {
    console.error("User load error:", e);
  }
}

async function loadTopSermons() {
  try {
    const res = await apiFetch("/api/v1/dashboard/top-sermons");

    if (!res.ok) throw new Error("Failed to fetch top sermons");

    const sermons = await res.json();

    const container = $("topSermons");

    if (!container) return;

    if (!sermons.length) {
      container.innerHTML = "<p>No top sermons yet</p>";
      return;
    }

    container.innerHTML = sermons.map(s => `
      <div class="sermon-item clickable" onclick="openSermon(${s.id})">
        <strong>${s.title}</strong><br>
        <small>Shares: ${s.shares}</small>
      </div>
    `).join("");

  } catch (err) {
    console.error("Top sermons error:", err);

    const container = $("topSermons");
    if (container) {
      container.innerHTML = "<p>Error loading data</p>";
    }
  }
}

async function loadAIInsights() {
  try {
    const res = await apiFetch("/api/v1/dashboard/insights");

    if (!res.ok) throw new Error("Failed to fetch insights");

    const data = await res.json();

    const container = $("aiInsights");

    if (!container) return;

    if (!data.insights || !data.insights.length) {
      container.innerHTML = "<p>No insights available yet</p>";
      return;
    }

    container.innerHTML = data.insights.map(i => `
      <div class="insight-item">
        ${i}
      </div>
    `).join("");

  } catch (err) {
    console.error("AI insights error:", err);

    const container = $("aiInsights");
    if (container) {
      container.innerHTML = "<p>Error loading insights</p>";
    }
  }
}

function startDashboardAutoRefresh() {
  if (window.dashboardInterval) {
    clearInterval(window.dashboardInterval);
  }

  window.dashboardInterval = setInterval(async () => {
    const user = window.currentUser;

    if (!user) return;

    try {
      // =========================
      // 👨‍🏫 PASTOR DASHBOARD
      // =========================
      if (user.role === "pastor") {
        await loadDashboard();

        // These are part of pastor dashboard UI
        loadTopSermons();
        loadAIInsights();
      }

      // =========================
      // 👥 MEMBER DASHBOARD
      // =========================
      if (user.role === "member") {
        await loadMemberDashboard();
        // ❌ DO NOT call loadTopSermons / loadAIInsights here
        // Member dashboard already handles its own rendering
      }

    } catch (err) {
      console.error("Auto refresh error:", err);
    }

  }, 30000);
}

window.upgradeToPastor = async function () {

  try {

    const token = localStorage.getItem("access_token");

    const response = await fetch(
      "/api/v1/users/upgrade-to-pastor",
      {
        method: "POST",

        headers: {
          "Authorization": `Bearer ${token}`
        }
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Upgrade failed");
    }

    // =========================
    // UPDATE CURRENT USER
    // =========================
    window.currentUser = data.user;

    // =========================
    // UPDATE LOCAL STORAGE
    // =========================
    localStorage.setItem(
      "user",
      JSON.stringify(data.user)
    );

    // 🔥 IMPORTANT
    localStorage.setItem(
      "userRole",
      data.user.role
    );

    // =========================
    // SUCCESS TOAST
    // =========================
    showToast(
      "🎉 You are now a Pastor!",
      "success"
    );

    // =========================
    // REFRESH NAVBAR
    // =========================
    if (typeof renderNavbar === "function") {
      renderNavbar();
    }

    // =========================
    // LOAD PASTOR DASHBOARD
    // =========================
    navigate("dashboard");

  } catch (err) {

    console.error(err);

    showToast(
      err.message || "Upgrade failed",
      "error"
    );
  }
};

window.openPastorProfile = function (pastorId) {
  localStorage.setItem(
    "selected_pastor_id",
    pastorId
  );
  navigate("pastor-profile");
};

document.addEventListener("click", (e) => {

  if (e.target.id === "upgradePastorBtn") {
    upgradeToPastor();
  }

});

})();