(() => {
  "use strict";

  const ROOT_ID = "xfBibleQuizReview2485";

  let root = null;
  let church = null;
  let draft = null;
  let snapshots = new Map();
  let busy = false;
  let generation = 0;

  const el = id => document.getElementById(id);

  function status(text) {
    const target = el("xfReviewStatus");
    if (target) target.textContent = text;
  }

  function selectedChurch() {
    const value = Number(el("xfBqChurch")?.value);

    if (!Number.isSafeInteger(value) || value <= 0) {
      throw new Error("Select a valid church first.");
    }

    return value;
  }

  function formData(form) {
    return Object.fromEntries(
      new FormData(form).entries()
    );
  }

  function snapshot(form) {
    return JSON.stringify(formData(form));
  }

  function forms() {
    return Array.from(
      el("xfReviewQuestions")?.querySelectorAll(
        "form[data-question-id]"
      ) || []
    );
  }

  function dirty() {
    return forms().some(form =>
      snapshots.get(form.dataset.questionId) !== snapshot(form)
    );
  }

  function confirmDiscard() {
    return !dirty() || window.confirm(
      "You have unsaved question changes. Discard them?"
    );
  }

  function updatePublish() {
    const button = el("xfReviewPublish");
    if (!button) return;

    const unsaved = dirty();

    button.disabled = busy || unsaved || !draft;
    button.title = unsaved
      ? "Save all question changes before publishing."
      : "";
  }

  function clearDraft() {
    draft = null;
    snapshots.clear();

    el("xfReviewQuestions")?.replaceChildren();

    const button = el("xfReviewPublish");
    if (button) {
      button.hidden = true;
      button.disabled = true;
    }
  }

  function setChurch() {
    const next = selectedChurch();

    if (next === church) return true;

    if (church !== null && !confirmDiscard()) {
      el("xfBqChurch").value = String(church);
      return false;
    }

    church = next;
    generation++;
    clearDraft();

    const select = el("xfReviewDraftSelect");
    if (select) select.replaceChildren();

    status("Church changed. Load drafts for this church.");

    return true;
  }

  async function request(path, method = "GET", body, expectedChurch = church) {
    if (typeof window.apiFetch !== "function") {
      throw new Error("Authenticated API client unavailable.");
    }

    if (!Number.isSafeInteger(expectedChurch) ||
        expectedChurch <= 0 ||
        expectedChurch !== church ||
        selectedChurch() !== expectedChurch) {
      throw new Error(
        "Church context changed. Reload drafts before continuing."
      );
    }

    const response = await window.apiFetch(
      "/api/v1/churches/" +
        encodeURIComponent(expectedChurch) +
        "/bible-quizzes" + path,
      {
        method,
        headers: {
          "Content-Type": "application/json"
        },
        ...(body === undefined ? {} : {
          body: JSON.stringify(body)
        })
      }
    );

    if (response && typeof response.json === "function") {
      const payload = await response.json();

      if (response.ok === false) {
        throw new Error(
          typeof payload?.detail === "string"
            ? payload.detail
            : "The operation was rejected."
        );
      }

      return payload;
    }

    if (!response || typeof response !== "object") {
      throw new Error("Unexpected API response.");
    }

    return response;
  }

  function field(label, value, name, multiline = false) {
    const wrapper = document.createElement("label");
    wrapper.style.display = "block";
    wrapper.style.margin = "8px 0";

    const heading = document.createElement("span");
    heading.textContent = label;
    heading.style.display = "block";

    const input = document.createElement(
      multiline ? "textarea" : "input"
    );

    input.name = name;
    input.value = value ?? "";
    input.style.width = "100%";

    if (multiline) input.rows = 2;

    wrapper.append(heading, input);
    return wrapper;
  }

  function renderDraft(value) {
    clearDraft();
    draft = value;

    const panel = el("xfReviewQuestions");

    const heading = document.createElement("h3");
    heading.textContent =
      value.title + " — Draft #" + value.id;

    panel.append(heading);

    for (const question of value.questions || []) {
      const form = document.createElement("form");
      form.dataset.questionId = String(question.id);

      const title = document.createElement("h4");
      title.textContent = "Question " + question.position;
      form.append(title);

      for (const [label, name, multiline] of [
        ["Question", "question_text", true],
        ["Option A", "option_a", false],
        ["Option B", "option_b", false],
        ["Option C", "option_c", false],
        ["Option D", "option_d", false],
        ["Explanation", "explanation", true]
      ]) {
        form.append(
          field(label, question[name], name, multiline)
        );
      }

      const answerLabel = document.createElement("label");
      answerLabel.textContent = "Correct answer ";

      const answer = document.createElement("select");
      answer.name = "correct_option";

      for (const option of ["A", "B", "C", "D"]) {
        const item = document.createElement("option");
        item.value = option;
        item.textContent = option;
        item.selected = option === question.correct_option;
        answer.append(item);
      }

      answerLabel.append(answer);
      form.append(answerLabel);

      const save = document.createElement("button");
      save.type = "submit";
      save.textContent = "Save question";
      save.style.margin = "12px";
      form.append(save);

      form.addEventListener("input", updatePublish);
      form.addEventListener("change", updatePublish);

      form.addEventListener("submit", async event => {
        event.preventDefault();

        if (busy) return;

        const data = formData(form);

        for (const key of [
          "question_text", "option_a", "option_b",
          "option_c", "option_d"
        ]) {
          if (!String(data[key] || "").trim()) {
            status("Question and options cannot be blank.");
            return;
          }
        }

        const savedVersion = generation;
        const savedChurch = church;
        const submittedSnapshot = JSON.stringify(data);

        try {
          busy = true;
          save.disabled = true;
          updatePublish();

          await request(
            "/" + value.id +
              "/questions/" + question.id,
            "PATCH",
            data,
            savedChurch
          );

          if (savedVersion !== generation ||
              savedChurch !== church ||
              !root?.isConnected) {
            return;
          }

          snapshots.set(
            String(question.id),
            submittedSnapshot
          );

          status(
            snapshot(form) === submittedSnapshot
              ? "Question saved."
              : "Question saved. You have newer unsaved edits."
          );
        } catch (error) {
          if (savedVersion === generation) {
            status(error.message);
          }
        } finally {
          if (savedVersion === generation) {
            busy = false;
            save.disabled = false;
            updatePublish();
          }
        }
      });

      panel.append(form);

      snapshots.set(
        String(question.id),
        snapshot(form)
      );
    }

    const publishButton = el("xfReviewPublish");
    publishButton.hidden = false;

    updatePublish();
  }

  async function loadDraft(id, version, selected) {
    const value = await request(
      "/" + encodeURIComponent(id) + "/author-draft",
      "GET",
      undefined,
      selected
    );

    if (version !== generation ||
        selected !== church ||
        !root?.isConnected) {
      return false;
    }

    renderDraft(value);
    status("Review the questions before publishing.");
    return true;
  }

  async function loadDrafts(successMessage = "") {
    if (!setChurch()) return false;
    if (!confirmDiscard()) return false;

    const version = generation;
    const selected = church;

    const drafts = await request(
      "/my-drafts",
      "GET",
      undefined,
      selected
    );

    if (version !== generation ||
        selected !== church ||
        !root?.isConnected) {
      return false;
    }

    const select = el("xfReviewDraftSelect");
    select.replaceChildren();

    for (const item of drafts) {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent =
        "#" + item.id + " — " + item.title;
      select.append(option);
    }

    if (drafts.length) {
      await loadDraft(drafts[0].id, version, selected);
    } else {
      clearDraft();
      status("No drafts found for this author.");
    }

    if (successMessage &&
        version === generation &&
        root?.isConnected) {
      status(successMessage);
    }

    return true;
  }

  async function publish() {
    if (!draft || busy) return;

    if (!setChurch()) return;
    if (!draft) {
      status("Reload drafts before publishing.");
      return;
    }

    if (dirty()) {
      status("Save all question changes before publishing.");
      updatePublish();
      return;
    }

    const id = draft.id;

    if (!window.confirm(
      "Publish quiz #" + id +
      "? This makes it available to church members."
    )) return;

    const version = generation;
    const selected = church;

    try {
      busy = true;
      updatePublish();

      await request(
        "/" + id + "/publish",
        "POST",
        undefined,
        selected
      );

      if (version !== generation ||
          selected !== church ||
          !root?.isConnected) {
        return;
      }

      clearDraft();

      try {
        await loadDrafts(
          "Quiz #" + id + " published successfully."
        );
      } catch (error) {
        status(
          "Quiz #" + id +
          " published successfully. " +
          "Draft refresh failed: " + error.message
        );
      }
    } catch (error) {
      if (version === generation) {
        status(error.message);
      }
    } finally {
      if (version === generation) {
        busy = false;
        updatePublish();
      }
    }
  }

  function initialize() {
    const generator = el("xfBibleQuizAI");

    if (!generator) return;

    if (generator !== root) {
      root = generator;
      church = null;
      draft = null;
      snapshots.clear();
      generation++;
      busy = false;
    }

    if (el(ROOT_ID)) return;

    const section = document.createElement("section");
    section.id = ROOT_ID;
    section.style.marginTop = "24px";

    const title = document.createElement("h2");
    title.textContent = "Review Bible Quiz Drafts";

    const refresh = document.createElement("button");
    refresh.type = "button";
    refresh.textContent = "Load my drafts";

    const select = document.createElement("select");
    select.id = "xfReviewDraftSelect";
    select.setAttribute(
      "aria-label",
      "Select quiz draft"
    );

    const questions = document.createElement("div");
    questions.id = "xfReviewQuestions";

    const publishButton = document.createElement("button");
    publishButton.id = "xfReviewPublish";
    publishButton.type = "button";
    publishButton.textContent = "Publish reviewed quiz";
    publishButton.hidden = true;

    const message = document.createElement("p");
    message.id = "xfReviewStatus";
    message.setAttribute("role", "status");

    section.append(
      title,
      refresh,
      select,
      questions,
      publishButton,
      message
    );

    generator.append(section);

    el("xfBqChurch")?.addEventListener("change", () => {
      if (busy) {
        if (church !== null) {
          el("xfBqChurch").value = String(church);
        }
        status("Wait for the current operation to finish.");
        return;
      }

      try {
        setChurch();
      } catch (error) {
        status(error.message);
      }
    });

    refresh.addEventListener("click", async () => {
      if (busy) return;

      try {
        if (!setChurch() || !confirmDiscard()) return;

        busy = true;
        updatePublish();

        await loadDrafts();
      } catch (error) {
        status(error.message);
      } finally {
        busy = false;
        updatePublish();
      }
    });

    select.addEventListener("change", async () => {
      if (!select.value || busy) return;

      if (!setChurch() || !confirmDiscard()) {
        if (draft) select.value = String(draft.id);
        return;
      }

      const version = generation;
      const selected = church;

      try {
        busy = true;
        updatePublish();

        await loadDraft(select.value, version, selected);
      } catch (error) {
        status(error.message);
        if (draft) select.value = String(draft.id);
      } finally {
        busy = false;
        updatePublish();
      }
    });

    publishButton.addEventListener("click", publish);
  }

  document.addEventListener(
    "DOMContentLoaded",
    initialize
  );

  if (document.readyState !== "loading") {
    initialize();
  }

  new MutationObserver(initialize).observe(
    document.documentElement,
    {
      childList: true,
      subtree: true
    }
  );
})();
