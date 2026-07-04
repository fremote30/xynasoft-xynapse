(() => {

  const API_BASE = window.API_BASE || "/api/v1";
  let prayerState = {
  view: "wall",
  filter: "recent",
  search: "",
  skip: 0,
  limit: 10,
  loading: false,
  hasMore: true,
  selectedRecipients: []
};

let prayerLiveTimer = null;

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
      <div class="answered-icon">🎉</div>
      <div>
        <strong>Prayer Answered</strong>
        <p>God answered this request. Thank you for praying with the XynaFaith community.</p>
      </div>
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


  function prayerCardV2(prayer) {
  const name = prayer.user_name || "Anonymous";
  const initials = name.charAt(0).toUpperCase();
  const visibility = prayer.visibility || "community";

  const visibilityBadge =
    visibility === "mixed"
      ? "🌍 Shared"
      : visibility === "selected"
        ? "🔒 Private"
        : "🌍 Community";

  const answeredBadge =
    prayer.status === "answered"
      ? `<span class="prayer-card-badge answered">🎉 Answered</span>`
      : prayer.status === "partially_answered"
        ? `<span class="prayer-card-badge partial">Partially Answered</span>`
        : `<span class="prayer-card-badge praying">Still Praying</span>`;

  return `
    <article class="prayer-card-v2" data-prayer-id="${prayer.id}">

      <div class="prayer-card-v2-header">

        <div class="prayer-author">
          <div class="prayer-avatar">${escapeHTML(initials)}</div>

          <div>
            <h3>${escapeHTML(name)}</h3>
            <p>
              ${escapeHTML(prayer.category || "Prayer")}
              • ${timeAgo(prayer.created_at)}
            </p>
          </div>
        </div>

        <div class="prayer-card-badges">
          <span class="prayer-card-badge visibility">
            ${visibilityBadge}
          </span>

          ${answeredBadge}
        </div>

      </div>

      <p class="prayer-card-v2-message">
        ${escapeHTML(prayer.message)}
      </p>

      ${answeredCelebration(prayer)}

      <div class="prayer-card-v2-stats">
        <span>🙏 ${prayer.prayer_count || 0} prayed</span>
        <span>❤️ ${prayer.support_count || 0} support</span>
        <span>💬 ${prayer.comment_count || 0} comments</span>
        <span>📤 ${prayer.share_count || 0} shares</span>
      </div>

      <div class="prayer-card-v2-actions">

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
        <h3>Loading Prayer Network...</h3>
        <p>Connecting you to the global prayer community.</p>
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
          <h3>No prayers yet</h3>
          <p>Be the first to share a prayer with the community.</p>
          <button class="btn-primary" onclick="openPrayerComposer()">
            🙏 Submit Prayer
          </button>
        </div>
      `;
    } else {
      feed.insertAdjacentHTML(
        "beforeend",
        items.map(prayerCardV2).join("")
      );
    }

    prayerState.skip += prayerState.limit;
    prayerState.hasMore = items.length === prayerState.limit;

    if (loadMoreBtn) {
      loadMoreBtn.style.display = prayerState.hasMore
        ? "inline-flex"
        : "none";
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

async function loadPrayerInbox() {
  const feed = document.getElementById("prayerFeed");
  const loadMoreBtn = document.getElementById("loadMorePrayersBtn");

  if (loadMoreBtn) loadMoreBtn.style.display = "none";
  if (!feed) return;

  feed.innerHTML = `
    <div class="empty-state">
      <h3>Loading Prayer Inbox...</h3>
      <p>Checking private prayer requests sent to you.</p>
    </div>
  `;

  try {
    const data = await prayerFetch("/prayers/inbox");
    const items = data.items || [];

    feed.innerHTML = items.length
      ? items.map(prayerCard).join("")
      : `
        <div class="empty-state">
          <h3>No private prayer requests</h3>
          <p>When someone sends you a prayer request, it will appear here.</p>
        </div>
      `;
  } catch (err) {
    console.error("Prayer inbox failed:", err);

    feed.innerHTML = `
      <div class="empty-state error">
        <h3>Could not load inbox</h3>
        <p>${escapeHTML(err.message)}</p>
      </div>
    `;
  }
}


async function loadSentPrayers() {
  const feed = document.getElementById("prayerFeed");
  const loadMoreBtn = document.getElementById("loadMorePrayersBtn");

  if (loadMoreBtn) loadMoreBtn.style.display = "none";
  if (!feed) return;

  feed.innerHTML = `
    <div class="empty-state">
      <h3>Loading Sent Prayers...</h3>
      <p>Reviewing prayer requests you have submitted.</p>
    </div>
  `;

  try {
    const data = await prayerFetch("/prayers/sent");
    const items = data.items || [];

    feed.innerHTML = items.length
      ? items.map(prayerCard).join("")
      : `
        <div class="empty-state">
          <h3>No sent prayers yet</h3>
          <p>Prayer requests you submit will appear here.</p>
        </div>
      `;
  } catch (err) {
    console.error("Sent prayers failed:", err);

    feed.innerHTML = `
      <div class="empty-state error">
        <h3>Could not load sent prayers</h3>
        <p>${escapeHTML(err.message)}</p>
      </div>
    `;
  }
}

window.loadPrayerWall = async function () {

  prayerState = {
    view: "wall",
    filter: "recent",
    search: "",
    skip: 0,
    limit: 10,
    loading: false,
    hasMore: true,
    selectedRecipients: []
  };

  await loadPrayerAnalytics();
  await loadPrayerFeed(true);
  await loadPrayerNotifications();

  // Start automatic refresh every 30 seconds
  startPrayerLiveUpdates();
};

window.setPrayerView = async function (view) {
  prayerState.view = view;

  document.querySelectorAll("[data-view]").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.view === view);
  });

  const filters = document.getElementById("prayerFeedFilters");
  const search = document.getElementById("prayerSearch");

  if (filters) {
    filters.style.display = view === "wall" ? "flex" : "none";
  }

  if (search) {
    search.style.display = view === "wall" ? "block" : "none";
  }

  if (view === "inbox") {
    await loadPrayerInbox();
    return;
  }

  if (view === "sent") {
    await loadSentPrayers();
    return;
  }

  await loadPrayerFeed(true);
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

  const sendToCommunity = document.getElementById("sendToCommunity")?.checked || false;
  const sendToSelectedPeople = document.getElementById("sendToSelectedPeople")?.checked || false;

  let visibility = "community";

  if (
    sendToCommunity &&
    sendToSelectedPeople &&
    prayerState.selectedRecipients.length
  ) {
    visibility = "mixed";
  } else if (
    !sendToCommunity &&
    sendToSelectedPeople &&
    prayerState.selectedRecipients.length
  ) {
    visibility = "selected";
  } else {
    visibility = "community";
  }

  if (!message) {
    alert("Prayer message is required.");
    return;
  }

  if (!sendToCommunity && !prayerState.selectedRecipients.length) {
    alert("Please choose Community Prayer Wall or select at least one person.");
    return;
  }

  try {
    await prayerFetch("/prayers", {
      method: "POST",
      body: JSON.stringify({
        message,
        category,
        visibility,
        recipients: prayerState.selectedRecipients,
        is_anonymous: isAnonymous
      })
    });

    document.getElementById("newPrayerMessage").value = "";
    document.getElementById("newPrayerCategory").value = "";
    document.getElementById("newPrayerAnonymous").checked = false;

    const communityBox = document.getElementById("sendToCommunity");
    if (communityBox) communityBox.checked = true;

    const selectedBox = document.getElementById("sendToSelectedPeople");
    if (selectedBox) selectedBox.checked = false;

    const recipientSearchBox = document.getElementById("recipientSearchBox");
    if (recipientSearchBox) recipientSearchBox.classList.add("hidden");

    const recipientInput = document.getElementById("recipientSearch");
    if (recipientInput) recipientInput.value = "";

    const recipientResults = document.getElementById("recipientResults");
    if (recipientResults) {
      recipientResults.innerHTML = `
        <p class="text-muted">
          Start typing a pastor or member's name...
        </p>
      `;
    }

    prayerState.selectedRecipients = [];
    renderPrayerRecipients();


    closePrayerComposer();

    await loadPrayerAnalytics();

    if (prayerState.view === "sent") {
      await loadSentPrayers();
    } else if (prayerState.view === "inbox") {
      await loadPrayerInbox();
    } else {
      await loadPrayerFeed(true);
    }

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

  if (button?.classList.contains("active")) return;

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
      const stats =
        card.querySelector(".prayer-card-v2-stats") ||
        card.querySelector(".prayer-card-stats");

      if (stats) {
        stats.innerHTML = `
          <span>🙏 ${prayer.prayer_count || 0} prayed</span>
          <span>❤️ ${prayer.support_count || 0} support</span>
          <span>💬 ${prayer.comment_count || 0} comments</span>
          <span>📤 ${prayer.share_count || 0} shares</span>
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
    if (button) button.disabled = false;
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

async function loadPrayerComments(prayerId) {
  const list = document.getElementById(`commentList-${prayerId}`);

  if (!list) return;

  list.innerHTML = `
    <div class="comment-empty">
      Loading encouragements...
    </div>
  `;

  try {
    const data = await prayerFetch(`/prayers/${prayerId}/comments`);
    const comments = data.items || [];

    if (!comments.length) {
      list.innerHTML = `
        <div class="comment-empty">
          No encouragements yet. Be the first to pray or share scripture.
        </div>
      `;
      return;
    }

    list.innerHTML = comments.map(comment => `
      <div class="comment-card-v2 ${comment.is_pastor_response ? "pastor-comment" : ""}">
        <div class="comment-avatar">
          ${escapeHTML((comment.user_name || "U").charAt(0).toUpperCase())}
        </div>

        <div class="comment-body">
          <div class="comment-header">
            <strong>${escapeHTML(comment.user_name || "XynaFaith User")}</strong>

            ${comment.is_pastor_response
              ? `<span class="pastor-response-badge">✓ Pastor Response</span>`
              : ""
            }

            ${comment.is_pinned
              ? `<span class="pastor-response-badge">📌 Pinned</span>`
              : ""
            }
          </div>

          ${comment.is_pastor_response
            ? `<div class="pastor-encouragement-label">
                Ministry encouragement
              </div>`
            : ""
          }

          <p>${escapeHTML(comment.comment)}</p>

          <span class="comment-time">${timeAgo(comment.created_at)}</span>
        </div>
      </div>
    `).join("");

  } catch (err) {
    list.innerHTML = `
      <div class="comment-empty error">
        Could not load comments.
      </div>
    `;
    console.error(err);
  }
}

  window.togglePrayerComments = async function (prayerId) {
    const box = document.getElementById(`comments-${prayerId}`);

    if (!box) return;

    box.classList.toggle("hidden");

    if (!box.classList.contains("hidden")) {
      await loadPrayerComments(prayerId);
    }
  };



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
    const data = await prayerFetch(`/prayers/${prayerId}/comments`, {
      method: "POST",
      body: JSON.stringify({ comment })
    });

    input.value = "";

    await loadPrayerComments(prayerId);

    const card = document.querySelector(`[data-prayer-id="${prayerId}"]`);
    const statSpans = card?.querySelectorAll(
      ".prayer-card-v2-stats span, .prayer-card-stats span"
    );

    if (statSpans && statSpans[2]) {
      const current = parseInt(statSpans[2].textContent) || 0;
      statSpans[2].textContent = `💬 ${current + 1} comments`;
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


window.toggleRecipientSearch = function () {
  const checked = document.getElementById("sendToSelectedPeople")?.checked;
  const box = document.getElementById("recipientSearchBox");

  if (box) {
    box.classList.toggle("hidden", !checked);
  }

  if (!checked) {
    prayerState.selectedRecipients = [];
    renderPrayerRecipients();
  }
};

window.refreshPrayerNotifications = async function () {
  await loadPrayerNotifications();
};


window.searchPrayerRecipients = async function () {
  const input = document.getElementById("recipientSearch");
  const results = document.getElementById("recipientResults");

  if (!input || !results) return;

  const q = input.value.trim();

  if (!q || q.length < 2) {
    results.innerHTML = `
      <p class="text-muted">
        Start typing a pastor or member's name...
      </p>
    `;
    return;
  }

  results.innerHTML = `
    <p class="text-muted">Searching...</p>
  `;

  try {
    const users = await prayerFetch(
      `/users/search?q=${encodeURIComponent(q)}&type=all`
    );

    results.innerHTML = users.length
      ? users.map(user => {
          const selected = prayerState.selectedRecipients.some(
            r => r.user_id === user.id
          );

          return `
            <button
              class="recipient-result ${selected ? "selected" : ""}"
              ${selected ? "disabled" : ""}
              onclick="addPrayerRecipient(
                ${user.id},
                '${escapeHTML(user.name || user.email || "User")}',
                '${escapeHTML(user.role || "member")}',
                '${escapeHTML(user.email || "")}'
              )"
            >
              <div class="recipient-avatar">
                ${user.avatar
                  ? `<img src="${escapeHTML(user.avatar)}" alt="">`
                  : `<span>${escapeHTML((user.name || "U").charAt(0).toUpperCase())}</span>`
                }
              </div>

              <div class="recipient-info">
                <strong>
                  ${escapeHTML(user.name || user.email || "User")}
                  ${user.verified ? `<span class="verified-badge">✓ Pastor</span>` : ""}
                </strong>

                <small>
                  ${escapeHTML(user.role || "member")}
                  ${user.church ? ` • ${escapeHTML(user.church)}` : ""}
                  ${user.city ? ` • ${escapeHTML(user.city)}` : ""}
                  ${user.country ? `, ${escapeHTML(user.country)}` : ""}
                </small>
              </div>

              <span class="recipient-add">
                ${selected ? "Selected" : "+ Add"}
              </span>
            </button>
          `;
        }).join("")
      : `<p class="text-muted">No users found.</p>`;

  } catch (err) {
    console.error("Recipient search failed:", err);
    results.innerHTML = `<p class="text-muted">Could not search users.</p>`;
  }
};


window.addPrayerRecipient = function (id, name, role, email = null) {
  const exists = prayerState.selectedRecipients.some(
    user => user.user_id === id
  );

  if (exists) return;

  prayerState.selectedRecipients.push({
    user_id: id,
    name,
    role,
    email
  });

  renderPrayerRecipients();

  const input = document.getElementById("recipientSearch");
  const results = document.getElementById("recipientResults");

  if (input) input.value = "";

  if (results) {
    results.innerHTML = `
      <p class="text-muted">
        Start typing a pastor or member's name...
      </p>
    `;
  }
};

window.removePrayerRecipient = function (id) {
  prayerState.selectedRecipients = prayerState.selectedRecipients.filter(
    user => user.user_id !== id
  );

  renderPrayerRecipients();
};

function renderPrayerRecipients() {
  const container = document.getElementById("selectedRecipients");

  if (!container) return;

  if (!prayerState.selectedRecipients.length) {
    container.innerHTML = `
      <p class="text-muted">No recipients selected.</p>
    `;
    return;
  }

  container.innerHTML = prayerState.selectedRecipients.map(user => {
    const initial = (user.name || "U").charAt(0).toUpperCase();

    return `
      <div class="recipient-chip-v2">
        <span class="recipient-chip-avatar">${escapeHTML(initial)}</span>

        <span class="recipient-chip-text">
          <strong>${escapeHTML(user.name || "User")}</strong>
          <small>${escapeHTML(user.role || "member")}</small>
        </span>

        <button onclick="removePrayerRecipient(${user.user_id})">×</button>
      </div>
    `;
  }).join("");
}

// =====================================
// LIVE PRAYER UPDATES
// =====================================

function startPrayerLiveUpdates() {

  stopPrayerLiveUpdates();

  prayerLiveTimer = setInterval(async () => {

    // Only run while Prayer Wall is open
    if (window.currentPage !== "prayer") return;

    try {

      // Refresh analytics
      await loadPrayerAnalytics();

      // Refresh notification badge
      if (typeof refreshPrayerNotifications === "function") {
        await refreshPrayerNotifications();
      }

      // Refresh notification drawer
      await loadPrayerNotifications();

      // Refresh current view
      switch (prayerState.view) {

        case "wall":
          await loadPrayerFeed(true);
          break;

        case "inbox":
          await loadPrayerInbox();
          break;

        case "sent":
          await loadSentPrayers();
          break;
      }

    } catch (err) {

      console.error(
        "Prayer live update failed:",
        err
      );

    }

  }, 30000);

}

function stopPrayerLiveUpdates() {
  if (prayerLiveTimer) {
    clearInterval(prayerLiveTimer);
    prayerLiveTimer = null;
  }
}

window.stopPrayerLiveUpdates = stopPrayerLiveUpdates;


})();