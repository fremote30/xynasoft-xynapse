// =====================================
// DASHBOARD.JS
// STEP 1P — DASHBOARD ENGINE
// =====================================

(() => {

  // =====================================
  // SHORTCUT
  // =====================================
  const $ = (id) =>
    document.getElementById(id);

  // =====================================
  // LOAD DASHBOARDPRAYER
  // =====================================
async function loadDashboardPrayerWidget() {
  const container = $("prayerWall");

  if (!container) return;

  container.innerHTML = `<p>Loading recent prayers...</p>`;

  // =========================
  // ANALYTICS — SAFE
  // =========================
  try {
    const analyticsRes = await apiFetch("/api/v1/prayers/analytics");

    if (analyticsRes.ok) {
      const analytics = await analyticsRes.json();

      if ($("dashboardPrayerTotal")) {
        $("dashboardPrayerTotal").textContent = analytics.total_prayers || 0;
      }

      if ($("dashboardPrayerAnswered")) {
        $("dashboardPrayerAnswered").textContent = analytics.answered_prayers || 0;
      }

      if ($("dashboardPrayerToday")) {
        $("dashboardPrayerToday").textContent = analytics.people_praying_today || 0;
      }
    }
  } catch (err) {
    console.warn("Prayer analytics skipped:", err);
  }

  // =========================
  // RECENT PRAYERS — SAFE
  // =========================
  try {
    const prayerRes = await apiFetch("/api/v1/dashboard/recent-prayers");

    if (!prayerRes.ok) {
      throw new Error("Failed to load recent prayers");
    }

    const prayers = await prayerRes.json();

    container.innerHTML = prayers.length
      ? prayers.slice(0, 3).map(p => `
        <div class="dashboard-prayer-item">
          <strong>${p.user_name || "Anonymous"}</strong>
          <p>${typeof p.message === "object" ? JSON.stringify(p.message) : p.message}</p>
          <small>${typeof formatDate === "function" ? formatDate(p.created_at) : ""}</small>
        </div>
      `).join("")
      : `
        <div class="dashboard-prayer-empty">
          <p>No prayers yet.</p>
          <button class="btn-primary" onclick="navigate('prayer')">
            Submit the first prayer
          </button>
        </div>
      `;

  } catch (err) {
    console.error("Prayer widget error:", err);

    container.innerHTML = `
      <p>Could not load Prayer Wall preview.</p>
      <button class="btn-secondary" onclick="navigate('prayer')">
        Open Prayer Wall
      </button>
    `;
  }
}


// =====================================
// LOAD DASHBOARD
// =====================================
async function loadDashboard() {
  try {
    const user = window.currentUser;

    const adminCard = $("adminApplicationsCard");
    const adminStatsSection = $("adminStatsSection");

    if (adminCard && user?.role !== "admin") {
      adminCard.remove();
    }

    if (adminStatsSection && user?.role !== "admin") {
      adminStatsSection.remove();
    }

    if (adminCard) {
      adminCard.style.display = "none";
    }

    if (adminStatsSection) {
      adminStatsSection.style.display = "none";
    }

    if (user && user.role === "admin") {
      if (adminCard) adminCard.style.display = "block";
      if (adminStatsSection) adminStatsSection.style.display = "grid";
      await loadAdminStats();
    }

    if (user) {
      const heroTitle = document.querySelector(".hero-title");
      if (heroTitle) {
        heroTitle.innerHTML = `Welcome back, <span class="highlight">${user.name}</span>!`;
      }

      const heroSub = document.querySelector(".hero-sub");
      if (heroSub) {
        heroSub.textContent = "Manage your sermons and lead your congregation.";
      }
    }

    const summaryRes = await apiFetch("/api/v1/dashboard/summary");

    if (!summaryRes.ok) {
      throw new Error("Summary fetch failed");
    }

    const summary = await summaryRes.json();

    if ($("sermonCount")) {
      $("sermonCount").innerText = summary.total_sermons ?? 0;
    }

    if ($("memberCount")) {
      $("memberCount").innerText = summary.total_members ?? 0;
    }

    if ($("engagementRate")) {
      const rate = summary.engagement ?? 0;
      $("engagementRate").style.width = rate + "%";
      $("engagementRate").textContent = rate + "%";
    }

    const recentContainer = $("recentSermons");

    if (recentContainer) {
      recentContainer.innerHTML = `<p>Loading...</p>`;
    }

    const recentRes = await apiFetch("/api/v1/dashboard/recent-sermons");

    if (recentRes.ok) {
      const recent = await recentRes.json();

      if (recentContainer) {
        recentContainer.innerHTML = recent.length
          ? recent.map(s => `
            <div class="sermon-item clickable" onclick="window.openSermon(${s.id})">
              <h4>${s.title}</h4>
              <p>${window.safeSermonText(s.content).substring(0, 120)}</p>
              <span>Shares: ${s.shares ?? 0}</span>
            </div>
          `).join("")
          : `<p>No recent sermons</p>`;
      }
    }

    await loadTopSermons();
    await loadAIInsights();
    await loadDashboardPrayerWidget();

  } catch (err) {
    console.error("Dashboard load error:", err);
    showToast?.("Failed to load dashboard data", "error");
  }
}

// =====================================
// MEMBER DASHBOARD
// =====================================
async function loadMemberDashboard() {
  try {
    const user = window.currentUser;

    if (!user) return;

    if (user.role === "pastor") {
      navigate("dashboard");
      return;
    }

    const badge = $("pastorStatusBadge");
    const message = $("pastorUpgradeMessage");
    const button = $("upgradePastorBtn");
    const card = $("pastorUpgradeCard");
    const title = $("pastorCardTitle");

    if (badge) {
      if (user.pastor_status === "pending") {
        badge.textContent = "Pending Approval";

        if (message) {
          message.textContent = "Your pastor application is currently under review.";
        }

        if (button) {
          button.disabled = true;
          button.textContent = "Application Pending";
        }

      } else if (user.pastor_status === "rejected") {
        badge.textContent = "Rejected";

        if (title) {
          title.textContent = "Pastor Application Rejected";
        }

        if (message) {
          message.textContent = "Your pastor application was not approved. You may apply again.";
        }

        if (button) {
          button.disabled = false;
          button.textContent = "Apply Again";
        }

      } else if (user.pastor_status === "approved") {
        badge.textContent = "Pastor";

        if (card) {
          card.style.display = "none";
        }

      } else {
        badge.textContent = "Member";
      }
    }

    const nameEl = $("userName");

    if (nameEl) {
      nameEl.textContent = user.name;
    }

    const summaryRes = await apiFetch("/api/v1/dashboard/summary");

    if (summaryRes.ok) {
      const summary = await summaryRes.json();

      if ($("sermonCount")) {
        $("sermonCount").innerText = summary.total_sermons ?? 0;
      }

      if ($("memberCount")) {
        $("memberCount").innerText = summary.total_members ?? 0;
      }

      const engagement = summary.engagement ?? 0;

      if ($("engagementRate")) {
        $("engagementRate").textContent = `${engagement}%`;
      }

      if ($("engagementFill")) {
        $("engagementFill").style.width = `${engagement}%`;
      }
    }

    if (typeof loadMemberFeed === "function") {
      await loadMemberFeed();
    }

    await loadTopSermons();
    await loadAIInsights();
    await loadDashboardPrayerWidget();

  } catch (err) {
    console.error("Member dashboard error:", err);
    showToast?.("Failed to load dashboard", "error");
  }
}

  // =====================================
  // TOP SERMONS
  // =====================================
  async function loadTopSermons() {

    try {

      const res =
        await apiFetch(
          "/api/v1/dashboard/top-sermons"
        );

      if (!res.ok) {

        throw new Error(
          "Failed to fetch top sermons"
        );
      }

      const sermons =
        await res.json();

      const container =
        $("topSermons");

      if (!container) return;

      if (!sermons.length) {

        container.innerHTML =
          "<p>No top sermons yet</p>";

        return;
      }

      container.innerHTML =
        sermons.map(s => `

          <div
            class="
              sermon-item
              clickable
            "

            onclick="
              window.openSermon(${s.id})
            "
          >

            <strong>
              ${s.title}
            </strong>

            <br>

            <small>
              ${window.safeSermonText(s.content).substring(0, 120)}
            </small>

          </div>

        `).join("");

    } catch (err) {

      console.error(
        "Top sermons error:",
        err
      );

      const container =
        $("topSermons");

      if (container) {

        container.innerHTML =
          "<p>Error loading data</p>";
      }
    }
  }

  // =====================================
  // AI INSIGHTS
  // =====================================
  async function loadAIInsights() {

    try {

      const res =
        await apiFetch(
          "/api/v1/dashboard/insights"
        );

      if (!res.ok) {

        throw new Error(
          "Failed to fetch insights"
        );
      }

      const data =
        await res.json();

      const container =
        $("aiInsights");

      if (!container) return;

      if (
        !data.insights ||
        !data.insights.length
      ) {

        container.innerHTML =
          "<p>No insights available yet</p>";

        return;
      }

      container.innerHTML =
        data.insights.map(i => `

          <div class="insight-item">

            ${i}

          </div>

        `).join("");

    } catch (err) {

      console.error(
        "AI insights error:",
        err
      );

      const container =
        $("aiInsights");

      if (container) {

        container.innerHTML =
          "<p>Error loading insights</p>";
      }
    }
  }

  // =====================================
  // CHART RENDER
  // =====================================
  function renderChart(chartData) {

    const canvas =
      $("sermonChart");

    if (!canvas) {

      console.warn(
        "Chart canvas missing"
      );

      return null;
    }

    if (
      typeof Chart ===
      "undefined"
    ) {

      console.warn(
        "Chart.js missing"
      );

      return null;
    }

    if (
      window.sermonChartInstance
    ) {

      window.sermonChartInstance
        .destroy();
    }

    const ctx =
      canvas.getContext("2d");

    window.sermonChartInstance =
      new Chart(ctx, {

        type: "line",

        data: {

          labels:
            chartData?.labels || [],

          datasets: [{

            label:
              "Sermons Created",

            data:
              chartData?.data || [],

            borderWidth: 2,

            tension: 0.4
          }]
        },

        options: {

          responsive: true,

          maintainAspectRatio:
            false
        }
      });

    return window
      .sermonChartInstance;
  }

  // =====================================
  // AUTO REFRESH
  // =====================================
  function startDashboardAutoRefresh() {

    // =========================
    // CLEAR
    // =========================
    if (
      window.dashboardInterval
    ) {

      clearInterval(
        window.dashboardInterval
      );
    }

    // =========================
    // START
    // =========================
    window.dashboardInterval =
        setInterval(async () => {

          const user = window.currentUser;
          if (!user) return;

          // 🚨 STOP AUTO REFRESH ON SERMON PAGES
          if (
            window.currentPage === "mysermons" ||
            window.currentPage === "sermon" ||
            window.currentPage === "network"
          ) {
            return;
          }

          try {

            if (user.role === "pastor") {
              await loadDashboard();
              loadTopSermons();
              loadAIInsights();
            }

            if (user.role === "member") {
              await loadMemberDashboard();
            }

          } catch (err) {
            console.error("Auto refresh error:", err);
          }

        }, 30000);

    // =========================
    // CLEANUP
    // =========================
    if (
      window.pageCleanupTasks
    ) {

      window.pageCleanupTasks
        .push(() => {

          clearInterval(
            window.dashboardInterval
          );
        });
    }
  }

  // =====================================
  // LoadAdminStats
  // =====================================
async function loadAdminStats() {

    try {

        const response =
            await apiFetch(
                "/api/v1/users/admin/stats"
            );

        if (!response.ok) {
            throw new Error(
                "Failed to load admin stats"
            );
        }

        const stats =
            await response.json();

        const memberCount =
            document.getElementById(
                "adminMemberCount"
            );

        const pastorCount =
            document.getElementById(
                "adminPastorCount"
            );

        const pendingCount =
            document.getElementById(
                "pendingApprovalCount"
            );

        const sermonCount =
            document.getElementById(
                "adminSermonCount"
            );

        if (memberCount) {
            memberCount.textContent =
                stats.members || 0;
        }

        if (pastorCount) {
            pastorCount.textContent =
                stats.pastors || 0;
        }

        if (pendingCount) {
            pendingCount.textContent =
                stats.pending_applications || 0;
        }

        if (sermonCount) {
            sermonCount.textContent =
                stats.sermons || 0;
        }

    } catch (error) {

        console.error(
            "Admin stats error:",
            error
        );

    }
}
  // =====================================
  // EXPORTS
  // =====================================
  window.loadDashboard =
    loadDashboard;

  window.loadMemberDashboard =
    loadMemberDashboard;

  window.loadTopSermons =
    loadTopSermons;

  window.loadAIInsights =
    loadAIInsights;

  window.renderChart =
    renderChart;

  window.startDashboardAutoRefresh =
    startDashboardAutoRefresh;

})();