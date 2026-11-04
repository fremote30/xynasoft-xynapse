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
// ESCAPE HTML
// =====================================
const escapeHTML = (value = "") => {

  const div = document.createElement("div");

  div.textContent = String(value);

  return div.innerHTML;

};
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

    if (user.role === "pastor" || user.role === "admin") {
      navigate("dashboard");
      return;
    }

    // =====================================
    // PASTOR APPLICATION STATUS
    // =====================================
    const badge = $("pastorStatusBadge");
    const message = $("pastorUpgradeMessage");
    const button = $("upgradePastorBtn");
    const card = $("pastorUpgradeCard");
    const title = $("pastorCardTitle");

    if (badge) {
      if (user.pastor_status === "pending") {
        badge.textContent = "Pending Approval";

        if (message) {
          message.textContent =
            "Your pastor application is currently under review.";
        }

        if (button) {
          button.disabled = true;
          button.textContent = "Application Pending";
        }

      } else if (user.pastor_status === "rejected") {
        badge.textContent = "Rejected";

        if (title) {
          title.textContent =
            "Pastor Application Rejected";
        }

        if (message) {
          message.textContent =
            "Your pastor application was not approved. You may apply again.";
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

    // =====================================
    // BASIC USER NAME
    // =====================================
    const nameEl = $("userName");

    if (nameEl) {
      nameEl.textContent =
        user.name || "Member";
    }

    // =====================================
    // LOAD MEMBER PROFILE
    // =====================================
    try {
      const profileRes = await apiFetch(
        "/api/v1/member-profile/me"
      );

      const profileData = await profileRes
        .json()
        .catch(() => ({}));

      if (!profileRes.ok) {
        throw new Error(
          profileData.detail ||
          "Failed to load member profile"
        );
      }

      const profile = profileData;

      window.currentMemberProfile = profile;

      const avatar =
        $("memberDashboardAvatar");

      if (avatar) {
        if (profile.profile_image) {
          avatar.style.backgroundImage =
            `url('${profile.profile_image}')`;

          avatar.style.backgroundSize =
            "cover";

          avatar.style.backgroundPosition =
            "center";

          avatar.style.backgroundRepeat =
            "no-repeat";

          avatar.textContent = "";
        } else {
          avatar.style.backgroundImage = "";

          avatar.textContent =
            (
              profile.name ||
              user.name ||
              "M"
            )
              .charAt(0)
              .toUpperCase();
        }
      }

      const locationEl =
        $("memberDashboardLocation");

      if (locationEl) {
        const location = [
          profile.city,
          profile.state,
          profile.country
        ]
          .filter(Boolean)
          .join(", ");

        locationEl.textContent =
          location
            ? `📍 ${location}`
            : "🌎 Growing in faith every day.";
      }

      const favoriteVerseEl =
        $("memberFavoriteVerse");

      if (favoriteVerseEl) {
        favoriteVerseEl.textContent =
          profile.favorite_scripture
            ? `📖 ${profile.favorite_scripture}`
            : "📖 Add your favorite scripture in Edit Profile.";
      }

    } catch (profileErr) {
      console.error(
        "Member profile dashboard load failed:",
        profileErr
      );
    }

    // =====================================
    // MEMBER ACTIVITY SUMMARY
    // =====================================
    try {
      const activityRes = await apiFetch(
        "/api/v1/member-profile/me/activity"
      );

      const activityData = await activityRes
        .json()
        .catch(() => ({}));

      if (!activityRes.ok) {
        throw new Error(
          activityData.detail ||
          "Failed to load member activity"
        );
      }

      if ($("followingPastorsCount")) {
        $("followingPastorsCount").textContent =
          activityData.following_pastors ?? 0;
      }

      if ($("savedSermonsCount")) {
        $("savedSermonsCount").textContent =
          activityData.saved_sermons ?? 0;
      }

      if ($("memberPrayerCount")) {
        $("memberPrayerCount").textContent =
          activityData.prayer_requests ?? 0;
      }

      if ($("memberAnsweredPrayerCount")) {
        $("memberAnsweredPrayerCount").textContent =
          activityData.answered_prayers ?? 0;
      }

    } catch (activityErr) {
      console.error(
        "Member activity load failed:",
        activityErr
      );

      if ($("followingPastorsCount")) {
        $("followingPastorsCount").textContent = "0";
      }

      if ($("savedSermonsCount")) {
        $("savedSermonsCount").textContent = "0";
      }

      if ($("memberPrayerCount")) {
        $("memberPrayerCount").textContent = "0";
      }

      if ($("memberAnsweredPrayerCount")) {
        $("memberAnsweredPrayerCount").textContent = "0";
      }
    }

    // =====================================
    // GENERAL DASHBOARD SUMMARY
    // =====================================
    try {
      const summaryRes = await apiFetch(
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

    } catch (summaryErr) {
      console.error(
        "General dashboard summary failed:",
        summaryErr
      );
    }

    // =====================================
    // MEMBER CONTENT
    // =====================================
    if (
      typeof loadMemberFeed === "function"
    ) {
      await loadMemberFeed();
    }

    if (
      typeof loadTopSermons === "function"
    ) {
      await loadTopSermons();
    }

    if (
      typeof loadAIInsights === "function"
    ) {
      await loadAIInsights();
    }
    if (
      typeof loadSuggestedPastors === "function"
    ) {
      await loadSuggestedPastors();
    }

    if (
      typeof loadContinueReading === "function"
    ) {
      await loadContinueReading();
    }
    if (
      typeof loadDashboardPrayerWidget ===
      "function"
    ) {
      await loadDashboardPrayerWidget();
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
// SUGGESTED PASTORS
// =====================================
async function loadSuggestedPastors() {
  const container = $("suggestedPastors");

  if (!container) return;

  container.innerHTML = `
    <div class="feature-card">
      <p>Loading pastor suggestions...</p>
    </div>
  `;

  try {
    const res = await apiFetch(
      "/api/v1/pastors/?limit=3&offset=0"
    );

    const data = await res
      .json()
      .catch(() => ({}));

    if (!res.ok) {
      throw new Error(
        data.detail ||
        "Failed to load suggested pastors"
      );
    }

    const pastors = data.items || [];

    if (!pastors.length) {
      container.innerHTML = `
        <div class="feature-card empty-state">
          <h3>No suggestions yet</h3>
          <p>Explore the Network to discover pastors.</p>

          <button
            class="btn-secondary"
            onclick="navigate('network')"
          >
            Explore Network
          </button>
        </div>
      `;

      return;
    }

    container.innerHTML = pastors
      .map(pastor => {
        const location = [
          pastor.city,
          pastor.state,
          pastor.country
        ]
          .filter(Boolean)
          .join(", ");

        const initial = (
          pastor.name ||
          "P"
        )
          .charAt(0)
          .toUpperCase();

        const image = pastor.profile_image
          ? `
            <div
              class="suggested-pastor-avatar"
              style="
                background-image:url('${pastor.profile_image}');
                background-size:cover;
                background-position:center;
              "
            ></div>
          `
          : `
            <div class="suggested-pastor-avatar">
              ${initial}
            </div>
          `;

        return `
          <article class="feature-card suggested-pastor-card">

            ${image}

            <div class="suggested-pastor-content">
              <h3>
                ${pastor.name || "Pastor"}
              </h3>

              <p>
                ${pastor.church_name || "XynaFaith Ministry"}
              </p>

              <small>
                ${location || pastor.denomination || "XynaFaith Network"}
              </small>
            </div>

            <div class="suggested-pastor-actions">
              <button
                class="btn-secondary"
                onclick="openPastorProfile(${pastor.id})"
              >
                View Profile
              </button>

              ${
                window.currentUser?.role === "member"
                  ? `
                    <button
                      class="btn-primary"
                      onclick="followPastor(${pastor.id})"
                    >
                      Follow
                    </button>
                  `
                  : ""
              }
            </div>

          </article>
        `;
      })
      .join("");

  } catch (err) {
    console.error(
      "Suggested pastors load failed:",
      err
    );

    container.innerHTML = `
      <div class="feature-card empty-state error">
        <h3>Could not load suggestions</h3>
        <p>Please try again later.</p>
      </div>
    `;
  }
}

window.loadSuggestedPastors =
  loadSuggestedPastors;


// =====================================
// CONTINUE READING
// =====================================
async function loadContinueReading() {
  const container =
    $("continueReadingSection");

  if (!container) return;

  container.innerHTML = `
    <div class="feature-card">
      <p>Loading sermon...</p>
    </div>
  `;

  try {
    let sermon = null;
    let source = "";

    // =====================================
    // 1. SERVER-SAVED RECENT SERMON
    // =====================================
    if (
      window.currentUser?.role ===
      "member"
    ) {
      try {
        const recentRes =
          await apiFetch(
            "/api/v1/member-profile/recent-sermon"
          );

        const recentData =
          await recentRes
            .json()
            .catch(() => ({}));

        if (
          recentRes.ok &&
          recentData.sermon &&
          recentData.sermon.id
        ) {
          sermon =
            recentData.sermon;

          source =
            "server";

        } else if (
          !recentRes.ok
        ) {
          console.warn(
            "Recent sermon request failed:",
            recentData.detail ||
            recentRes.status
          );
        }

      } catch (recentErr) {
        console.warn(
          "Server recent sermon unavailable:",
          recentErr
        );
      }
    }

    // =====================================
    // 2. LOCAL STORAGE FALLBACK
    // Only saved sermons with a database ID
    // may appear in Continue Reading.
    // =====================================
    if (!sermon) {
      const cached =
        localStorage.getItem(
          "latest_sermon"
        );

      if (cached) {
        try {
          const parsed =
            JSON.parse(cached);

          if (
            parsed &&
            (
              parsed.id ||
              parsed.sermon_id ||
              parsed.sermon?.id
            )
          ) {
            sermon = parsed;
            source = "local";

          } else if (
            parsed?.title
          ) {
            console.warn(
              "Cached sermon has no database ID and cannot be reopened:",
              parsed
            );
          }

        } catch (err) {
          console.warn(
            "Could not parse latest sermon:",
            err
          );
        }
      }
    }

   // =====================================
// 3. RECOMMENDATION FALLBACK
// =====================================
if (!sermon) {

  try {

    const res =
      await apiFetch(
        "/api/v1/dashboard/top-sermons"
      );


    const data =
      await res
        .json()
        .catch(() => ({}));


    const sermons =
      Array.isArray(data)
        ? data
        : (
            data.sermons ||
            data.items ||
            []
          );


    if (
      res.ok &&
      sermons.length > 0
    ) {

      sermon =
        sermons[0];

      sermon.recommended =
        true;

      source =
        "recommended-sermon";


    } else {

      console.warn(
        "No recommended sermons found"
      );

    }


  } catch (
    recommendationErr
  ) {

    console.warn(
      "Recommended sermon load failed:",
      recommendationErr
    );

  }
}

    // =====================================
    // EMPTY STATE
    // =====================================
    if (!sermon) {
      container.innerHTML = `
        <div class="feature-card empty-state">

          <h3>
            No sermons to continue yet
          </h3>

          <p>
            Open a saved sermon to begin your reading journey.
          </p>

          <button
            id="continueReadingEmptyBtn"
            type="button"
            class="btn-primary"
          >
            Explore Sermons
          </button>

        </div>
      `;

      const emptyButton =
        $("continueReadingEmptyBtn");

      if (emptyButton) {
        emptyButton.addEventListener(
          "click",
          () =>
            navigate(
              "mysermons"
            )
        );
      }

      return;
    }

    // =====================================
    // NORMALIZE SERMON DATA
    // =====================================
    const title =
      sermon.title ||
      sermon.sermon?.title ||
      "Untitled Sermon";

    const scripture =
      sermon.scripture ||
      sermon.sermon?.scripture ||
      "";

    const pastorName =
      sermon.author_name ||
      sermon.pastor_name ||
      sermon.sermon
        ?.author_name ||
      "";

    const sermonId =
      Number(
        sermon.id ||
        sermon.sermon_id ||
        sermon.sermon?.id ||
        0
      );

    const pastorId =
      Number(
        sermon.pastor_id ||
        sermon.author_id ||
        0
      );

    console.log(
      "📖 Continue Reading source:",
      source
    );

    console.log(
      "📖 Continue Reading sermon:",
      sermon
    );

    console.log(
      "📖 Continue Reading sermon ID:",
      sermonId
    );

    // =====================================
    // RENDER CARD
    // =====================================
    container.innerHTML = `
      <article
        class="
          feature-card
          continue-reading-card
        "
      >

        <div
          class="
            continue-reading-icon
          "
        >
          📖
        </div>

        <div
          class="
            continue-reading-content
          "
        >

          <span class="eyebrow">
            ${
              sermon.recommended
                ? "Recommended Sermon"
                : "Continue Reading"
            }
          </span>

          <h3>
            ${escapeHTML(title)}
          </h3>

          ${
            scripture
              ? `
                <p
                  class="
                    continue-reading-scripture
                  "
                >
                  ${escapeHTML(
                    scripture
                  )}
                </p>
              `
              : ""
          }

          ${
            pastorName
              ? `
                <small>
                  ${escapeHTML(
                    pastorName
                  )}
                </small>
              `
              : ""
          }

        </div>

        <button
          id="continueReadingBtn"
          type="button"
          class="btn-primary"
        >
          ${
            sermon.recommended
              ? "Discover Sermon"
              : "Continue Reading"
          }
        </button>

      </article>
    `;

    // =====================================
    // ATTACH CLICK HANDLER
    // =====================================
    const continueButton =
      $("continueReadingBtn");

    if (!continueButton) {
      return;
    }

    continueButton
      .addEventListener(
        "click",
        async () => {
          try {
            continueButton.disabled =
              true;

            continueButton.textContent =
              sermon.recommended
                ? "Opening..."
                : "Loading Sermon...";

            // =================================
            // OPEN A REAL SAVED SERMON
            // =================================
            if (sermonId) {
              const opener =
                window.openSavedSermon;

              if (
                typeof opener !==
                "function"
              ) {
                throw new Error(
                  "Saved sermon opener is unavailable"
                );
              }

              await opener(
                sermonId
              );

              return;
            }

            // =================================
            // OPEN RECOMMENDED PASTOR
            // =================================
            if (
              sermon.recommended &&
              pastorId
            ) {
              if (
                typeof window
                  .openPastorProfile ===
                "function"
              ) {
                await window
                  .openPastorProfile(
                    pastorId
                  );

              } else {
                localStorage.setItem(
                  "selected_pastor_id",
                  String(
                    pastorId
                  )
                );

                await navigate(
                  "pastor-profile"
                );
              }

              return;
            }

            // =================================
            // NEVER OPEN BLANK SERMON STUDIO
            // =================================
            throw new Error(
              "This sermon was not saved and cannot be reopened. Open a saved public sermon first."
            );

          } catch (clickErr) {
            console.error(
              "Continue Reading click failed:",
              clickErr
            );

            showToast?.(
              clickErr.message ||
              "Could not open sermon",
              "error"
            );

            continueButton.disabled =
              false;

            continueButton.textContent =
              sermon.recommended
                ? "Discover Sermon"
                : "Continue Reading";
          }
        }
      );

  } catch (err) {
    console.error(
      "Continue reading load failed:",
      err
    );

    container.innerHTML = `
      <div
        class="
          feature-card
          empty-state
          error
        "
      >

        <h3>
          Could not load sermon
        </h3>

        <p>
          Please try again later.
        </p>

      </div>
    `;
  }
}

window.loadContinueReading =
  loadContinueReading;



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