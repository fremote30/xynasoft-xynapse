/**
 * XynaFaith V2 ministry intelligence client.
 *
 * Browser responsibility:
 * - create request identity
 * - send skill + typed input
 * - return structured result
 *
 * The browser never selects entitlement, metric,
 * quota owner, external user identity, or trusted
 * XynAssist credentials.
 */
(() => {
  "use strict";

  const ENDPOINT =
    "/api/v1/faith/ministry/execute";

  let pendingUncertainRequest = null;

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

  function detailMessage(
    payload,
    fallback
  ) {
    if (
      payload &&
      typeof payload.detail === "string" &&
      payload.detail.trim()
    ) {
      return payload.detail.trim();
    }

    return fallback;
  }

  function isUncertainResponse(
    response,
    payload
  ) {
    if (response?.status !== 503) {
      return false;
    }

    const detail =
      typeof payload?.detail === "string"
        ? payload.detail.toLowerCase()
        : "";

    return (
      detail.includes("same request id") ||
      detail.includes("same request")
    );
  }

  async function execute(
    skill,
    input,
    options = {}
  ) {
    if (
      typeof window.apiFetch !==
        "function"
    ) {
      throw new Error(
        "Authenticated API service is unavailable"
      );
    }

    const retry =
      options.retry === true;

    let requestId;

    if (retry) {
      if (
        !pendingUncertainRequest ||
        pendingUncertainRequest.skill !== skill
      ) {
        throw new Error(
          "There is no uncertain ministry request to retry"
        );
      }

      requestId =
        pendingUncertainRequest.requestId;
    } else {
      requestId =
        createRequestId();

      pendingUncertainRequest = null;
    }

    const response =
      await window.apiFetch(
        ENDPOINT,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json"
          },

          body: JSON.stringify({
            request_id: requestId,
            skill,
            input
          })
        }
      );

    const payload =
      await response
        .json()
        .catch(() => ({}));

    if (!response.ok) {
      const uncertain =
        isUncertainResponse(
          response,
          payload
        );

      if (uncertain) {
        pendingUncertainRequest = {
          requestId,
          skill
        };
      } else {
        pendingUncertainRequest = null;
      }

      const error =
        new Error(
          detailMessage(
            payload,
            "Xyniva could not complete the ministry request"
          )
        );

      error.status =
        response.status;

      error.requestId =
        requestId;

      error.uncertain =
        uncertain;

      throw error;
    }

    if (
      payload?.request_id !== requestId ||
      payload?.skill !== skill ||
      !payload?.result ||
      typeof payload.result !== "object"
    ) {
      pendingUncertainRequest = null;

      throw new Error(
        "Xyniva returned an invalid ministry response"
      );
    }

    pendingUncertainRequest = null;

    return {
      requestId,
      skill,
      result: payload.result
    };
  }

  function canRetry(
    skill
  ) {
    return Boolean(
      pendingUncertainRequest &&
      pendingUncertainRequest.skill === skill
    );
  }

  function clearRetry() {
    pendingUncertainRequest = null;
  }

  window.XynaFaithMinistry = {
    execute,
    canRetry,
    clearRetry
  };
})();
