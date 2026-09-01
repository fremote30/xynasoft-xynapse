/**
 * ==========================================================
 * XYNIVA CONVERSATIONAL UI
 * ----------------------------------------------------------
 * Presentation/controller layer for Ask Xyniva.
 *
 * Responsibilities:
 * - Bind composer and prompt buttons
 * - Create conversation on first turn
 * - Reuse conversation for follow-ups
 * - Render conversation messages
 * - Manage loading/error state
 *
 * Does NOT:
 * - Know external user identity
 * - Know XynAssist credentials
 * - Talk directly to XynAssist
 * ==========================================================
 */

(() => {

  "use strict";

  let conversationId = null;
  let sending = false;


  // ========================================================
  // DOM
  // ========================================================

  function byId(id) {

    if (
      typeof document ===
      "undefined"
    ) {
      return null;
    }

    return document.getElementById(id);

  }


  // ========================================================
  // CLIENT
  // ========================================================

  function client() {

    const service =
      window.XynivaConversation;

    if (
      !service ||
      typeof service.create !==
        "function" ||
      typeof service.turn !==
        "function"
    ) {

      throw new Error(
        "Xyniva conversation service is unavailable"
      );

    }

    return service;

  }


  // ========================================================
  // CONTENT EXTRACTION
  // ========================================================

  function assistantContent(result) {

    const candidates = [
      result?.assistant_content,
      result?.assistant_message?.content,
      result?.assistant?.content,
      result?.message?.content,
      result?.content,
      result?.response
    ];

    for (const value of candidates) {

      if (
        typeof value === "string" &&
        value.trim()
      ) {

        return value.trim();

      }

    }

    return "Xyniva completed the request.";

  }


  // ========================================================
  // RENDERING
  // ========================================================

  function hideWelcome() {

    const welcome =
      byId("xynivaWelcome");

    if (welcome) {
      welcome.style.display =
        "none";
    }

  }


  function parseSermon(content) {

    if (
      typeof content !== "string" ||
      !content.trim()
    ) {
      return null;
    }

    let payload;

    try {
      payload = JSON.parse(
        content
      );
    } catch (_) {
      return null;
    }

    if (
      !payload ||
      typeof payload !== "object" ||
      Array.isArray(payload)
    ) {
      return null;
    }

    const title =
      typeof payload.title === "string"
        ? payload.title.trim()
        : "";

    const scripture =
      typeof payload.scripture === "string"
        ? payload.scripture.trim()
        : "";

    const introduction =
      typeof payload.introduction === "string"
        ? payload.introduction.trim()
        : "";

    const application =
      typeof payload.application === "string"
        ? payload.application.trim()
        : "";

    const conclusion =
      typeof payload.conclusion === "string"
        ? payload.conclusion.trim()
        : "";

    const mainPoints =
      Array.isArray(payload.main_points)
        ? payload.main_points.filter(
            (point) =>
              point &&
              typeof point === "object"
          )
        : [];

    if (
      !title ||
      !scripture ||
      !introduction ||
      mainPoints.length === 0
    ) {
      return null;
    }

    return {
      title,
      scripture,
      introduction,
      mainPoints,
      application,
      conclusion
    };

  }


  function appendTextElement(
    parent,
    tag,
    className,
    content
  ) {

    if (
      !content ||
      typeof document ===
        "undefined"
    ) {
      return null;
    }

    const element =
      document.createElement(tag);

    element.className =
      className;

    // AI-generated output remains untrusted.
    // Never inject it as HTML.
    element.textContent =
      content;

    parent.appendChild(element);

    return element;

  }


  function renderSermon(
    body,
    sermon
  ) {

    body.classList?.add(
      "xyniva-sermon"
    );

    appendTextElement(
      body,
      "h2",
      "xyniva-sermon-title",
      sermon.title
    );

    appendTextElement(
      body,
      "div",
      "xyniva-sermon-scripture",
      sermon.scripture
    );

    const introduction =
      document.createElement("section");

    introduction.className =
      "xyniva-sermon-section";

    appendTextElement(
      introduction,
      "h3",
      "xyniva-sermon-heading",
      "Introduction"
    );

    appendTextElement(
      introduction,
      "p",
      "xyniva-sermon-text",
      sermon.introduction
    );

    body.appendChild(
      introduction
    );

    sermon.mainPoints.forEach(
      (point, index) => {

        const section =
          document.createElement(
            "section"
          );

        section.className =
          "xyniva-sermon-section";

        const pointTitle =
          typeof point.title ===
            "string"
            ? point.title.trim()
            : "";

        const pointContent =
          typeof point.content ===
            "string"
            ? point.content.trim()
            : "";

        appendTextElement(
          section,
          "h3",
          "xyniva-sermon-heading",
          pointTitle
            ? `${index + 1}. ${pointTitle}`
            : `Point ${index + 1}`
        );

        appendTextElement(
          section,
          "p",
          "xyniva-sermon-text",
          pointContent
        );

        body.appendChild(
          section
        );

      }
    );

    if (sermon.application) {

      const section =
        document.createElement(
          "section"
        );

      section.className =
        "xyniva-sermon-section";

      appendTextElement(
        section,
        "h3",
        "xyniva-sermon-heading",
        "Application"
      );

      appendTextElement(
        section,
        "p",
        "xyniva-sermon-text",
        sermon.application
      );

      body.appendChild(
        section
      );

    }

    if (sermon.conclusion) {

      const section =
        document.createElement(
          "section"
        );

      section.className =
        "xyniva-sermon-section";

      appendTextElement(
        section,
        "h3",
        "xyniva-sermon-heading",
        "Conclusion"
      );

      appendTextElement(
        section,
        "p",
        "xyniva-sermon-text",
        sermon.conclusion
      );

      body.appendChild(
        section
      );

    }

  }


  function appendMessage(
    role,
    content
  ) {

    const container =
      byId("xynivaMessages");

    if (
      !container ||
      typeof document ===
        "undefined" ||
      typeof document.createElement !==
        "function"
    ) {
      return;
    }

    const message =
      document.createElement("div");

    message.className =
      `xyniva-message xyniva-message-${role}`;

    const label =
      document.createElement("div");

    label.className =
      "xyniva-message-label";

    label.textContent =
      role === "user"
        ? "You"
        : "Xyniva";

    const body =
      document.createElement("div");

    body.className =
      "xyniva-message-body";

    const sermon =
      role === "assistant"
        ? parseSermon(content)
        : null;

    if (sermon) {

      renderSermon(
        body,
        sermon
      );

    } else {

      // Deliberately textContent, not innerHTML.
      // Conversation output is untrusted text.
      body.textContent =
        content;

    }

    message.appendChild(label);
    message.appendChild(body);

    container.appendChild(message);

    if (
      typeof message.scrollIntoView ===
      "function"
    ) {

      message.scrollIntoView({
        behavior: "smooth",
        block: "end"
      });

    }

  }


  function appendError(message) {

    const container =
      byId("xynivaMessages");

    if (
      !container ||
      typeof document ===
        "undefined"
    ) {
      return;
    }

    const element =
      document.createElement("div");

    element.className =
      "xyniva-error";

    element.textContent =
      message;

    container.appendChild(element);

  }


  // ========================================================
  // NAVIGATION
  // ========================================================

  function goBack() {

    if (
      typeof window !== "undefined" &&
      typeof window.navigate === "function"
    ) {

      window.navigate("dashboard");
      return;

    }

    if (
      typeof window !== "undefined" &&
      window.location
    ) {

      window.location.href =
        "/faith/";

    }

  }


  function bindBackButton() {

    const button =
      byId("xynivaBack");

    if (
      !button ||
      typeof button.addEventListener !==
        "function"
    ) {
      return;
    }

    if (
      button.dataset?.xynivaBound ===
      "true"
    ) {
      return;
    }

    if (button.dataset) {
      button.dataset.xynivaBound =
        "true";
    }

    button.addEventListener(
      "click",
      goBack
    );

  }


  // ========================================================
  // STATUS / PROGRESS
  // ========================================================

  const STATUS_MESSAGES = [
    "Understanding your request…",
    "Preparing your sermon…",
    "Developing the message…",
    "Almost ready…"
  ];

  let statusTimer = null;
  let statusIndex = 0;


  function updateStatusText() {

    const text =
      byId("xynivaStatusText");

    if (!text) {
      return;
    }

    text.textContent =
      STATUS_MESSAGES[
        statusIndex %
        STATUS_MESSAGES.length
      ];

  }


  function startStatus() {

    const status =
      byId("xynivaStatus");

    const progress =
      byId("xynivaProgressBar");

    statusIndex = 0;

    if (status) {
      status.hidden = false;
    }

    if (progress) {
      progress.classList?.add(
        "is-active"
      );
    }

    updateStatusText();

    if (
      typeof window !== "undefined" &&
      typeof window.setInterval ===
        "function"
    ) {

      statusTimer =
        window.setInterval(
          () => {
            statusIndex += 1;
            updateStatusText();
          },
          2200
        );

    }

  }


  function stopStatus() {

    const status =
      byId("xynivaStatus");

    const progress =
      byId("xynivaProgressBar");

    if (
      statusTimer !== null &&
      typeof window !== "undefined" &&
      typeof window.clearInterval ===
        "function"
    ) {

      window.clearInterval(
        statusTimer
      );

    }

    statusTimer = null;
    statusIndex = 0;

    if (status) {
      status.hidden = true;
    }

    if (progress) {
      progress.classList?.remove(
        "is-active"
      );
    }

  }


  // ========================================================
  // LOADING STATE
  // ========================================================

  function setSending(value) {

    sending = value;

    const button =
      byId("xynivaSend");

    const input =
      byId("xynivaInput");

    if (button) {

      button.disabled =
        value;

      button.textContent =
        value
          ? "Thinking..."
          : "Send";

    }

    if (input) {
      input.disabled = value;
    }

    if (value) {
      startStatus();
    } else {
      stopStatus();
    }

  }


  // ========================================================
  // CONVERSATION
  // ========================================================

  async function ensureConversation() {

    if (conversationId) {
      return conversationId;
    }

    const conversation =
      await client().create();

    const id =
      String(
        conversation?.id ?? ""
      ).trim();

    if (!id) {

      throw new Error(
        "Xyniva could not start a conversation"
      );

    }

    conversationId = id;

    return conversationId;

  }


  async function send(content) {

    const message =
      String(
        content ?? ""
      ).trim();

    if (!message) {

      throw new Error(
        "Message is required"
      );

    }

    if (sending) {

      throw new Error(
        "Xyniva is already responding"
      );

    }

    // Validate service before changing UI.
    client();

    hideWelcome();

    appendMessage(
      "user",
      message
    );

    setSending(true);

    try {

      const id =
        await ensureConversation();

      const result =
        await client().turn(
          id,
          message
        );

      appendMessage(
        "assistant",
        assistantContent(result)
      );

      return result;

    } catch (error) {

      appendError(
        error?.message ||
        "Xyniva could not complete the request."
      );

      throw error;

    } finally {

      setSending(false);

    }

  }


  // ========================================================
  // FORM
  // ========================================================

  bindBackButton();


  function bindForm() {

    const form =
      byId("xynivaForm");

    const input =
      byId("xynivaInput");

    if (!form || !input) {
      return;
    }

    if (
      form.dataset?.xynivaBound ===
      "true"
    ) {
      return;
    }

    if (form.dataset) {
      form.dataset.xynivaBound =
        "true";
    }

    form.addEventListener(
      "submit",
      async event => {

        event.preventDefault();

        const content =
          input.value.trim();

        if (!content || sending) {
          return;
        }

        input.value = "";

        try {

          await send(content);

        } catch (error) {

          console.error(
            "Xyniva conversation failed",
            error
          );

        } finally {

          if (!sending) {
            input.focus();
          }

        }

      }
    );

  }


  // ========================================================
  // PROMPT BUTTONS
  // ========================================================

  function bindPrompts() {

    if (
      typeof document ===
      "undefined"
    ) {
      return;
    }

    const prompts =
      document.querySelectorAll(
        "[data-xyniva-prompt]"
      );

    prompts.forEach(button => {

      if (
        button.dataset
          ?.xynivaBound ===
        "true"
      ) {
        return;
      }

      if (button.dataset) {
        button.dataset.xynivaBound =
          "true";
      }

      button.addEventListener(
        "click",
        () => {

          const input =
            byId("xynivaInput");

          if (!input) {
            return;
          }

          input.value =
            button.dataset
              ?.xynivaPrompt || "";

          input.focus();

        }
      );

    });

  }


  // ========================================================
  // PAGE BINDING
  // ========================================================

  function bind() {

    if (!byId("xynivaForm")) {
      return;
    }

    bindForm();
    bindPrompts();

  }


  function getConversationId() {
    return conversationId;
  }


  // ========================================================
  // PUBLIC API
  // ========================================================

  window.XynivaUI = {
    bind,
    send,
    getConversationId
  };

  window.bindXyniva =
    bind;

})();
