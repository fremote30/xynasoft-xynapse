// =====================================
// PLATFORM.JS
// STEP 1T — PLATFORM SERVICES
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
  // UPLOAD SERMON
  // =====================================
  async function uploadSermon() {

    let loadingInterval;

    try {

      const fileInput =
        $("sermonFile");

      if (
        !fileInput ||
        !fileInput.files ||
        !fileInput.files[0]
      ) {

        showToast(
          "Choose a file first",
          "error"
        );

        return;
      }

      const file =
        fileInput.files[0];

      const output =
        $("sermonOutput");

      if (output) {

        output.innerHTML = `

          <div class="loading-state">

            <div
              class="loading-spinner"
            ></div>

            <div
              style="
                font-size:48px;
                margin-bottom:20px;
              "
            >
              ✨
            </div>

            <h2>
              Rewriting uploaded sermon...
            </h2>

            <p id="uploadLoaderText">
              AI is restructuring your sermon.
            </p>

          </div>

        `;
      }

      const loaderText =
        $("uploadLoaderText");

      const loadingSteps = [

        "✨ Rebuilding sermon structure...",
        "📖 Strengthening biblical flow...",
        "🔥 Enhancing sermon transitions...",
        "🎯 Improving applications...",
        "🧠 Optimizing cadence...",
        "✨ Finalizing sermon..."

      ];

      let loadingIndex = 0;

      loadingInterval =
        setInterval(() => {

          if (loaderText) {

            loaderText.innerHTML =
              loadingSteps[
                loadingIndex %
                loadingSteps.length
              ];
          }

          loadingIndex++;

        }, 2200);

      const formData =
        new FormData();

      formData.append(
        "file",
        file
      );

      const res = await fetch(
        "/sermon/upload-sermon",
        {
          method: "POST",

          headers:
            getAuthHeaders(),

          body: formData
        }
      );

      const data =
        await res.json();

      if (!res.ok) {

        throw new Error(
          data.detail ||
          "Upload failed"
        );
      }

      clearInterval(
        loadingInterval
      );

      window.currentGeneratedSermon =
        data.sermon;

      set(
        "latest_sermon",
        data.sermon
      );

      renderCurrentSermon(
        data.sermon
      );

      showToast(
        "✨ Sermon rewritten successfully",
        "success"
      );

    } catch (err) {

      clearInterval(
        loadingInterval
      );

      console.error(
        "Upload sermon error:",
        err
      );

      showToast(
        err.message ||
        "Upload failed",
        "error"
      );
    }
  }

  // =====================================
  // REFINE
  // =====================================
  async function refine(type) {

    if (
      !window.currentGeneratedSermon
    ) {

      showToast(
        "Generate a sermon first",
        "error"
      );

      return;
    }

    try {

      showToast(
        "✨ Refining sermon...",
        "success"
      );

      const res =
        await apiFetch(
          "/api/v1/faith/sermon/refine",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json"
            },

            body: JSON.stringify({

              sermon:
                window.currentGeneratedSermon,

              refine_type:
                type
            })
          }
        );

      if (!res.ok) {

        throw new Error(
          "Refine failed"
        );
      }

      const data =
        await res.json();

      window.currentGeneratedSermon =
        data.sermon;

      set(
        "latest_sermon",
        data.sermon
      );

      renderCurrentSermon(
        data.sermon
      );

      showToast(
        "✨ Sermon refined",
        "success"
      );

    } catch (err) {

      console.error(
        "Refine error:",
        err
      );

      showToast(
        "Refine failed",
        "error"
      );
    }
  }

  // =====================================
  // MULTIVERSE
  // =====================================
  async function generateMultiverse() {

    try {

      const topic =
        $("topic")
          ?.value
          ?.trim();

      if (!topic) {

        showToast(
          "Enter a sermon topic first",
          "error"
        );

        return;
      }

      const output =
        $("multiverseOutput");

      if (output) {

        output.innerHTML = `

          <div class="loading-state">

            <div
              class="loading-spinner"
            ></div>

            <h2>
              🌌 Generating Sermon Universes...
            </h2>

          </div>

        `;
      }

      const res =
        await apiFetch(
          "/api/v1/faith/sermon/multiverse",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json"
            },

            body: JSON.stringify({
              topic
            })
          }
        );

      if (!res.ok) {

        throw new Error(
          "Multiverse failed"
        );
      }

      const data =
        await res.json();

      output.innerHTML =
        data.universes.map(
          (u, index) => `

          <div class="feature-card">

            <h2>
              🌌 Universe ${index + 1}
            </h2>

            <h3>
              ${u.title}
            </h3>

            <p>
              ${u.introduction}
            </p>

            <button
              class="generate-btn"

              onclick='useMultiverseSermon(
                ${JSON.stringify(u)}
              )'
            >
              Use This Sermon
            </button>

          </div>

        `
        ).join("");

      showToast(
        "🌌 Multiverse generated",
        "success"
      );

    } catch (err) {

      console.error(
        "Multiverse error:",
        err
      );

      showToast(
        "Multiverse failed",
        "error"
      );
    }
  }

  // =====================================
  // USE MULTIVERSE
  // =====================================
  function useMultiverseSermon(
    universe
  ) {

    window.currentGeneratedSermon =
      universe;

    set(
      "latest_sermon",
      universe
    );

    renderCurrentSermon(
      universe
    );

    showToast(
      "✨ Sermon loaded",
      "success"
    );
  }

  // =====================================
  // EXPAND MULTIVERSE
  // =====================================
  function expandMultiverse() {

    showToast(
      "🚧 Expansion engine coming",
      "success"
    );
  }

  // =====================================
  // SHARE WHATSAPP
  // =====================================
  function shareWhatsApp() {

    const sermon =
      window.currentGeneratedSermon;

    if (!sermon) {

      showToast(
        "Generate sermon first",
        "error"
      );

      return;
    }

    const message = `

🙏 ${sermon.title || ""}

📖 ${sermon.scripture || ""}

✨ Generated with XynaFaith

    `;

    const encoded =
      encodeURIComponent(
        message
      );

    window.open(
      `https://wa.me/?text=${encoded}`,
      "_blank"
    );

    showToast(
      "📲 Opening WhatsApp",
      "success"
    );
  }

  // =====================================
  // COPY SERMON
  // =====================================
  async function copySermon() {

    const sermon =
      window.currentGeneratedSermon;

    if (!sermon) {

      showToast(
        "Generate sermon first",
        "error"
      );

      return;
    }

    try {

      await navigator.clipboard.writeText(
        JSON.stringify(
          sermon,
          null,
          2
        )
      );

      showToast(
        "📋 Sermon copied",
        "success"
      );

    } catch (err) {

      console.error(
        "Copy error:",
        err
      );

      showToast(
        "Copy failed",
        "error"
      );
    }
  }

  // =====================================
  // PRINT SERMON
  // =====================================
  function printSermon() {

    window.print();

    showToast(
      "🖨 Print opened",
      "success"
    );
  }

  // =====================================
  // OPEN SHARE MODAL
  // =====================================
  function openPastorShareModal() {

    const modal =
      $("pastorShareModal");

    if (modal) {

      modal.style.display =
        "flex";
    }
  }

  // =====================================
  // CLOSE SHARE MODAL
  // =====================================
  function closePastorShareModal() {

    const modal =
      $("pastorShareModal");

    if (modal) {

      modal.style.display =
        "none";
    }
  }

  // =====================================
  // CLEAR DRAFT
  // =====================================
  function clearSermonDraft() {

    localStorage.removeItem(
      "latest_sermon"
    );

    showToast(
      "Draft cleared",
      "success"
    );
  }

  // =====================================
  // DELETE SERMON
  // =====================================
  async function deleteSermon(
    sermonId
  ) {

    const confirmed =
      confirm(
        "Delete this sermon?"
      );

    if (!confirmed) return;

    try {

      const res =
        await apiFetch(
          `/api/sermon/${sermonId}`,
          {
            method: "DELETE"
          }
        );

      if (!res.ok) {

        throw new Error(
          "Delete failed"
        );
      }

      showToast(
        "🗑 Sermon deleted",
        "success"
      );

      await loadMySermons();

    } catch (err) {

      console.error(
        "Delete sermon error:",
        err
      );

      showToast(
        "Delete failed",
        "error"
      );
    }
  }

// =====================================
// APPLY FOR PASTOR
// =====================================
async function upgradeToPastor() {

  try {

    const token =
      getToken();

    const response =
      await fetch(
        "/api/v1/pastors/apply",
        {
          method: "POST",

          headers: {
            Authorization:
              `Bearer ${token}`
          }
        }
      );

    const data =
      await response.json();

    if (!response.ok) {

      throw new Error(
        data.detail ||
        "Application failed"
      );
    }

    showToast(
      "✅ Pastor application submitted",
      "success"
    );

    const badge =
      document.getElementById(
        "pastorStatusBadge"
      );

    if (badge) {

      badge.textContent =
        "Application Pending";

      badge.classList.add(
        "pending"
      );
    }

    const msg =
      document.getElementById(
        "pastorUpgradeMessage"
      );

    if (msg) {

      msg.textContent =
        "Your application has been submitted and is awaiting administrator review.";
    }

    const btn =
      document.getElementById(
        "upgradePastorBtn"
      );

    if (btn) {

      btn.disabled = true;

      btn.textContent =
        "Application Pending";
    }

  } catch (err) {

    console.error(err);

    showToast(
      err.message ||
      "Application failed",
      "error"
    );
  }
}

  // =====================================
  // GLOBAL EXPORTS
  // =====================================

  window.uploadSermon =
    uploadSermon;

  window.refine =
    refine;

  window.generateMultiverse =
    generateMultiverse;

  window.useMultiverseSermon =
    useMultiverseSermon;

  window.expandMultiverse =
    expandMultiverse;

  window.clearSermonDraft =
    clearSermonDraft;

  window.shareWhatsApp =
    shareWhatsApp;

  window.copySermon =
    copySermon;

  window.printSermon =
    printSermon;

  window.openPastorShareModal =
    openPastorShareModal;

  window.closePastorShareModal =
    closePastorShareModal;

  window.deleteSermon =
    deleteSermon;

  window.upgradeToPastor =
    upgradeToPastor;

})();