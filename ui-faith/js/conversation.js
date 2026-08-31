/**
 * ==========================================================
 * XYNIVA CONVERSATION CLIENT
 * ----------------------------------------------------------
 * Browser/mobile client for XynaFaith conversations.
 *
 * Security boundary:
 * - Talks only to authenticated XynaFaith endpoints.
 * - Never knows XynAssist service credentials.
 * - Never sends external_user_id.
 * - Never sends product identity.
 * - Never talks directly to XynAssist.
 * ==========================================================
 */

(() => {

  "use strict";

  const BASE_PATH =
    "/api/v1/faith/conversations";


  // ========================================================
  // RESPONSE HANDLING
  // ========================================================

  async function parseResponse(response) {

    let data = {};

    try {

      data =
        await response.json();

    } catch (_) {

      data = {};

    }

    if (!response.ok) {

      const message =
        data?.detail ||
        data?.message ||
        "Xyniva request failed";

      const error =
        new Error(message);

      error.status =
        response.status;

      throw error;

    }

    return data;

  }


  // ========================================================
  // REQUEST
  // ========================================================

  async function request(
    path,
    options = {}
  ) {

    if (
      typeof window.apiFetch !==
      "function"
    ) {

      throw new Error(
        "Xyniva API client is unavailable"
      );

    }

    const response =
      await window.apiFetch(
        path,
        options
      );

    return parseResponse(
      response
    );

  }


  // ========================================================
  // VALIDATION
  // ========================================================

  function conversationPath(
    conversationId
  ) {

    const id =
      String(
        conversationId ?? ""
      ).trim();

    if (!id) {

      throw new Error(
        "Conversation ID is required"
      );

    }

    return (
      `${BASE_PATH}/` +
      encodeURIComponent(id)
    );

  }


  function normalizeMessage(
    content
  ) {

    const message =
      String(
        content ?? ""
      ).trim();

    if (!message) {

      throw new Error(
        "Message is required"
      );

    }

    return message;

  }


  // ========================================================
  // CREATE
  // ========================================================

  async function create(
    title = null
  ) {

    const normalizedTitle =
      typeof title === "string"
        ? title.trim() || null
        : null;

    return request(
      BASE_PATH,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json"
        },

        body: JSON.stringify({
          title: normalizedTitle
        })
      }
    );

  }


  // ========================================================
  // LIST
  // ========================================================

  async function list() {

    return request(
      BASE_PATH
    );

  }


  // ========================================================
  // GET
  // ========================================================

  async function get(
    conversationId
  ) {

    return request(
      conversationPath(
        conversationId
      )
    );

  }


  // ========================================================
  // TURN
  // ========================================================

  async function turn(
    conversationId,
    content
  ) {

    const path =
      conversationPath(
        conversationId
      );

    const message =
      normalizeMessage(
        content
      );

    return request(
      `${path}/turns`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json"
        },

        body: JSON.stringify({
          content: message
        })
      }
    );

  }


  // ========================================================
  // PUBLIC API
  // ========================================================

  window.XynivaConversation = {
    create,
    list,
    get,
    turn
  };

})();
