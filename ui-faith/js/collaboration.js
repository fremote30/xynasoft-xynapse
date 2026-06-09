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
  async function openSermon(id) {

    try {

      localStorage.setItem(
        "selected_sermon_id",
        id
      );

      await navigate(
        "sermon"
      );

    } catch (err) {

      console.error(
        "Open sermon error:",
        err
      );

      showToast(
        "Unable to open sermon",
        "error"
      );
    }
  }

  // =====================================
  // CONTINUE EDITING
  // =====================================
  async function continueEditing(
    sermonId
  ) {

    try {

      const res =
        await apiFetch(
          `/api/sermon/${sermonId}`
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

      await navigate(
        "sermon"
      );

      renderCurrentSermon(
        data.content,
        false
      );

      if ($("userInput")) {

        $("userInput").value =
          data.content?.title || "";
      }

      showToast(
        "✍ Sermon loaded",
        "success"
      );

    } catch (err) {

      console.error(
        "Continue editing error:",
        err
      );

      showToast(
        "Unable to load sermon",
        "error"
      );
    }
  }

  // =====================================
  // LOAD SELECTED SERMON
  // =====================================
  async function loadSelectedSermon() {

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
  // LOAD MY SERMONS
  // =====================================
  async function loadMySermons() {

    try {

      const container =
        $("sermonList");

      if (!container) return;

      container.innerHTML = `

        <div class="feature-card">

          <p>
            ⏳ Loading sermons...
          </p>

        </div>

      `;

      const res =
        await apiFetch(
          "/api/sermon/my"
        );

      if (!res.ok) {

        throw new Error(
          "Failed to load sermons"
        );
      }

      const sermons =
        await res.json();

      if (!sermons.length) {

        container.innerHTML = `

          <div class="feature-card">

            <h3>
              No sermons yet
            </h3>

            <p>
              Generate and save sermons
              to see them here.
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

      container.innerHTML =
        sermons.map(sermon => `

          <div
            class="
              feature-card
              sermon-library-card
            "
          >

            <div
              class="sermon-library-top"
            >

              <div>

                <h3>
                  ${
                    sermon.title ||
                    "Untitled Sermon"
                  }
                </h3>

                <small>
                  ${formatDate(
                    sermon.created_at
                  )}
                </small>

              </div>

            </div>

            <div
              class="sermon-library-body"
            >

              <p>

                ${
                  sermon.content
                    ?.introduction

                    ? sermon.content
                        .introduction
                        .substring(0, 180)

                    : "Saved sermon"
                }...

              </p>

            </div>

            <div
              class="
                sermon-library-stats
              "
            >

              <span>
                👁 ${sermon.views || 0}
              </span>

              <span>
                🔄 ${sermon.shares || 0}
              </span>

            </div>

            <div
              class="
                sermon-library-actions
              "
            >

              <button
                class="btn-primary"

                onclick="
                  openSermon(${sermon.id})
                "
              >
                👁 View
              </button>

              <button
                class="btn-secondary"

                onclick="
                  continueEditing(${sermon.id})
                "
              >
                ✍ Continue Editing
              </button>

              <button
                class="btn-secondary"

                onclick="
                  deleteSermon(${sermon.id})
                "
              >
                🗑 Delete
              </button>

            </div>

          </div>

        `).join("");

    } catch (err) {

      console.error(
        "Load sermons error:",
        err
      );

      const container =
        $("sermonList");

      if (container) {

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
      }
    }
  }

  // =====================================
  // LOAD SHARED SERMONS
  // =====================================
  async function loadSharedSermons(){

    const container =
      document.getElementById(
        "sharedList"
      );

    if(!container){
      return;
    }

    try {

      const response =
        await apiFetch(
          "/api/v1/faith/sermon/shared-with-me"
        );

      if(!response.ok){

        throw new Error(
          "Failed to load shared sermons"
        );
      }

      const data =
        await response.json();

      const shared =
        data.shared_sermons || [];

      if(!shared.length){

        container.innerHTML = `

          <div class="empty-state">

            <h3>
              No shared sermons yet
            </h3>

          </div>

        `;

        return;
      }

      container.innerHTML =
        shared.map(item => `

          <div
            class="
              feature-card
              sermon-card
            "
          >

            <h3>
              ${item.title}
            </h3>

            <p>
              Shared by:
              ${item.sender_name}
            </p>

            <button

              onclick="
                openSavedSermon(
                  ${item.sermon_id}
                )
              "
            >
              📖 Open Sermon
            </button>

          </div>

        `).join("");

    } catch(err){

      console.error(
        "Load shared sermons error:",
        err
      );

      showToast(
        "Unable to load shared sermons",
        "error"
      );
    }
  }

  // =====================================
  // OPEN SAVED SERMON
  // =====================================
  async function openSavedSermon(
    sermonId
  ){

    try {

      const response =
        await apiFetch(

          `/api/v1/faith/sermon/${sermonId}`

        );

      if(!response.ok){

        throw new Error(
          "Failed to open sermon"
        );
      }

      const data =
        await response.json();

      const sermon =
        data.sermon;

      window.currentGeneratedSermon =
        sermon;

      window.currentSermonId =
        sermonId;

      set(
        "latest_sermon",
        sermon
      );

      await navigate(
        "sermon"
      );

      const output =
        await waitForElement(
          "sermonOutput"
        );

      if(output){

        renderCurrentSermon(
          sermon
        );

        if(
          window.currentSermonId
        ){

          loadSermonComments(
            window.currentSermonId
          );
        }
      }

      showToast(
        "✅ Sermon opened",
        "success"
      );

    } catch(err){

      console.error(
        "Open sermon error:",
        err
      );

      showToast(
        "Failed to open sermon",
        "error"
      );
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
    pastorId
  ){

    try {

      const res =
        await apiFetch(

          `/api/v1/pastors/${pastorId}/follow`,

          {
            method: "POST"
          }
        );

      if(!res.ok){

        throw new Error(
          "Failed to follow pastor"
        );
      }

      showToast(
        "Pastor followed",
        "success"
      );

      await loadPastors?.();

    } catch(err){

      console.error(
        "Follow error:",
        err
      );

      showToast(
        "Follow failed",
        "error"
      );
    }
  }

  // =====================================
  // UNFOLLOW PASTOR
  // =====================================
  async function unfollowPastor(
    pastorId
  ){

    try {

      const res =
        await apiFetch(

          `/api/v1/pastors/${pastorId}/unfollow`,

          {
            method: "DELETE"
          }
        );

      if(!res.ok){

        throw new Error(
          "Failed to unfollow"
        );
      }

      showToast(
        "Pastor unfollowed",
        "success"
      );

      await loadPastors?.();

    } catch(err){

      console.error(
        "Unfollow error:",
        err
      );

      showToast(
        "Unfollow failed",
        "error"
      );
    }
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