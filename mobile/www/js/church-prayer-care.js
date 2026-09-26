(() => {
  "use strict";

  const state = {
    churchId: null,
    currentUserId: null,
    capabilities: {},
    prayers: [],
    testimonies: [],
    pendingTestimonies: [],
    cases: [],
    assignees: [],
    activeCaseId: null
  };

  const $ = (id) => document.getElementById(id);

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatStatus(value) {
    return String(value || "")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function formatDateTime(value) {
    if (!value) return "Not scheduled";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return String(value);
    }

    return date.toLocaleString();
  }

  function show(id, visible) {
    const element = $(id);
    if (element) element.hidden = !visible;
  }

  function api(path, options) {
    return window.apiFetch(path, options);
  }

  function prayerBadge(prayer) {
    if (prayer.status === "answered") {
      return "Answered";
    }

    if (prayer.status === "partially_answered") {
      return "Partially Answered";
    }

    return "Still Praying";
  }

  function privacyLabel(prayer) {
    if (prayer.visibility === "community") {
      return "Church Community";
    }

    return "Private";
  }

  function testimonyMarkup(prayer) {
    if (
      prayer.status !== "answered" ||
      !prayer.answer_testimony
    ) {
      return "";
    }

    if (prayer.testimony_status === "pending") {
      return `
        <div class="church-community-item">
          <strong>Testimony submitted</strong>
          <p>
            Your testimony is waiting for church review
            before it appears on the Testimony Wall.
          </p>
        </div>
      `;
    }

    if (prayer.testimony_status === "approved") {
      return `
        <div class="church-community-item">
          <strong>Testimony published</strong>
          <p>
            This answered-prayer testimony is now on the
            Testimony Wall.
          </p>
        </div>
      `;
    }

    if (prayer.testimony_status === "rejected") {
      return `
        <div class="church-community-item">
          <strong>Testimony reviewed</strong>
          <p>
            This testimony is not currently published on
            the Testimony Wall.
          </p>
        </div>
      `;
    }

    return `
      <div class="church-community-item">
        <strong>Answered Prayer</strong>
        <p>
          Your testimony is saved privately and has not
          been submitted for publication.
        </p>
      </div>
    `;
  }


  function ownerActions(prayer) {
    if (prayer.user_id !== state.currentUserId) {
      return "";
    }

    if (prayer.status === "answered") {
      return "";
    }

    return `
      <div>
        <button
          type="button"
          class="btn btn-secondary"
          data-prayer-partial="${prayer.id}"
        >
          Partially Answered
        </button>

        <button
          type="button"
          class="btn btn-primary"
          data-prayer-answered="${prayer.id}"
        >
          Mark Answered
        </button>
      </div>
    `;
  }

  function renderPrayers() {
    const list = $("churchPrayerList");
    if (!list) return;

    if (!state.prayers.length) {
      list.innerHTML = `
        <div class="church-community-item">
          <p>No church prayer requests yet.</p>
        </div>
      `;
      return;
    }

    list.innerHTML = state.prayers
      .map((prayer) => `
        <article class="church-community-item">
          <div class="section-heading">
            <div>
              <h3>
                ${escapeHtml(
                  prayer.is_anonymous
                    ? "Anonymous"
                    : prayer.user_name || "Church Member"
                )}
              </h3>

              <p>
                ${escapeHtml(privacyLabel(prayer))}
                •
                ${escapeHtml(prayerBadge(prayer))}
              </p>
            </div>
          </div>

          ${
            prayer.category
              ? `<p><strong>${escapeHtml(
                  prayer.category
                )}</strong></p>`
              : ""
          }

          <p>${escapeHtml(prayer.message)}</p>

          ${
            prayer.pastoral_care_requested
              ? `
                <p>
                  <strong>Pastoral follow-up requested</strong>
                </p>
              `
              : ""
          }

          ${testimonyMarkup(prayer)}
          ${ownerActions(prayer)}
        </article>
      `)
      .join("");
  }

  async function loadPrayers() {
    if (!state.churchId || !$("churchPrayerList")) {
      return;
    }

    try {
      const response = await api(
        `/api/v1/churches/${state.churchId}/prayers`
      );

      if (!response.ok) {
        throw new Error("Could not load church prayers");
      }

      const data = await response.json();

      state.prayers = Array.isArray(data.prayers)
        ? data.prayers
        : [];

      renderPrayers();
    } catch (error) {
      console.error("Church prayer load failed:", error);

      $("churchPrayerList").innerHTML = `
        <p>Church prayers could not be loaded.</p>
      `;
    }
  }

  function resetPrayerForm() {
    if ($("churchPrayerMessage")) {
      $("churchPrayerMessage").value = "";
    }

    if ($("churchPrayerCategory")) {
      $("churchPrayerCategory").value = "";
    }

    if ($("churchPrayerVisibility")) {
      $("churchPrayerVisibility").value = "community";
    }

    if ($("churchPrayerAnonymous")) {
      $("churchPrayerAnonymous").checked = false;
    }

    if ($("churchPrayerPastoralCare")) {
      $("churchPrayerPastoralCare").checked = false;
    }

    if ($("churchPrayerFormState")) {
      $("churchPrayerFormState").textContent = "";
    }
  }

  async function submitPrayer(event) {
    event.preventDefault();

    const message =
      $("churchPrayerMessage")?.value?.trim() || "";

    const formState = $("churchPrayerFormState");

    if (!message) {
      if (formState) {
        formState.textContent =
          "Please enter your prayer request.";
      }
      return;
    }

    const payload = {
      message,
      category:
        $("churchPrayerCategory")?.value || null,
      visibility:
        $("churchPrayerVisibility")?.value || "community",
      is_anonymous:
        Boolean($("churchPrayerAnonymous")?.checked),
      request_pastoral_care:
        Boolean($("churchPrayerPastoralCare")?.checked),
      recipient_user_ids: []
    };

    try {
      const response = await api(
        `/api/v1/churches/${state.churchId}/prayers`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(payload)
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(
          data.detail || "Prayer could not be submitted"
        );
      }

      resetPrayerForm();
      show("churchPrayerForm", false);

      await loadPrayers();

      if (state.capabilities.can_manage_pastoral_care) {
        await loadAssignees();
        await loadCases();
      }
    } catch (error) {
      console.error("Church prayer submit failed:", error);

      if (formState) {
        formState.textContent =
          error.message || "Prayer could not be submitted.";
      }
    }
  }

  async function updatePrayerStatus(
    prayerId,
    statusValue,
    testimony = null,
    shareTestimony = false
  ) {
    const response = await api(
      `/api/v1/churches/${state.churchId}/prayers/` +
        `${prayerId}/status`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          status: statusValue,
          answer_testimony: testimony,
          share_testimony: shareTestimony
        })
      }
    );

    if (!response.ok) {
      throw new Error("Prayer status could not be updated");
    }

    await loadPrayers();
  }

  async function markAnswered(prayerId) {
    const testimony = window.prompt(
      "How was this prayer answered? " +
        "You may leave this blank."
    );

    if (testimony === null) {
      return;
    }

    let share = false;

    if (testimony.trim()) {
      share = window.confirm(
        "Submit this testimony for your church Testimony Wall? " +
          "It will be reviewed before publication. " +
          "Choose Cancel to keep it private."
      );
    }

    try {
      await updatePrayerStatus(
        prayerId,
        "answered",
        testimony.trim() || null,
        share
      );
    } catch (error) {
      console.error("Answered prayer update failed:", error);
    }
  }

  function renderTestimonies() {
    const list = $("churchTestimonyList");
    if (!list) return;

    if (!state.testimonies.length) {
      list.innerHTML = `
        <div class="church-community-item">
          <p>
            No approved testimonies have been shared yet.
          </p>
        </div>
      `;
      return;
    }

    list.innerHTML = state.testimonies
      .map(
        (item) => `
          <article class="church-community-item">
            <div class="section-heading">
              <div>
                <h3>
                  ${escapeHtml(
                    item.is_anonymous
                      ? "Anonymous"
                      : item.user_name || "Church Member"
                  )}
                </h3>
                <p>
                  ${escapeHtml(
                    formatDateTime(item.shared_at)
                  )}
                </p>
              </div>
            </div>

            <p>${escapeHtml(item.testimony)}</p>
          </article>
        `
      )
      .join("");
  }


  async function loadTestimonies() {
    if (!state.churchId || !$("churchTestimonyList")) {
      return;
    }

    try {
      const response = await api(
        `/api/v1/churches/${state.churchId}/testimonies`
      );

      if (!response.ok) {
        throw new Error("Could not load testimonies");
      }

      const data = await response.json();

      state.testimonies = Array.isArray(data.testimonies)
        ? data.testimonies
        : [];

      renderTestimonies();
    } catch (error) {
      console.error("Testimony Wall load failed:", error);

      $("churchTestimonyList").innerHTML = `
        <p>Testimonies could not be loaded.</p>
      `;
    }
  }


  function renderPendingTestimonies() {
    const list = $("churchPendingTestimonyList");
    if (!list) return;

    if (!state.pendingTestimonies.length) {
      list.innerHTML = `
        <p>No testimonies are waiting for review.</p>
      `;
      return;
    }

    list.innerHTML = state.pendingTestimonies
      .map(
        (item) => `
          <article class="church-community-item">
            <div class="section-heading">
              <div>
                <h4>
                  ${escapeHtml(
                    item.is_anonymous
                      ? "Anonymous"
                      : item.user_name || "Church Member"
                  )}
                </h4>
                <p>
                  Submitted
                  ${escapeHtml(
                    formatDateTime(item.submitted_at)
                  )}
                </p>
              </div>
            </div>

            <p>${escapeHtml(item.testimony)}</p>

            <div>
              <button
                type="button"
                class="btn btn-primary"
                data-testimony-approve="${item.prayer_id}"
              >
                Approve
              </button>

              <button
                type="button"
                class="btn btn-secondary"
                data-testimony-reject="${item.prayer_id}"
              >
                Reject
              </button>
            </div>
          </article>
        `
      )
      .join("");
  }


  async function loadPendingTestimonies() {
    if (
      !state.churchId ||
      !state.capabilities.can_manage_content
    ) {
      state.pendingTestimonies = [];
      show("churchTestimonyModeration", false);
      return;
    }

    show("churchTestimonyModeration", true);

    try {
      const response = await api(
        `/api/v1/churches/${state.churchId}/testimonies/pending`
      );

      if (!response.ok) {
        throw new Error(
          "Could not load pending testimonies"
        );
      }

      const data = await response.json();

      state.pendingTestimonies = Array.isArray(
        data.testimonies
      )
        ? data.testimonies
        : [];

      renderPendingTestimonies();
    } catch (error) {
      console.error(
        "Pending testimony load failed:",
        error
      );

      if ($("churchPendingTestimonyList")) {
        $("churchPendingTestimonyList").innerHTML = `
          <p>Pending testimonies could not be loaded.</p>
        `;
      }
    }
  }


  async function moderateTestimony(
    prayerId,
    decision
  ) {
    const response = await api(
      `/api/v1/churches/${state.churchId}/testimonies/` +
        prayerId,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          status: decision
        })
      }
    );

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));

      throw new Error(
        data.detail || "Testimony could not be reviewed"
      );
    }

    await Promise.all([
      loadPendingTestimonies(),
      loadTestimonies(),
      loadPrayers()
    ]);
  }


  function caseCard(item) {
    return `
      <article class="church-community-item">
        <div class="section-heading">
          <div>
            <h3>Care Request #${item.id}</h3>
            <p>
              ${escapeHtml(formatStatus(item.status))}
              •
              ${escapeHtml(formatStatus(item.priority))}
            </p>
          </div>
        </div>

        <p>
          <strong>Member:</strong>
          ${escapeHtml(item.member_user_id)}
        </p>

        <p>
          <strong>Follow-up:</strong>
          ${escapeHtml(formatDateTime(item.follow_up_at))}
        </p>

        <button
          type="button"
          class="btn btn-secondary"
          data-care-open="${item.id}"
        >
          Open Care Record
        </button>
      </article>
    `;
  }

  function renderCases() {
    const list = $("churchPastoralCareList");
    if (!list) return;

    if (!state.cases.length) {
      list.innerHTML = `
        <div class="church-community-item">
          <p>No pastoral-care requests are waiting.</p>
        </div>
      `;
      return;
    }

    list.innerHTML = state.cases
      .map(caseCard)
      .join("");
  }

  async function loadAssignees() {
    if (
      !state.churchId ||
      !state.capabilities.can_manage_pastoral_care
    ) {
      return;
    }

    try {
      const response = await api(
        `/api/v1/churches/${state.churchId}/pastoral-care-assignees`
      );

      if (!response.ok) {
        throw new Error(
          "Could not load pastoral-care leaders"
        );
      }

      const data = await response.json();

      state.assignees = Array.isArray(data.assignees)
        ? data.assignees
        : [];
    } catch (error) {
      console.error(
        "Pastoral-care assignee load failed:",
        error
      );
      state.assignees = [];
    }
  }


  async function loadCases() {
    if (
      !state.churchId ||
      !state.capabilities.can_manage_pastoral_care
    ) {
      return;
    }

    try {
      const response = await api(
        `/api/v1/churches/${state.churchId}/pastoral-care`
      );

      if (!response.ok) {
        throw new Error("Could not load pastoral care");
      }

      const data = await response.json();

      state.cases = Array.isArray(data.cases)
        ? data.cases
        : [];

      renderCases();
    } catch (error) {
      console.error("Pastoral care load failed:", error);

      if ($("churchPastoralCareList")) {
        $("churchPastoralCareList").innerHTML = `
          <p>Pastoral-care requests could not be loaded.</p>
        `;
      }
    }
  }

  function activityList(activities) {
    if (!activities?.length) {
      return "<p>No care activity yet.</p>";
    }

    return `
      <ul>
        ${activities
          .map(
            (item) => `
              <li>
                ${escapeHtml(
                  formatStatus(item.activity_type)
                )}
                —
                ${escapeHtml(
                  formatDateTime(item.created_at)
                )}
              </li>
            `
          )
          .join("")}
      </ul>
    `;
  }

  function notesList(notes) {
    if (!notes?.length) {
      return "<p>No private pastoral notes yet.</p>";
    }

    return notes
      .map(
        (note) => `
          <div class="church-community-item">
            <p>${escapeHtml(note.body)}</p>
            <small>
              ${escapeHtml(formatDateTime(note.created_at))}
            </small>
          </div>
        `
      )
      .join("");
  }

  function renderCaseDetail(data) {
    const detail = $("churchPastoralCareDetail");
    if (!detail) return;

    const careCase = data.case;
    const prayer = data.prayer;

    state.activeCaseId = careCase.id;

    detail.innerHTML = `
      <div class="section-heading">
        <div>
          <h3>Pastoral Care #${careCase.id}</h3>
          <p>
            ${escapeHtml(formatStatus(careCase.status))}
            •
            ${escapeHtml(formatStatus(careCase.priority))}
          </p>
        </div>

        <button
          type="button"
          class="btn btn-secondary"
          id="churchCareCloseDetail"
        >
          Close
        </button>
      </div>

      <div class="church-community-item">
        <strong>Prayer request</strong>
        <p>${escapeHtml(prayer.message)}</p>
      </div>

      <label>
        Priority
        <select id="churchCarePriority">
          <option value="routine">Routine</option>
          <option value="important">Important</option>
          <option value="urgent">Urgent</option>
        </select>
      </label>

      <label>
        Status
        <select id="churchCareStatus">
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="waiting">Waiting</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
      </label>

      <label>
        Assign pastoral-care leader
        <select id="churchCareAssignee">
          <option value="">Unassigned</option>
          ${state.assignees
            .map(
              (item) => `
                <option
                  value="${item.user_id}"
                  ${
                    item.user_id ===
                    careCase.assigned_to_user_id
                      ? "selected"
                      : ""
                  }
                >
                  ${escapeHtml(item.name)}
                  — ${escapeHtml(formatStatus(item.role))}
                </option>
              `
            )
            .join("")}
        </select>
      </label>

      <label>
        Follow-up
        <input
          id="churchCareFollowUp"
          type="datetime-local"
        >
      </label>

      <button
        type="button"
        class="btn btn-primary"
        id="churchCareSave"
      >
        Save Care Plan
      </button>

      <p id="churchCareSaveState"></p>

      <hr>

      <h4>Private Pastoral Notes</h4>
      <p>
        These notes are visible only to authorized
        pastoral-care leaders.
      </p>

      <div id="churchCareNotes">
        ${notesList(data.notes)}
      </div>

      <textarea
        id="churchCareNoteBody"
        rows="4"
        maxlength="10000"
        placeholder="Add a private pastoral note..."
      ></textarea>

      <button
        type="button"
        class="btn btn-secondary"
        id="churchCareAddNote"
      >
        Add Private Note
      </button>

      <hr>

      <h4>Care Activity</h4>
      <div id="churchCareActivities">
        ${activityList(data.activities)}
      </div>
    `;

    $("churchCarePriority").value =
      careCase.priority || "routine";

    $("churchCareStatus").value =
      careCase.status || "open";

    if (careCase.follow_up_at) {
      const date = new Date(careCase.follow_up_at);
      const offset = date.getTimezoneOffset() * 60000;

      $("churchCareFollowUp").value = new Date(
        date.getTime() - offset
      )
        .toISOString()
        .slice(0, 16);
    }

    $("churchCareCloseDetail").addEventListener(
      "click",
      () => {
        state.activeCaseId = null;
        show("churchPastoralCareDetail", false);
      }
    );

    $("churchCareSave").addEventListener(
      "click",
      saveCareCase
    );

    $("churchCareAddNote").addEventListener(
      "click",
      addCareNote
    );

    show("churchPastoralCareDetail", true);
  }

  async function openCareCase(caseId) {
    try {
      const response = await api(
        `/api/v1/churches/${state.churchId}/pastoral-care/` +
          caseId
      );

      if (!response.ok) {
        throw new Error("Could not open care record");
      }

      renderCaseDetail(await response.json());
    } catch (error) {
      console.error("Pastoral care detail failed:", error);
    }
  }

  async function saveCareCase() {
    if (!state.activeCaseId) return;

    const assigneeValue =
      $("churchCareAssignee")?.value?.trim() || "";

    const followUp =
      $("churchCareFollowUp")?.value || null;

    const payload = {
      status: $("churchCareStatus")?.value || "open",
      priority:
        $("churchCarePriority")?.value || "routine",
      assigned_to_user_id:
        assigneeValue
          ? Number(assigneeValue)
          : null,
      follow_up_at:
        followUp
          ? new Date(followUp).toISOString()
          : null
    };

    const stateBox = $("churchCareSaveState");

    try {
      const response = await api(
        `/api/v1/churches/${state.churchId}/pastoral-care/` +
          state.activeCaseId,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(payload)
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(
          data.detail || "Care plan could not be saved"
        );
      }

      if (stateBox) {
        stateBox.textContent = "Care plan saved.";
      }

      await loadCases();
      await openCareCase(state.activeCaseId);
    } catch (error) {
      console.error("Pastoral care update failed:", error);

      if (stateBox) {
        stateBox.textContent =
          error.message || "Care plan could not be saved.";
      }
    }
  }

  async function addCareNote() {
    if (!state.activeCaseId) return;

    const body =
      $("churchCareNoteBody")?.value?.trim() || "";

    if (!body) return;

    try {
      const response = await api(
        `/api/v1/churches/${state.churchId}/pastoral-care/` +
          `${state.activeCaseId}/notes`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ body })
        }
      );

      if (!response.ok) {
        throw new Error("Private note could not be saved");
      }

      await openCareCase(state.activeCaseId);
    } catch (error) {
      console.error("Pastoral note create failed:", error);
    }
  }

  function bindEvents() {
    $("churchPrayerCreateButton")?.addEventListener(
      "click",
      () => show("churchPrayerForm", true)
    );

    $("churchPrayerCancelButton")?.addEventListener(
      "click",
      () => {
        resetPrayerForm();
        show("churchPrayerForm", false);
      }
    );

    $("churchPrayerForm")?.addEventListener(
      "submit",
      submitPrayer
    );

    $("churchPrayerList")?.addEventListener(
      "click",
      async (event) => {
        const partial = event.target.closest(
          "[data-prayer-partial]"
        );

        if (partial) {
          try {
            await updatePrayerStatus(
              Number(partial.dataset.prayerPartial),
              "partially_answered"
            );
          } catch (error) {
            console.error(
              "Prayer status update failed:",
              error
            );
          }
          return;
        }

        const answered = event.target.closest(
          "[data-prayer-answered]"
        );

        if (answered) {
          await markAnswered(
            Number(answered.dataset.prayerAnswered)
          );
        }
      }
    );

    $("churchPendingTestimonyList")?.addEventListener(
      "click",
      async (event) => {
        const approve = event.target.closest(
          "[data-testimony-approve]"
        );

        const reject = event.target.closest(
          "[data-testimony-reject]"
        );

        const button = approve || reject;

        if (!button) return;

        const prayerId = Number(
          approve
            ? button.dataset.testimonyApprove
            : button.dataset.testimonyReject
        );

        const decision = approve
          ? "approved"
          : "rejected";

        try {
          await moderateTestimony(
            prayerId,
            decision
          );
        } catch (error) {
          console.error(
            "Testimony moderation failed:",
            error
          );
        }
      }
    );

    $("churchPastoralCareList")?.addEventListener(
      "click",
      (event) => {
        const button = event.target.closest(
          "[data-care-open]"
        );

        if (button) {
          openCareCase(
            Number(button.dataset.careOpen)
          );
        }
      }
    );
  }

  async function init() {
    const root = $("churchPrayerSection");

    if (!root || typeof window.apiFetch !== "function") {
      return;
    }

    /*
     * church-space.js loads the authenticated Church Space.
     * Reuse that endpoint so this module receives only the
     * server-approved membership/capability contract.
     */
    try {
      const response = await api("/api/v1/churches/mine");

      if (!response.ok) return;

      const data = await response.json();

      state.churchId = data?.church?.id || null;
      state.currentUserId =
        data?.membership?.user_id || null;
      state.capabilities = data?.capabilities || {};

      if (!state.churchId) return;

      show(
        "churchPastoralCareWorkspace",
        Boolean(
          state.capabilities.can_manage_pastoral_care
        )
      );

      bindEvents();

      await Promise.all([
        loadPrayers(),
        loadTestimonies()
      ]);

      if (state.capabilities.can_manage_content) {
        await loadPendingTestimonies();
      } else {
        show("churchTestimonyModeration", false);
      }

      if (state.capabilities.can_manage_pastoral_care) {
        await loadAssignees();
        await loadCases();
      }
    } catch (error) {
      console.error(
        "Church Prayer/Care initialization failed:",
        error
      );
    }
  }

  window.XynaFaithChurchPrayerCare = {
    init,
    loadPrayers,
    loadTestimonies,
    loadPendingTestimonies,
    loadAssignees,
    loadCases
  };

  init();
})();
