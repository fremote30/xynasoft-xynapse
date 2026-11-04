(() => {
  "use strict";

  const FORMATS = [
    ["whatsapp_summary", "WhatsApp Summary"],
    ["social_post", "Social Media Post"],
    ["church_announcement", "Church Announcement"],
    ["discussion_questions", "Discussion Questions"],
    ["sermon_recap", "Sermon Recap"],
    ["newsletter", "Newsletter"],
    ["devotional", "Devotional"]
  ];

  const $ = id => document.getElementById(id);

  let pending = null;
  let busy = false;
  let sessionGeneration = 0;

  function setStatus(message) {
    $("status").textContent = message;
  }

  const TOKEN_KEY = "xynafaith_v2_access_token";

  function token() {
    return sessionStorage.getItem(TOKEN_KEY);
  }

  function showLogin(message = "") {
    sessionGeneration += 1;
    $("loginPanel").hidden = false;
    $("studioWorkspace").hidden = true;
    $("signOut").hidden = true;
    $("loginStatus").textContent = message;
    pending = null;
    busy = false;
    $("generatePack").disabled = false;
    $("sermonSelect").replaceChildren(
      new Option("Choose a sermon", "")
    );
    $("results").replaceChildren();
    $("status").textContent = "";
    $("retryPack").hidden = true;
    $("resultsPanel").hidden = true;
  }

  function showStudio() {
    $("loginPanel").hidden = true;
    $("studioWorkspace").hidden = false;
    $("signOut").hidden = false;
    $("loginPassword").value = "";
  }

  function signOut() {
    sessionStorage.removeItem(TOKEN_KEY);
    showLogin("You have signed out.");
  }

  async function validateSession() {
    const generation = sessionGeneration;
    const accessToken = token();

    if (!accessToken) {
      showLogin();
      return;
    }

    try {
      await api("/auth/me");

      if (
        generation !== sessionGeneration ||
        token() !== accessToken
      ) return;

      showStudio();
    } catch (error) {
      if (error.stale) return;

      if (error.status === 401) {
        sessionStorage.removeItem(TOKEN_KEY);
        showLogin("Your session expired. Please sign in.");
      } else {
        showLogin("Unable to verify your session. Please try again.");
      }
      return;
    }

    await loadSermons();
  }

  async function login(event) {
    event.preventDefault();

    const button = $("loginButton");
    button.disabled = true;
    $("loginStatus").textContent = "Signing in...";

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: $("loginEmail").value.trim(),
          password: $("loginPassword").value
        })
      });

      const body = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          response.status === 401
            ? "Invalid email or password."
            : "Unable to sign in. Please try again."
        );
      }

      if (typeof body.access_token !== "string" ||
          !body.access_token) {
        throw new Error("Invalid authentication response.");
      }

      sessionStorage.setItem(TOKEN_KEY, body.access_token);
      await validateSession();
    } catch (error) {
      $("loginStatus").textContent = error.message;
    } finally {
      button.disabled = false;
      $("loginPassword").value = "";
    }
  }

  async function api(path, options = {}) {
    const accessToken = token();
    const generation = sessionGeneration;

    if (!accessToken) {
      throw new Error(
        "Please sign in to XynaFaith before using Ministry Studio."
      );
    }

    const response = await fetch(path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
        ...(options.headers || {})
      }
    });

    const body = await response.json().catch(() => ({}));

    if (
      generation !== sessionGeneration ||
      token() !== accessToken
    ) {
      const error = new Error("Session changed");
      error.stale = true;
      throw error;
    }

    if (!response.ok) {
      const error = new Error(
        typeof body.detail === "string"
          ? body.detail
          : "Request failed"
      );

      error.status = response.status;

      if (response.status === 401) {
        sessionStorage.removeItem(TOKEN_KEY);
        showLogin("Your session expired. Please sign in.");
      }

      error.uncertain =
        response.status === 503 &&
        /same request id/i.test(error.message);

      throw error;
    }

    return body;
  }

  function renderFormats() {
    const root = $("formatOptions");
    root.replaceChildren();

    for (const [value, label] of FORMATS) {
      const item = document.createElement("label");
      const checkbox = document.createElement("input");

      checkbox.type = "checkbox";
      checkbox.value = value;
      checkbox.checked =
        value === "whatsapp_summary" ||
        value === "discussion_questions";

      item.append(checkbox, document.createTextNode(label));
      root.append(item);
    }
  }

  async function loadSermons() {
    const generation = sessionGeneration;
    const accessToken = token();

    if (!accessToken || $("studioWorkspace").hidden) return;

    setStatus("Loading your sermons...");

    const select = $("sermonSelect");
    select.replaceChildren(new Option("Choose a sermon", ""));

    try {
      const sermons = await api("/api/v1/faith/sermon/my");

      if (
        generation !== sessionGeneration ||
        token() !== accessToken
      ) return;

      if (!Array.isArray(sermons)) {
        throw new Error("Invalid sermon list response");
      }

      for (const sermon of sermons) {
        if (!Number.isSafeInteger(sermon.id) || sermon.id <= 0) {
          continue;
        }

        select.add(
          new Option(sermon.title || "Untitled Sermon", sermon.id)
        );
      }

      setStatus(
        sermons.length
          ? "Select a sermon and choose your content formats."
          : "You have no saved sermons yet."
      );
    } catch (error) {
      if (
        generation !== sessionGeneration ||
        token() !== accessToken ||
        error.stale
      ) return;

      setStatus(error.message);
    }
  }

  function selectedFormats() {
    return Array.from(
      $("formatOptions").querySelectorAll("input:checked"),
      element => element.value
    );
  }

  function renderResults(result) {
    const root = $("results");
    root.replaceChildren();

    const pieces = result?.pieces;
    const expected = pending?.formats || [];

    if (
      !Array.isArray(pieces) ||
      pieces.length !== expected.length ||
      new Set(pieces.map(piece => piece?.format)).size !==
        expected.length ||
      pieces.some(piece =>
        !piece ||
        !expected.includes(piece.format) ||
        typeof piece.content !== "string" ||
        !piece.content.trim() ||
        (piece.title != null &&
          typeof piece.title !== "string")
      )
    ) {
      throw new Error("Invalid Ministry Content Pack response");
    }

    for (const piece of pieces) {
      const article = document.createElement("article");
      article.className = "result-item";

      const title = document.createElement("h3");
      title.textContent = piece.title || piece.format || "Content";

      const content = document.createElement("p");
      content.textContent = piece.content || "";

      article.append(title, content);
      root.append(article);
    }

    $("resultsPanel").hidden = false;
  }

  async function generate(retry = false) {
    if (busy || !token() || $("studioWorkspace").hidden) return;

    const generation = sessionGeneration;
    const accessToken = token();

    const sermonId = Number($("sermonSelect").value);
    const formats = selectedFormats();

    if (!Number.isSafeInteger(sermonId) || sermonId <= 0) {
      setStatus("Please select a saved sermon.");
      return;
    }

    if (!formats.length) {
      setStatus("Select at least one content format.");
      return;
    }

    if (!retry) {
      if (pending) {
        setStatus(
          "An earlier request is uncertain. Retry it before starting another."
        );
        return;
      }

      if (!window.crypto?.randomUUID) {
        setStatus("Secure request identity is unavailable.");
        return;
      }

      pending = {
        requestId: window.crypto.randomUUID(),
        sermonId,
        formats
      };
    } else if (
      !pending ||
      pending.sermonId !== sermonId ||
      JSON.stringify(pending.formats) !== JSON.stringify(formats)
    ) {
      setStatus("Your selection changed. Start a new request.");
      $("retryPack").hidden = true;
      return;
    }

    busy = true;
    $("generatePack").disabled = true;
    $("retryPack").hidden = true;
    $("resultsPanel").hidden = true;
    setStatus("Xyniva is preparing your Ministry Content Pack...");

    try {
      const body = await api(
        `/api/v1/faith/ministry/sermons/${sermonId}/transform`,
        {
          method: "POST",
          body: JSON.stringify({
            request_id: pending.requestId,
            formats: pending.formats
          })
        }
      );

      if (
        generation !== sessionGeneration ||
        token() !== accessToken
      ) return;

      if (
        body.request_id !== pending.requestId ||
        body.sermon_id !== sermonId
      ) {
        throw new Error("Invalid transformation response");
      }

      renderResults(body.result);
      pending = null;
      setStatus("Your Ministry Content Pack is ready.");
    } catch (error) {
      if (
        generation !== sessionGeneration ||
        token() !== accessToken ||
        error.stale
      ) return;

      setStatus(error.message);

      if (error.uncertain && pending) {
        $("retryPack").hidden = false;
      } else {
        pending = null;
      }
    } finally {
      if (
        generation === sessionGeneration &&
        token() === accessToken
      ) {
        busy = false;
        $("generatePack").disabled = false;
      }
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    renderFormats();
    validateSession();

    $("loginForm").addEventListener("submit", login);
    $("signOut").addEventListener("click", signOut);

    $("refreshSermons").addEventListener("click", loadSermons);
    $("generatePack").addEventListener("click", () => generate());
    $("retryPack").addEventListener("click", () => generate(true));
  });
})();
