// =====================================
// SERMON.JS
// STEP 1Q — SERMON ENGINE
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
  // RESTORE SERMON DRAFT
  // =====================================
  function restoreLatestSermon(){

    try {

      const latest =
        localStorage.getItem(
          "latest_sermon"
        );

      const output =
        $("sermonOutput");

      if(
        !latest ||
        !output
      ){
        return;
      }

      const parsed =
        JSON.parse(latest);

      window.currentGeneratedSermon =
        parsed;

      renderCurrentSermon(parsed,false);

    } catch(err){

      console.error(
        "Restore sermon error:",
        err
      );
    }
  }

  // =====================================
  // BIND SERMON STUDIO
  // =====================================
function bindSermonStudio() {

  if (!$("userInput"))
    return;

  restoreLatestSermon();

  initializeMobileTabs();
}
  // =====================================
  // GENERATE SERMON
  // =====================================
  async function generateSermon() {

    const output = $("sermonOutput");

    output.innerHTML = `

      <div class="loading-state">

        <div class="loading-spinner"></div>

        <h2>
          ✨ Crafting your sermon...
        </h2>

        <p>
          Connecting scripture, structure,
          illustrations, and applications.
        </p>

      </div>

    `;

    try {

      const payload = {

        input:
          $("userInput")?.value || "",

        scripture:
          $("bibleInput")?.value || "",
        denomination:
          $("denomination")?.value || "general",

        audience:
          $("audience")?.value || "",

        context:
          $("context")?.value || "",

        tone:
          $("tone")?.value || "balanced",

        duration:
          $("duration")?.value || "30"
      };

      console.log(
        "SERMON PAYLOAD",
        payload
      );
      const res = await apiFetch(
        "/api/v1/faith/sermon",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json"
          },

          body: JSON.stringify(payload)
        }
      );

        if (!res.ok) {

        const errorText =
          await res.text();

        console.error(
          "Generation API Error:",
          errorText
        );

        throw new Error(
          errorText
        );
      }

      const data =
        await res.json();

      window.currentGeneratedSermon =
        data;

      set(
        "latest_sermon",
        data
      );

      renderCurrentSermon(data);
      showMobileTab("output");
      showToast(
        "✨ Sermon generated successfully",
        "success"
      );

    } catch (err) {

      console.error(
        "Generate sermon error:",
        err
      );

      output.innerHTML = `

        <div class="error-state">

          <h2>
            Unable to generate sermon
          </h2>

          <p>
            Please try again.
          </p>

        </div>

      `;

      showToast(
        "Failed to generate sermon",
        "error"
      );
    }
  }

  // =====================================
  // RENDER CURRENT SERMON
  // =====================================

function renderCurrentSermon(
  sermon,
  scroll = true
) {

  const output =
    $("sermonOutput");

  const emptyState =
    $("emptyState");

  const collaborationSection =
    $("collaborationSection");

  if (!output) {
    return;
  }

  // =====================================
  // NO SERMON YET
  // =====================================
  if (!sermon) {

    if (emptyState) {
      emptyState.style.display =
        "block";
    }

    if (collaborationSection) {
      collaborationSection.style.display =
        "none";
    }

    output.innerHTML = "";

    return;
  }

  // =====================================
  // HIDE EMPTY STATE
  // =====================================
  if (emptyState) {

    emptyState.style.display =
      "none";
  }

  // =====================================
  // SHOW COLLABORATION
  // =====================================
  if (collaborationSection) {

    collaborationSection.style.display =
      "block";
  }

  // =====================================
  // RENDER SERMON
  // =====================================
  output.innerHTML =
    renderSermonHTML(
      sermon
    );

  // =====================================
  // SCROLL TO OUTPUT
  // =====================================
  if (scroll) {

    output.scrollIntoView({
      behavior: "smooth"
    });
  }
}

  // =====================================
  // RENDER SERMON HTML
  // =====================================
  function renderSermonHTML(data) {

    return `

      <div class="sermon-rendered">

        <div
          style="
            display:flex;
            gap:12px;
            flex-wrap:wrap;
            margin-bottom:30px;
          "
        >

          <button
            class="generate-btn"

            onclick="
              openPreachMode()
            "
          >
            🎤 Preach Mode
          </button>

        </div>

        <div class="sermon-header">

          <h1 class="sermon-title">
            ${data.title || "Untitled Sermon"}
          </h1>

          ${
            data.scripture
              ? `
                <div class="scripture-block">
                  📖 ${data.scripture}
                </div>
              `
              : ""
          }

        </div>

        ${
          data.introduction
            ? `
              <section class="sermon-section">

                <h2>
                  Introduction
                </h2>

                <p>
                  ${data.introduction}
                </p>

              </section>
            `
            : ""
        }

        ${
          data.main_points?.length

            ? data.main_points.map((point, index) => `

                <section class="sermon-section">

                  <div class="point-number">
                    ${index + 1}
                  </div>

                  <h2>
                    ${point.title || "Point"}
                  </h2>

                  <p>
                    ${point.content || ""}
                  </p>

                </section>

              `).join("")

            : ""
        }

        ${
          data.application
            ? `
              <section
                class="
                  sermon-section
                  application-section
                "
              >

                <h2>
                  Application
                </h2>

                <p>
                  ${data.application}
                </p>

              </section>
            `
            : ""
        }

        ${
          data.conclusion
            ? `
              <section
                class="
                  sermon-section
                  conclusion-section
                "
              >

                <h2>
                  Conclusion
                </h2>

                <p>
                  ${data.conclusion}
                </p>

              </section>
            `
            : ""
        }

      </div>

    `;
  }

  // =====================================
  // SAVE CURRENT SERMON
  // =====================================
  async function saveCurrentSermon(){

    const sermon =
      window.currentGeneratedSermon;

    if(!sermon){

      showToast(
        "Generate sermon first",
        "error"
      );

      return;
    }

    try {

      showToast(
        "💾 Saving sermon...",
        "success"
      );

      const response =
      await apiFetch(

          "/api/v1/faith/sermon/save",

          {
          method: "POST",

          body: JSON.stringify(
              sermon
          )
          }
      );

      if(!response.ok){

        throw new Error(
          "Failed to save sermon"
        );
      }

      const data =
        await response.json();

      set(
        "latest_sermon",
        sermon
      );

      if(data.sermon_id){

        localStorage.setItem(
          "last_saved_sermon_id",
          data.sermon_id
        );
      }

      window.currentSermonId =
        data.sermon_id;

      showToast(
        "✅ Sermon saved",
        "success"
      );

    } catch(err){

      console.error(
        "Save sermon error:",
        err
      );

      showToast(
        "Save failed",
        "error"
      );
    }
  }

  // =====================================
  // UPDATE CURRENT SERMON
  // =====================================
  async function updateCurrentSermon(){

    const sermon =
      window.currentGeneratedSermon;

    const sermonId =
      window.currentSermonId;

    if(
      !sermon ||
      !sermonId
    ){

      showToast(
        "No saved sermon loaded",
        "error"
      );

      return;
    }

    try {

      showToast(
        "📝 Updating sermon...",
        "success"
      );

      const response =
      await apiFetch(

          `/api/v1/faith/sermon/update/${sermonId}`,

          {
          method: "PUT",

          body: JSON.stringify(
              sermon
          )
          }
      );

      if(!response.ok){

        throw new Error(
          "Failed to update sermon"
        );
      }

      showToast(
        "✅ Sermon updated",
        "success"
      );

    } catch(err){

      console.error(
        "Update sermon error:",
        err
      );

      showToast(
        "Update failed",
        "error"
      );
    }
  }

  // =====================================
  // EXPORT PDF
  // =====================================
  window.exportPDF =
    async function(){

    const sermon =
      window.currentGeneratedSermon;

    if(!sermon){

      showToast(
        "Generate sermon first",
        "error"
      );

      return;
    }

    try {

      showToast(
        "📄 Generating PDF...",
        "success"
      );

      const response =
        await fetch(

          "/api/v1/faith/sermon/export-pdf",

          {
            method: "POST",

            headers:
              getAuthHeaders({

                "Content-Type":
                  "application/json"

              }),

            body: JSON.stringify(
              sermon
            )
          }
        );

      if(!response.ok){

        throw new Error(
          "PDF export failed"
        );
      }

      const blob =
        await response.blob();

      const url =
        window.URL.createObjectURL(
          blob
        );

      const a =
        document.createElement("a");

      a.href = url;

      const filename =
        (
          sermon.title ||
          "sermon"
        )

        .replace(/\s+/g, "_")

        + ".pdf";

      a.download =
        filename;

      document.body.appendChild(
        a
      );

      a.click();

      a.remove();

      window.URL.revokeObjectURL(
        url
      );

      showToast(
        "✅ PDF downloaded",
        "success"
      );

    } catch(err){

      console.error(
        "PDF export error:",
        err
      );

      showToast(
        "PDF export failed",
        "error"
      );
    }
  };

  // =====================================
  // EXPORT DOCX
  // =====================================
  window.exportDOCX =
    async function(){

    const sermon =
      window.currentGeneratedSermon;

    if(!sermon){

      showToast(
        "Generate sermon first",
        "error"
      );

      return;
    }

    try {

      showToast(
        "📝 Generating DOCX...",
        "success"
      );

      const response =
        await fetch(

          "/api/v1/faith/sermon/export-docx",

          {
            method: "POST",

            headers:
              getAuthHeaders({

                "Content-Type":
                  "application/json"

              }),

            body: JSON.stringify(
              sermon
            )
          }
        );

      if(!response.ok){

        throw new Error(
          "DOCX export failed"
        );
      }

      const blob =
        await response.blob();

      const url =
        window.URL.createObjectURL(
          blob
        );

      const a =
        document.createElement("a");

      a.href = url;

      const filename =
        (
          sermon.title ||
          "sermon"
        )

        .replace(/\s+/g, "_")

        + ".docx";

      a.download =
        filename;

      document.body.appendChild(
        a
      );

      a.click();

      a.remove();

      window.URL.revokeObjectURL(
        url
      );

      showToast(
        "✅ DOCX downloaded",
        "success"
      );

    } catch(err){

      console.error(
        "DOCX export error:",
        err
      );

      showToast(
        "DOCX export failed",
        "error"
      );
    }
  };

  // =====================================
  // PREACH MODE
  // =====================================
  function openPreachMode(){

    const sermon =
      window.currentGeneratedSermon;

    if(!sermon){

      showToast(
        "Generate sermon first",
        "error"
      );

      return;
    }

    const preachWindow =
      window.open(
        "",
        "_blank"
      );

    if(!preachWindow){

      showToast(
        "Popup blocked",
        "error"
      );

      return;
    }

    preachWindow.document.write(`
      <html>
        <head>
          <title>
            ${sermon.title || "Preach Mode"}
          </title>
        </head>

        <body
          style="
            font-family:Arial;
            background:#0F172A;
            color:white;
            padding:60px;
            line-height:2;
          "
        >

          <h1>
            ${sermon.title || ""}
          </h1>

          <h2>
            📖 ${sermon.scripture || ""}
          </h2>

          <p>
            ${sermon.introduction || ""}
          </p>

        </body>
      </html>
    `);

    preachWindow.document.close();

    showToast(
      "🎤 Preach Mode launched",
      "success"
    );
  }

  // =====================================
  // CLOSE PREACH MODE
  // =====================================
  function closePreachMode(){

    if(window.preachWindow){

      window.preachWindow.close();
    }
  }


  // ============================
// MOBILE TABS FUNCTION
// ============================
function showMobileTab(tab) {

  const inputs =
    document.getElementById(
      "mobileInputsTab"
    );

  const output =
    document.getElementById(
      "mobileOutputTab"
    );

  const actions =
    document.getElementById(
      "mobileActionsTab"
    );

  // ==========================
  // SHOW / HIDE SECTIONS
  // ==========================
  if (inputs) {
    inputs.style.display =
      tab === "inputs"
        ? "block"
        : "none";
  }

  if (output) {
    output.style.display =
      tab === "output"
        ? "block"
        : "none";
  }

  if (actions) {
    actions.style.display =
      tab === "actions"
        ? "block"
        : "none";
  }

  // ==========================
  // TAB ACTIVE STATE
  // ==========================
  document
    .querySelectorAll(
      ".mobile-tab"
    )
    .forEach(btn =>
      btn.classList.remove(
        "active"
      )
    );

  const activeBtn =
    document.querySelector(
      `.mobile-tab[data-tab="${tab}"]`
    );

  if (activeBtn) {
    activeBtn.classList.add(
      "active"
    );
  }

  console.log(
    "📱 Mobile Tab:",
    tab
  );
}


// =====================================
// SPA INITIALIZATION
// =====================================
function initializeMobileTabs() {

  const inputs =
    document.getElementById(
      "mobileInputsTab"
    );

  const output =
    document.getElementById(
      "mobileOutputTab"
    );

  const actions =
    document.getElementById(
      "mobileActionsTab"
    );

  if (
    inputs ||
    output ||
    actions
  ) {

    showMobileTab(
      "inputs"
    );

    console.log(
      "✅ Mobile tabs initialized"
    );
  }
}


// =====================================
// DOM READY
// =====================================
document.addEventListener(
  "DOMContentLoaded",
  () => {

    initializeMobileTabs();

  }
);


// =====================================
// EXPORTS
// =====================================
window.showMobileTab =
  showMobileTab;

window.initializeMobileTabs =
  initializeMobileTabs;

window.bindSermonStudio =
  bindSermonStudio;

window.generateSermon =
  generateSermon;

window.renderCurrentSermon =
  renderCurrentSermon;

window.renderSermonHTML =
  renderSermonHTML;

window.saveCurrentSermon =
  saveCurrentSermon;

window.updateCurrentSermon =
  updateCurrentSermon;

window.openPreachMode =
  openPreachMode;

window.closePreachMode =
  closePreachMode;


// =====================================
// SPA RE-INITIALIZATION
// =====================================
// IMPORTANT:
// Because sermon.html is injected
// dynamically by router.js,
// call this after navigation.
if (
  typeof window !== "undefined"
) {

  setTimeout(() => {

    initializeMobileTabs();

  }, 100);
}


// =====================================
// CLOSE IIFE
// =====================================
})();