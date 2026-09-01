/**
 * ==========================================================
 * XYNIVA — SERMON STUDIO CONTROLLER
 * ----------------------------------------------------------
 * Contextual Xyniva assistant for Sermon Studio.
 *
 * Uses the authenticated XynaFaith conversation client.
 * The current sermon is supplied on the first turn only.
 *
 * Xyniva may refine the in-memory Studio sermon, but this
 * controller never saves, updates, exports, or shares it.
 * ==========================================================
 */

(() => {

  "use strict";

  let conversationId = null;
  let sending = false;
  let sermonContextSeeded = false;
  let boundForm = null;


  function byId(id) {

    if (
      typeof document === "undefined"
    ) {
      return null;
    }

    return document.getElementById(id);

  }


  function client() {

    const service =
      window.XynivaConversation;

    if (
      !service ||
      typeof service.create !== "function" ||
      typeof service.turn !== "function"
    ) {
      throw new Error(
        "Xyniva conversation service is unavailable"
      );
    }

    return service;

  }


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

    return "";
  }


  function parseSermon(content) {

    if (
      typeof content !== "string" ||
      !content.trim()
    ) {
      return null;
    }

    let sermon;

    try {
      sermon = JSON.parse(content);
    } catch (_) {
      return null;
    }

    if (
      !sermon ||
      typeof sermon !== "object" ||
      Array.isArray(sermon)
    ) {
      return null;
    }

    if (
      typeof sermon.title !== "string" ||
      typeof sermon.introduction !== "string" ||
      !Array.isArray(sermon.main_points)
    ) {
      return null;
    }

    return sermon;
  }


  function appendMessage(
    role,
    content
  ) {

    const container =
      byId("xynivaStudioMessages");

    if (!container) {
      return;
    }

    const welcome =
      container.querySelector?.(
        ".xyniva-studio-welcome"
      );

    if (welcome) {
      welcome.remove();
    }

    const message =
      document.createElement("div");

    message.className =
      `xyniva-studio-message ` +
      `xyniva-studio-message-${role}`;

    message.textContent =
      String(content ?? "");

    container.appendChild(message);

    container.scrollTop =
      container.scrollHeight;

  }


  function setSending(value) {

    sending = Boolean(value);

    const status =
      byId("xynivaStudioStatus");

    const button =
      byId("xynivaStudioSend");

    const input =
      byId("xynivaStudioInput");

    if (status) {
      status.hidden =
        !sending;
    }

    if (button) {
      button.disabled =
        sending;

      button.textContent =
        sending
          ? "Xyniva is working…"
          : "Ask Xyniva";
    }

    if (input) {
      input.disabled =
        sending;
    }

  }


  async function ensureConversation() {

    if (conversationId) {
      return conversationId;
    }

    const conversation =
      await client().create(
        "Sermon Studio"
      );

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


  function sermonContext() {

    const sermon =
      window.currentGeneratedSermon;

    if (
      !sermon ||
      typeof sermon !== "object"
    ) {
      return null;
    }

    return {
      title:
        sermon.title || "",
      scripture:
        sermon.scripture || "",
      introduction:
        sermon.introduction || "",
      main_points:
        Array.isArray(
          sermon.main_points
        )
          ? sermon.main_points
          : [],
      application:
        sermon.application || "",
      conclusion:
        sermon.conclusion || "",
      denomination:
        sermon.denomination ||
        byId("denomination")?.value ||
        "general",
      audience:
        sermon.audience ||
        byId("audience")?.value ||
        "",
      context:
        sermon.context ||
        sermon.local_context ||
        byId("context")?.value ||
        "",
      tone:
        sermon.tone ||
        byId("tone")?.value ||
        "balanced",
      duration:
        sermon.duration ||
        byId("duration")?.value ||
        "30"
    };

  }


  function buildTurnContent(
    instruction
  ) {

    const current =
      sermonContext();

    if (
      sermonContextSeeded ||
      !current
    ) {
      return instruction;
    }

    return [
      "You are assisting with the sermon currently open in Sermon Studio.",
      "Treat the following sermon as the existing sermon to refine.",
      "Preserve anything the user does not ask you to change.",
      "",
      "CURRENT SERMON:",
      JSON.stringify(current),
      "",
      "USER INSTRUCTION:",
      instruction
    ].join("\n");

  }


  function preserveStudioMetadata(
    refined
  ) {

    const current =
      window.currentGeneratedSermon;

    if (
      !current ||
      typeof current !== "object"
    ) {
      return refined;
    }

    const merged = {
      ...current,
      ...refined
    };

    if (current.id) {
      merged.id =
        current.id;
    }

    if (current.author_id) {
      merged.author_id =
        current.author_id;
    }

    return merged;
  }


  function applySermon(content) {

    const refined =
      parseSermon(content);

    if (!refined) {
      return false;
    }

    const sermon =
      preserveStudioMetadata(
        refined
      );

    window.currentGeneratedSermon =
      sermon;

    if (
      typeof window.renderCurrentSermon ===
        "function"
    ) {
      window.renderCurrentSermon(
        sermon,
        false
      );
    }

    return true;
  }


  async function send(content) {

    const instruction =
      String(content ?? "").trim();

    if (!instruction) {
      return null;
    }

    if (sending) {
      return null;
    }

    client();

    appendMessage(
      "user",
      instruction
    );

    setSending(true);

    try {

      const id =
        await ensureConversation();

      const turnContent =
        buildTurnContent(
          instruction
        );

      const result =
        await client().turn(
          id,
          turnContent
        );

      sermonContextSeeded = true;

      const response =
        assistantContent(result);

      if (!response) {
        throw new Error(
          "Xyniva returned an empty response"
        );
      }

      const applied =
        applySermon(response);

      appendMessage(
        "assistant",
        applied
          ? "I updated the sermon on your Studio canvas."
          : response
      );

      return result;

    } catch (error) {

      appendMessage(
        "assistant",
        error?.message ||
          "Xyniva could not complete the request."
      );

      throw error;

    } finally {

      setSending(false);

    }

  }


  function bind() {

    const form =
      byId("xynivaStudioForm");

    const input =
      byId("xynivaStudioInput");

    if (!form || !input) {
      return;
    }

    if (boundForm !== form) {

      conversationId = null;
      sending = false;
      sermonContextSeeded = false;
      boundForm = form;

    }

    if (
      form.dataset?.xynivaStudioBound ===
        "true"
    ) {
      return;
    }

    if (form.dataset) {
      form.dataset.xynivaStudioBound =
        "true";
    }

    form.addEventListener(
      "submit",
      async event => {

        event.preventDefault();

        const content =
          input.value.trim();

        if (
          !content ||
          sending
        ) {
          return;
        }

        input.value = "";

        try {

          await send(content);

        } catch (error) {

          console.error(
            "Xyniva Studio conversation failed",
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


  function reset() {

    conversationId = null;
    sending = false;
    sermonContextSeeded = false;
    boundForm = null;

  }


  window.XynivaStudio = {
    bind,
    send,
    reset
  };

  window.bindXynivaStudio =
    bind;

})();
