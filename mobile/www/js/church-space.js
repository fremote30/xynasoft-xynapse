(() => {
  const $ = (id) =>
    document.getElementById(id);

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

  function renderUnavailable(message) {
    const state = $("churchSpaceState");
    const content = $("churchSpaceContent");

    if (content) {
      content.hidden = true;
    }

    if (state) {
      state.hidden = false;
      state.innerHTML = `
        <h3>Church Space unavailable</h3>
        <p>${escapeHtml(message)}</p>
      `;
    }
  }

  function renderChurchSpace(data) {
    const church = data?.church || {};
    const membership = data?.membership || {};
    const capabilities = data?.capabilities || {};

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

    const state = $("churchSpaceState");

    if (state) {
      state.hidden = true;
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
