(() => {
  "use strict";

  const STORAGE_PREFIX = "xf-bible-quiz-ai-v2:";
  let busy = false;
  let activeRequest = null;
  let activeRoot = null;

  const byId = (id) => document.getElementById(id);

  function status(message) {
    const element = byId("xfBqStatus");
    if (element) element.textContent = message;
  }

  function updateButtons() {
    const generate = byId("xfBqGenerate");
    const recover = byId("xfBqRecover");
    const startNew = byId("xfBqNew");

    if (generate) {
      generate.disabled = busy || !!activeRequest;
    }
    if (recover) {
      recover.hidden = !activeRequest;
      recover.disabled = busy;
    }
    if (startNew) {
      startNew.hidden = !activeRequest;
      startNew.disabled = busy;
    }

    const form = byId("xfBqForm");
    if (form) {
      form.querySelectorAll("input, select").forEach(
        field => { field.disabled = busy || !!activeRequest; }
      );
    }
  }

  function churchId() {
    const input = byId("xfBqChurch");
    const id = Number(input?.value);
    if (!Number.isSafeInteger(id) || id <= 0) {
      throw new Error("Enter a valid church ID.");
    }
    return id;
  }

  function storageKey(id) {
    return STORAGE_PREFIX + id;
  }

  function getInputs() {
    const id = churchId();
    const topic = byId("xfBqTopic").value.trim();
    const scripture = byId("xfBqScripture").value.trim();
    const difficulty = byId("xfBqDifficulty").value;
    const question_count = Number(byId("xfBqCount").value);

    if (!topic || topic.length > 200) {
      throw new Error("Enter a valid Bible topic.");
    }
    if (!scripture || scripture.length > 500) {
      throw new Error("Enter a valid scripture reference.");
    }
    if (!["beginner", "intermediate", "advanced"]
          .includes(difficulty)) {
      throw new Error("Choose a valid difficulty.");
    }
    if (!Number.isInteger(question_count) ||
        question_count < 1 || question_count > 50) {
      throw new Error("Choose between 1 and 50 questions.");
    }

    if (!globalThis.crypto?.randomUUID) {
      throw new Error(
        "Secure request IDs are unavailable in this browser."
      );
    }

    return {
      church_id: id,
      request_id: crypto.randomUUID(),
      topic,
      scripture,
      difficulty,
      question_count
    };
  }

  function saveRequest(request) {
    sessionStorage.setItem(
      storageKey(request.church_id),
      JSON.stringify(request)
    );
  }

  function clearRequest() {
    if (activeRequest) {
      sessionStorage.removeItem(
        storageKey(activeRequest.church_id)
      );
    }
    activeRequest = null;
  }

  function setRequest(request) {
    activeRequest = request;

    byId("xfBqChurch").value = request.church_id;
    byId("xfBqTopic").value = request.topic;
    byId("xfBqScripture").value = request.scripture;
    byId("xfBqDifficulty").value = request.difficulty;
    byId("xfBqCount").value = request.question_count;

    updateButtons();
  }

  function restoreRequest() {
    if (activeRequest) return;

    let id;
    try {
      id = churchId();
    } catch (_) {
      return;
    }

    try {
      const saved = sessionStorage.getItem(storageKey(id));
      if (!saved) return;

      const request = JSON.parse(saved);
      if (request.church_id !== id ||
          !request.request_id ||
          !request.topic ||
          !request.scripture) {
        return;
      }

      setRequest(request);
      status(
        "A previous AI request was found. " +
        "Use Check / Recover Request to verify its status."
      );
    } catch (_) {
      status("Unable to restore the previous request.");
    }
  }

  function fillChurchContext() {
    const input = byId("xfBqChurch");
    if (!input || input.value) return;

    const candidates = [
      window.currentChurchId,
      window.activeChurchId,
      window.currentChurch?.id,
      window.activeChurch?.id
    ];

    for (const candidate of candidates) {
      const id = Number(candidate);
      if (Number.isSafeInteger(id) && id > 0) {
        input.value = String(id);
        break;
      }
    }
  }

  async function apiRequest(request, action) {
    if (typeof window.apiFetch !== "function") {
      throw new Error(
        "Authenticated API client is unavailable. " +
        "Sign in through XynaFaith."
      );
    }

    const endpoint =
      "/api/v1/churches/" +
      encodeURIComponent(request.church_id) +
      "/bible-quizzes/ai/" + action;

    const { church_id, ...body } = request;

    const response = await window.apiFetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body)
    });

    if (response && typeof response.json === "function") {
      if (response.ok === false) {
        let detail = "";
        try {
          const payload = await response.json();
          detail = typeof payload.detail === "string"
            ? payload.detail : "";
        } catch (_) {}

        throw new Error(
          detail || "AI request could not be completed."
        );
      }
      return await response.json();
    }

    if (!response || typeof response !== "object") {
      throw new Error(
        "Unexpected response from the AI service."
      );
    }

    return response;
  }

  function renderResult(result) {
    const panel = byId("xfBqResult");
    const text = byId("xfBqResultText");

    if (!panel || !text) return;

    const state = result?.status;

    if (state === "completed" &&
        Number.isSafeInteger(Number(result.quiz_id)) &&
        Number(result.quiz_id) > 0) {
      panel.hidden = false;
      text.textContent =
        "Draft #" + result.quiz_id +
        " was saved successfully. It has not been published.";
      status("Bible Quiz draft created successfully.");
      return;
    }

    panel.hidden = true;

    if (state === "pending" || state === "running") {
      status(
        "The AI request is " + state +
        ". Use Check / Recover Request to update its status."
      );
    } else if (state === "uncertain") {
      status(
        "The execution status is uncertain. " +
        "Use recovery; do not submit a new request."
      );
    } else if (state === "failed") {
      status(
        "The AI request failed. Check the service " +
        "before starting a new request."
      );
    } else {
      status(
        "The server returned an unexpected request status."
      );
    }
  }

  async function run(action) {
    if (busy) return;

    busy = true;
    updateButtons();

    try {
      if (action === "generate") {
        if (activeRequest) {
          throw new Error(
            "Recover or resolve the existing request first."
          );
        }

        activeRequest = getInputs();
        saveRequest(activeRequest);
      }

      if (!activeRequest) {
        throw new Error("No request is available to recover.");
      }

      status(
        action === "generate"
          ? "Generating your Bible Quiz with Xyniva..."
          : "Checking the existing AI execution..."
      );

      const result = await apiRequest(
        activeRequest,
        action
      );

      if (result.request_id !== activeRequest.request_id) {
        throw new Error(
          "The server returned a different request ID."
        );
      }

      renderResult(result);

    } catch (error) {
      status(
        (error?.message || "The request could not be verified.") +
        " Your request ID has been retained for recovery."
      );
    } finally {
      busy = false;
      updateButtons();
    }
  }

  function initialize() {
    const root = byId("xfBibleQuizAI");

    if (!root || root === activeRoot) return;

    activeRoot = root;
    activeRequest = null;
    busy = false;

    const form = byId("xfBqForm");
    const recover = byId("xfBqRecover");
    const startNew = byId("xfBqNew");
    const church = byId("xfBqChurch");

    if (!form || !recover || !startNew || !church) {
      return;
    }

    form.addEventListener("submit", event => {
      event.preventDefault();
      run("generate");
    });

    recover.addEventListener("click", () => {
      run("recover");
    });

    startNew.addEventListener("click", () => {
      if (busy) return;

      const confirmed = window.confirm(
        "Start a new quiz? Only do this after the " +
        "previous request is completed or definitively resolved."
      );

      if (!confirmed) return;

      clearRequest();
      byId("xfBqResult").hidden = true;
      status("Ready for a new Bible Quiz.");
      updateButtons();
    });

    church.addEventListener("change", () => {
      if (activeRequest) return;
      restoreRequest();
    });

    fillChurchContext();
    restoreRequest();
    updateButtons();
  }

  function start() {
    initialize();

    if (!document.body) return;

    new MutationObserver(initialize).observe(
      document.body,
      { childList: true, subtree: true }
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded", start, { once: true }
    );
  } else {
    start();
  }
})();
