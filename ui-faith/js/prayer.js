(() => {

  const API_BASE = window.API_BASE || "/api/v1";
  let prayerState = {
    filter: "recent",
    search: "",
    skip: 0,
    limit: 10,
    loading: false,
    hasMore: true
  };

  function getTokenSafe() {
    if (typeof getToken === "function") return getToken();
    return localStorage.getItem("access_token");
  }

  async function prayerFetch(path, options = {}) {
    const token = getTokenSafe();

    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || "Prayer request failed");
    }

    return await res.json();
  }

  function escapeHTML(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function timeAgo(dateString) {
    if (!dateString) return "";

    const diff = Date.now() - new Date(dateString).getTime();
    const mins = Math.floor(diff / 60000);
    const hours = Math.floor(mins / 60);
    const days = Math.floor(hours / 24);

    if (mins < 1) return "Just now";
    if (mins < 60) return `${mins}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  }

  function statusBadge(prayer) {
    if (prayer.status === "answered") {
      return `<span class="prayer-badge answered">Answered Prayer 🎉</span>`;
    }

    if (prayer.status === "partially_answered") {
      return `<span class="prayer-badge partial">Partially Answered</span>`;
    }

    return `<span class="prayer-badge praying">Still Praying</span>`;
  }

  function statusControls(prayer) {
  if (!prayer.can_update_status) return "";

  return `
    <select
      class="prayer-status-select"
      onchange="updatePrayerStatus(${prayer.id}, this.value)"
    >
      <option value="still_praying" ${prayer.status === "still_praying" ? "selected" : ""}>
        Still Praying
      </option>
      <option value="partially_answered" ${prayer.status === "partially_answered" ? "selected" : ""}>
        Partially Answered
      </option>
      <option value="answered" ${prayer.status === "answered" ? "selected" : ""}>
        Answered
      </option>
    </select>
  `;
}


function answeredCelebration(prayer) {
  if (prayer.status !== "answered") return "";

  return `
    <div class="answered-celebration">
      <strong>🎉 Praise God — this prayer was answered.</strong>
      <p>Thank you for praying with the XynaFaith community.</p>
    </div>
  `;
}

  function prayerCard(prayer) {
    return `
      <article class="prayer-card" data-prayer-id="${prayer.id}">

        <div class="prayer-card-header">
          <div>
            <h3>${escapeHTML(prayer.user_name || "Anonymous")}</h3>
            <p>
              ${escapeHTML(prayer.category || "Prayer")}
              • ${timeAgo(prayer.created_at)}
            </p>
          </div>

          <div class="prayer-status-wrap">
            ${statusBadge(prayer)}
            ${statusControls(prayer)}
          </div>
        </div>

        <p class="prayer-message">
          ${escapeHTML(prayer.message)}
        </p>

        ${answeredCelebration(prayer)}

        <div class="prayer-card-stats">
          <span>${prayer.prayer_count || 0} prayed</span>
          <span>${prayer.support_count || 0} supports</span>
          <span>${prayer.comment_count || 0} comments</span>
          <span>${prayer.share_count || 0} shares</span>
        </div>

        <div class="prayer-actions">
          <button
            class="${prayer.has_prayed ? "active" : ""}"
            onclick="reactToPrayer(${prayer.id}, 'prayed')"
          >
            🙏 Pray
          </button>

          <button
            class="${prayer.has_supported ? "active" : ""}"
            onclick="reactToPrayer(${prayer.id}, 'support')"
          >
            ❤️ Support
          </button>

          <button onclick="togglePrayerComments(${prayer.id})">
            💬 Comment
          </button>

          <button
            class="${prayer.is_bookmarked ? "active" : ""}"
            onclick="togglePrayerBookmark(${prayer.id})"
          >
            🔖 Save
          </button>

          <button onclick="sharePrayer(${prayer.id})">
            📤 Share
          </button>
        </div>

        <div id="comments-${prayer.id}" class="prayer-comments hidden">
          <div class="comment-list" id="commentList-${prayer.id}">
            Loading comments...
          </div>

          <div class="comment-box">
            <input
              id="commentInput-${prayer.id}"
              class="input"
              placeholder="Encourage, share scripture, or post an update..."
            />

            <button class="btn-primary" onclick="submitPrayerComment(${prayer.id})">
              Send
            </button>
          </div>
        </div>

      </article>
    `;
  }

  async function loadPrayerAnalytics() {
    try {
      const data = await prayerFetch("/prayers/analytics");

      document.getElementById("prayerStatTotal").textContent = data.total_prayers || 0;
      document.getElementById("prayerStatWeek").textContent = data.prayers_this_week || 0;
      document.getElementById("prayerStatAnswered").textContent = data.answered_prayers || 0;
      document.getElementById("prayerStatToday").textContent = data.people_praying_today || 0;

    } catch (err) {
      console.error("Prayer analytics failed:", err);
    }
  }

  async function loadPrayerFeed(reset = true) {
    if (prayerState.loading) return;

    prayerState.loading = true;

    const feed = document.getElementById("prayerFeed");
    const loadMoreBtn = document.getElementById("loadMorePrayersBtn");

    if (!feed) return;

    if (reset) {
      prayerState.skip = 0;
      prayerState.hasMore = true;
      feed.innerHTML = `
        <div class="empty-state">
          <h3>Loading prayers...</h3>
          <p>Gathering the latest community requests.</p>
        </div>
      `;
    }

    try {
      const params = new URLSearchParams({
        filter: prayerState.filter,
        skip: prayerState.skip,
        limit: prayerState.limit
      });

      if (prayerState.search) {
        params.set("search", prayerState.search);
      }

      const data = await prayerFetch(`/prayers/feed?${params.toString()}`);
      const items = data.items || [];

      if (reset) {
        feed.innerHTML = "";
      }

      if (items.length === 0 && prayerState.skip === 0) {
        feed.innerHTML = `
          <div class="empty-state">
            <h3>No prayers found</h3>
            <p>Be the first to share a prayer request with the community.</p>
            <button class="btn-primary" onclick="openPrayerComposer()">Submit Prayer</button>
          </div>
        `;
      } else {
        feed.insertAdjacentHTML(
          "beforeend",
          items.map(prayerCard).join("")
        );
      }

      prayerState.skip += prayerState.limit;
      prayerState.hasMore = items.length === prayerState.limit;

      if (loadMoreBtn) {
        loadMoreBtn.style.display = prayerState.hasMore ? "inline-flex" : "none";
      }

    } catch (err) {
      console.error("Prayer feed failed:", err);

      feed.innerHTML = `
        <div class="empty-state error">
          <h3>Could not load Prayer Wall</h3>
          <p>${escapeHTML(err.message)}</p>
        </div>
      `;
    } finally {
      prayerState.loading = false;
    }
  }

  window.loadPrayerWall = async function () {
    prayerState = {
      filter: "recent",
      search: "",
      skip: 0,
      limit: 10,
      loading: false,
      hasMore: true
    };

    await loadPrayerAnalytics();
    await loadPrayerFeed(true);
    await loadPrayerNotifications();
  };

  window.loadMorePrayers = async function () {
    await loadPrayerFeed(false);
  };

  window.setPrayerFilter = async function (filter) {
    prayerState.filter = filter;

    document.querySelectorAll(".filter-chip").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.filter === filter);
    });

    await loadPrayerFeed(true);
  };

  let searchTimer = null;

  window.handlePrayerSearch = function () {
    clearTimeout(searchTimer);

    searchTimer = setTimeout(async () => {
      const input = document.getElementById("prayerSearch");
      prayerState.search = input ? input.value.trim() : "";
      await loadPrayerFeed(true);
    }, 350);
  };

  window.openPrayerComposer = function () {
    const modal = document.getElementById("prayerComposerModal");
    if (modal) modal.classList.remove("hidden");
  };

  window.closePrayerComposer = function () {
    const modal = document.getElementById("prayerComposerModal");
    if (modal) modal.classList.add("hidden");
  };

  window.submitPrayer = async function () {
    const message = document.getElementById("newPrayerMessage")?.value.trim();
    const category = document.getElementById("newPrayerCategory")?.value || null;
    const isAnonymous = document.getElementById("newPrayerAnonymous")?.checked || false;

    if (!message) {
      alert("Prayer message is required.");
      return;
    }

    try {
      await prayerFetch("/prayers", {
        method: "POST",
        body: JSON.stringify({
          message,
          category,
          is_anonymous: isAnonymous
        })
      });

      document.getElementById("newPrayerMessage").value = "";
      document.getElementById("newPrayerCategory").value = "";
      document.getElementById("newPrayerAnonymous").checked = false;

      closePrayerComposer();

      await loadPrayerAnalytics();
      await loadPrayerFeed(true);

    } catch (err) {
      alert("Could not submit prayer.");
      console.error(err);
    }
  };

window.reactToPrayer = async function (prayerId, reactionType) {
  const card = document.querySelector(`[data-prayer-id="${prayerId}"]`);
  const button = card?.querySelector(
    `button[onclick="reactToPrayer(${prayerId}, '${reactionType}')"]`
  );

  if (button?.classList.contains("active")) {
    return;
  }

  if (button) {
    button.classList.add("active");
    button.disabled = true;
  }

  try {
    const data = await prayerFetch(`/prayers/${prayerId}/react`, {
      method: "POST",
      body: JSON.stringify({
        reaction_type: reactionType
      })
    });

    const prayer = data.prayer;

    if (prayer && card) {
      const stats = card.querySelector(".prayer-card-stats");

      if (stats) {
        stats.innerHTML = `
          <span>${prayer.prayer_count || 0} prayed</span>
          <span>${prayer.support_count || 0} supports</span>
          <span>${prayer.comment_count || 0} comments</span>
          <span>${prayer.share_count || 0} shares</span>
        `;
      }
    }

    await loadPrayerAnalytics();

  } catch (err) {
    console.error("Prayer reaction failed:", err);

    if (button) {
      button.classList.remove("active");
      button.disabled = false;
    }

  } finally {
    if (button) {
      button.disabled = false;
    }
  }
};

window.togglePrayerBookmark = async function (prayerId) {
  const card = document.querySelector(`[data-prayer-id="${prayerId}"]`);
  const button = card?.querySelector(
    `button[onclick="togglePrayerBookmark(${prayerId})"]`
  );

  if (button) {
    button.disabled = true;
  }

  try {
    const data = await prayerFetch(`/prayers/${prayerId}/bookmark`, {
      method: "POST"
    });

    if (button) {
      button.classList.toggle("active", !!data.bookmarked);
      button.innerHTML = data.bookmarked ? "🔖 Saved" : "🔖 Save";
    }

  } catch (err) {
    console.error("Prayer bookmark failed:", err);
    alert("Could not update bookmark.");

  } finally {
    if (button) {
      button.disabled = false;
    }
  }
};


window.sharePrayer = async function (prayerId) {
  const card = document.querySelector(`[data-prayer-id="${prayerId}"]`);
  const button = card?.querySelector(
    `button[onclick="sharePrayer(${prayerId})"]`
  );

  if (button) button.disabled = true;

  try {
    const data = await prayerFetch(`/prayers/${prayerId}/share`, {
      method: "POST"
    });

    const url = `${window.location.origin}/faith/#prayer-${prayerId}`;

    if (navigator.share) {
      await navigator.share({
        title: "Prayer Request",
        text: "Please pray with me on XynaFaith.",
        url
      });
    } else {
      await navigator.clipboard.writeText(url);
      alert("Prayer link copied.");
    }

    const statSpans = card?.querySelectorAll(".prayer-card-stats span");

    if (statSpans && statSpans[3]) {
      statSpans[3].textContent = `${data.share_count || 0} shares`;
    }

  } catch (err) {
    console.error("Prayer share failed:", err);
    alert("Could not share prayer.");

  } finally {
    if (button) button.disabled = false;
  }
};

  window.togglePrayerComments = async function (prayerId) {
    const box = document.getElementById(`comments-${prayerId}`);

    if (!box) return;

    box.classList.toggle("hidden");

    if (!box.classList.contains("hidden")) {
      await loadPrayerComments(prayerId);
    }
  };

  async function loadPrayerComments(prayerId) {
    const list = document.getElementById(`commentList-${prayerId}`);

    if (!list) return;

    list.innerHTML = "Loading comments...";

    try {
      const data = await prayerFetch(`/prayers/${prayerId}/comments`);
      const comments = data.items || [];

      if (!comments.length) {
        list.innerHTML = `
          <div class="comment-empty">
            No comments yet. Be the first to encourage this person.
          </div>
        `;
        return;
      }

      list.innerHTML = comments.map(comment => `
        <div class="comment-card ${comment.is_pastor_response ? "pastor-comment" : ""}">
          <div class="comment-header">
            <strong>
              ${comment.is_pastor_response ? "✝️ " : ""}
              ${escapeHTML(comment.user_name)}
            </strong>

            ${comment.is_pastor_response ? `<span class="pastor-response-badge">Pastor Response</span>` : ""}
          </div>

          ${comment.is_pastor_response ? `<div class="pastor-encouragement-label">📌 Encouragement from a verified ministry leader</div>` : ""}

          <p>${escapeHTML(comment.comment)}</p>

          <span class="comment-time">${timeAgo(comment.created_at)}</span>
        </div>
      `).join("");

    } catch (err) {
      list.innerHTML = "Could not load comments.";
      console.error(err);
    }
  }

  window.updatePrayerStatus = async function (prayerId, status) {
  try {
    await prayerFetch(`/prayers/${prayerId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status })
    });

    await loadPrayerAnalytics();
    await loadPrayerFeed(true);

  } catch (err) {
    console.error("Prayer status update failed:", err);
    alert("Could not update prayer status.");
  }
};

  window.submitPrayerComment = async function (prayerId) {
  const input = document.getElementById(`commentInput-${prayerId}`);
  const comment = input?.value.trim();

  if (!comment) return;

  input.disabled = true;

  try {
    await prayerFetch(`/prayers/${prayerId}/comments`, {
      method: "POST",
      body: JSON.stringify({
        comment
      })
    });

    input.value = "";

    await loadPrayerComments(prayerId);

    const card = document.querySelector(`[data-prayer-id="${prayerId}"]`);
    const statSpans = card?.querySelectorAll(".prayer-card-stats span");

    if (statSpans && statSpans[2]) {
      const current = parseInt(statSpans[2].textContent) || 0;
      statSpans[2].textContent = `${current + 1} comments`;
    }

  } catch (err) {
    console.error("Prayer comment failed:", err);
    alert("Could not post comment.");

  } finally {
    input.disabled = false;
    input.focus();
  }
};

async function loadPrayerNotifications() {
  const bell = document.getElementById("notificationBell");
  const badge = document.getElementById("notificationBadge");

  if (!bell || !badge) return;

  try {
    const data = await prayerFetch("/prayers/notifications");
    const count = data.unread_count || 0;

    bell.classList.remove("hidden");

    if (count > 0) {
      badge.textContent = count > 99 ? "99+" : count;
      badge.classList.remove("hidden");
    } else {
      badge.classList.add("hidden");
    }

    window.__prayerNotifications = data.items || [];

  } catch (err) {
    console.error("Prayer notifications failed:", err);
  }
}

window.togglePrayerNotifications = async function () {
  let panel = document.getElementById("notificationPanel");

  if (panel) {
    panel.remove();
    return;
  }

  await loadPrayerNotifications();

  const items = window.__prayerNotifications || [];

  panel = document.createElement("div");
  panel.id = "notificationPanel";
  panel.className = "notification-panel";

  panel.innerHTML = `
    <h3>Notifications</h3>

    ${
      items.length
        ? items.map(item => `
          <div class="notification-item ${item.is_read ? "" : "unread"}">
            <p>${escapeHTML(item.message)}</p>
            <span>${timeAgo(item.created_at)}</span>
          </div>
        `).join("")
        : `
          <div class="notification-item">
            <p>No notifications yet.</p>
            <span>Prayer activity will appear here.</span>
          </div>
        `
    }
  `;

  document.body.appendChild(panel);

  try {
    await prayerFetch("/prayers/notifications/read", {
      method: "PATCH"
    });

    const badge = document.getElementById("notificationBadge");
    if (badge) badge.classList.add("hidden");

  } catch (err) {
    console.error("Mark notifications read failed:", err);
  }
};

window.refreshPrayerNotifications = async function () {
  await loadPrayerNotifications();
};

})();