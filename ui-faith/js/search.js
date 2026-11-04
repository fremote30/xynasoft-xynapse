// =====================================
// SEARCH.JS
// GLOBAL XYNAFAITH SEARCH
// =====================================

(() => {

  // =====================================
  // SHORTCUT
  // =====================================
  const $ = (id) =>
    document.getElementById(id);

  // =====================================
  // SEARCH STATE
  // =====================================
  window.currentSearchQuery =
    window.currentSearchQuery || "";

  window.__searchRequestId =
    window.__searchRequestId || 0;

  // =====================================
  // HTML ESCAPE
  // =====================================
  function escapeSearchHTML(value) {

    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  // =====================================
  // DATE FORMATTER
  // =====================================
  function formatSearchDate(value) {

    if (!value) {
      return "";
    }

    const date =
      new Date(value);

    if (
      Number.isNaN(
        date.getTime()
      )
    ) {
      return "";
    }

    return date.toLocaleDateString(
      undefined,
      {
        year: "numeric",
        month: "short",
        day: "numeric"
      }
    );
  }

  // =====================================
  // LOADING STATE
  // =====================================
  function renderSearchLoading() {

    const container =
      $("searchResults");

    if (!container) {
      return;
    }

    container.innerHTML = `
      <div class="feature-card search-loading-card">
        <div class="loader"></div>
        <p>Searching XynaFaith...</p>
      </div>
    `;
  }

  // =====================================
  // EMPTY STATE
  // =====================================
  function renderSearchEmpty(query) {

    const container =
      $("searchResults");

    if (!container) {
      return;
    }

    container.innerHTML = `
      <div class="feature-card search-empty-card">
        <h3>No results found</h3>

        <p>
          We could not find anything matching
          <strong>
            “${escapeSearchHTML(query)}”
          </strong>.
        </p>

        <p class="muted">
          Try a pastor name, sermon title,
          scripture, church, or prayer topic.
        </p>
      </div>
    `;
  }

  // =====================================
  // SERMON RESULTS
  // =====================================
  function renderSermonResults(sermons) {

    if (
      !Array.isArray(sermons) ||
      sermons.length === 0
    ) {
      return "";
    }

    const cards =
      sermons.map(sermon => {

        const title =
          escapeSearchHTML(
            sermon.title ||
            "Untitled Sermon"
          );

        const scripture =
          escapeSearchHTML(
            sermon.scripture || ""
          );

        const author =
          escapeSearchHTML(
            sermon.author_name ||
            "Pastor"
          );

        const date =
          formatSearchDate(
            sermon.created_at
          );

        return `
          <article
                class="feature-card search-result-card"
                data-search-type="sermon"
                data-search-id="${escapeSearchHTML(sermon.id)}"
                role="button"
                tabindex="0"
                aria-label="Open sermon ${title}"
                >
            <div class="search-result-icon">
              📖
            </div>

            <div class="search-result-content">
              <span class="search-result-type">
                Sermon
              </span>

              <h3>${title}</h3>

              ${
                scripture
                  ? `
                    <p class="search-result-subtitle">
                      ${scripture}
                    </p>
                  `
                  : ""
              }

              <div class="search-result-meta">
                <span>${author}</span>

                ${
                  date
                    ? `<span>${date}</span>`
                    : ""
                }
              </div>
            </div>
          </article>
        `;
      }).join("");

    return `
      <section class="search-result-section">
        <div class="search-section-heading">
          <h2>Sermons</h2>
          <span>${sermons.length}</span>
        </div>

        <div class="search-result-grid">
          ${cards}
        </div>
      </section>
    `;
  }

  // =====================================
  // PASTOR RESULTS
  // =====================================
  function renderPastorResults(pastors) {

    if (
      !Array.isArray(pastors) ||
      pastors.length === 0
    ) {
      return "";
    }

    const cards =
      pastors.map(pastor => {

        const name =
          escapeSearchHTML(
            pastor.name ||
            "Pastor"
          );

        const church =
          escapeSearchHTML(
            pastor.church_name || ""
          );

        const denomination =
          escapeSearchHTML(
            pastor.denomination || ""
          );

        const location =
          [
            pastor.city,
            pastor.state,
            pastor.country
          ]
            .filter(Boolean)
            .map(escapeSearchHTML)
            .join(", ");

        const image =
          pastor.profile_image
            ? `
              <img
                src="${escapeSearchHTML(pastor.profile_image)}"
                alt="${name}"
                class="search-pastor-image"
                loading="lazy"
              >
            `
            : `
              <div class="search-pastor-placeholder">
                ${name.charAt(0).toUpperCase()}
              </div>
            `;

        return `
          <article
                class="feature-card search-result-card"
                data-search-type="pastor"
                data-search-id="${escapeSearchHTML(pastor.id)}"
                role="button"
                tabindex="0"
                aria-label="Open pastor profile for ${name}"
                >
            <div class="search-result-avatar">
              ${image}
            </div>

            <div class="search-result-content">
              <span class="search-result-type">
                Pastor
              </span>

              <h3>${name}</h3>

              ${
                church
                  ? `
                    <p class="search-result-subtitle">
                      ${church}
                    </p>
                  `
                  : ""
              }

              <div class="search-result-meta">
                ${
                  denomination
                    ? `<span>${denomination}</span>`
                    : ""
                }

                ${
                  location
                    ? `<span>${location}</span>`
                    : ""
                }
              </div>
            </div>
          </article>
        `;
      }).join("");

    return `
      <section class="search-result-section">
        <div class="search-section-heading">
          <h2>Pastors</h2>
          <span>${pastors.length}</span>
        </div>

        <div class="search-result-grid">
          ${cards}
        </div>
      </section>
    `;
  }

  // =====================================
  // CHURCH RESULTS
  // =====================================
  function renderChurchResults(churches) {

    if (
      !Array.isArray(churches) ||
      churches.length === 0
    ) {
      return "";
    }

    const cards =
      churches.map(church => {

        const name =
          escapeSearchHTML(
            church.name ||
            "Church"
          );

        const location =
          [
            church.city,
            church.state,
            church.country
          ]
            .filter(Boolean)
            .map(escapeSearchHTML)
            .join(", ");

        return `
          <article
                class="feature-card search-result-card"
                data-search-type="church"
                data-search-id="${escapeSearchHTML(church.id)}"
                role="button"
                tabindex="0"
                aria-label="Open church ${name}"
                >
            <div class="search-result-icon">
              ⛪
            </div>

            <div class="search-result-content">
              <span class="search-result-type">
                Church
              </span>

              <h3>${name}</h3>

              ${
                location
                  ? `
                    <p class="search-result-subtitle">
                      ${location}
                    </p>
                  `
                  : ""
              }
            </div>
          </article>
        `;
      }).join("");

    return `
      <section class="search-result-section">
        <div class="search-section-heading">
          <h2>Churches</h2>
          <span>${churches.length}</span>
        </div>

        <div class="search-result-grid">
          ${cards}
        </div>
      </section>
    `;
  }

  // =====================================
  // PRAYER RESULTS
  // =====================================
  function renderPrayerResults(prayers) {

    if (
      !Array.isArray(prayers) ||
      prayers.length === 0
    ) {
      return "";
    }

    const cards =
      prayers.map(prayer => {

        const message =
          escapeSearchHTML(
            prayer.message ||
            "Prayer request"
          );

        const category =
          escapeSearchHTML(
            prayer.category || ""
          );

        const userName =
          escapeSearchHTML(
            prayer.user_name ||
            "Anonymous"
          );

        const status =
          escapeSearchHTML(
            prayer.status || ""
          );

        const date =
          formatSearchDate(
            prayer.created_at
          );

        return `
          <article
            class="feature-card search-result-card"
            data-search-type="prayer"
            data-search-id="${escapeSearchHTML(prayer.id)}"
            role="button"
            tabindex="0"
            aria-label="Open prayer request"
            >
            <div class="search-result-icon">
              🙏
            </div>

            <div class="search-result-content">
              <span class="search-result-type">
                Prayer
              </span>

              <p class="search-prayer-message">
                ${message}
              </p>

              <div class="search-result-meta">
                <span>${userName}</span>

                ${
                  category
                    ? `<span>${category}</span>`
                    : ""
                }

                ${
                  status
                    ? `<span>${status}</span>`
                    : ""
                }

                ${
                  date
                    ? `<span>${date}</span>`
                    : ""
                }
              </div>
            </div>
          </article>
        `;
      }).join("");

    return `
      <section class="search-result-section">
        <div class="search-section-heading">
          <h2>Prayers</h2>
          <span>${prayers.length}</span>
        </div>

        <div class="search-result-grid">
          ${cards}
        </div>
      </section>
    `;
  }

  // =====================================
  // RENDER ALL RESULTS
  // =====================================
  function renderSearchResults(data) {

    const container =
      $("searchResults");

    const summary =
      $("searchSummary");

    if (!container) {
      return;
    }

    const query =
      data?.query ||
      window.currentSearchQuery ||
      "";

    const sermons =
      Array.isArray(data?.sermons)
        ? data.sermons
        : [];

    const pastors =
      Array.isArray(data?.pastors)
        ? data.pastors
        : [];

    const churches =
      Array.isArray(data?.churches)
        ? data.churches
        : [];

    const prayers =
      Array.isArray(data?.prayers)
        ? data.prayers
        : [];

    const totalResults =
      Number.isFinite(
        Number(data?.total_results)
      )
        ? Number(data.total_results)
        : (
          sermons.length +
          pastors.length +
          churches.length +
          prayers.length
        );

    if (summary) {

      summary.innerHTML = `
        ${totalResults}
        ${
          totalResults === 1
            ? "result"
            : "results"
        }
        for
        <strong>
          “${escapeSearchHTML(query)}”
        </strong>
      `;
    }

    if (totalResults === 0) {

      renderSearchEmpty(query);

      return;
    }

    container.innerHTML = `
      ${renderSermonResults(sermons)}
      ${renderPastorResults(pastors)}
      ${renderChurchResults(churches)}
      ${renderPrayerResults(prayers)}
    `;
    bindSearchResultClicks();
  }

  // =====================================
  // SEARCH ERROR
  // =====================================
  function renderSearchError(message) {

    const container =
      $("searchResults");

    if (!container) {
      return;
    }

    container.innerHTML = `
      <div class="feature-card search-error-card">
        <h3>Search unavailable</h3>

        <p>
          ${
            escapeSearchHTML(
              message ||
              "Search failed. Please try again."
            )
          }
        </p>

        <button
          type="button"
          class="btn btn-primary"
          id="retryGlobalSearch"
        >
          Try Again
        </button>
      </div>
    `;

    const retryButton =
      $("retryGlobalSearch");

    if (retryButton) {

      retryButton.addEventListener(
        "click",
        () => {

          loadSearchPage(
            window.currentSearchQuery
          );
        }
      );
    }
  }

// =====================================
// LOAD SEARCH PAGE
// =====================================
async function loadSearchPage(query = "") {

  const container =
    $("searchResults");

  if (!container) {

    console.warn(
      "Search results container not found"
    );

    return;
  }


  const normalizedQuery =
    String(
      query ||
      window.currentSearchQuery ||
      localStorage.getItem(
        "xynafaith_search_query"
      ) ||
      ""
    ).trim();


  const summary =
    $("searchSummary");


  // =====================================
  // EMPTY SEARCH
  // =====================================
  if (!normalizedQuery) {

    if (summary) {

      summary.textContent =
        "Search sermons, pastors, churches, and prayers.";

    }


    container.innerHTML = `

      <div class="feature-card search-start-card">

        <h3>
          Search XynaFaith
        </h3>

        <p>
          Enter at least two characters in the
          search bar above.
        </p>

      </div>

    `;

    return;
  }


  // =====================================
  // MINIMUM LENGTH
  // =====================================
  if (
    normalizedQuery.length < 2
  ) {

    if (summary) {

      summary.textContent =
        "Please enter at least two characters.";

    }


    container.innerHTML = `

      <div class="feature-card search-start-card">

        <p>
          Search terms must contain at least
          two characters.
        </p>

      </div>

    `;

    return;
  }


  // =====================================
  // SAVE SEARCH STATE
  // =====================================
  window.currentSearchQuery =
    normalizedQuery;


  localStorage.setItem(
    "xynafaith_search_query",
    normalizedQuery
  );


  const navbarInput =
    $("globalSearch");


  if (navbarInput) {

    navbarInput.value =
      normalizedQuery;

  }


  const requestId =
    ++window.__searchRequestId;


  renderSearchLoading();


  try {


    // =====================================
    // CALL SEARCH API
    // =====================================
    const response =
      await apiFetch(
        `/api/v1/search?q=${
          encodeURIComponent(
            normalizedQuery
          )
        }`
      );


    if (
      requestId !==
      window.__searchRequestId
    ) {

      return;

    }


    // =====================================
    // HANDLE BOTH:
    // JSON OBJECT OR FETCH RESPONSE
    // =====================================
    let data =
      response;


    if (
      response &&
      typeof response.json === "function"
    ) {

      data =
        await response.json();

    }


    console.log(
      "🔎 SEARCH RESPONSE:",
      data
    );


    renderSearchResults(
      data
    );


  } catch (err) {


    if (
      requestId !==
      window.__searchRequestId
    ) {

      return;

    }


    console.error(
      "Global search failed:",
      err
    );


    renderSearchError(
      err?.message ||
      "Search failed. Please try again."
    );

  }

}

  // =====================================
  // SUBMIT GLOBAL SEARCH
  // =====================================
  async function submitGlobalSearch(input) {

    const query =
      String(
        input?.value || ""
      ).trim();

    if (!query) {

      if (
        typeof showToast ===
        "function"
      ) {
        showToast(
          "Enter something to search.",
          "warning"
        );
      }

      input?.focus();

      return;
    }

    if (query.length < 2) {

      if (
        typeof showToast ===
        "function"
      ) {
        showToast(
          "Search requires at least two characters.",
          "warning"
        );
      }

      input?.focus();

      return;
    }

    // =====================================
    // SAVE SEARCH STATE
    // =====================================
    window.currentSearchQuery =
      query;

    localStorage.setItem(
      "xynafaith_search_query",
      query
    );


    if (
      window.currentPage ===
      "search"
    ) {

      await loadSearchPage(query);

      return;
    }

    if (
      typeof window.navigate ===
      "function"
    ) {

      await window.navigate("search");

    } else {

      console.error(
        "navigate() is unavailable"
      );
    }
  }


  // =====================================
// BIND SEARCH EVENTS
// =====================================
function bindGlobalSearchEvents() {

    if (
        window.__globalSearchEventsBound
    ) {
        return;
    }

    window.__globalSearchEventsBound =
        true;


    // =====================================
    // ENTER KEY SEARCH
    // Supports:
    // - Desktop navbar search
    // - Mobile search page
    // =====================================

    document.addEventListener(
        "keydown",
        async event => {

            const input =
                event.target;


            if (
                !input ||
                (
                    input.id !== "globalSearch" &&
                    input.id !== "mobileSearchInput"
                )
            ) {
                return;
            }


            if (
                event.key !== "Enter"
            ) {
                return;
            }


            event.preventDefault();


            await submitGlobalSearch(
                input
            );

        }
    );



    // =====================================
    // DESKTOP SEARCH BUTTON
    // =====================================

    document.addEventListener(
        "click",
        async event => {


            const button =
                event.target.closest(
                    "#globalSearchButton"
                );


            if (!button) {
                return;
            }


            event.preventDefault();


            const input =
                document.getElementById(
                    "globalSearch"
                );


            await submitGlobalSearch(
                input
            );


        }
    );



    // =====================================
    // MOBILE SEARCH BUTTON
    // =====================================

    document.addEventListener(
        "click",
        async event => {


            const button =
                event.target.closest(
                    "#mobileSearchButton"
                );


            if (!button) {
                return;
            }


            event.preventDefault();


            const input =
                document.getElementById(
                    "mobileSearchInput"
                );


            await submitGlobalSearch(
                input
            );


        }
    );


    console.log(
        "🔎 Search events bound"
    );

}

  // =====================================
// SEARCH RESULT NAVIGATION
// =====================================
function bindSearchResultClicks() {

  const container =
    $("searchResults");

  if (!container) {
    return;
  }

  // Prevent duplicate listeners when
  // another search is performed.
  if (
    container.dataset.searchClicksBound ===
    "true"
  ) {
    return;
  }

  container.dataset.searchClicksBound =
    "true";

  container.addEventListener(
    "click",
    async event => {

      const card =
        event.target.closest(
          ".search-result-card"
        );

      if (!card) {
        return;
      }

      const type =
        card.dataset.searchType;

      const id =
        Number(
          card.dataset.searchId
        );

      if (
        !type ||
        !Number.isFinite(id)
      ) {
        console.error(
          "Invalid search result:",
          {
            type,
            id:
              card.dataset.searchId
          }
        );

        return;
      }

      card.classList.add(
        "search-result-opening"
      );

      try {

        // =================================
        // SERMON
        // =================================
        if (type === "sermon") {

          if (
            typeof window.openSavedSermon ===
            "function"
          ) {

            await window.openSavedSermon(id);

          } else {

            window.selectedSermonId =
              id;

            await window.navigate(
              "sermon"
            );
          }

          return;
        }

        // =================================
        // PASTOR
        // =================================
        if (type === "pastor") {

          window.selectedPastorId =
            id;

          localStorage.setItem(
            "selected_pastor_id",
            String(id)
          );

          await window.navigate(
            "pastor-profile"
          );

          return;
        }

        // =================================
        // PRAYER
        // =================================
        if (type === "prayer") {

          window.selectedPrayerId =
            id;

          sessionStorage.setItem(
            "selected_prayer_id",
            String(id)
          );

          await window.navigate(
            "prayer"
          );

          return;
        }

        // =================================
        // CHURCH
        // =================================
        if (type === "church") {

          window.selectedChurchId =
            id;

          sessionStorage.setItem(
            "selected_church_id",
            String(id)
          );

          if (
            window.routes &&
            window.routes[
              "church-profile"
            ]
          ) {

            await window.navigate(
              "church-profile"
            );

          } else {

            if (
              typeof showToast ===
              "function"
            ) {
              showToast(
                "Church profiles are coming soon.",
                "info"
              );
            }
          }
        }

      } catch (err) {

        console.error(
          "Search result navigation failed:",
          err
        );

        if (
          typeof showToast ===
          "function"
        ) {
          showToast(
            "Unable to open this result.",
            "error"
          );
        }

      } finally {

        card.classList.remove(
          "search-result-opening"
        );
      }
    }
  );

  // Keyboard accessibility
  container.addEventListener(
    "keydown",
    event => {

      const card =
        event.target.closest(
          ".search-result-card"
        );

      if (!card) {
        return;
      }

      if (
        event.key !== "Enter" &&
        event.key !== " "
      ) {
        return;
      }

      event.preventDefault();
      card.click();
    }
  );
}
  // =====================================
  // INITIALIZE
  // =====================================
  bindGlobalSearchEvents();

  // =====================================
  // GLOBAL EXPORTS
  // =====================================
  window.loadSearchPage =
    loadSearchPage;

  window.renderSearchResults =
    renderSearchResults;

  window.submitGlobalSearch =
    submitGlobalSearch;

  window.bindGlobalSearchEvents =
    bindGlobalSearchEvents;

  window.bindSearchResultClicks =
    bindSearchResultClicks;

})();