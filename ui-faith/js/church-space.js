(() => {
  const $ = (id) =>
    document.getElementById(id);

  const state = {
    churchId: null,
    currentUserId: null,
    capabilities: {},
    announcements: [],
    events: [],
    editingAnnouncementId: null,
    editingEventId: null
  };

  function setVisible(id, visible) {
    const element = $(id);

    if (element) {
      element.hidden = !visible;
    }
  }

  function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
  }

  function formatRole(role) {
    return String(role || "member")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (letter) =>
        letter.toUpperCase()
      );
  }

  function formatStatus(status) {
    return String(status || "")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (letter) =>
        letter.toUpperCase()
      );
  }

  function formatDateTime(value) {
    if (!value) {
      return "";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return String(value);
    }

    return date.toLocaleString();
  }

  function renderUnavailable(message) {
    const status = $("churchSpaceState");
    const content = $("churchSpaceContent");

    if (content) {
      content.hidden = true;
    }

    if (status) {
      status.hidden = false;
      status.innerHTML = `
        <h3>Church Space unavailable</h3>
        <p>${escapeHtml(message)}</p>
      `;
    }
  }

  function renderChurchSpace(data) {
    const church = data?.church || {};
    const membership = data?.membership || {};
    const capabilities = data?.capabilities || {};

    state.churchId = church.id || null;
    state.currentUserId =
      membership.user_id || null;
    state.capabilities = capabilities;

    if ($("churchSpaceName")) {
      $("churchSpaceName").textContent =
        church.name || "My Church";
    }

    const location = [
      church.city,
      church.country
    ]
      .filter(Boolean)
      .join(", ");

    const identityParts = [
      church.denomination,
      location
    ].filter(Boolean);

    if ($("churchSpaceIdentity")) {
      $("churchSpaceIdentity").textContent =
        identityParts.join(" • ") ||
        "Your church community";
    }

    const roleBadge = $("churchSpaceRole");

    if (roleBadge) {
      roleBadge.textContent =
        formatRole(membership.role);
      roleBadge.hidden = false;
    }

    setVisible(
      "churchContentCard",
      Boolean(capabilities.can_create_content)
    );

    setVisible(
      "churchPastoralCareCard",
      Boolean(
        capabilities.can_manage_pastoral_care
      )
    );

    setVisible(
      "churchAnalyticsCard",
      Boolean(capabilities.can_view_analytics)
    );

    setVisible(
      "churchPeopleSection",
      Boolean(capabilities.can_view_members)
    );

    setVisible(
      "churchAnnouncementCreateButton",
      Boolean(capabilities.can_create_content)
    );

    setVisible(
      "churchEventCreateButton",
      Boolean(capabilities.can_create_content)
    );

    const status = $("churchSpaceState");

    if (status) {
      status.hidden = true;
    }

    const content = $("churchSpaceContent");

    if (content) {
      content.hidden = false;
    }

    return {
      church,
      membership,
      capabilities
    };
  }

  function canEditAnnouncement(item) {
    if (state.capabilities.can_manage_content) {
      return true;
    }

    return Boolean(
      state.capabilities.can_create_content &&
      item.status === "draft" &&
      item.author_user_id === state.currentUserId
    );
  }

  function canEditEvent(item) {
    if (state.capabilities.can_manage_content) {
      return true;
    }

    return Boolean(
      state.capabilities.can_create_content &&
      item.status === "draft" &&
      item.created_by_user_id === state.currentUserId
    );
  }

  function announcementActions(item) {
    const edit = canEditAnnouncement(item)
      ? `
          <button
            type="button"
            class="btn btn-secondary"
            data-announcement-edit="${item.id}"
          >
            Edit
          </button>
        `
      : "";

    if (!state.capabilities.can_manage_content) {
      return edit
        ? `<div>${edit}</div>`
        : "";
    }

    const publish =
      item.status === "draft"
        ? `
          <button
            type="button"
            class="btn btn-primary"
            data-announcement-action="published"
            data-announcement-id="${item.id}"
          >
            Publish
          </button>
        `
        : "";

    const archive =
      item.status !== "archived"
        ? `
          <button
            type="button"
            class="btn btn-secondary"
            data-announcement-action="archived"
            data-announcement-id="${item.id}"
          >
            Archive
          </button>
        `
        : "";

    return `
      <div>
        ${edit}
        ${publish}
        ${archive}
      </div>
    `;
  }

  function eventActions(item) {
    const edit = canEditEvent(item)
      ? `
          <button
            type="button"
            class="btn btn-secondary"
            data-event-edit="${item.id}"
          >
            Edit
          </button>
        `
      : "";

    if (!state.capabilities.can_manage_content) {
      return edit
        ? `<div>${edit}</div>`
        : "";
    }

    const publish =
      item.status === "draft"
        ? `
          <button
            type="button"
            class="btn btn-primary"
            data-event-action="published"
            data-event-id="${item.id}"
          >
            Publish
          </button>
        `
        : "";

    const cancel =
      item.status !== "cancelled"
        ? `
          <button
            type="button"
            class="btn btn-secondary"
            data-event-action="cancelled"
            data-event-id="${item.id}"
          >
            Cancel Event
          </button>
        `
        : "";

    return `
      <div>
        ${edit}
        ${publish}
        ${cancel}
      </div>
    `;
  }

  function renderAnnouncements() {
    const list = $("churchAnnouncementsList");

    if (!list) {
      return;
    }

    if (!state.announcements.length) {
      list.innerHTML = `
        <p>
          No church announcements yet.
        </p>
      `;
      return;
    }

    list.innerHTML = state.announcements
      .map((item) => `
        <article class="church-community-item">
          <div class="section-heading">
            <div>
              <h4>${escapeHtml(item.title)}</h4>
              <p>
                ${escapeHtml(
                  formatStatus(item.status)
                )}
              </p>
            </div>
          </div>

          <p>${escapeHtml(item.body)}</p>

          ${
            item.published_at
              ? `
                <p>
                  Published
                  ${escapeHtml(
                    formatDateTime(
                      item.published_at
                    )
                  )}
                </p>
              `
              : ""
          }

          ${announcementActions(item)}
        </article>
      `)
      .join("");
  }

  function renderEvents() {
    const list = $("churchEventsList");

    if (!list) {
      return;
    }

    if (!state.events.length) {
      list.innerHTML = `
        <p>
          No upcoming church events yet.
        </p>
      `;
      return;
    }

    list.innerHTML = state.events
      .map((item) => {
        const eventUrl = item.event_url
          ? escapeHtml(item.event_url)
          : "";

        return `
          <article class="church-community-item">
            <div class="section-heading">
              <div>
                <h4>${escapeHtml(item.title)}</h4>
                <p>
                  ${escapeHtml(
                    formatStatus(item.status)
                  )}
                </p>
              </div>
            </div>

            ${
              item.description
                ? `<p>${escapeHtml(
                    item.description
                  )}</p>`
                : ""
            }

            <p>
              <strong>Starts:</strong>
              ${escapeHtml(
                formatDateTime(item.starts_at)
              )}
            </p>

            ${
              item.ends_at
                ? `
                  <p>
                    <strong>Ends:</strong>
                    ${escapeHtml(
                      formatDateTime(
                        item.ends_at
                      )
                    )}
                  </p>
                `
                : ""
            }

            ${
              item.location
                ? `
                  <p>
                    <strong>Location:</strong>
                    ${escapeHtml(item.location)}
                  </p>
                `
                : ""
            }

            ${
              eventUrl
                ? `
                  <p>
                    <a
                      href="${eventUrl}"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Event link
                    </a>
                  </p>
                `
                : ""
            }

            ${eventActions(item)}
          </article>
        `;
      })
      .join("");
  }

  async function loadAnnouncements() {
    const list = $("churchAnnouncementsList");

    if (!state.churchId || !list) {
      return;
    }

    list.innerHTML =
      "<p>Loading announcements...</p>";

    try {
      const response = await window.apiFetch(
        `/api/v1/churches/${state.churchId}/announcements`
      );

      if (!response.ok) {
        throw new Error(
          "Could not load announcements"
        );
      }

      const data = await response.json();

      state.announcements =
        Array.isArray(data.announcements)
          ? data.announcements
          : [];

      renderAnnouncements();
    } catch (error) {
      console.error(
        "Church announcements load failed:",
        error
      );

      list.innerHTML = `
        <p>
          Church announcements could not be loaded.
        </p>
      `;
    }
  }

  async function loadEvents() {
    const list = $("churchEventsList");

    if (!state.churchId || !list) {
      return;
    }

    list.innerHTML =
      "<p>Loading events...</p>";

    try {
      const response = await window.apiFetch(
        `/api/v1/churches/${state.churchId}/events`
      );

      if (!response.ok) {
        throw new Error(
          "Could not load events"
        );
      }

      const data = await response.json();

      state.events =
        Array.isArray(data.events)
          ? data.events
          : [];

      renderEvents();
    } catch (error) {
      console.error(
        "Church events load failed:",
        error
      );

      list.innerHTML = `
        <p>
          Church events could not be loaded.
        </p>
      `;
    }
  }

  function toggleAnnouncementForm(show) {
    setVisible(
      "churchAnnouncementForm",
      Boolean(show)
    );

    if (!show) {
      state.editingAnnouncementId = null;

      if ($("churchAnnouncementTitle")) {
        $("churchAnnouncementTitle").value = "";
      }

      if ($("churchAnnouncementBody")) {
        $("churchAnnouncementBody").value = "";
      }

      if ($("churchAnnouncementFormState")) {
        $("churchAnnouncementFormState")
          .textContent = "";
      }
    }
  }

  function toggleEventForm(show) {
    setVisible(
      "churchEventForm",
      Boolean(show)
    );

    if (!show) {
      state.editingEventId = null;

      [
        "churchEventTitle",
        "churchEventDescription",
        "churchEventStartsAt",
        "churchEventEndsAt",
        "churchEventLocation",
        "churchEventUrl"
      ].forEach((id) => {
        if ($(id)) {
          $(id).value = "";
        }
      });

      if ($("churchEventFormState")) {
        $("churchEventFormState").textContent =
          "";
      }
    }
  }

  function toDateTimeLocal(value) {
    if (!value) {
      return "";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return String(value).slice(0, 16);
    }

    const offset =
      date.getTimezoneOffset() * 60000;

    return new Date(
      date.getTime() - offset
    )
      .toISOString()
      .slice(0, 16);
  }

  function beginAnnouncementEdit(item) {
    if (!canEditAnnouncement(item)) {
      return;
    }

    state.editingAnnouncementId = item.id;

    if ($("churchAnnouncementTitle")) {
      $("churchAnnouncementTitle").value =
        item.title || "";
    }

    if ($("churchAnnouncementBody")) {
      $("churchAnnouncementBody").value =
        item.body || "";
    }

    toggleAnnouncementForm(true);
  }

  function beginEventEdit(item) {
    if (!canEditEvent(item)) {
      return;
    }

    state.editingEventId = item.id;

    if ($("churchEventTitle")) {
      $("churchEventTitle").value =
        item.title || "";
    }

    if ($("churchEventDescription")) {
      $("churchEventDescription").value =
        item.description || "";
    }

    if ($("churchEventStartsAt")) {
      $("churchEventStartsAt").value =
        toDateTimeLocal(item.starts_at);
    }

    if ($("churchEventEndsAt")) {
      $("churchEventEndsAt").value =
        toDateTimeLocal(item.ends_at);
    }

    if ($("churchEventLocation")) {
      $("churchEventLocation").value =
        item.location || "";
    }

    if ($("churchEventUrl")) {
      $("churchEventUrl").value =
        item.event_url || "";
    }

    toggleEventForm(true);
  }

  async function createAnnouncement() {
    const title =
      $("churchAnnouncementTitle")
        ?.value
        ?.trim() || "";

    const body =
      $("churchAnnouncementBody")
        ?.value
        ?.trim() || "";

    const formState =
      $("churchAnnouncementFormState");

    if (!title || !body) {
      if (formState) {
        formState.textContent =
          "Title and announcement are required.";
      }
      return;
    }

    try {
      const editingId =
        state.editingAnnouncementId;

      const response = await window.apiFetch(
        editingId
          ? `/api/v1/churches/${state.churchId}/announcements/${editingId}`
          : `/api/v1/churches/${state.churchId}/announcements`,
        {
          method: editingId
            ? "PATCH"
            : "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(
            editingId
              ? {
                  title,
                  body
                }
              : {
                  title,
                  body,
                  status: "draft"
                }
          )
        }
      );

      if (!response.ok) {
        throw new Error(
          "Announcement could not be saved"
        );
      }

      toggleAnnouncementForm(false);
      await loadAnnouncements();
    } catch (error) {
      console.error(
        "Church announcement create failed:",
        error
      );

      if (formState) {
        formState.textContent =
          "Announcement could not be saved.";
      }
    }
  }

  async function createEvent() {
    const title =
      $("churchEventTitle")
        ?.value
        ?.trim() || "";

    const startsAt =
      $("churchEventStartsAt")
        ?.value || "";

    const formState =
      $("churchEventFormState");

    if (!title || !startsAt) {
      if (formState) {
        formState.textContent =
          "Title and start time are required.";
      }
      return;
    }

    const payload = {
      title,
      description:
        $("churchEventDescription")
          ?.value
          ?.trim() || null,
      starts_at: startsAt,
      ends_at:
        $("churchEventEndsAt")?.value || null,
      location:
        $("churchEventLocation")
          ?.value
          ?.trim() || null,
      event_url:
        $("churchEventUrl")
          ?.value
          ?.trim() || null,
      status: "draft"
    };

    try {
      const editingId =
        state.editingEventId;

      if (editingId) {
        delete payload.status;
      }

      const response = await window.apiFetch(
        editingId
          ? `/api/v1/churches/${state.churchId}/events/${editingId}`
          : `/api/v1/churches/${state.churchId}/events`,
        {
          method: editingId
            ? "PATCH"
            : "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(payload)
        }
      );

      if (!response.ok) {
        throw new Error(
          "Event could not be saved"
        );
      }

      toggleEventForm(false);
      await loadEvents();
    } catch (error) {
      console.error(
        "Church event create failed:",
        error
      );

      if (formState) {
        formState.textContent =
          "Event could not be saved.";
      }
    }
  }

  async function updateAnnouncementStatus(
    announcementId,
    status
  ) {
    const response = await window.apiFetch(
      `/api/v1/churches/${state.churchId}/announcements/${announcementId}`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ status })
      }
    );

    if (!response.ok) {
      throw new Error(
        "Announcement update failed"
      );
    }

    await loadAnnouncements();
  }

  async function updateEventStatus(
    eventId,
    status
  ) {
    const response = await window.apiFetch(
      `/api/v1/churches/${state.churchId}/events/${eventId}`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ status })
      }
    );

    if (!response.ok) {
      throw new Error("Event update failed");
    }

    await loadEvents();
  }

  function bindCommunityActions() {
    $("churchAnnouncementCreateButton")
      ?.addEventListener("click", () => {
        toggleAnnouncementForm(false);
        toggleAnnouncementForm(true);
      });

    $("churchAnnouncementCancelButton")
      ?.addEventListener("click", () => {
        toggleAnnouncementForm(false);
      });

    $("churchAnnouncementSaveButton")
      ?.addEventListener(
        "click",
        createAnnouncement
      );

    $("churchEventCreateButton")
      ?.addEventListener("click", () => {
        toggleEventForm(false);
        toggleEventForm(true);
      });

    $("churchEventCancelButton")
      ?.addEventListener("click", () => {
        toggleEventForm(false);
      });

    $("churchEventSaveButton")
      ?.addEventListener(
        "click",
        createEvent
      );

    $("churchAnnouncementsList")
      ?.addEventListener(
        "click",
        async (event) => {
          const editButton =
            event.target.closest(
              "[data-announcement-edit]"
            );

          if (editButton) {
            const id =
              Number(
                editButton.dataset
                  .announcementEdit
              );

            const item =
              state.announcements.find(
                (entry) =>
                  Number(entry.id) === id
              );

            if (item) {
              beginAnnouncementEdit(item);
            }

            return;
          }

          const button = event.target.closest(
            "[data-announcement-action]"
          );

          if (!button) {
            return;
          }

          try {
            await updateAnnouncementStatus(
              button.dataset.announcementId,
              button.dataset.announcementAction
            );
          } catch (error) {
            console.error(
              "Church announcement update failed:",
              error
            );
          }
        }
      );

    $("churchEventsList")
      ?.addEventListener(
        "click",
        async (event) => {
          const editButton =
            event.target.closest(
              "[data-event-edit]"
            );

          if (editButton) {
            const id =
              Number(
                editButton.dataset.eventEdit
              );

            const item =
              state.events.find(
                (entry) =>
                  Number(entry.id) === id
              );

            if (item) {
              beginEventEdit(item);
            }

            return;
          }

          const button = event.target.closest(
            "[data-event-action]"
          );

          if (!button) {
            return;
          }

          try {
            await updateEventStatus(
              button.dataset.eventId,
              button.dataset.eventAction
            );
          } catch (error) {
            console.error(
              "Church event update failed:",
              error
            );
          }
        }
      );
  }

  async function loadChurchMembers(churchId) {
    const list = $("churchPeopleList");

    if (!list) {
      return;
    }

    list.innerHTML = `
      <article class="feature-card">
        <p>Loading church members...</p>
      </article>
    `;

    try {
      const response = await window.apiFetch(
        `/api/v1/churches/${churchId}/members`
      );

      if (!response.ok) {
        throw new Error(
          "Could not load church members"
        );
      }

      const data = await response.json();
      const members = Array.isArray(data.members)
        ? data.members
        : [];

      if (!members.length) {
        list.innerHTML = `
          <article class="feature-card">
            <p>No active members found.</p>
          </article>
        `;
        return;
      }

      list.innerHTML = members
        .map((item) => {
          const name =
            item?.user?.name || "Church Member";

          return `
            <article class="feature-card">
              <h3>${escapeHtml(name)}</h3>
              <p>
                ${escapeHtml(formatRole(item.role))}
              </p>
            </article>
          `;
        })
        .join("");
    } catch (error) {
      console.error(
        "Church member directory load failed:",
        error
      );

      list.innerHTML = `
        <article class="feature-card">
          <p>
            Church members could not be loaded.
          </p>
        </article>
      `;
    }
  }

  async function loadChurchSpace() {
    if (
      typeof window.apiFetch !==
      "function"
    ) {
      renderUnavailable(
        "Church Space could not connect."
      );
      return;
    }

    try {
      const response = await window.apiFetch(
        "/api/v1/churches/mine"
      );

      if (response.status === 404) {
        renderUnavailable(
          "You do not have a primary Church Space yet."
        );
        return;
      }

      if (!response.ok) {
        throw new Error(
          "Church Space request failed"
        );
      }

      const data = await response.json();
      const rendered = renderChurchSpace(data);

      bindCommunityActions();

      await Promise.all([
        loadAnnouncements(),
        loadEvents()
      ]);

      if (
        rendered.capabilities.can_view_members &&
        rendered.church.id
      ) {
        await loadChurchMembers(
          rendered.church.id
        );
      }
    } catch (error) {
      console.error(
        "Church Space load failed:",
        error
      );

      renderUnavailable(
        "We could not load your Church Space. Please try again."
      );
    }
  }

  window.loadChurchSpace =
    loadChurchSpace;
})();
