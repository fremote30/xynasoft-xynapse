/**
 * ==========================================================
 * XYNIVA — SERMON STUDIO CONTROLLER
 * ----------------------------------------------------------
 * Contextual Xyniva assistant for Sermon Studio.
 *
 * Uses the authenticated XynaFaith conversation client.
 * The current sermon is supplied on the first turn only.
 *
 * Xyniva may refine the in-memory Studio sermon.
 * Trusted product actions are requested through the
 * authenticated XynaFaith backend; this controller never
 * performs direct database mutations.
 * ==========================================================
 */

(() => {

  "use strict";

  let conversationId = null;
  let sending = false;
  let sermonContextSeeded = false;
  let boundForm = null;
  let statusTimer = null;

  const STATUS_MESSAGES = [
    "Understanding your request…",
    "Refining your sermon…",
    "Preserving your sermon context…",
    "Preparing the updated message…"
  ];


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


  function createRequestId() {

    const cryptoApi =
      window.crypto;

    if (
      !cryptoApi ||
      typeof cryptoApi.randomUUID !==
        "function"
    ) {
      throw new Error(
        "Secure request identity is unavailable"
      );
    }

    return cryptoApi.randomUUID();

  }


  function assistantContent(result) {

    const candidates = [
      result?.assistant_content,
        result?.prompt,
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


  function completedAction(result) {

    const action =
      result?.action;

    if (
      !action ||
      typeof action !== "object" ||
      action.status !== "completed"
    ) {
      return null;
    }

    return action;

  }


  function applyCompletedAction(result) {

    const action =
      completedAction(result);

    if (!action) {
      return null;
    }

    if (
      action.name !== "sermon.save" &&
      action.name !== "sermon.update" &&
      action.name !== "sermon.delete"
    ) {
      return null;
    }

    const isDelete =
      action.name === "sermon.delete";

    const isUpdate =
      action.name === "sermon.update";

    const sermonId =
      Number(
        action?.result?.sermon_id
      );

    if (
      !Number.isInteger(sermonId) ||
      sermonId <= 0
    ) {
      throw new Error(
        "Xyniva returned an invalid saved sermon"
      );
    }

    const sermon =
      window.currentGeneratedSermon;

    if (
      !sermon ||
      typeof sermon !== "object"
    ) {
      throw new Error(
        "The saved sermon is no longer open"
      );
    }

    if (isDelete) {

      const currentId =
        Number(
          window.currentSermonId ??
          sermon.id
        );

      if (
        !Number.isInteger(currentId) ||
        currentId <= 0 ||
        currentId !== sermonId
      ) {
        throw new Error(
          "The deleted sermon is no longer open"
        );
      }

      try {

        window.localStorage?.removeItem(
          "last_saved_sermon_id"
        );

        const userId =
          window.currentUser?.id;

        if (userId) {
          window.localStorage?.removeItem(
            `latest_sermon_${userId}`
          );
        }

      } catch (_) {
        // Server deletion already succeeded.
        // Local persistence cleanup is best-effort.
      }

      window.currentGeneratedSermon =
        null;

      window.currentSermonId =
        null;

      if (
        typeof window.renderCurrentSermon ===
          "function"
      ) {
        window.renderCurrentSermon(
          null,
          false
        );
      }

      return "I deleted this sermon.";
    }

    sermon.id =
      sermonId;

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
      sermonId;

    try {

      window.localStorage?.setItem(
        "last_saved_sermon_id",
        String(sermonId)
      );

      const userId =
        window.currentUser?.id;

      if (userId) {
        window.localStorage?.setItem(
          `latest_sermon_${userId}`,
          JSON.stringify(sermon)
        );
      }

    } catch (_) {
      // Persistence is best-effort; server save already succeeded.
    }

    if (
      typeof window.renderCurrentSermon ===
        "function"
    ) {
      window.renderCurrentSermon(
        sermon,
        false
      );
    }

    return (
      isUpdate
        ? "I saved your changes."
        : "I saved this sermon to your sermons."
    );

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


  function stopStatusTimer() {

    if (
      statusTimer !== null &&
      typeof clearInterval === "function"
    ) {
      clearInterval(
        statusTimer
      );
    }

    statusTimer = null;

  }


  function startStatus() {

    stopStatusTimer();

    const status =
      byId("xynivaStudioStatus");

    const text =
      byId("xynivaStudioStatusText");

    const progress =
      byId("xynivaStudioProgressBar");

    if (status) {
      status.hidden = false;
    }

    if (text) {
      text.textContent =
        STATUS_MESSAGES[0];
    }

    if (progress) {
      progress.classList?.remove(
        "active"
      );

      void progress.offsetWidth;

      progress.classList?.add(
        "active"
      );
    }

    if (
      typeof setInterval !== "function"
    ) {
      return;
    }

    let index = 0;

    statusTimer =
      setInterval(
        () => {

          index =
            (index + 1) %
            STATUS_MESSAGES.length;

          if (text) {
            text.textContent =
              STATUS_MESSAGES[index];
          }

        },
        2200
      );

  }


  function stopStatus() {

    stopStatusTimer();

    const status =
      byId("xynivaStudioStatus");

    const progress =
      byId("xynivaStudioProgressBar");

    if (status) {
      status.hidden = true;
    }

    if (progress) {
      progress.classList?.remove(
        "active"
      );
    }

  }


  function setSending(value) {

    sending = Boolean(value);

    const status =
      byId("xynivaStudioStatus");

    const button =
      byId("xynivaStudioSend");

    const input =
      byId("xynivaStudioInput");

    if (sending) {
      startStatus();
    } else {
      stopStatus();
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


  function sermonActionContext() {

    const data =
      sermonContext();

    if (!data) {
      return null;
    }

    const rawId =
      window.currentSermonId ??
      window.currentGeneratedSermon?.id ??
      null;

    const numericId =
      rawId === null ||
      rawId === undefined ||
      rawId === ""
        ? null
        : Number(rawId);

    return {
      id:
        Number.isInteger(numericId) &&
        numericId > 0
          ? numericId
          : null,
      data
    };

  }


  function isTrustedStudioAction(
    instruction
  ) {

    const normalized =
      String(instruction ?? "")
        .trim()
        .toLowerCase()
          .replace(/[.!?]+$/, "")
          .replace(/,/g, "");

    return [
      "save this",
      "save this sermon",
      "save the sermon",
      "save my sermon",
      "save these changes",
      "save the changes",
      "save my changes",
        "delete",
        "delete this",
        "delete this sermon",
        "delete the sermon",
        "delete my sermon",
        "yes",
        "yes delete it",
        "yes delete this",
        "yes delete this sermon",
        "confirm",
        "confirm deletion",
        "delete it"
    ].includes(normalized);

  }


  function buildTurnContent(
    instruction
  ) {

    const current =
      sermonContext();

    /*
     * Trusted product actions must reach XynAssist as the
     * user's literal instruction. The authoritative sermon
     * payload is transported separately in `options.sermon`.
     *
     * Wrapping an action inside the refinement context would
     * cause words such as "sermon" in the envelope to route
     * the turn back through sermon.generate.
     */
    if (
      isTrustedStudioAction(instruction) ||
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

      const requestId =
        createRequestId();

      const result =
        await client().turn(
          id,
          turnContent,
          {
            requestId,
            sermon:
              sermonActionContext()
          }
        );

      sermonContextSeeded = true;

      const actionMessage =
        applyCompletedAction(
          result
        );

      if (actionMessage) {

        appendMessage(
          "assistant",
          actionMessage
        );

        return result;

      }

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
    stopStatus();

  }


  window.XynivaStudio = {
    bind,
    send,
    reset
  };

  window.bindXynivaStudio =
    bind;

})();
