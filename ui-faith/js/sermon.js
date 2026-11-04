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
    // GENERATE THROUGH V2 MINISTRY BOUNDARY
    // =====================================
    const ministry =
      window.XynaFaithMinistry;

    if (
      !ministry ||
      typeof ministry.execute !==
        "function"
    ) {
      throw new Error(
        "Xyniva ministry service is unavailable"
      );
    }

    const execution =
      await ministry.execute(
        "sermon.generate",
        payload
      );

    const result =
      execution?.result;

    if (
      !result ||
      typeof result !== "object"
    ) {
      throw new Error(
        "Invalid sermon response"
      );
    }

    // =====================================
    // ADAPT STRUCTURED V2 OUTPUT TO THE
    // EXISTING STUDIO SERMON DOCUMENT
    // =====================================
    const data = {
      ...result,

      input:
        payload.input,

      message:
        payload.input,

      denomination:
        payload.denomination,

      audience:
        payload.audience,

      context:
        payload.context,

      local_context:
        payload.context,

      tone:
        payload.tone,

      duration:
        payload.duration
    };

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

    // A new sermon starts a new contextual
    // Xyniva Studio conversation.
    window.XynivaStudio?.reset?.();

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
      "✨ Sermon generated with Xyniva",
      "success"
    );

  } catch (err) {
    console.error(
      "Generate sermon error:",
      err
    );

    const uncertain =
      err?.uncertain === true;

    // Do not destroy the currently open sermon
    // when a new generation attempt fails.
    output.innerHTML = `
      <div class="error-state">

        <h2>
          ${
            uncertain
              ? "Generation status is uncertain"
              : "Unable to generate sermon"
          }
        </h2>

        <p>
          ${
            uncertain
              ? (
                  "Xyniva could not confirm whether "
                  + "the request completed. "
                  + "Your existing sermon was not changed."
                )
              : (
                  err.message ||
                  "Please try again."
                )
          }
        </p>

      </div>
    `;

    showToast?.(
      uncertain
        ? "Generation status could not be confirmed"
        : (
            err.message ||
            "Failed to generate sermon"
          ),
      "error"
    );
  }
}



// =====================================
// V2 MINISTRY TOOLS
// =====================================

const REFINE_INSTRUCTIONS = {
  deepen:
    "Deepen the sermon with stronger biblical "
    + "reasoning, richer explanation, and clearer "
    + "ministry application while preserving its "
    + "core message.",

  illustration:
    "Strengthen the sermon by adding a relevant "
    + "illustration where it improves understanding. "
    + "Keep the sermon biblically grounded.",

  simplify:
    "Simplify the sermon for clarity and accessibility "
    + "without weakening its biblical substance.",

  scripture:
    "Strengthen the sermon with relevant supporting "
    + "scripture. Do not invent quotations or citations."
};


function canonicalSermonForMinistry(
  sermon
) {

  if (
    !sermon ||
    typeof sermon !== "object"
  ) {
    throw new Error(
      "Generate or open a sermon first"
    );
  }

  const mainPoints =
    Array.isArray(
      sermon.main_points
    )
      ? sermon.main_points
      : [];

  if (
    !String(
      sermon.title || ""
    ).trim() ||
    !String(
      sermon.introduction || ""
    ).trim() ||
    mainPoints.length === 0 ||
    !String(
      sermon.application || ""
    ).trim() ||
    !String(
      sermon.conclusion || ""
    ).trim()
  ) {
    throw new Error(
      "The current sermon is not ready for refinement"
    );
  }

  return {
    title:
      String(
        sermon.title
      ).trim(),

    scripture:
      String(
        sermon.scripture || ""
      ).trim(),

    introduction:
      String(
        sermon.introduction
      ).trim(),

    main_points:
      mainPoints.map(
        point => ({
          title:
            String(
              point?.title || ""
            ).trim(),

          content:
            String(
              point?.content || ""
            ).trim()
        })
      ),

    application:
      String(
        sermon.application
      ).trim(),

    conclusion:
      String(
        sermon.conclusion
      ).trim()
  };
}


function currentMinistryContext() {

  return {
    denomination:
      $("denomination")
        ?.value ||
      window.currentGeneratedSermon
        ?.denomination ||
      "general",

    audience:
      $("audience")
        ?.value
        ?.trim() ||
      window.currentGeneratedSermon
        ?.audience ||
      "",

    context:
      $("context")
        ?.value
        ?.trim() ||
      window.currentGeneratedSermon
        ?.context ||
      window.currentGeneratedSermon
        ?.local_context ||
      "",

    tone:
      $("tone")
        ?.value ||
      window.currentGeneratedSermon
        ?.tone ||
      "balanced"
  };
}


function setRefineBusy(
  busy
) {

  document
    .querySelectorAll(
      "[data-refine-action]"
    )
    .forEach(button => {
      button.disabled =
        Boolean(busy);
    });
}


async function refine(
  refineType
) {

  const ministry =
    window.XynaFaithMinistry;

  if (
    !ministry ||
    typeof ministry.execute !==
      "function"
  ) {
    showToast?.(
      "Xyniva ministry service is unavailable",
      "error"
    );

    return;
  }

  const instruction =
    REFINE_INSTRUCTIONS[
      refineType
    ];

  if (!instruction) {
    showToast?.(
      "Unknown refinement option",
      "error"
    );

    return;
  }

  const existing =
    window.currentGeneratedSermon;

  if (!existing) {
    showToast?.(
      "Generate or open a sermon first",
      "error"
    );

    return;
  }

  const savedId =
    existing.id ||
    window.currentSermonId ||
    null;

  const authorId =
    existing.author_id ||
    null;

  const metadata = {
    input:
      existing.input ||
      existing.message ||
      "",

    message:
      existing.message ||
      existing.input ||
      "",

    duration:
      existing.duration ||
      $("duration")
        ?.value ||
      "30"
  };

  try {

    const sermon =
      canonicalSermonForMinistry(
        existing
      );

    const context =
      currentMinistryContext();

    setRefineBusy(
      true
    );

    showToast?.(
      "✨ Xyniva is refining your sermon...",
      "success"
    );

    const execution =
      await ministry.execute(
        "sermon.refine",
        {
          sermon,
          instruction,

          denomination:
            context.denomination,

          audience:
            context.audience,

          context:
            context.context,

          tone:
            context.tone
        }
      );

    const result =
      execution?.result;

    if (
      !result ||
      typeof result !== "object"
    ) {
      throw new Error(
        "Invalid sermon refinement response"
      );
    }

    const refined = {
      ...result,

      ...metadata,

      denomination:
        context.denomination,

      audience:
        context.audience,

      context:
        context.context,

      local_context:
        context.context,

      tone:
        context.tone
    };

    if (savedId) {
      refined.id =
        Number(savedId);
    }

    if (authorId) {
      refined.author_id =
        Number(authorId);
    }

    window.currentGeneratedSermon =
      refined;

    window.currentSermonId =
      savedId
        ? Number(savedId)
        : null;

    const draftKey =
      getLatestSermonKey();

    if (draftKey) {
      localStorage.setItem(
        draftKey,
        JSON.stringify(
          refined
        )
      );
    }

    if (
      typeof window.renderCurrentSermon ===
        "function"
    ) {
      window.renderCurrentSermon(
        refined,
        false
      );
    } else {
      throw new Error(
        "Sermon renderer is unavailable"
      );
    }

    showToast?.(
      savedId
        ? (
            "✨ Sermon refined. "
            + "Use Update Sermon to save changes."
          )
        : "✨ Sermon refined with Xyniva",
      "success"
    );

  } catch (err) {

    console.error(
      "Refine sermon error:",
      err
    );

    showToast?.(
      err?.uncertain
        ? (
            "Refinement status could not be "
            + "confirmed. Your sermon was not changed."
          )
        : (
            err?.message ||
            "Failed to refine sermon"
          ),
      "error"
    );

  } finally {

    setRefineBusy(
      false
    );
  }
}


function escapeMinistryHTML(
  value
) {

  return String(
    value ?? ""
  )
    .replaceAll(
      "&",
      "&amp;"
    )
    .replaceAll(
      "<",
      "&lt;"
    )
    .replaceAll(
      ">",
      "&gt;"
    )
    .replaceAll(
      '"',
      "&quot;"
    )
    .replaceAll(
      "'",
      "&#039;"
    );
}


function renderResearchSections(
  title,
  sections
) {

  if (
    !Array.isArray(sections) ||
    sections.length === 0
  ) {
    return "";
  }

  const items =
    sections
      .map(
        section => `
          <div
            style="
              padding:12px;
              border:1px solid #E5E7EB;
              border-radius:12px;
            "
          >
            <strong>
              ${
                escapeMinistryHTML(
                  section?.heading
                )
              }
            </strong>

            <p
              style="
                margin-top:8px;
                line-height:1.7;
                white-space:pre-wrap;
              "
            >
              ${
                escapeMinistryHTML(
                  section?.content
                )
              }
            </p>
          </div>
        `
      )
      .join("");

  return `
    <section>
      <h4
        style="
          margin-bottom:10px;
        "
      >
        ${
          escapeMinistryHTML(
            title
          )
        }
      </h4>

      <div
        style="
          display:grid;
          gap:10px;
        "
      >
        ${items}
      </div>
    </section>
  `;
}


function renderBiblicalResearch(
  research
) {

  const output =
    $("biblicalResearchOutput");

  if (!output) {
    return;
  }

  const cautions =
    Array.isArray(
      research?.cautions
    )
      ? research.cautions
      : [];

  const cautionHTML =
    cautions.length
      ? `
        <section>
          <h4>
            ⚠️ Interpretive Cautions
          </h4>

          <ul
            style="
              margin-top:10px;
              padding-left:20px;
              line-height:1.7;
            "
          >
            ${
              cautions
                .map(
                  item => `
                    <li>
                      ${
                        escapeMinistryHTML(
                          item
                        )
                      }
                    </li>
                  `
                )
                .join("")
            }
          </ul>
        </section>
      `
      : "";

  output.innerHTML = `
    <section>
      <h3>
        ${
          escapeMinistryHTML(
            research?.title ||
            "Biblical Research"
          )
        }
      </h3>

      ${
        research?.scripture
          ? `
            <p
              style="
                margin-top:6px;
                color:#64748B;
              "
            >
              ${
                escapeMinistryHTML(
                  research.scripture
                )
              }
            </p>
          `
          : ""
      }

      <p
        style="
          margin-top:10px;
          line-height:1.7;
        "
      >
        ${
          escapeMinistryHTML(
            research?.summary || ""
          )
        }
      </p>
    </section>

    ${
      renderResearchSections(
        "Textual Observations",
        research?.observations
      )
    }

    ${
      renderResearchSections(
        "Interpretation",
        research?.interpretation
      )
    }

    ${
      renderResearchSections(
        "Theological Perspectives",
        research?.theological_perspectives
      )
    }

    ${
      renderResearchSections(
        "Ministry Application",
        research?.ministry_application
      )
    }

    ${cautionHTML}
  `;

  output.hidden =
    false;

  output.style.display =
    "grid";
}


async function researchCurrentSermon() {

  const ministry =
    window.XynaFaithMinistry;

  const button =
    $("biblicalResearchBtn");

  const status =
    $("biblicalResearchStatus");

  if (
    !ministry ||
    typeof ministry.execute !==
      "function"
  ) {
    showToast?.(
      "Xyniva ministry service is unavailable",
      "error"
    );

    return;
  }

  const current =
    window.currentGeneratedSermon ||
    {};

  const scripture =
    $("bibleInput")
      ?.value
      ?.trim() ||
    current.scripture ||
    "";

  const topic =
    $("userInput")
      ?.value
      ?.trim() ||
    current.input ||
    current.message ||
    current.title ||
    "";

  const question =
    $("biblicalResearchQuestion")
      ?.value
      ?.trim() ||
    "";

  if (
    !scripture &&
    !topic
  ) {
    showToast?.(
      "Enter a scripture passage or sermon topic first",
      "error"
    );

    return;
  }

  const context =
    currentMinistryContext();

  try {

    if (button) {
      button.disabled =
        true;
    }

    if (status) {
      status.hidden =
        false;

      status.textContent =
        "Xyniva is researching the biblical context…";
    }

    const execution =
      await ministry.execute(
        "biblical.research",
        {
          scripture,
          topic,
          question,

          denomination:
            context.denomination,

          audience:
            context.audience,

          context:
            context.context
        }
      );

    const result =
      execution?.result;

    if (
      !result ||
      typeof result !== "object"
    ) {
      throw new Error(
        "Invalid biblical research response"
      );
    }

    renderBiblicalResearch(
      result
    );

    if (status) {
      status.textContent =
        "Research complete";
    }

    showToast?.(
      "📚 Biblical research ready",
      "success"
    );

  } catch (err) {

    console.error(
      "Biblical research error:",
      err
    );

    if (status) {
      status.hidden =
        false;

      status.textContent =
        err?.uncertain
          ? (
              "Research status could not "
              + "be confirmed."
            )
          : (
              err?.message ||
              "Biblical research failed"
            );
    }

    showToast?.(
      err?.uncertain
        ? "Research status could not be confirmed"
        : (
            err?.message ||
            "Biblical research failed"
          ),
      "error"
    );

  } finally {

    if (button) {
      button.disabled =
        false;
    }
  }
}



function sermonSourceContent(
  sermon
) {

  const canonical =
    canonicalSermonForMinistry(
      sermon
    );

  const points =
    canonical.main_points
      .map(
        (point, index) =>
          `${index + 1}. ${point.title}\n${point.content}`
      )
      .join("\n\n");

  return [
    `Title: ${canonical.title}`,
    canonical.scripture
      ? `Scripture: ${canonical.scripture}`
      : "",
    `Introduction:\n${canonical.introduction}`,
    `Main Points:\n${points}`,
    `Application:\n${canonical.application}`,
    `Conclusion:\n${canonical.conclusion}`
  ]
    .filter(Boolean)
    .join("\n\n");
}


function selectedContentFormats() {

  return Array.from(
    document.querySelectorAll(
      "#contentEngineFormats "
      + 'input[type="checkbox"]:checked'
    )
  )
    .map(input =>
      String(
        input.value || ""
      ).trim()
    )
    .filter(Boolean);
}


function contentFormatLabel(
  format
) {

  const labels = {
    social_post:
      "Social Post",

    whatsapp_summary:
      "WhatsApp Summary",

    church_announcement:
      "Church Announcement",

    discussion_questions:
      "Discussion Questions",

    sermon_recap:
      "Sermon Recap",

    newsletter:
      "Newsletter",

    devotional:
      "Devotional"
  };

  return labels[format] ||
    String(format || "");
}


function renderContentEngineResult(
  result
) {

  const output =
    $("contentEngineOutput");

  if (!output) {
    return;
  }

  const pieces =
    Array.isArray(
      result?.pieces
    )
      ? result.pieces
      : [];

  output.innerHTML =
    pieces
      .map(piece => {

        const format =
          String(
            piece?.format || ""
          ).trim();

        const title =
          String(
            piece?.title || ""
          ).trim();

        const content =
          String(
            piece?.content || ""
          ).trim();

        return `
          <section
            style="
              border:1px solid #E2E8F0;
              border-radius:14px;
              padding:16px;
              background:#FFFFFF;
            "
          >
            <div
              style="
                color:#64748B;
                font-size:0.85rem;
                font-weight:600;
                margin-bottom:6px;
              "
            >
              ${escapeMinistryHTML(
                contentFormatLabel(format)
              )}
            </div>

            ${
              title
                ? `
                  <h4
                    style="
                      margin:0 0 10px;
                    "
                  >
                    ${escapeMinistryHTML(
                      title
                    )}
                  </h4>
                `
                : ""
            }

            <div
              style="
                white-space:pre-wrap;
                line-height:1.65;
              "
            >${escapeMinistryHTML(
              content
            )}</div>
          </section>
        `;
      })
      .join("");

  output.hidden =
    pieces.length === 0;

  output.style.display =
    pieces.length
      ? "grid"
      : "none";
}


async function createFromCurrentSermon() {

  const ministry =
    window.XynaFaithMinistry;

  const button =
    $("contentEngineBtn");

  const status =
    $("contentEngineStatus");

  if (
    !ministry ||
    typeof ministry.execute !==
      "function"
  ) {
    showToast?.(
      "Xyniva ministry service is unavailable",
      "error"
    );

    return;
  }

  const formats =
    selectedContentFormats();

  if (formats.length === 0) {
    showToast?.(
      "Choose at least one content format",
      "error"
    );

    return;
  }

  let sermon;
  let sourceContent;

  try {
    sermon =
      canonicalSermonForMinistry(
        window.currentGeneratedSermon
      );

    sourceContent =
      sermonSourceContent(
        sermon
      );
  } catch (err) {
    showToast?.(
      err?.message ||
        "Generate or open a sermon first",
      "error"
    );

    return;
  }

  const context =
    currentMinistryContext();

  try {

    if (button) {
      button.disabled =
        true;
    }

    if (status) {
      status.hidden =
        false;

      status.textContent =
        "Xyniva is creating ministry content…";
    }

    const execution =
      await ministry.execute(
        "content.transform",
        {
          source_title:
            sermon.title,

          source_scripture:
            sermon.scripture,

          source_content:
            sourceContent,

          formats,

          audience:
            context.audience,

          tone:
            context.tone,

          denomination:
            context.denomination,

          context:
            context.context
        }
      );

    const result =
      execution?.result;

    const pieces =
      Array.isArray(
        result?.pieces
      )
        ? result.pieces
        : [];

    const returnedFormats =
      pieces.map(piece =>
        String(
          piece?.format || ""
        ).trim()
      );

    const expected =
      new Set(formats);

    const returned =
      new Set(
        returnedFormats
      );

    if (
      !result ||
      typeof result !== "object" ||
      pieces.length !== formats.length ||
      returned.size !== expected.size ||
      [...expected].some(
        format =>
          !returned.has(format)
      ) ||
      pieces.some(
        piece =>
          !String(
            piece?.content || ""
          ).trim()
      )
    ) {
      throw new Error(
        "Invalid content transformation response"
      );
    }

    renderContentEngineResult(
      result
    );

    if (status) {
      status.textContent =
        "Content ready";
    }

    showToast?.(
      "✨ Ministry content ready",
      "success"
    );

  } catch (err) {

    console.error(
      "Content transformation error:",
      err
    );

    if (status) {
      status.hidden =
        false;

      status.textContent =
        err?.uncertain
          ? (
              "Content creation status "
              + "could not be confirmed."
            )
          : (
              err?.message ||
              "Content creation failed"
            );
    }

    showToast?.(
      err?.uncertain
        ? (
            "Content creation status "
            + "could not be confirmed"
          )
        : (
            err?.message ||
            "Content creation failed"
          ),
      "error"
    );

  } finally {

    if (button) {
      button.disabled =
        false;
    }
  }
}


window.createFromCurrentSermon =
  createFromCurrentSermon;


window.refine =
  refine;

window.researchCurrentSermon =
  researchCurrentSermon;

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

            ? data.main_points.map((point) => `

                <section class="sermon-section">

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