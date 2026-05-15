(() => {

  const $ = (id) => document.getElementById(id);

  const routes = {
    home: "/faith/pages/home.html",
    login: "/faith/pages/login.html",
    register: "/faith/pages/register.html",
    dashboard: "/faith/pages/dashboard.html",
    network: "/faith/pages/network.html",
    sermon: "/faith/pages/sermon.html",
    member: "/faith/pages/member.html",
    mysermons: "/faith/pages/my-sermons.html"
  };

  let lastGeneratedSermon = null;

  // 🔥 MULTIVERSE STATE
  let sermons = [];
  let currentIndex = 0;

  // 🔥 LOCAL COMMENTS FALLBACK
  let comments = [];


  // ✅ PATCH 1 (ADDED)
  function buildInputByMode() {
    return $("userInput")?.value || "";
  }
 
// =========================
// 🧭 SAFE NAVIGATION (PRODUCTION)
// =========================

let __navRequestId = 0; // prevents race conditions

async function navigate(page) {
  const requestId = ++__navRequestId;

  console.log("➡️ Navigating to:", page);

  try {
    const route = routes[page];

    if (!route) {
      console.error("❌ Route not found:", page);
      document.getElementById("app").innerHTML = `
        <div style="padding:20px;">
          <h2>Page not found</h2>
        </div>
      `;
      return;
    }

    // =========================
    // 🌐 FETCH PAGE HTML
    // =========================
    const res = await fetch(route);

    // If another navigation happened, ignore this one
    if (requestId !== __navRequestId) return;

    if (!res.ok) {
      console.error("❌ Failed to load:", route, res.status);

      document.getElementById("app").innerHTML = `
        <div style="padding:20px;">
          <h2>Failed to load page</h2>
          <p>Status: ${res.status}</p>
        </div>
      `;
      return;
    }

    const html = await res.text();

    if (requestId !== __navRequestId) return;

    document.getElementById("app").innerHTML = html;

    console.log("✅ Page loaded:", page);

    // =========================
    // 👤 SAFE USER LOAD
    // =========================
    let user = null;

    try {
      user = await getCurrentUser();
      console.log("👤 User:", user);
    } catch (err) {
      console.warn("⚠️ Failed to fetch user:", err);
    }

    // =========================
    // 🧠 SAFE UI FUNCTIONS
    // =========================
    safeRun(() => updateNavbar(user), "updateNavbar");
    safeRun(() => setWelcomeName(user), "setWelcomeName");
    safeRun(() => setDashboardUser(user), "setDashboardUser");

    safeRun(() => bindAuthForms(), "bindAuthForms");
    safeRun(() => bindPasswordToggle(), "bindPasswordToggle");
    safeRun(() => bindSermonStudio(), "bindSermonStudio");

  } catch (err) {
    console.error("🔥 Navigation crash:", err);

    document.getElementById("app").innerHTML = `
      <div style="padding:20px;">
        <h2>Something went wrong</h2>
        <p>Please refresh the page</p>
      </div>
    `;
  }
}

async function loadAnalyticsAndInsights() {
  try {

    console.log("🚀 Loading analytics + insights...");

    const token = localStorage.getItem("access_token");

    // =========================
    // 🔥 FETCH WITH AUTH (FIXED PATHS)
    // =========================
    const [analyticsRes, insightsRes] = await Promise.all([
      fetch("/api/dashboard/analytics", {   // ✅ FIXED
        headers: {
          Authorization: `Bearer ${token}`
        }
      }),
      fetch("/api/dashboard/insights", {   // ✅ FIXED
        headers: {
          Authorization: `Bearer ${token}`
        }
      })
    ]);

    const analytics = analyticsRes.ok ? await analyticsRes.json() : {};
    const insights = insightsRes.ok ? await insightsRes.json() : {};

    console.log("📊 Analytics:", analytics);
    console.log("🧠 Insights:", insights);


// =========================
// 🔥 TOP SERMONS (IMPROVED)
// =========================
const topContainer = document.getElementById("topSermons");

if (topContainer) {
  if (!analytics.top_sermons || !analytics.top_sermons.length){
      topContainer.innerHTML = `<p>No top sermons yet</p>`;
  } else {

    topContainer.innerHTML = analytics.top_sermons.map(s => `
      <div class="sermon-item clickable"
           onclick="openSermon(${s.id})">

        <div>
          <h4>${s.title || "Untitled Sermon"}</h4>
          <p>${s.created_at ? formatDate(s.created_at) : "Recent"}</p>
        </div>

        <span>🔥 ${s.shares ?? 0} shares</span>
      </div>
    `).join("");
  }
}

// =========================
// 🔥 OPEN SERMON (IMPROVED)
// =========================
window.openSermon = function (id) {

  if (!id) {
    console.error("❌ Missing sermon ID");
    return;
  }

  console.log("📖 Opening sermon:", id);

  // Store selected sermon
  localStorage.setItem("selected_sermon_id", id);

  // Navigate to sermon studio
  navigate("sermon");

  // Optional UX feedback (can remove if not needed)
  const output = document.getElementById("sermonOutput");
  if (output) {
    output.innerHTML = `
      <div class="loading-state">
        📖 Loading sermon...
      </div>
    `;
  }
};

    // =========================
    // 🧠 AI INSIGHTS
    // =========================
    const insightsContainer = document.getElementById("aiInsights");

    if (insightsContainer) {

      if (!insights.insights || insights.insights.length === 0) {
        insightsContainer.innerHTML = `
          <div class="insight-item">No insights available yet</div>
        `;
      } else {
        insightsContainer.innerHTML = insights.insights.map(i => `
          <div class="insight-item">${i}</div>
        `).join("");
      }
    }

  } catch (err) {
    console.error("❌ Analytics/Insights error:", err);

    // =========================
    // FAILSAFE UI
    // =========================
    const insightsContainer = document.getElementById("aiInsights");
    if (insightsContainer) {
      insightsContainer.innerHTML = `
        <div class="insight-item">⚠️ Unable to load insights</div>
      `;
    }
  }
}

window.navigate = navigate;

function bindAuthForms() {

  // =========================
  // 🔐 LOGIN FORM
  // =========================
  const loginForm = $("loginForm");

  if (loginForm) {
    loginForm.onsubmit = async (e) => {
      e.preventDefault();

      try {
        const res = await fetch("/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: $("email").value,
            password: $("password").value
          })
        });

        const data = await res.json();

        if (!res.ok) {
          alert(data.detail || "Login failed");
          return;
        }

        // =========================
        // 🔥 CRITICAL: STORE TOKEN
        // =========================
        if (data.access_token) {
          localStorage.setItem("access_token", data.access_token);
          console.log("✅ Token stored:", data.access_token);
        } else {
          console.warn("⚠️ No access_token returned");
        }

        // =========================
        // 👤 STORE USER INFO
        // =========================
        if (data.user) {
          localStorage.setItem("user", JSON.stringify(data.user));
          localStorage.setItem("user_name", data.user.name || "User");
          localStorage.setItem("user_role", data.user.role || "member");
        } else {
          // fallback
          localStorage.setItem("user_name", $("email").value.split("@")[0]);
        }

        console.log("👤 User:", data.user);

        // =========================
        // 🚀 REDIRECT BASED ON ROLE
        // =========================
        if (data.user?.role === "member") {
          navigate("member");
        } else {
          navigate("dashboard");
        }

      } catch (err) {
        console.error("❌ Login error:", err);
        alert("Something went wrong during login");
      }
    };
  }

  // =========================
  // 📝 REGISTER FORM
  // =========================
  const registerForm = $("registerForm");

  if (registerForm) {
    registerForm.onsubmit = async (e) => {
      e.preventDefault();

      const name = $("name").value;
      const email = $("email").value;
      const role = $("role").value;
      const password = $("password").value;
      const confirmPassword = $("confirmPassword").value;

      if (password !== confirmPassword) {
        alert("Passwords do not match");
        return;
      }

      try {
        const res = await fetch("/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name,
            email,
            password,
            role
          })
        });

        const data = await res.json();

        if (!res.ok) {
          alert(data.detail || "Registration failed");
          return;
        }

        alert("Account created successfully!");

        // Optional: store basic info
        localStorage.setItem("user_name", name);
        localStorage.setItem("user_role", role);

        navigate("login");

      } catch (err) {
        console.error("❌ Register error:", err);
        alert("Something went wrong");
      }
    };
  }
}

window.openSermon = async function (id) {

  try {

    const res = await fetch(`/sermon/${id}`);
    const sermon = await res.json();

    console.log("Opened sermon:", sermon);

    // 🔥 RENDER INTO OUTPUT (reuse your existing UI)
    if (sermon.content) {
      try {
        const parsed = typeof sermon.content === "string"
          ? JSON.parse(sermon.content)
          : sermon.content;

        streamTextStructured(parsed);
      } catch {
        $("sermonOutput").innerHTML = sermon.content;
      }
    }

    // 🔥 OPTIONAL: scroll to view
    $("sermonOutput")?.scrollIntoView({ behavior: "smooth" });

  } catch (err) {
    console.error("Error opening sermon:", err);
  }
};
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

function setDashboardUser(user) {
  if (!user) return;

  const avatar = $("dashboardAvatar");
  const username = $("dashboardUserName");
  const role = $("userRole");

  // 🔥 helper
  function formatRole(role) {
    return role.charAt(0).toUpperCase() + role.slice(1);
  }

  if (avatar) avatar.innerText = user.name?.charAt(0)?.toUpperCase() || "U";
  if (username) username.innerText = user.name || "User";

  // ✅ FIXED LINE (capitalize)
  if (role && user.role) {
    role.innerText = formatRole(user.role);
  }
}

function setWelcomeName(user) {
  const el = $("welcomeSub");
  if (!el || !user) return;

  el.innerText = `Welcome back, ${user.name} 👋`;
}

  let currentUser = null;
async function getCurrentUser() {
  if (currentUser) return currentUser;

  const token = localStorage.getItem("access_token");
  if (!token) return null;

  try {
    const res = await fetch("/auth/me", {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (!res.ok) {
      console.log("Auth failed:", res.status);
      return null;
    }

    const data = await res.json();

    currentUser = data.user || data;

    return currentUser;

  } catch (err) {
    console.log("Auth error:", err);
    return null;
  }
}

function formatRole(role) {
  return role.charAt(0).toUpperCase() + role.slice(1);
}

  /* ================================
     SERMON STUDIO
  ================================= */
  function bindSermonStudio() {

    if (!$("userInput")) return;

    // Restore draft
    const draft = localStorage.getItem("draft_sermon");
    if (draft) {
      try {
        lastGeneratedSermon = JSON.parse(draft);
        setTimeout(() => {
          streamTextStructured(lastGeneratedSermon);

          // 🔥 LOAD COMMENTS IF EXIST
          if (lastGeneratedSermon?.id) {
            loadComments(lastGeneratedSermon.id);
          }

        }, 100);
      } catch {}
    }

    // Load shared sermon
    const sharedId = localStorage.getItem("view_sermon_id");
    if (sharedId) {
      loadSharedSermon(sharedId);
      localStorage.removeItem("view_sermon_id");
    }

  window.generateSermon = async function () {

  const output = $("sermonOutput");

  output.innerHTML = `
    <div class="loading-state">
      ✨ Generating your sermon...<br>
      📖 Connecting scriptures...<br>
      🙏 Structuring message...
    </div>
  `;

  try {

    const mode = $("mode")?.value || "default";
    const isMultiverse = mode === "multiverse";

    sermons = [];
    const count = isMultiverse ? 3 : 1;

    for (let i = 0; i < count; i++) {

      const res = await fetch("/api/v1/faith/sermon", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          input: buildInputByMode(),
          mode: mode,
          bible: $("bibleInput").value,
          theme: $("themeInput").value,
          denomination: $("denomination").value,
          audience: $("audience").value,
          context: $("context").value,
          service_type: $("serviceType").value,
          tone: $("tone").value,
          duration: $("duration").value,
          variation: i
        })
      });

      const data = await res.json();
      console.log("AI RESPONSE:", data);

      if (data.error) {
        output.innerHTML = "Error generating sermon";
        return;
      }

      sermons.push(data);
    }

    lastGeneratedSermon = sermons[0];

    localStorage.setItem("draft_sermon", JSON.stringify(lastGeneratedSermon));

    renderTabs();
    switchTab(0);

    // 🔥 UX IMPROVEMENT — AUTO SCROLL TO OUTPUT
    setTimeout(() => {
      $("sermonOutput")?.scrollIntoView({ behavior: "smooth" });
    }, 300);

    // 🔥 LOAD COMMENTS AFTER GENERATE
    if (lastGeneratedSermon?.id) {
      loadComments(lastGeneratedSermon.id);
    }

  } catch (err) {
    console.error("Generate error:", err);
    output.innerHTML = "Error generating sermon";
  }
};

    window.uploadSermon = async function () {
      const fileInput = $("sermonFile");
      const status = $("uploadStatus");

      if (!fileInput || !fileInput.files.length) {
        if (status) status.innerText = "Please select a file";
        return;
      }

      const file = fileInput.files[0];
      const formData = new FormData();
      formData.append("file", file);

      if (status) status.innerText = "Uploading...";

      try {
        const res = await fetch("/sermon/upload-sermon", {
          method: "POST",
          body: formData
        });

        const data = await res.json();

        if (data.success) {
          $("userInput").value = data.text;
          if (status) status.innerText = "✅ Sermon loaded";
        }

      } catch {
        if (status) status.innerText = "Error uploading file";
      }
    };
  }

  /* ================================
     MULTIVERSE + STREAM
  ================================= */
  function renderTabs() {
    const tabsEl = document.getElementById("tabs");
    if (!tabsEl) return;

    tabsEl.innerHTML = "";

    sermons.forEach((_, i) => {
      const tab = document.createElement("div");
      tab.className = "tab";
      tab.innerText = `Version ${i+1}`;
      tab.onclick = () => switchTab(i);
      tabsEl.appendChild(tab);
    });
  }

function switchTab(index) {
  currentIndex = index;

  let sermon = sermons[index];

  // =========================
  // 🔥 STEP 1 — HANDLE STRING CASE
  // =========================
  if (typeof sermon === "string") {
    try {
      sermon = JSON.parse(sermon);
    } catch (e) {
      console.error("❌ Failed to parse sermon JSON");
    }
  }

  // =========================
  // 🔥 STEP 2 — NORMALIZE (CRITICAL)
  // =========================
  sermon = normalizeSermon(sermon);

  // =========================
  // 🔥 SAVE CURRENT SERMON
  // =========================
  lastGeneratedSermon = sermon;

  // =========================
  // 🔥 STEP 3 — USE STREAM ONLY (FIX DUPLICATION)
  // =========================
  const output = $("sermonOutput");
  if (output) {
    output.innerHTML = ""; // clear previous content
  }

  // 🔥 STREAM CLEAN OUTPUT
  streamTextStructured(sermon);

  // =========================
  // 🔥 LOAD COMMENTS (UNCHANGED)
  // =========================
  if (sermon?.id) {
    loadComments(sermon.id);
  }

  // =========================
  // 🔥 UPDATE ACTIVE TAB UI
  // =========================
  document.querySelectorAll(".tab").forEach((t, i) => {
    t.classList.toggle("active", i === index);
  });
}

function streamTextStructured(sermon) {

  const output = $("sermonOutput");
  if (!output) return;

  // =========================
  // 🔥 STEP 1 — HANDLE STRING CASE
  // =========================
  if (typeof sermon === "string") {
    try {
      sermon = JSON.parse(sermon);
    } catch (e) {
      console.error("❌ Failed to parse sermon JSON");
      output.innerHTML = sermon;
      return;
    }
  }

  // =========================
  // 🔥 STEP 2 — NORMALIZE DATA
  // =========================
  sermon = normalizeSermon(sermon);

  // =========================
  // 🔥 STEP 3 — CLEAR OUTPUT
  // =========================
  output.innerHTML = "";

  // =========================
  // 🔥 STEP 4 — EXTRACT CONTENT FLEXIBLY (CRITICAL FIX)
  // =========================
  let points =
    sermon.points ||
    sermon.main_points ||
    sermon.body ||
    sermon.outline ||
    sermon.sections ||
    [];

  // =========================
  // 🔥 STEP 5 — BUILD SECTIONS
  // =========================
  let sections = [];

  if (sermon.title) {
    sections.push(`<h2>${sermon.title}</h2>`);
  }

  if (sermon.introduction) {
    sections.push(`
      <h3>📖 Introduction</h3>
      <p>${sermon.introduction}</p>
    `);
  }

  // 🔥 MAIN CONTENT (FIXED)
  if (Array.isArray(points) && points.length > 0) {

    sections.push(`<h3>🧩 Main Points</h3>`);

    points.forEach(p => {

      if (typeof p === "string") {
        sections.push(`<p>${p}</p>`);
      } else {
        sections.push(`
          <div class="sermon-point">
            <h4>${p.title || p.heading || p.topic || ""}</h4>
            <p>${
              p.content ||
              p.message ||
              p.explanation ||
              p.body ||
              Object.values(p).join(" ")
            }</p>
          </div>
        `);
      }

    });
  }

  if (sermon.conclusion) {
    sections.push(`
      <h3>🙏 Conclusion</h3>
      <p>${sermon.conclusion}</p>
    `);
  }

  // =========================
  // 🔥 STEP 6 — STREAM
  // =========================
  let i = 0;

  function next() {
    if (i < sections.length) {
      output.innerHTML += sections[i];
      i++;
      setTimeout(next, 120);
    }
  }

  next();
}

  /* ================================
     COMMENTS (SAFE HYBRID)
  ================================= */

  window.addComment = async function () {

    const input = $("commentInput");
    if (!input || !input.value.trim()) return;

    const text = input.value;
    input.value = "";

    if (lastGeneratedSermon?.id) {
      try {
        await fetch("/api/sermon/comment", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            sermon_id: lastGeneratedSermon.id,
            pastor_id: localStorage.getItem("pastor_id"),
            text: text
          })
        });

        loadComments(lastGeneratedSermon.id);
        return;

      } catch {
        console.log("Fallback to local comments");
      }
    }

    comments.push({
      text: text,
      time: new Date().toLocaleString()
    });

    renderComments();
  };

  function renderComments() {
    const list = $("commentsList");
    if (!list) return;

    if (!comments.length) {
      list.innerHTML = "<p>No comments yet</p>";
      return;
    }

    list.innerHTML = comments.map(c => `
      <div class="comment-item">
        <p>${c.text}</p>
        <small>${c.time}</small>
      </div>
    `).join("");
  }

  async function loadComments(sermonId) {

    const list = $("commentsList");
    if (!list) return;

    try {
      const res = await fetch(`/api/sermon/comments/${sermonId}`);
      const data = await res.json();

      if (!data.length) {
        renderComments();
        return;
      }

      list.innerHTML = data.map(c => `
        <div class="comment-item">
          <p>${c.text}</p>
          <small>Pastor ${c.pastor_id} • ${c.created_at}</small>
        </div>
      `).join("");

    } catch {
      renderComments();
    }
  }

  // 🔥 POLLING
  setInterval(() => {
    if (lastGeneratedSermon?.id) {
      loadComments(lastGeneratedSermon.id);
    }
  }, 5000);

  /*CLEAR SERMON */
  window.clearSermon = function() {

  const output = $("sermonOutput");
  if (!output) return;

  const confirmClear = confirm("Clear current sermon?");
  if (!confirmClear) return;

  output.innerHTML = `
    <div class="empty-state">
      Your sermon will appear here
    </div>
  `;

  // Reset state
  lastGeneratedSermon = null;
  sermons = [];
  currentIndex = 0;

  localStorage.removeItem("draft_sermon");

  const tabs = $("tabs");
  if (tabs) tabs.innerHTML = "";

};
  /* ================================
     🔥 NEW: REFINE FUNCTION (ADDED — SAFE)
  ================================= */
  window.refine = async function(action) {

    if (!lastGeneratedSermon) return alert("Generate sermon first");

    const output = $("sermonOutput");

    output.innerHTML = `
      <div class="loading-state">
        ✨ Refining sermon... (${action})
      </div>
    `;

    try {

      const res = await fetch("/api/sermon/refine", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          action: action,
          content: lastGeneratedSermon
        })
      });

      const data = await res.json();

      console.log("REFINE RESPONSE:", data);

      if (!data) {
        output.innerHTML = "Refine failed";
        return;
      }

      // 🔥 UPDATE CURRENT VERSION
      sermons[currentIndex] = data;
      lastGeneratedSermon = data;

      streamTextStructured(data);

    } catch (err) {
      console.error("Refine error:", err);
      output.innerHTML = "Error refining sermon";
    }
  };
  
    /* ================================
     🔥 DASHBOARD SYSTEM
  ================================= */

function waitForCanvasAndRender(data) {
  const interval = setInterval(() => {
    const canvas = document.getElementById("sermonChart");

    if (canvas) {
      clearInterval(interval);
      console.log("✅ Canvas ready — rendering chart");
      renderChart(data);
    }
  }, 100);
}

async function loadSelectedSermon() {
  try {
    const id = localStorage.getItem("selected_sermon_id");
    if (!id) return;

    const token = localStorage.getItem("access_token");

    const res = await fetch(`/api/v1/sermon/${id}`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (!res.ok) {
      console.error("❌ Failed to load sermon");
      return;
    }

    const data = await res.json();

    console.log("📖 Loaded sermon:", data);

    renderSermon(data); // you already have this

  } catch (err) {
    console.error("❌ Error loading sermon:", err);
  }
}

async function loadDashboard() {
  try {

    // =========================
    // 👤 USER
    // =========================
    const user = await getCurrentUser();

    if (!user) {
      console.warn("No user found");
      return;
    }

    console.log("✅ REAL ROLE FROM BACKEND:", user.role);
    console.log("Chart.js check:", typeof Chart);

    const token = localStorage.getItem("access_token");

    // =========================
    // 🔄 API CALLS
    // =========================
    const [dashboardRes, summaryRes, recentRes] = await Promise.all([
      fetch("/api/v1/dashboard", {
        headers: { Authorization: `Bearer ${token}` }
      }),
      fetch("/api/v1/dashboard/summary", {
        headers: { Authorization: `Bearer ${token}` }
      }),
      fetch("/api/v1/dashboard/recent-sermons", {
        headers: { Authorization: `Bearer ${token}` }
      })
    ]);

    if (!summaryRes.ok) {
      console.error("❌ Summary failed:", summaryRes.status);
      return;
    }

    const dashboardData = dashboardRes.ok ? await dashboardRes.json() : {};
    const summaryData = await summaryRes.json();
    const recentData = recentRes.ok ? await recentRes.json() : [];

    console.log("📊 Dashboard:", dashboardData);
    console.log("📊 Summary:", summaryData);

    // =========================
    // 🔢 METRICS
    // =========================
    const sermonCount = document.getElementById("sermonCount");
    const reachCount = document.getElementById("reachCount");
    const shareCount = document.getElementById("shareCount");
    const engagementRate = document.getElementById("engagementRate");

    if (sermonCount) sermonCount.innerText = summaryData.total_sermons ?? 0;
    if (reachCount) reachCount.innerText = summaryData.members_reached ?? 0;

    const totalShares =
      summaryData.total_shares ??
      summaryData.shares ??
      0;

    if (shareCount) shareCount.innerText = totalShares;

    // =========================
    // 🔥 ENGAGEMENT
    // =========================
    if (engagementRate) {
      const views = dashboardData.total_views ?? 0;

      const rate = views > 0
        ? Math.round((totalShares / views) * 100)
        : 0;

      engagementRate.innerText = rate + "%";
    }

    // =========================
    // 📊 PERFORMANCE CARD
    // =========================
    const perfCard = document.getElementById("performanceCard");

    if (perfCard) {
      perfCard.innerHTML = `
        <h3>📊 Sermon Performance</h3>
        <p><strong>Top Sermon:</strong> ${dashboardData.top_sermon || "N/A"}</p>
        <p>Total Views: ${dashboardData.total_views ?? 0}</p>
        <p>Total Shares: ${totalShares}</p>
      `;
    }

    // =========================
    // 📝 RECENT SERMONS
    // =========================
    const recentContainer = document.getElementById("recentSermons");

    if (recentContainer) {
      if (!recentData.length) {
        recentContainer.innerHTML = `<p>No sermons yet</p>`;
      } else {
        recentContainer.innerHTML = recentData.map(s => `
          <div class="sermon-item clickable"
               onclick="openSermon(${s.id})">

            <div>
              <h4>${s.title}</h4>
              <p>${formatDate(s.created_at)}</p>
            </div>

            <span>Shares: ${s.shares ?? 0}</span>
          </div>
        `).join("");
      }
    }

    // =========================
    // 📈 CHART (IMPROVED VERSION)
    // =========================
    console.log("📊 Dashboard Data:", dashboardData);

    if (!window.Chart) {
      console.error("❌ Chart.js not loaded");
      return;
    }

    const canvas = document.getElementById("sermonChart");

    if (!canvas) {
      console.error("❌ Canvas missing");
      return;
    }

    // ✅ Handle empty data (CRITICAL)
    if (!dashboardData.chart_data || !dashboardData.chart_data.labels?.length) {
      console.warn("⚠️ No chart data — using fallback");

      dashboardData.chart_data = {
        labels: ["No Data"],
        data: [0]
      };
    }

    let chartData = dashboardData.chart_data;

    console.log("📊 FINAL CHART DATA:", chartData);

    // ✅ SPA timing fix
    setTimeout(() => {

      const ctx = canvas.getContext("2d");

      if (window.sermonChartInstance) {
        window.sermonChartInstance.destroy();
      }

      window.sermonChartInstance = new Chart(ctx, {
        type: "line",
        data: {
          labels: chartData.labels,
          datasets: [{
            label: "Sermons",
            data: chartData.data,

            // 🔥 IMPROVED VISIBILITY
            borderColor: "#3b82f6",
            backgroundColor: "rgba(59,130,246,0.2)",
            fill: true,
            pointRadius: 4,
            borderWidth: 3,
            tension: 0.4
          }]
        },
     

      );

      console.log("✅ Chart rendered");

      // 🔥 EMPTY DATA MESSAGE (AFTER RENDER)
      if (chartData.data.every(v => v === 0)) {
        const parent = document.getElementById("sermonChart").parentElement;

        // prevent duplicates on SPA reload
        if (!parent.querySelector(".no-data-msg")) {
          parent.innerHTML += `
            <p class="no-data-msg" style="margin-top:10px; color:#888;">
              No activity yet — create sermons to see trends 📈
            </p>
          `;
        }
      }

    }, 200);

  } catch (err) {
    console.log("❌ Dashboard error:", err);
  }
}


 function renderMemberDashboard() {

  const html = `
    <div class="content">

      <div class="hero">
        <h2>Welcome 👋</h2>
        <p>Follow pastors and grow spiritually</p>
        <button class="primary-btn" onclick="navigate('member')">
          🔍 Explore Pastors
        </button>
      </div>

      <h3 class="section-title">Your Activity</h3>

      <div class="cards">

        <div class="card premium">
          <h4>Following</h4>
          <p id="memberFollowingCount">--</p>
        </div>

        <div class="card premium">
          <h4>Feed</h4>
          <p id="memberFeedCount">--</p>
        </div>

      </div>

    </div>
  `;


  const container = document.getElementById("dashboardContent");
  if (!container) return;

  container.innerHTML = html;

  // OPTIONAL: load counts
       loadMemberStats();
   }



   async function loadMemberStats() {

  const token = localStorage.getItem("access_token");

  try {
    const pastorsRes = await fetch("/api/my-pastors", {
      headers: { Authorization: `Bearer ${token}` }
    });

    const pastors = await pastorsRes.json();

    const feedRes = await fetch("/api/feed", {
      headers: { Authorization: `Bearer ${token}` }
    });

    const feed = await feedRes.json();

    const followingEl = document.getElementById("memberFollowingCount");
    const feedEl = document.getElementById("memberFeedCount");

    if (followingEl) followingEl.innerText = pastors.length;
    if (feedEl) feedEl.innerText = feed.length;

  } catch (err) {
    console.log("Stats error:", err);
  }
}
  /* ================================
     🔥 FALLBACK RENDER (ADDED)
  ================================= */
  document.addEventListener("DOMContentLoaded", () => {

    const el = document.getElementById("dashboardContent");

    if (el && !el.innerHTML.trim()) {
      console.log("Fallback dashboard render triggered");

      renderPastorDashboard({
        stats: {
          sermons: 12,
          drafts: 3,
          members: 245
        },
        recent: [
          { title: "Faith in Trials" },
          { title: "Walking with God" }
        ]
      });
    }

  });

  /* ================================
     OTHER FUNCTIONS (UNCHANGED)
  ================================= */


  window.openPreachMode = function () {
    const output = $("sermonOutput");
    if (!output || !output.innerHTML.trim()) return alert("Generate sermon first");

    const win = window.open("", "_blank");
    win.document.write(`<body>${output.innerHTML}</body>`);
    win.document.close();
  };

  window.shareWithPastor = async function () {
    if (!lastGeneratedSermon) return alert("Generate sermon first");

    const pastorId = prompt("Enter Pastor ID:");
    if (!pastorId) return;

    await fetch("/api/sermon/share", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        from_pastor_id: localStorage.getItem("pastor_id"),
        to_pastor_id: pastorId,
        sermon: lastGeneratedSermon
      })
    });

    alert("Shared!");
  };

  window.saveCurrentSermon = async function () {
  if (!lastGeneratedSermon) return alert("Generate sermon first");

  try {
    const token = localStorage.getItem("access_token");

    if (!token) {
      alert("You are not logged in. Please log in again.");
      return;
    }

    const res = await fetch("/api/sermon/save", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`   // 🔥 CRITICAL FIX
      },
      body: JSON.stringify({
        // ❌ REMOVE pastor_id (backend now uses auth user)
        title: lastGeneratedSermon.title,
        content: lastGeneratedSermon
      })
    });

    const data = await res.json();

    if (!res.ok) {
      console.error("❌ Save failed:", data);
      alert(data.detail || "Failed to save sermon");
      return;
    }

    console.log("✅ Saved:", data);

    localStorage.removeItem("draft_sermon");
    alert("Saved!");

  } catch (err) {
    console.error("❌ Save error:", err);
    alert("Something went wrong while saving");
  }
};

  window.shareWhatsApp = function () {
    if (!lastGeneratedSermon) return alert("Generate sermon first");
    window.open(`https://wa.me/?text=${encodeURIComponent(lastGeneratedSermon.title)}`);
  };

  window.exportPDF = function () {
    if (!lastGeneratedSermon) return alert("Generate sermon first");
    const win = window.open("", "_blank");
    win.document.write(`<pre>${JSON.stringify(lastGeneratedSermon, null, 2)}</pre>`);
    win.print();
  };

  window.logout = function () {
    localStorage.clear();
    navigate("home");
  };

function updateNavbar(user) {
  const nav = document.querySelector(".nav-links");
  if (!nav) return;

  const token = localStorage.getItem("access_token");

  if (token && user) {

    let navLinks = `
      <a href="#" onclick="navigate('home')">Home</a>
      <a href="#" onclick="navigate('dashboard')">Dashboard</a>
    `;

    if (user.role === "pastor") {
      navLinks += `
        <a href="#" onclick="navigate('sermon')">Sermon</a>
        <a href="#" onclick="navigate('mysermons')">My Sermons</a>
      `;
    }

    if (user.role === "member") {
      navLinks += `
        <a href="#" onclick="navigate('member')">Explore</a>
      `;
    }

    navLinks += `
      <div class="nav-user">
        <span class="avatar">${user.name.charAt(0)}</span>
        <span>${user.name}</span>
      </div>

      <button class="btn-nav" onclick="logout()">Logout</button>
    `;

    nav.innerHTML = navLinks;

  } else {
    nav.innerHTML = `
      <a href="#" onclick="navigate('home')">Home</a>
      <a href="#" onclick="navigate('login')">Login</a>
      <a href="#" onclick="navigate('register')">Register</a>
    `;
  }
}

function applyRoleUI() {
  const role = localStorage.getItem("user_role");

  // Hide pastor-specific features for members
  if (role === "member") {
    // Hide elements related to pastor-only features (e.g., sermon creation)
    document.querySelectorAll("[data-role='pastor']").forEach(el => {
      el.style.display = "none";
    });
  }
}

function replyToPrayer(name) {
  alert(`Replying to ${name} (feature coming next)`);
}
window.addEventListener("load", () => navigate("home"));
window.toggleAdvanced = function () {
  const panel = document.getElementById("advancedPanel");
  const arrow = document.getElementById("advArrow");

  if (!panel) return;

  const isOpen = panel.style.display === "block";

  panel.style.display = isOpen ? "none" : "block";
  arrow.innerText = isOpen ? "▸" : "▼";
};

window.scrollToOutput = function () {
  document.getElementById("sermonOutput")
    ?.scrollIntoView({ behavior: "smooth" });
};
function toggleSidebar() {
  document.getElementById("sidebar")?.classList.toggle("open");
}

// =========================
// 🔥 MEMBER SYSTEM
// =========================

// 🔹 LOAD ALL PASTORS
window.loadPastors = async function () {

  const token = localStorage.getItem("access_token");

  const res = await fetch("/api/pastors");
  const pastors = await res.json();

  const container = document.getElementById("pastorList");

  container.innerHTML = "<h3>Discover Pastors</h3>";

  container.innerHTML += pastors.map(p => `
    <div class="card">
      <h3>${p.name}</h3>
      <p>${p.email}</p>
      <button onclick="followPastor(${p.id})">Follow</button>
    </div>
  `).join("");
};

// 🔹 FOLLOW
window.followPastor = async function (pastorId) {

  const token = localStorage.getItem("access_token");

  const res = await fetch(`/api/follow/${pastorId}`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`
    }
  });

  const data = await res.json();

  alert(data.message);
};

window.unfollowPastor = async function (pastorId) {

  const token = localStorage.getItem("access_token");

  const res = await fetch(`/api/unfollow/${pastorId}`, {
    method: "DELETE",
    headers: {
      "Authorization": `Bearer ${token}`
    }
  });

  const data = await res.json();

  alert(data.message);

  loadMyPastors(); // refresh list
};

window.loadMyPastors = async function () {

  const token = localStorage.getItem("access_token");

  const res = await fetch("/api/my-pastors", {
    headers: {
      "Authorization": `Bearer ${token}`
    }
  });

  const pastors = await res.json();

  const container = document.getElementById("myPastorList");

  if (!pastors.length) {
    container.innerHTML = "<p>You are not following anyone yet</p>";
    return;
  }

  container.innerHTML = "<h3>My Pastors</h3>";

  container.innerHTML += pastors.map(p => `
    <div class="card">
      <h3>${p.name}</h3>
      <p>${p.email}</p>
      <button onclick="unfollowPastor(${p.id})">Unfollow</button>
    </div>
  `).join("");
};
// 🔹 LOAD FEED

window.loadFeed = async function () {

  const token = localStorage.getItem("access_token");

  const res = await fetch("/api/feed", {
    headers: { Authorization: `Bearer ${token}` }
  });

  const sermons = await res.json();

  const container = document.getElementById("feedList");

  if (!sermons.length) {
    container.innerHTML = "<p>No sermons yet</p>";
    return;
  }

  container.innerHTML = "<h3>🔥 Your Feed</h3>";

  container.innerHTML += sermons.map(s => `
    <div class="feed-card">

      <div class="feed-header">
        <div class="avatar">${(s.author_id || "P").toString().charAt(0)}</div>
        <div>
          <strong>Pastor ${s.author_id}</strong>
          <p class="muted">Recent Sermon</p>
        </div>
      </div>

      <h3>${s.title}</h3>

      <p>${(s.content || "").slice(0, 250)}...</p>

      <div class="feed-actions">
        <button onclick="alert('Liked')">❤️</button>
        <button onclick="alert('Saved')">🔖</button>
      </div>

    </div>
  `).join("");
};


function normalizeSermon(sermon) {

  if (!sermon) return sermon;

  // =========================
  // 🔥 INTRO
  // =========================
  if (typeof sermon.introduction === "object") {
    sermon.introduction = Object.values(sermon.introduction).join(" ");
  }

  // =========================
  // 🔥 CONCLUSION
  // =========================
  if (typeof sermon.conclusion === "object") {
    sermon.conclusion = Object.values(sermon.conclusion).join(" ");
  }

  // =========================
  // 🔥 FIND MAIN CONTENT (CRITICAL FIX)
  // =========================
  let points =
    sermon.points ||
    sermon.main_points ||
    sermon.body ||
    sermon.outline ||
    sermon.sections ||
    [];

  // =========================
  // 🔥 NORMALIZE POINTS
  // =========================
  if (Array.isArray(points)) {
    sermon.points = points.map(p => {
      if (typeof p === "string") return p;

      return {
        title: p.title || p.heading || p.topic || "",
        content:
          p.content ||
          p.message ||
          p.explanation ||
          p.body ||
          Object.values(p).join(" ")
      };
    });
  } else {
    sermon.points = [];
  }

  return sermon;
}

function formatSermon(sermon) {
  if (!sermon) return "<p>No sermon generated</p>";

  return `
    <h2>${sermon.title || "Untitled Sermon"}</h2>

    <h3>📖 Introduction</h3>
    <p>${sermon.introduction || ""}</p>

    <h3>🧩 Main Points</h3>
    ${(sermon.points || []).map(p => `
      <div class="sermon-point">
        <h4>${p.title || ""}</h4>
        <p>${p.content || ""}</p>
      </div>
    `).join("")}

    <h3>🙏 Conclusion</h3>
    <p>${sermon.conclusion || ""}</p>
  `;
}


navigate("home");
})();