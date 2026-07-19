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

    const draftKey =
      getLatestSermonKey();

    if (!draftKey) {
      return;
    }

    const latest =
      localStorage.getItem(
        draftKey
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
      JSON.parse(
        latest
      );

    window.currentGeneratedSermon =
      parsed;

    window.currentSermonId =
      parsed?.id
        ? Number(parsed.id)
        : null;
    renderCurrentSermon(
      parsed,
      false
    );

    console.log(
      "✅ Draft restored:",
      draftKey
    );

  } catch(err){

    console.error(
      "Restore sermon error:",
      err
    );
  }
}

// =====================================
// CLEAR CURRENT SERMON
// =====================================
function clearCurrentSermon(){

  if(
    !confirm(
      "Clear current sermon draft?"
    )
  ){
    return;
  }

  // =========================
  // REMOVE SAVED DRAFT
  // =========================
  const draftKey =
    getLatestSermonKey();

  if(draftKey){

    localStorage.removeItem(
      draftKey
    );
  }

  // =========================
  // CLEAR MEMORY
  // =========================
  window.currentGeneratedSermon =
    null;

  window.currentSermonId =
    null;

  localStorage.removeItem(
    "last_saved_sermon_id"
  );

  // =========================
  // CLEAR FORM FIELDS
  // =========================
  const userInput =
    $("userInput");

  const bibleInput =
    $("bibleInput");

  const audience =
    $("audience");

  const context =
    $("context");

  const denomination =
    $("denomination");

  const tone =
    $("tone");

  const duration =
    $("duration");

  if(userInput){
    userInput.value = "";
  }

  if(bibleInput){
    bibleInput.value = "";
  }

  if(audience){
    audience.value = "";
  }

  if(context){
    context.value = "";
  }

  if(denomination){
    denomination.value = "general";
  }

  if(tone){
    tone.value = "balanced";
  }

  if(duration){
    duration.value = "30";
  }

  // =========================
  // RESET OUTPUT
  // =========================
  const output =
    $("sermonOutput");

  if(output){

    output.innerHTML = `

      <div
        id="emptyState"
        class="empty-state"
      >

        <div class="empty-icon">
          ✨
        </div>

        <h2>
          Ready to help craft
          your next message
        </h2>

        <p>
          Generate sermons,
          refine ideas,
          build illustrations,
          and prepare impactful
          teachings powered by AI.
        </p>

      </div>

    `;
  }

  // =========================
  // HIDE COLLABORATION
  // =========================
  const collab =
    $("collaborationSection");

  if(collab){

    collab.style.display =
      "none";
  }

  // =====================================
  // RESET SAVE / UPDATE BUTTONS
  // =====================================
  const saveButton =
    $("saveSermonBtn");

  const updateButton =
    $("updateSermonBtn");

  if (saveButton) {
    saveButton.hidden = false;
    saveButton.style.removeProperty(
      "display"
    );
  }

  if (updateButton) {
    updateButton.hidden = true;
    updateButton.style.setProperty(
      "display",
      "none",
      "important"
    );
  }

  // Restore editable fields for a new sermon.
  [
    $("userInput"),
    $("bibleInput"),
    $("denomination"),
    $("audience"),
    $("context"),
    $("tone"),
    $("duration")
  ].forEach(field => {
    if (field) {
      field.disabled = false;
    }
  });

  if (output) {
    output.contentEditable = "true";
  }

  showToast(
    "🗑️ Sermon cleared",
    "success"
  );
}

// =====================================
// BIND SERMON STUDIO
// =====================================
function bindSermonStudio() {

  if (
    !$("userInput")
  ){
    return;
  }

  // =====================================
  // ROLE-BASED UI
  // =====================================
  const isPastor =
    window.currentUser?.role ===
      "pastor" ||
    window.currentUser?.role ===
      "admin";

  document
    .querySelectorAll(
      ".pastor-only"
    )
    .forEach(el => {

      el.style.display =
        isPastor
          ? ""
          : "none";
    });

  console.log(
    "ROLE CHECK:",
    window.currentUser?.role,
    "isPastor:",
    isPastor
  );

// =====================================
// RESTORE DRAFT
// Do not overwrite a sermon that is
// already being opened from the server.
// =====================================
if (
  !window.__openingSavedSermon
) {
  restoreLatestSermon();
} else {
  console.log(
    "⏭ Skipping draft restore during saved-sermon navigation"
  );
}

  // =====================================
  // MOBILE TABS
  // =====================================
  initializeMobileTabs();

  // =====================================
  // MEMBER EXPERIENCE
  // =====================================
  if (!isPastor) {

    const collaborationSection =
      $("collaborationSection");

    if (
      collaborationSection
    ) {

      collaborationSection.style.display =
        "none";
    }
  }
}

// =====================================
// GENERATE SERMON
// =====================================
async function generateSermon() {

  const output =
    $("sermonOutput");

  if (!output) {
    return;
  }

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
    // =====================================
    // BUILD PAYLOAD
    // =====================================
    const payload = {
      input:
        $("userInput")
          ?.value
          ?.trim() || "",

      scripture:
        $("bibleInput")
          ?.value
          ?.trim() || "",

      denomination:
        $("denomination")
          ?.value || "general",

      audience:
        $("audience")
          ?.value
          ?.trim() || "",

      context:
        $("context")
          ?.value
          ?.trim() || "",

      tone:
        $("tone")
          ?.value || "balanced",

      duration:
        $("duration")
          ?.value || "30"
    };

    console.log(
      "SERMON PAYLOAD",
      payload
    );

    // =====================================
    // GENERATE SERMON
    // =====================================
    const res =
      await apiFetch(
        "/api/v1/faith/sermon",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json"
          },

          body: JSON.stringify(
            payload
          )
        }
      );

    const data =
      await res
        .json()
        .catch(() => ({}));

    if (!res.ok) {
      console.error(
        "Generation API Error:",
        data
      );

      throw new Error(
        data.detail ||
        data.message ||
        "Failed to generate sermon"
      );
    }

    if (
      !data ||
      typeof data !== "object"
    ) {
      throw new Error(
        "Invalid sermon response"
      );
    }

    // =====================================
    // NEW GENERATED SERMON IS UNSAVED
    // =====================================
    delete data.id;
    delete data.author_id;

    window.currentSermonId =
      null;

    window.currentGeneratedSermon =
      data;

    localStorage.removeItem(
      "last_saved_sermon_id"
    );

    // =====================================
    // USER-SPECIFIC DRAFT
    // =====================================
    const draftKey =
      getLatestSermonKey();

    if (draftKey) {
      localStorage.setItem(
        draftKey,
        JSON.stringify(
          data
        )
      );
    }

    // =====================================
    // RENDER SERMON
    // =====================================
    if (
      typeof window.renderCurrentSermon ===
      "function"
    ) {
      window.renderCurrentSermon(
        data,
        false
      );
    } else {
      throw new Error(
        "Sermon renderer is unavailable"
      );
    }

    // =====================================
    // SHOW OUTPUT
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
      "✨ Sermon generated successfully",
      "success"
    );

  } catch (err) {
    console.error(
      "Generate sermon error:",
      err
    );

    window.currentGeneratedSermon =
      null;

    window.currentSermonId =
      null;

    output.innerHTML = `
      <div class="error-state">

        <h2>
          Unable to generate sermon
        </h2>

        <p>
          ${
            err.message ||
            "Please try again."
          }
        </p>

      </div>
    `;

    showToast?.(
      err.message ||
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
    window.currentGeneratedSermon =
      null;

    window.currentSermonId =
      null;

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
  // GLOBAL SERMON STATE
  // =====================================
  window.currentGeneratedSermon =
    sermon;

  if (sermon.id) {
    window.currentSermonId =
      Number(sermon.id);
  }

  // =====================================
  // USER ROLE
  // =====================================
  const isPastor =
    window.currentUser?.role === "pastor" ||
    window.currentUser?.role === "admin";

  // =====================================
  // OWNERSHIP
  // =====================================
  const isSavedSermon =
    Boolean(sermon.id);

  const isOwner =
    !isSavedSermon ||
    Boolean(
      sermon.author_id &&
      window.currentUser?.id &&
      Number(sermon.author_id) ===
        Number(window.currentUser.id)
    );

  const shouldBeReadOnly =
    isSavedSermon &&
    !isOwner;

// =====================================
// SAVE VS UPDATE BUTTON
// =====================================
const saveButton =
  $("saveSermonBtn");

const updateButton =
  $("updateSermonBtn");

if (saveButton) {
  saveButton.style.display =
    isOwner && !isSavedSermon
      ? ""
      : "none";
}

if (updateButton) {
  updateButton.style.display =
    isOwner && isSavedSermon
      ? ""
      : "none";
}

  // =====================================
  // RESTORE INPUT FIELDS
  // =====================================
  const userInput =
    $("userInput");

  const bibleInput =
    $("bibleInput");

  const denomination =
    $("denomination");

  const audience =
    $("audience");

  const context =
    $("context");

  const tone =
    $("tone");

  const duration =
    $("duration");

  if (userInput) {
    userInput.value =
      sermon.message ||
      sermon.input ||
      sermon.prompt ||
      sermon.theme ||
      sermon.title ||
      "";
  }

  if (bibleInput) {
    bibleInput.value =
      sermon.scripture ||
      "";
  }

  if (denomination) {
    const value =
      String(
        sermon.denomination ||
        "general"
      );

    const exists =
      Array.from(
        denomination.options
      ).some(
        option =>
          option.value === value
      );

    denomination.value =
      exists
        ? value
        : "general";
  }

  if (audience) {
    audience.value =
      sermon.audience ||
      "";
  }

  if (context) {
    context.value =
      sermon.context ||
      sermon.local_context ||
      "";
  }

  if (tone) {
    const value =
      String(
        sermon.tone ||
        "balanced"
      );

    const exists =
      Array.from(
        tone.options
      ).some(
        option =>
          option.value === value
      );

    tone.value =
      exists
        ? value
        : "balanced";
  }

  if (duration) {
    const value =
      String(
        sermon.duration ||
        "30"
      );

    const exists =
      Array.from(
        duration.options
      ).some(
        option =>
          option.value === value
      );

    duration.value =
      exists
        ? value
        : "30";
  }

  // =====================================
  // PASTOR-ONLY UI
  // =====================================
  document
    .querySelectorAll(
      ".pastor-only"
    )
    .forEach(el => {
      el.style.display =
        isPastor
          ? ""
          : "none";
    });

  // =====================================
  // OWNER-ONLY UI
  // =====================================
  document
    .querySelectorAll(
      ".owner-only"
    )
    .forEach(el => {
      el.hidden =
        !isOwner;

      if (isOwner) {
        el.style.removeProperty(
          "display"
        );
      } else {
        el.style.setProperty(
          "display",
          "none",
          "important"
        );
      }
    });

  // =====================================
  // READ-ONLY FORM STATE
  // =====================================
  [
    userInput,
    bibleInput,
    denomination,
    audience,
    context,
    tone,
    duration
  ].forEach(field => {
    if (!field) {
      return;
    }

    field.disabled =
      shouldBeReadOnly;
  });

  output.contentEditable =
    shouldBeReadOnly
      ? "false"
      : "true";

  // =====================================
  // EMPTY STATE
  // =====================================
  if (emptyState) {
    emptyState.style.display =
      "none";
  }

  // =====================================
  // COLLABORATION
  // =====================================
  if (collaborationSection) {
    collaborationSection.style.display =
      isPastor
        ? "block"
        : "none";
  }

  // =====================================
  // RENDER OUTPUT
  // =====================================
  output.innerHTML =
    renderSermonHTML(
      sermon
    );

  // =====================================
  // LOAD COMMENTS
  // =====================================
  if (
    isPastor &&
    sermon.id &&
    typeof window.loadSermonComments ===
      "function"
  ) {
    window.loadSermonComments(
      sermon.id
    );
  }

  console.log(
    "✅ SERMON RENDERED:",
    {
      id:
        sermon.id,

      title:
        sermon.title,

      scripture:
        sermon.scripture,

      authorId:
        sermon.author_id,

      currentUserId:
        window.currentUser?.id,

      isOwner,
      shouldBeReadOnly
    }
  );

  // =====================================
  // SCROLL
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
async function saveCurrentSermon() {

  const sermon =
    window.currentGeneratedSermon;

  if (!sermon) {
    showToast?.(
      "Generate sermon first",
      "error"
    );

    return;
  }

  // =====================================
  // PREVENT DUPLICATE SAVES
  // =====================================
  const existingSermonId =
    Number(
      window.currentSermonId ||
      sermon.id ||
      0
    );

  if (existingSermonId) {
    showToast?.(
      "This sermon is already saved. Use Update Sermon instead.",
      "info"
    );

    return;
  }

  // =====================================
  // SYNC CURRENT FORM VALUES
  // =====================================
  const currentPrompt =
    $("userInput")
      ?.value
      ?.trim() || "";

  sermon.input =
    currentPrompt;

  sermon.message =
    currentPrompt;

  sermon.scripture =
    $("bibleInput")
      ?.value
      ?.trim() || "";

  sermon.denomination =
    $("denomination")
      ?.value || "general";

  sermon.audience =
    $("audience")
      ?.value
      ?.trim() || "";

  sermon.context =
    $("context")
      ?.value
      ?.trim() || "";

  sermon.local_context =
    sermon.context;

  sermon.tone =
    $("tone")
      ?.value || "balanced";

  sermon.duration =
    $("duration")
      ?.value || "30";

  window.currentGeneratedSermon =
    sermon;

  try {
    showToast?.(
      "💾 Saving sermon...",
      "success"
    );

    const response =
      await apiFetch(
        "/api/v1/faith/sermon/save",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json"
          },

          body: JSON.stringify(
            sermon
          )
        }
      );

    const data =
      await response
        .json()
        .catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data.detail ||
        "Failed to save sermon"
      );
    }

    const savedSermonId =
      Number(
        data.id ||
        data.sermon_id ||
        data.sermon?.id ||
        0
      );

    if (!savedSermonId) {
      throw new Error(
        "Saved sermon ID was not returned"
      );
    }

    // =====================================
    // UPDATE SAVED SERMON STATE
    // =====================================
    sermon.id =
      savedSermonId;

    if (
      window.currentUser?.id &&
      !sermon.author_id
    ) {
      sermon.author_id =
        Number(
          window.currentUser.id
        );
    }

    window.currentGeneratedSermon =
      sermon;

    window.currentSermonId =
      savedSermonId;

    localStorage.setItem(
      "last_saved_sermon_id",
      String(
        savedSermonId
      )
    );

    // =====================================
    // USER-SPECIFIC DRAFT
    // =====================================
    const draftKey =
      getLatestSermonKey();

    if (draftKey) {
      localStorage.setItem(
        draftKey,
        JSON.stringify(
          sermon
        )
      );
    }

    // =====================================
    // REFRESH UI
    // This hides Save and shows Update.
    // =====================================
    if (
      typeof window.renderCurrentSermon ===
      "function"
    ) {
      window.renderCurrentSermon(
        sermon,
        false
      );
    }

    showToast?.(
      "✅ Sermon saved",
      "success"
    );

  } catch (err) {
    console.error(
      "Save sermon error:",
      err
    );

    showToast?.(
      err.message ||
      "Save failed",
      "error"
    );
  }
}

// =====================================
// UPDATE CURRENT SERMON
// =====================================
async function updateCurrentSermon() {

  const sermon =
    window.currentGeneratedSermon;

  const sermonId =
    Number(
      window.currentSermonId
    );

  if (
    !sermon ||
    !sermonId
  ) {
    showToast?.(
      "No saved sermon loaded",
      "error"
    );

    return;
  }

  // =====================================
  // SYNC EDITED FORM VALUES
  // =====================================
  const editedPrompt =
    $("userInput")
      ?.value
      ?.trim() || "";

  sermon.input =
    editedPrompt;

  sermon.message =
    editedPrompt;

  sermon.scripture =
    $("bibleInput")
      ?.value
      ?.trim() || "";

  sermon.denomination =
    $("denomination")
      ?.value || "general";

  sermon.audience =
    $("audience")
      ?.value
      ?.trim() || "";

  sermon.context =
    $("context")
      ?.value
      ?.trim() || "";

  sermon.local_context =
    sermon.context;

  sermon.tone =
    $("tone")
      ?.value || "balanced";

  sermon.duration =
    $("duration")
      ?.value || "30";

  sermon.id =
    sermonId;

  window.currentGeneratedSermon =
    sermon;

  // =====================================
  // SAVE CURRENT DRAFT LOCALLY
  // =====================================
  const draftKey =
    getLatestSermonKey();

  if (draftKey) {
    localStorage.setItem(
      draftKey,
      JSON.stringify(
        sermon
      )
    );
  }

  try {
    showToast?.(
      "📝 Updating sermon...",
      "success"
    );

    const response =
      await apiFetch(
        `/api/v1/faith/sermon/update/${sermonId}`,
        {
          method: "PUT",

          headers: {
            "Content-Type":
              "application/json"
          },

          body: JSON.stringify(
            sermon
          )
        }
      );

    const data =
      await response
        .json()
        .catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data.detail ||
        "Failed to update sermon"
      );
    }

    const updatedSermon =
      data.sermon ||
      sermon;

    updatedSermon.id =
      updatedSermon.id ||
      sermonId;

    window.currentGeneratedSermon =
      updatedSermon;

    window.currentSermonId =
      sermonId;

    if (draftKey) {
      localStorage.setItem(
        draftKey,
        JSON.stringify(
          updatedSermon
        )
      );
    }

    if (
      typeof window.renderCurrentSermon ===
      "function"
    ) {
      window.renderCurrentSermon(
        updatedSermon,
        false
      );
    }

    showToast?.(
      "✅ Sermon updated",
      "success"
    );

  } catch (err) {
    console.error(
      "Update sermon error:",
      err
    );

    showToast?.(
      err.message ||
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

  // =====================================
  // DESKTOP NEVER USES MOBILE TABS
  // =====================================
  if (window.innerWidth > 768) {

    [
      "mobileInputsTab",
      "mobileOutputTab",
      "mobileActionsTab"
    ].forEach(id => {

      const section =
        document.getElementById(id);

      if (section) {
        section.style.display = "block";
      }

    });

    return;
  }


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


  // =====================================
  // CONTROL MOBILE SECTIONS
  // =====================================

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



  // =====================================
  // UPDATE ACTIVE TAB
  // =====================================

  document
    .querySelectorAll(
      ".mobile-tab"
    )
    .forEach(btn => {

      btn.classList.remove(
        "active"
      );

    });


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
    "📱 Sermon workspace tab:",
    tab
  );
}


// =====================================
// SPA INITIALIZATION
// =====================================
function initializeMobileTabs() {

  // Desktop should never use mobile tabs
  if (window.innerWidth > 768) {

    const output =
      document.getElementById(
        "mobileOutputTab"
      );

    const actions =
      document.getElementById(
        "mobileActionsTab"
      );

    if (output) {
      output.style.display = "block";
    }

    if (actions) {
      actions.style.display = "block";
    }

    return;
  }

  showMobileTab("inputs");

  console.log(
    "✅ Mobile tabs initialized"
  );
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
// USER-SPECIFIC DRAFT KEY
// =====================================
function getLatestSermonKey() {

  const userId =
    window.currentUser?.id;

  if (!userId) {
    return null;
  }

  return `latest_sermon_${userId}`;
}
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

window.clearCurrentSermon =
  clearCurrentSermon;

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