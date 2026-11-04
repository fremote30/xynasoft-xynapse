(() => {
  "use strict";

  const metrics = [
    [["members", "active"], "Active Members"],
    [["ministry", "published_announcements"], "Announcements"],
    [["ministry", "upcoming_events"], "Upcoming Events"],
    [["groups", "active"], "Active Groups"],
    [["pastoral_care", "active_cases"], "Active Care Cases"],
    [["pastoral_care", "overdue_follow_ups"], "Overdue Follow-ups"]
  ];

  function element(id) {
    return document.getElementById(id);
  }

  function setState(message) {
    const state = element("churchIntelligenceState");
    if (state) state.textContent = message;
  }

  function addMetric(container, label, value) {
    const card = document.createElement("article");
    card.className = "xf-intelligence-metric";

    const number = document.createElement("strong");
    number.textContent = String(value);

    const caption = document.createElement("span");
    caption.textContent = label;

    card.append(number, caption);
    container.appendChild(card);
  }

  async function loadChurchIntelligenceV2(churchId) {
    const panel = element("churchAnalyticsCard");
    const container = element("churchIntelligenceMetrics");

    if (!panel || !container) return;

    container.hidden = true;
    container.replaceChildren();
    setState("Loading church insights...");

    if (
      !Number.isSafeInteger(Number(churchId)) ||
      Number(churchId) <= 0 ||
      typeof window.apiFetch !== "function"
    ) {
      setState("Church insights are unavailable.");
      return;
    }

    try {
      const response = await window.apiFetch(
        `/api/v1/churches/${churchId}/intelligence/summary`
      );

      if (response.status === 403) {
        setState(
          "Church Intelligence requires an eligible plan and authorized access."
        );
        return;
      }

      if (!response.ok) {
        setState("Church insights could not be loaded.");
        return;
      }

      const data = await response.json();

      for (const [path, label] of metrics) {
        const group = data?.[path[0]];
        const value = group?.[path[1]];

        if (
          typeof value === "number" &&
          Number.isFinite(value) &&
          Number.isInteger(value) &&
          value >= 0
        ) {
          addMetric(container, label, value);
        }
      }

      if (!container.children.length) {
        setState("No summary metrics are available yet.");
        return;
      }

      container.hidden = false;
      setState("Church overview");
    } catch (error) {
      console.error("Church Intelligence load failed:", error);
      setState("Church insights could not be loaded.");
    }
  }

  window.loadChurchIntelligenceV2 =
    loadChurchIntelligenceV2;
})();
