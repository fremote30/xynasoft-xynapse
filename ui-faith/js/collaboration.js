// =====================================
// COLLABORATION.JS
// STEP 1R — COLLABORATION + LIBRARY
// =====================================

(() => {

  // =====================================
  // SHORTCUT
  // =====================================
  const $ = (id) =>
    document.getElementById(id);

  // =====================================
  // STORAGE
  // =====================================
  const {
    get,
    set,
    remove
  } = storage || {};

  // =====================================
  // OPEN SERMON
  // =====================================
window.openSermon = async function (id) {

  try {

    const res = await apiFetch(`/api/sermon/${id}`);

    if (!res.ok) {
      throw new Error("Failed to load sermon");
    }

    const data = await res.json();

    const sermon = data.content || data;

    // =========================
    // GLOBAL STATE
    // =========================
    window.currentGeneratedSermon = sermon;
    window.currentSermonId = id;

    storage?.set?.("latest_sermon", sermon);

    // =========================
    // NAVIGATE FIRST
    // =========================
    await navigate("sermon");

    // =========================
    // SAFE RENDER (no race condition)
    // =========================
    requestAnimationFrame(() => {

      if (typeof renderCurrentSermon === "function") {
        renderCurrentSermon(sermon);
      }

    });

  } catch (err) {
    console.error("openSermon error:", err);
  }
};

// =====================================
// CONTINUE EDITING
// =====================================
async function continueEditing(
  sermonId
) {
  const normalizedSermonId =
    Number(sermonId);

  if (!normalizedSermonId) {
    showToast?.(
      "Sermon ID is missing",
      "error"
    );

    return;
  }

  // Use the same reliable loader used by
  // Continue Reading and shared sermons.
  if (
    typeof window.openSavedSermon !==
    "function"
  ) {
    showToast?.(
      "Sermon loader is unavailable",
      "error"
    );

    return;
  }

  try {
    await window.openSavedSermon(
      normalizedSermonId
    );

    showToast?.(
      "✍ Sermon ready for editing",
      "success"
    );

  } catch (err) {
    console.error(
      "Continue editing error:",
      err
    );

    showToast?.(
      err.message ||
      "Unable to load sermon",
      "error"
    );
  }
}

  // =====================================
  // LOAD SELECTED SERMON
  // =====================================
  async function loadSelectedSermon() {
    if (window.__openingSavedSermon) {
      console.log(
        "⏭ Skipping loadSelectedSermon during saved-sermon navigation"
      );

      return;
    }

    const id =
      localStorage.getItem(
        "selected_sermon_id"
      );

    if (!id) return;

    try {

      const res =
        await apiFetch(
          `/api/sermon/${id}`
        );

      if (!res.ok) {

        throw new Error(
          "Failed to load sermon"
        );
      }

      const data =
        await res.json();

      window.currentGeneratedSermon =
        data.content;

      set(
        "latest_sermon",
        data.content
      );

      renderCurrentSermon(
        data.content
      );

      if ($("userInput")) {

        $("userInput").value =
          data.content?.title || "";
      }

    } catch (err) {

      console.error(
        "Load sermon error:",
        err
      );

      showToast(
        "Failed to load sermon",
        "error"
      );
    }
  }

// =====================================
// RENDER SERMON CARDS
// =====================================
function renderSermonCards(sermons) {

  const container = $("sermonList");

  if (!container) return;

  container.innerHTML = "";

  // =====================================
  // EMPTY STATE
  // =====================================
  if (!sermons.length) {

    container.innerHTML = `

      <div class="feature-card">

        <h3>
          No sermons found
        </h3>

        <p>
          Try another search term.
        </p>

      </div>

    `;

    return;
  }

  // =====================================
  // PAGINATION
  // =====================================
  const visibleSermons =
    sermons.slice(
      0,
      window.currentSermonPage *
      window.SERMONS_PER_PAGE
    );

  // =====================================
  // RENDER CARDS
  // =====================================
  visibleSermons.forEach(
    (sermon) => {

      const card =
        document.createElement("div");

      card.className =
        "feature-card sermon-library-card";

      card.setAttribute(
        "data-sermon-id",
        sermon.id
      );

      const title =
        sermon.title ||
        "Untitled Sermon";

      let dateText = "";

      try {

        dateText =
          sermon.created_at
            ? new Date(
                sermon.created_at
              ).toLocaleDateString()
            : "";

      } catch (e) {}

      const preview =
        window.safeSermonText(
          sermon.content
        ).substring(0, 80);

      card.innerHTML = `
        <div class="sermon-library-top">

          <div>

            <h3>${title}</h3>

            <small>
              ${dateText}
            </small>

          </div>

        </div>

        <div class="sermon-library-body">

          <p>
            ${preview}
          </p>

        </div>

        <div class="sermon-library-stats">

          <span>
            👁 ${sermon.views ?? 0}
          </span>

          <span>
            🔄 ${sermon.shares ?? 0}
          </span>

        </div>

        <div class="sermon-library-actions">

          <button
            class="btn-primary js-view"
          >
            👁 View
          </button>

          <button
            class="btn-secondary js-edit"
          >
            ✍ Continue Editing
          </button>

          <button
            class="btn-secondary js-favorite"
          >
            ⭐ Favorite
          </button>

          <button
            class="btn-secondary js-delete"
          >
            🗑 Delete
          </button>

        </div>
      `;

      // =====================================
      // VIEW
      // =====================================
      card.querySelector(".js-view")
        .addEventListener(
          "click",
          () => {

            if (
              window.openSermon
            ) {

              window.openSermon(
                sermon.id
              );
            }
          }
        );

      // =====================================
      // EDIT
      // =====================================
      card.querySelector(".js-edit")
        .addEventListener(
          "click",
          () => {

            if (
              typeof continueEditing
              === "function"
            ) {

              continueEditing(
                sermon.id
              );
            }
          }
        );

      // =====================================
      // FAVORITE
      // (future feature)
      // =====================================
      card.querySelector(".js-favorite")
        .addEventListener(
          "click",
          () => {

            showToast?.(
              "⭐ Favorites coming soon",
              "info"
            );
          }
        );

      // =====================================
      // DELETE
      // =====================================
      card.querySelector(".js-delete")
        .addEventListener(
          "click",
          async () => {

            await deleteSermon?.(
              sermon.id
            );
          }
        );

      container.appendChild(card);
    }
  );

  // =====================================
  // LOAD MORE BUTTON
  // =====================================
  const existingLoadMore =
    document.getElementById(
      "loadMoreSermons"
    );

  if (existingLoadMore) {
    existingLoadMore.remove();
  }

  if (
    sermons.length >
    visibleSermons.length
  ) {

    const remaining =
      sermons.length -
      visibleSermons.length;

    const btn =
      document.createElement(
        "button"
      );

    btn.id =
      "loadMoreSermons";

    btn.className =
      "btn-primary";

    btn.style.margin =
      "20px auto";

    btn.style.display =
      "block";

    btn.innerHTML =
      `Load More (${remaining} remaining)`;

    btn.onclick = () => {

      window.currentSermonPage++;

      renderSermonCards(
        sermons
      );
    };

    container.appendChild(btn);
  }
}


// =====================================
// LOAD MY SERMONS (STABLE VERSION)
// =====================================
async function loadMySermons() {

  // =========================
  // 🔒 GUARD (PREVENT DOUBLE LOAD)
  // =========================
  if (window.__mySermonsLoading) return;

  window.__mySermonsLoading = true;

  const container = $("sermonList");

  if (!container) {

    window.__mySermonsLoading = false;

    return;
  }

  try {

    // =========================
    // LOADING STATE
    // =========================
    container.innerHTML = `
      <div class="feature-card">
        <p>⏳ Loading sermons...</p>
      </div>
    `;

    // =========================
    // FETCH DATA
    // =========================
    const res = await apiFetch(
      "/api/sermon/my"
    );

    if (!res.ok) {

      throw new Error(
        "Failed to load sermons"
      );
    }

    let sermons =
      await res.json();

    if (
      !Array.isArray(
        sermons
      )
    ) {

      sermons = [];
    }

    // =====================================
    // RESET PAGINATION
    // =====================================
    window.currentSermonPage = 1;

    // =====================================
    // STORE FOR SEARCH/SORT
    // =====================================
    window.allSermons =
      sermons;

    // =====================================
    // COUNTER
    // =====================================
    const sermonCount =
      document.getElementById(
        "sermonCount"
      );

    if (sermonCount) {

      sermonCount.textContent =
        sermons.length;
    }

    // =========================
    // EMPTY STATE
    // =========================
    if (
      sermons.length === 0
    ) {

      container.innerHTML = `
        <div class="feature-card">

          <h3>
            No sermons yet
          </h3>

          <p>
            Generate and save sermons to see them here.
          </p>

          <button
            class="btn-primary"
            onclick="navigate('sermon')"
          >
            ✨ Open Sermon Studio
          </button>

        </div>
      `;

      return;
    }

    // =========================
    // CLEAR CONTAINER
    // =========================
    container.innerHTML = "";

    // =========================
    // RENDER CARDS
    // =========================
    renderSermonCards(
      sermons
    );

    initializeSermonTabs();

    // =========================
    // SEARCH
    // =========================
    const searchInput =
      document.getElementById(
        "sermonSearch"
      );

    if (searchInput) {

      searchInput.oninput =
        filterSermons;
    }

    // =========================
    // SORT
    // =========================
    const sortSelect =
      document.getElementById(
        "sermonSort"
      );

    if (sortSelect) {

      sortSelect.onchange =
        sortSermons;
    }

  } catch (err) {

    console.error(
      "Load sermons error:",
      err
    );

    container.innerHTML = `
      <div class="feature-card">

        <h3>
          Failed to load sermons
        </h3>

        <p>
          Please try again later.
        </p>

      </div>
    `;

  } finally {

    // =========================
    // RESET LOCK
    // =========================
    window.__mySermonsLoading =
      false;
  }

  

}


// =====================================
// FILTER SERMONS
// =====================================
function filterSermons() {

  const search =
    document.getElementById(
      "sermonSearch"
    );

  if (
    !search ||
    !window.allSermons
  ) {
    return;
  }

  const term =
    search.value
      .toLowerCase()
      .trim();

  // =====================================
  // FILTER
  // =====================================
  let filtered =
    window.allSermons.filter(
      sermon => {

        const title =
          (
            sermon.title || ""
          ).toLowerCase();

        const content =
          window.safeSermonText(
            sermon.content
          )
          .toLowerCase();

        return (
          title.includes(term) ||
          content.includes(term)
        );
      }
    );

  // =====================================
  // APPLY CURRENT SORT
  // =====================================
  const sortSelect =
    document.getElementById(
      "sermonSort"
    );

  if (sortSelect) {

    switch (
      sortSelect.value
    ) {

      case "title":

        filtered.sort(
          (a, b) =>
            (a.title || "")
              .localeCompare(
                b.title || ""
              )
        );

        break;

      case "oldest":

        filtered.sort(
          (a, b) =>
            new Date(
              a.created_at
            ) -
            new Date(
              b.created_at
            )
        );

        break;

      case "mostViewed":

        filtered.sort(
          (a, b) =>
            (b.views || 0) -
            (a.views || 0)
        );

        break;

      case "mostShared":

        filtered.sort(
          (a, b) =>
            (b.shares || 0) -
            (a.shares || 0)
        );

        break;

      default:

        filtered.sort(
          (a, b) =>
            new Date(
              b.created_at
            ) -
            new Date(
              a.created_at
            )
        );
    }
  }

  // =====================================
  // RESET PAGINATION
  // =====================================
  window.currentSermonPage = 1;

  // =====================================
  // RE-RENDER RESULTS
  // =====================================
  renderSermonCards(
    filtered
  );

      const count =
      document.getElementById(
        "searchResultsCount"
      );

    if (count) {

              if (term) {

          count.textContent =
            `${filtered.length} sermon(s) found`;

        } else {

          count.textContent = "";
        }
    }
}


// =====================================
// SORT SERMONS
// =====================================
function sortSermons() {

  const select =
    document.getElementById(
      "sermonSort"
    );

  if (
    !select ||
    !window.allSermons
  ) {
    return;
  }

  let sermons =
    [...window.allSermons];

  switch (
    select.value
  ) {

    // =========================
    // TITLE A-Z
    // =========================
    case "title":

      sermons.sort(
        (a, b) =>
          (a.title || "")
            .localeCompare(
              b.title || ""
            )
      );

      break;

    // =========================
    // OLDEST FIRST
    // =========================
    case "oldest":

      sermons.sort(
        (a, b) =>
          new Date(
            a.created_at
          ) -
          new Date(
            b.created_at
          )
      );

      break;

    // =========================
    // MOST VIEWED
    // =========================
    case "mostViewed":

      sermons.sort(
        (a, b) =>
          (b.views || 0) -
          (a.views || 0)
      );

      break;

    // =========================
    // MOST SHARED
    // =========================
    case "mostShared":

      sermons.sort(
        (a, b) =>
          (b.shares || 0) -
          (a.shares || 0)
      );

      break;

    // =========================
    // NEWEST FIRST (DEFAULT)
    // =========================
    default:

      sermons.sort(
        (a, b) =>
          new Date(
            b.created_at
          ) -
          new Date(
            a.created_at
          )
      );
  }

  // =========================
  // RESET PAGINATION
  // =========================
  window.currentSermonPage = 1;

  // =========================
  // RE-RENDER
  // =========================
  renderSermonCards(
    sermons
  );
}
  // =====================================
  // LOAD SHARED SERMONS
  // =====================================
async function loadSharedSermons() {

  const container = document.getElementById("sharedList");
  if (!container) return;

  try {

    // =========================
    // LOADING STATE
    // =========================
    container.innerHTML = `
      <div class="feature-card">
        <p>⏳ Loading shared sermons...</p>
      </div>
    `;

    // =========================
    // FETCH DATA
    // =========================
    const response = await apiFetch(
      "/api/v1/faith/shared-sermons"
    );

    if (!response.ok) {
      throw new Error("Failed to load shared sermons");
    }

    const data = await response.json();

    // =========================
    // NORMALIZE RESPONSE SAFELY
    // =========================
    const shared = Array.isArray(data)
      ? data
      : (data.shared_sermons || []);
 
      const sharedCount =
        document.getElementById("sharedCount");

      if (sharedCount) {
        sharedCount.textContent = shared.length;
      }


    // =========================
    // EMPTY STATE
    // =========================
    if (!shared.length) {
      container.innerHTML = `
        <div class="empty-state">
          <h3>No shared sermons yet</h3>
          <p>When pastors share sermons with you, they will appear here.</p>
        </div>
      `;
      return;
    }

    // =========================
    // RENDER LIST
    // =========================
    container.innerHTML = "";

    shared.forEach(item => {

      const card = document.createElement("div");
      card.className = "feature-card sermon-card";

      const title = item.title || "Untitled Sermon";
      const sender = item.sender_name || "Unknown Pastor";

      card.innerHTML = `
        <h3>${title}</h3>

        <p>
          Shared by: ${sender}
        </p>

        <button class="btn-primary js-open">
          📖 Open Sermon
        </button>
      `;

      // =========================
      // EVENT BINDING (SAFE)
      // =========================
      card.querySelector(".js-open")
        .addEventListener("click", () => {

          if (typeof openSavedSermon === "function") {
            openSavedSermon(item.sermon_id);
          } else {
            console.warn("openSavedSermon() not found");
          }

        });

      container.appendChild(card);
    });

  } catch (err) {

    console.error("Load shared sermons error:", err);

    showToast(
      "Unable to load shared sermons",
      "error"
    );

    container.innerHTML = `
      <div class="feature-card">
        <h3>Failed to load shared sermons</h3>
        <p>Please try again later.</p>
      </div>
    `;
  }
}

// =====================================
// OPEN SAVED SERMON
// =====================================
async function openSavedSermon(
  sermonId
) {
  const normalizedSermonId =
    Number(sermonId);

  if (!normalizedSermonId) {
    showToast?.(
      "Sermon ID is missing",
      "error"
    );

    return;
  }

  // Prevent router.js and sermon.js from
  // restoring another cached sermon while
  // this sermon is opening.
  window.__openingSavedSermon =
    true;

  try {
    // =====================================
    // LOAD FULL SERMON
    // =====================================
    const response =
      await apiFetch(
        `/api/v1/faith/sermon/${normalizedSermonId}`
      );

    const data =
      await response
        .json()
        .catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data.detail ||
        "Failed to open sermon"
      );
    }

    const sermon =
      data.sermon ||
      data;

    if (
      !sermon ||
      !sermon.id
    ) {
      throw new Error(
        "Sermon data missing"
      );
    }

    const resolvedSermonId =
      Number(
        sermon.id ||
        normalizedSermonId
      );

    console.log(
      "📖 Loaded saved sermon:",
      sermon
    );

    // =====================================
    // RECORD RECENT SERMON FOR MEMBERS
    // =====================================
    if (
      window.currentUser?.role ===
      "member"
    ) {
      try {
        const recentResponse =
          await apiFetch(
            `/api/v1/member-profile/recent-sermon/${resolvedSermonId}`,
            {
              method: "POST"
            }
          );

        if (!recentResponse.ok) {
          const recentError =
            await recentResponse
              .json()
              .catch(() => ({}));

          console.warn(
            "Recent sermon tracking failed:",
            recentError.detail ||
            recentResponse.status
          );
        }

      } catch (recentErr) {
        console.warn(
          "Could not record recent sermon:",
          recentErr
        );
      }
    }

    // =====================================
    // STORE BEFORE NAVIGATION
    // =====================================
    window.currentGeneratedSermon =
      sermon;

    window.currentSermonId =
      resolvedSermonId;

    if (
      typeof set ===
      "function"
    ) {
      set(
        "latest_sermon",
        sermon
      );
    }

    const currentUserId =
      window.currentUser?.id;

    const userDraftKey =
      currentUserId
        ? `latest_sermon_${currentUserId}`
        : null;

    if (userDraftKey) {
      localStorage.setItem(
        userDraftKey,
        JSON.stringify(
          sermon
        )
      );
    }

    // =====================================
    // NAVIGATE TO SERMON STUDIO
    // =====================================
    await navigate(
      "sermon"
    );

    const output =
      await waitForElement(
        "sermonOutput",
        5000
      );

    if (!output) {
      throw new Error(
        "Sermon workspace did not load"
      );
    }

    // Allow the dynamically injected page
    // and its bindings to finish.
    await new Promise(resolve =>
      requestAnimationFrame(() =>
        requestAnimationFrame(resolve)
      )
    );

    // =====================================
    // RESTORE STATE AFTER NAVIGATION
    // =====================================
    window.currentGeneratedSermon =
      sermon;

    window.currentSermonId =
      resolvedSermonId;

    if (
      typeof set ===
      "function"
    ) {
      set(
        "latest_sermon",
        sermon
      );
    }

    if (userDraftKey) {
      localStorage.setItem(
        userDraftKey,
        JSON.stringify(
          sermon
        )
      );
    }

    // =====================================
    // RENDER SERMON
    // renderCurrentSermon now handles:
    // - restoring form fields
    // - global state
    // - ownership
    // - read-only mode
    // - output rendering
    // - comments
    // =====================================
    if (
      typeof window.renderCurrentSermon !==
      "function"
    ) {
      throw new Error(
        "Sermon renderer is unavailable"
      );
    }

    window.renderCurrentSermon(
      sermon,
      false
    );

    // =====================================
    // SHOW OUTPUT WORKSPACE
    // =====================================
    if (
      typeof window.showMobileTab ===
      "function"
    ) {
      window.showMobileTab(
        "output"
      );
    }

    showToast?.(
      "✅ Sermon opened",
      "success"
    );

  } catch (err) {
    console.error(
      "Open sermon error:",
      err
    );

    showToast?.(
      err.message ||
      "Failed to open sermon",
      "error"
    );

  } finally {
    window.__openingSavedSermon =
      false;
  }
}


  // =====================================
  // SHARE WITH PASTOR
  // =====================================
  async function shareWithPastor(){

    try {

      const sermonId =
        window.currentSermonId;

      if (!sermonId) {

        showToast(
          "Save sermon first",
          "error"
        );

        return;
      }

      const pastorId =
        window.selectedPastorId;

      if (!pastorId) {

        showToast(
          "Select a pastor first",
          "error"
        );

        return;
      }

      const comment =
        document.getElementById(
          "sharePastorComment"
        )?.value || "";

      const response =
        await apiFetch(

          "/api/v1/faith/sermon/share",

          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json"
            },

            body: JSON.stringify({

              sermon_id:
                sermonId,

              to_pastor_id:
                pastorId,

              comment:
                comment
            })
          }
        );

      const data =
        await response.json();

      if (!response.ok) {

        throw new Error(
          data.detail ||
          "Failed to share sermon"
        );
      }

      closePastorShareModal?.();

      const commentInput =
        document.getElementById(
          "sharePastorComment"
        );

      if (commentInput) {

        commentInput.value = "";
      }

      showToast(
        "✅ Sermon shared successfully",
        "success"
      );

    } catch (err) {

      console.error(
        "Share error:",
        err
      );

      showToast(
        err.message ||
        "Share failed",
        "error"
      );
    }
  }

  // =====================================
  // SEARCH PASTORS
  // =====================================
  async function searchPastors(
    query
  ){

    const resultsContainer =
      document.getElementById(
        "pastorSearchResults"
      );

    if(!resultsContainer){
      return;
    }

    if(
      !query ||
      query.length < 2
    ){

      resultsContainer.innerHTML =
        "";

      return;
    }

    try {

      const response =
        await apiFetch(

          `/api/v1/faith/pastors/search?q=${query}`

        );

      if(!response.ok){

        throw new Error(
          "Failed to search pastors"
        );
      }

      const data =
        await response.json();

      const pastors =
        data.pastors || [];

      resultsContainer.innerHTML =
        pastors.map(pastor => `

          <div

            onclick="
              selectPastor(
                ${pastor.id},
                '${pastor.name}'
              )
            "

            style="
              padding:14px;
              border-radius:14px;
              background:#F8FAFC;
              cursor:pointer;
            "
          >

            <div>
              ${pastor.name}
            </div>

          </div>

        `).join("");

    } catch(err){

      console.error(
        "Search pastors error:",
        err
      );
    }
  }

  // =====================================
  // SELECT PASTOR
  // =====================================
  function selectPastor(
    id,
    name
  ){

    window.selectedPastorId =
      id;

    const selected =
      document.getElementById(
        "selectedPastor"
      );

    if(selected){

      selected.style.display =
        "block";

      selected.innerHTML = `

        ✅ Selected Pastor:
        <strong>${name}</strong>

      `;
    }

    const results =
      document.getElementById(
        "pastorSearchResults"
      );

    if(results){

      results.innerHTML = "";
    }

    const input =
      document.getElementById(
        "pastorSearchInput"
      );

    if(input){

      input.value = name;
    }
  }

  // =====================================
  // LOAD COMMENTS
  // =====================================
  async function loadSermonComments(
    sermonId
  ){

    const container =
      document.getElementById(
        "sermonComments"
      );

    if(!container){
      return;
    }

    try {

      const response =
        await apiFetch(

          `/api/v1/faith/comments/${sermonId}`

        );

      if(!response.ok){

        throw new Error(
          "Failed to load comments"
        );
      }

      const data =
        await response.json();

      const comments =
        data.comments || [];

      container.innerHTML =
        comments.map(comment => `

          <div
            class="comment-card"
          >

            <strong>
              ${comment.pastor_name}
            </strong>

            <p>
              ${comment.comment}
            </p>

          </div>

        `).join("");

    } catch(err){

      console.error(
        "Load comments error:",
        err
      );
    }
  }

  // =====================================
  // SUBMIT COMMENT
  // =====================================
  async function submitComment(){

    try {

      const sermonId =
        window.currentSermonId;

      if(!sermonId){

        showToast(
          "Open sermon first",
          "error"
        );

        return;
      }

      const input =
        document.getElementById(
          "sermonCommentInput"
        );

      const comment =
        input?.value?.trim();

      if(!comment){

        showToast(
          "Enter comment",
          "error"
        );

        return;
      }

      const response =
        await apiFetch(

          `/api/v1/faith/comments/${sermonId}`,

          {
            method: "POST",

            body: JSON.stringify({
              comment
            })
          }
        );

      if(!response.ok){

        throw new Error(
          "Failed to add comment"
        );
      }

      if(input){

        input.value = "";
      }

      await loadSermonComments(
        sermonId
      );

      showToast(
        "✅ Comment added",
        "success"
      );

    } catch(err){

      console.error(
        "Comment error:",
        err
      );

      showToast(
        "Comment failed",
        "error"
      );
    }
  }


  // =====================================
// FOLLOW PASTOR
// =====================================
async function followPastor(
  pastorId,
  button = null
){

  let originalText = "";

  try {

    // ============================
    // LOADING STATE
    // ============================
    if (button) {

      originalText = button.textContent;

      button.disabled = true;

      button.textContent = "Following...";

    }

    const res =
      await apiFetch(

        `/api/v1/pastors/${pastorId}/follow`,

        {
          method: "POST"
        }

      );

    if (!res.ok) {

      throw new Error(
        "Failed to follow pastor"
      );

    }

    showToast(
      "Pastor followed",
      "success"
    );

    // Refresh platform widgets
    await loadNetworkOverview();

    // ============================
    // SUCCESS STATE
    // ============================
    if (button) {

      button.disabled = false;

      button.textContent = "Following";

      button.classList.remove(
        "btn-primary"
      );

      button.classList.add(
        "btn-secondary"
      );

      button.onclick = function(event){

        event.stopPropagation();

        unfollowPastor(
          pastorId,
          this
        );

      };

    }

  } catch (err) {

    console.error(
      "Follow error:",
      err
    );

    showToast(
      "Follow failed",
      "error"
    );

    // Restore button
    if (button) {

      button.disabled = false;

      button.textContent =
        originalText || "Follow";

    }

  }

}

// =====================================
// UNFOLLOW PASTOR
// =====================================
async function unfollowPastor(
  pastorId,
  button = null
){

  let originalText = "";

  try {

    // ============================
    // LOADING STATE
    // ============================
    if (button) {

      originalText = button.textContent;

      button.disabled = true;

      button.textContent = "Unfollowing...";

    }

    const res =
      await apiFetch(

        `/api/v1/pastors/${pastorId}/unfollow`,

        {
          method: "DELETE"
        }

      );

    if (!res.ok) {

      throw new Error(
        "Failed to unfollow pastor"
      );

    }

    showToast(
      "Pastor unfollowed",
      "success"
    );

    // Refresh platform widgets
    await loadNetworkOverview();

    // ============================
    // SUCCESS STATE
    // ============================
    if (button) {

      button.disabled = false;

      button.textContent = "Follow";

      button.classList.remove(
        "btn-secondary"
      );

      button.classList.add(
        "btn-primary"
      );

      button.onclick = function(event){

        event.stopPropagation();

        followPastor(
          pastorId,
          this
        );

      };

    }

  } catch (err) {

    console.error(
      "Unfollow error:",
      err
    );

    showToast(
      "Unfollow failed",
      "error"
    );

    // Restore button
    if (button) {

      button.disabled = false;

      button.textContent =
        originalText || "Following";

    }

  }

}

  // =====================================
// SERMON TABS
// =====================================
function initializeSermonTabs() {

  const tabMine =
    document.getElementById(
      "tabMine"
    );

  const tabShared =
    document.getElementById(
      "tabShared"
    );

  const sermonList =
    document.getElementById(
      "sermonList"
    );

  const sharedSection =
    document.getElementById(
      "sharedSection"
    );

  if (
    !tabMine ||
    !tabShared ||
    !sermonList ||
    !sharedSection
    )  {
    return;
  }

  // Default
  sharedSection.style.display =
    "none";

  tabMine.onclick = () => {

    tabMine.classList.add(
      "active"
    );

    tabShared.classList.remove(
      "active"
    );

    sermonList.style.display =
      "";

    sharedSection.style.display =
      "none";
  };

  tabShared.onclick = () => {

    tabShared.classList.add(
      "active"
    );

    tabMine.classList.remove(
      "active"
    );

    sermonList.style.display =
      "none";

    sharedSection.style.display =
      "";
  };
}
  // =====================================
  // GLOBAL EXPORTS
  // =====================================

  window.loadMySermons =
    loadMySermons;

  window.loadSharedSermons =
    loadSharedSermons;

  window.openSavedSermon =
    openSavedSermon;

  window.openSermon =
    openSermon;

  window.loadSelectedSermon =
    loadSelectedSermon;

  window.continueEditing =
    continueEditing;

  window.shareWithPastor =
    shareWithPastor;

  window.searchPastors =
    searchPastors;

  window.selectPastor =
    selectPastor;

  window.loadSermonComments =
    loadSermonComments;

  window.submitComment =
    submitComment;

  window.followPastor =
    followPastor;

  window.unfollowPastor =
    unfollowPastor;

})();