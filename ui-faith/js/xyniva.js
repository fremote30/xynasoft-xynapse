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

    // Deliberately textContent, not innerHTML.
    // Conversation output is untrusted text.
    body.textContent =
      content;

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
