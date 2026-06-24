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
  // LOAD DASHBOARD
  // =====================================
  async function loadDashboard() {

    try {

      // =========================
      // USER
      // =========================
      const user =
        window.currentUser;

      // =========================
      // ADMIN CARD
      // =========================
const adminCard =
    $("adminApplicationsCard");

const adminStatsSection =
    $("adminStatsSection");

// TEMP DEBUG FIX
if (
    adminCard &&
    user?.role !== "admin"
) {

    adminCard.remove();
}

if (
    adminStatsSection &&
    user?.role !== "admin"
) {

    adminStatsSection.remove();
}
// =====================================
// ALWAYS RESET ADMIN UI
// =====================================
if (adminCard) {

    adminCard.style.display =
        "none";
}

if (adminStatsSection) {

    adminStatsSection.style.display =
        "none";
}

// =====================================
// ADMIN ONLY
// =====================================
if (
    user &&
    user.role === "admin"
) {

    if (adminCard) {

        adminCard.style.display =
            "block";
    }

    if (adminStatsSection) {

        adminStatsSection.style.display =
            "grid";
    }

    await loadAdminStats();
}

      if (user) {

        const heroTitle =
          document.querySelector(
            ".hero-title"
          );

        if (heroTitle) {

          heroTitle.innerHTML =
            `Welcome back, <span class="highlight">${user.name}</span>!`;
        }

        const heroSub =
          document.querySelector(
            ".hero-sub"
          );

        if (heroSub) {

          heroSub.textContent =
            "Manage your sermons and lead your congregation.";
        }
      }

      // =========================
      // SUMMARY
      // =========================
      const summaryRes =
        await apiFetch(
          "/api/v1/dashboard/summary"
        );

      if (!summaryRes.ok) {

        throw new Error(
          "Summary fetch failed"
        );
      }

      const summary =
        await summaryRes.json();

      // =========================
      // COUNTS
      // =========================
      if ($("sermonCount")) {

        $("sermonCount").innerText =
          summary.total_sermons ?? 0;
      }

      if ($("memberCount")) {

        $("memberCount").innerText =
          summary.total_members ?? 0;
      }

      // =========================
      // ENGAGEMENT
      // =========================
      if ($("engagementRate")) {

        const rate =
          summary.engagement ?? 0;

        $("engagementRate").style.width =
          rate + "%";

        $("engagementRate").textContent =
          rate + "%";
      }

      // =========================
      // RECENT SERMONS
      // =========================
      const recentContainer =
        $("recentSermons");

      if (recentContainer) {

        recentContainer.innerHTML =
          `<p>Loading...</p>`;
      }

      const recentRes =
        await apiFetch(
          "/api/v1/dashboard/recent-sermons"
        );

      if (recentRes.ok) {

        const recent =
          await recentRes.json();

        if (recentContainer) {

           recentContainer.innerHTML =
              recent.length

                ? recent.map(s => `

                  <div
                    class="
                      sermon-item
                      clickable
                    "
                    onclick="
                      window.openSermon(${s.id})
                    "
                  >

                    <h4>
                      ${s.title}
                    </h4>

                    <p>
                      ${window.safeSermonText(s.content).substring(0, 120)}
                    </p>

                    <span>
                      Shares: ${s.shares ?? 0}
                    </span>

                  </div>

                `).join("")

                : `
                  <p>No recent sermons</p>
                `;

        
        }
      }

      // =========================
      // TOP SERMONS
      // =========================
      await loadTopSermons();

      // =========================
      // AI INSIGHTS
      // =========================
      await loadAIInsights();

      // =========================
      // PRAYER WALL
      // =========================
      const prayerContainer =
        $("prayerWall");

      if (prayerContainer) {

        prayerContainer.innerHTML =
          `<p>Loading recent prayers...</p>`;
      }

      try {

        const prayerRes =
          await apiFetch(
            "/api/v1/dashboard/recent-prayers"
          );

        if (prayerRes.ok) {

          const prayers =
            await prayerRes.json();

          prayerContainer.innerHTML =
            prayers.length

              ? prayers.map(p => `

                <div class="prayer-item">

                  <strong>
                    ${p.user_name}
                  </strong>

                  <span class="timestamp">

                    (${formatDate(
                      p.created_at
                    )})

                  </span>

                  :
                  ${typeof p.message === "object"
                    ? JSON.stringify(p.message)
                    : p.message}

                </div>

              `).join("")

              : `
                <p>
                  No prayers yet
                </p>
              `;
        }

      } catch (e) {

        if (prayerContainer) {

          prayerContainer.innerHTML =
            `<p>Failed to load prayers</p>`;
        }
      }

    } catch (err) {

      console.error(
        "Dashboard load error:",
        err
      );

      showToast?.(
        "Failed to load dashboard data",
        "error"
      );
    }
  }

  // =====================================
  // MEMBER DASHBOARD
  // =====================================
  async function loadMemberDashboard() {

    try {

      const user =
        window.currentUser;

      if (!user) return;
      
      // =========================
      // PASTOR REDIRECT
      // =========================
      if (
        user.role === "pastor"
      ) {

        navigate("dashboard");

        return;
      }

      // =========================
      // PASTOR STATUS UI
      // =========================
      const badge =
        $("pastorStatusBadge");

      const message =
        $("pastorUpgradeMessage");

      const button =
        $("upgradePastorBtn");

      const card =
        $("pastorUpgradeCard");
      const title =
        $("pastorCardTitle");
      if (badge) {

        // =====================
        // PENDING
        // =====================
        if (
          user.pastor_status ===
          "pending"
        ) {

          badge.textContent =
            "Pending Approval";

          if (message) {

            message.textContent =
              "Your pastor application is currently under review.";
          }

          if (button) {

            button.disabled =
              true;

            button.textContent =
              "Application Pending";
          }
        }

        // =====================
        // REJECTED
        // =====================
        else if (
          user.pastor_status ===
          "rejected"
        ) {

          badge.textContent =
            "Rejected";

          if (title) {

            title.textContent =
              "Pastor Application Rejected";
          }

          if (message) {

            message.textContent =
              "Your pastor application was not approved. You may apply again.";
          }

          if (button) {

            button.disabled =
              false;

            button.textContent =
              "Apply Again";
          }
        }

        // =====================
        // APPROVED
        // =====================
        else if (
          user.pastor_status ===
          "approved"
        ) {

          badge.textContent =
            "Pastor";

          if (card) {

            card.style.display =
              "none";
          }
        }

        // =====================
        // MEMBER
        // =====================
        else {

          badge.textContent =
            "Member";
        }
      }
      // =========================
      // USER NAME
      // =========================
      const nameEl =
        $("userName");

      if (nameEl) {

        nameEl.textContent =
          user.name;
      }

      // =========================
      // SUMMARY
      // =========================
      const summaryRes =
        await apiFetch(
          "/api/v1/dashboard/summary"
        );

      if (summaryRes.ok) {

        const summary =
          await summaryRes.json();

        if ($("sermonCount")) {

          $("sermonCount").innerText =
            summary.total_sermons ?? 0;
        }

        if ($("memberCount")) {

          $("memberCount").innerText =
            summary.total_members ?? 0;
        }

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
      if (
        typeof loadMemberFeed ===
        "function"
      ) {

        await loadMemberFeed();
      }

      // =========================
      // TOP SERMONS
      // =========================
      await loadTopSermons();

      // =========================
      // AI INSIGHTS
      // =========================
      await loadAIInsights();

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