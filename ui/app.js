/* ui-faith/app.js
   Xynasoft Faith PWA (Pastor + Member support)

   Pastor:
   - POST /api/v1/faith/sermon                 => outline JSON (SermonOutput)
   - POST /api/v1/faith/sermon/manuscript      => manuscript JSON
   - POST /api/v1/faith/share                  => create share link

   Member:
   - GET  /api/v1/faith/public/{share_id}
   - POST /api/v1/faith/public/{share_id}/questions

   Works across:
   - /faith/
   - /faith/pastor.html
   - /faith/church/{shareId}
*/

(() => {
  const $ = (id) => document.getElementById(id);

  const memberView = $("memberView");
  const pastorView = $("pastorView");

  // Member elements
  const mvTitle = $("mvTitle");
  const mvMeta = $("mvMeta");
  const mvBody = $("mvBody");
  const mvName = $("mvName");
  const mvQuestion = $("mvQuestion");
  const mvSubmit = $("mvSubmit");
  const mvStatus = $("mvStatus");

  // Pastor elements
  const els = {
    apiKey: $("apiKey"),

    passage: $("passage_reference"),
    theme: $("theme"),
    denomination: $("denomination"),
    audience: $("audience_type"),
    context: $("local_context"),
    service: $("service_type"),
    tone: $("tone"),
    duration: $("duration_minutes"),

    generateBtn: $("btnGenerate"),
    clearBtn: $("clearBtn"),
    copyBtn: $("copyBtn"),
    saveBtn: $("saveBtn"),
    loadBtn: $("loadBtn"),
    status: $("toast"),
    output: $("output"),

    manuscriptBtn: $("manuscriptBtn"),
    copyManuscriptBtn: $("copyManuscriptBtn"),
    downloadManuscriptBtn: $("downloadManuscriptBtn"),
    loadManuscriptBtn: $("loadManuscriptBtn"),
    exportPdfBtn: $("exportPdfBtn"),
    manuscriptOutput: $("manuscriptOutput"),

    // publish/share
    publishBtn: $("publishBtn"),
    copyShareBtn: $("copyShareBtn"),
    whatsAppShareBtn: $("whatsAppShareBtn"),
    shareBox: $("shareBox"),

    // preaching mode
    preachModeBtn: $("preachModeBtn"),
    preachOverlay: $("preachOverlay"),
    preachBody: $("preachBody"),
    preachTitle: $("preachTitle"),
    preachExitBtn: $("preachExitBtn"),
    preachBiggerBtn: $("preachBiggerBtn"),
    preachSmallerBtn: $("preachSmallerBtn"),
  };

  const STORE = {
    APIKEY: "xynasoft_faith_api_key",
    LAST: "xynasoft_faith_last_sermon",
    LAST_INPUT: "xynasoft_faith_last_input",
    LAST_MANUSCRIPT: "xynasoft_faith_last_manuscript",
    PREACH_FONT: "xynasoft_faith_preach_font_size",
    DENOM: "xynasoft_faith_denomination",
    SHARE: "xynasoft_faith_last_share",
    ACTIVE_HANDLE: "xynasoft_faith_active_handle",
  };

  function setStatus(msg) {
    if (els.status) els.status.textContent = msg || "";
  }

  function setMemberStatus(msg) {
    if (mvStatus) mvStatus.textContent = msg || "";
  }

  function setShareBox(msg) {
    if (els.shareBox) els.shareBox.textContent = msg || "";
  }

  function escapeHtml(s) {
    return (s ?? "")
      .toString()
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  function prettyDate(isoString) {
    try {
      const d = new Date(isoString);
      if (Number.isNaN(d.getTime())) return isoString;
      return d.toLocaleString();
    } catch {
      return isoString;
    }
  }

  function apiHeadersJson() {
    const headers = { "Content-Type": "application/json" };
    const apiKey = (els.apiKey?.value || "").trim();
    if (apiKey) headers["x-api-key"] = apiKey;
    return headers;
  }

  function getShareIdFromPath() {
    const path = window.location.pathname || "";
    const m = path.match(/^\/faith\/church\/([^\/?#]+)\/?$/);
    return m ? decodeURIComponent(m[1]) : null;
  }

  function getActivePastorHandle() {
    return (localStorage.getItem(STORE.ACTIVE_HANDLE) || "").trim() || null;
  }

  // -------- Render Outline ----------
  function renderSermonToHtml(data) {
    const po = data.passage_overview || {};
    const ts = data.theological_summary || {};
    const vb = Array.isArray(data.verse_breakdown) ? data.verse_breakdown : [];
    const ss = data.sermon_structure || {};
    const pts = Array.isArray(ss.main_points) ? ss.main_points : [];
    const ga = Array.isArray(data.ghana_application) ? data.ghana_application : [];
    const ill = Array.isArray(data.illustrations) ? data.illustrations : [];
    const meta = data.metadata || {};

    return `
      <div class="section">
        <h3>1. Passage Overview</h3>
        <div><b>Author:</b> ${escapeHtml(po.author || "")}</div>
        <div><b>Genre:</b> ${escapeHtml(po.literary_genre || "")}</div>
        <div><b>Audience:</b> ${escapeHtml(po.original_audience || "")}</div>
        <div style="margin-top:8px">${escapeHtml(po.historical_context || "")}</div>
      </div>

      <div class="section">
        <h3>2. Theological Summary</h3>
        <div>${escapeHtml(ts.core_message || "")}</div>
        <div style="margin-top:8px"><b>Themes:</b> ${escapeHtml((ts.doctrinal_themes || []).join(", "))}</div>
        <div style="margin-top:8px"><b>Christ-centered insight:</b> ${escapeHtml(ts.christ_centered_insight || "")}</div>
      </div>

      <div class="section">
        <h3>3. Verse Breakdown</h3>
        <ul>
          ${vb
            .map(
              (x) =>
                `<li><b>${escapeHtml(x.verse_range || "")}:</b> ${escapeHtml(x.explanation || "")}</li>`
            )
            .join("")}
        </ul>
      </div>

      <div class="section">
        <h3>4. Sermon Structure</h3>
        <div><b>Title:</b> ${escapeHtml(ss.title || "")}</div>
        <ol style="margin-top:10px">
          ${pts
            .map(
              (p) => `
            <li style="margin-bottom:10px">
              <div><b>${escapeHtml(p.point_title || "")}</b></div>
              <div>${escapeHtml(p.explanation || "")}</div>
              <div style="margin-top:6px;opacity:.85"><b>Supporting:</b> ${escapeHtml(
                (p.supporting_scriptures || []).join("; ")
              )}</div>
            </li>
          `
            )
            .join("")}
        </ol>
      </div>

      <div class="section">
        <h3>5. Contextual Application</h3>
        <ul>
          ${ga
            .map((a) => `<li><b>${escapeHtml(a.context_type || "")}:</b> ${escapeHtml(a.application || "")}</li>`)
            .join("")}
        </ul>
      </div>

      <div class="section">
        <h3>6. Illustration Ideas</h3>
        <ul>
          ${ill.map((i) => `<li>${escapeHtml(i)}</li>`).join("")}
        </ul>
      </div>

      <div class="section">
        <h3>7. Closing Prayer Draft</h3>
        <div>${escapeHtml(data.closing_prayer || "")}</div>
      </div>

      ${
        meta && (meta.generated_at || meta.model || meta.version || meta.platform)
          ? `
        <div class="section" style="opacity:.9">
          <h3>Metadata</h3>
          <div><b>Generated:</b> ${escapeHtml(meta.generated_at ? prettyDate(meta.generated_at) : "")}</div>
          <div><b>Model:</b> ${escapeHtml(meta.model || "")}</div>
          <div><b>Version:</b> ${escapeHtml(meta.version || "")}</div>
          <div><b>Platform:</b> ${escapeHtml(meta.platform || "")}</div>
        </div>
        `
          : ""
      }
    `;
  }

  function renderPastorSermon(data) {
    if (els.output) els.output.innerHTML = renderSermonToHtml(data);

    if (els.copyBtn) els.copyBtn.disabled = false;
    if (els.saveBtn) els.saveBtn.disabled = false;
    if (els.manuscriptBtn) els.manuscriptBtn.disabled = false;
    if (els.publishBtn) els.publishBtn.disabled = false;
  }

  // -------- Manuscript ----------
  function manuscriptToPlainText(m) {
    if (!m) return "";
    const lines = [];

    if (m.introduction) {
      lines.push("INTRODUCTION");
      lines.push(m.introduction);
      lines.push("");
    }

    const sections = Array.isArray(m.body_sections) ? m.body_sections : [];
    sections.forEach((s, idx) => {
      lines.push(`SECTION ${idx + 1}: ${(s.section_title || "").trim()}`.trim());
      if (s.content) lines.push(s.content);
      if (s.estimated_minutes != null) lines.push(`(Estimated: ${s.estimated_minutes} min)`);
      lines.push("");
    });

    if (m.application) {
      lines.push("APPLICATION");
      lines.push(m.application);
      lines.push("");
    }

    if (m.closing_prayer) {
      lines.push("CLOSING PRAYER");
      lines.push(m.closing_prayer);
      lines.push("");
    }

    if (m.notes_for_pastor) {
      lines.push("NOTES FOR PASTOR");
      lines.push(m.notes_for_pastor);
      lines.push("");
    }

    if (m.estimated_total_minutes != null) {
      lines.push(`TOTAL ESTIMATED MINUTES: ${m.estimated_total_minutes}`);
      lines.push("");
    }

    return lines.join("\n");
  }

  function renderManuscript(manuscriptObj) {
    if (!els.manuscriptOutput) return;

    const m = manuscriptObj?.manuscript || manuscriptObj;
    if (!m) {
      els.manuscriptOutput.innerHTML = `<div class="muted">No manuscript data.</div>`;
      return;
    }

    const safe = (s) => escapeHtml(s || "");
    const secs = Array.isArray(m.body_sections) ? m.body_sections : [];

    els.manuscriptOutput.innerHTML = `
      <div class="section">
        <h3>Introduction</h3>
        <div>${safe(m.introduction)}</div>
      </div>

      ${secs
        .map(
          (s, i) => `
        <div class="section">
          <h3>${i + 1}. ${safe(s.section_title)}</h3>
          <div>${safe(s.content)}</div>
          ${s.estimated_minutes != null ? `<div class="muted" style="margin-top:8px">(Estimated: ${safe(s.estimated_minutes)} min)</div>` : ""}
        </div>
      `
        )
        .join("")}

      <div class="section">
        <h3>Application</h3>
        <div>${safe(m.application)}</div>
      </div>

      <div class="section">
        <h3>Closing Prayer</h3>
        <div>${safe(m.closing_prayer)}</div>
      </div>

      ${
        m.notes_for_pastor
          ? `
        <div class="section">
          <h3>Notes for Pastor</h3>
          <div>${safe(m.notes_for_pastor)}</div>
        </div>
      `
          : ""
      }

      ${
        m.estimated_total_minutes != null
          ? `
        <div class="section" style="opacity:.9">
          <h3>Timing</h3>
          <div><b>Estimated total minutes:</b> ${safe(m.estimated_total_minutes)}</div>
        </div>
      `
          : ""
      }
    `;

    if (els.copyManuscriptBtn) els.copyManuscriptBtn.disabled = false;
    if (els.downloadManuscriptBtn) els.downloadManuscriptBtn.disabled = false;
    if (els.exportPdfBtn) els.exportPdfBtn.disabled = false;
    if (els.publishBtn) els.publishBtn.disabled = false;
  }

  // -------- Restore inputs ----------
  function restorePastorInputs() {
    if (els.apiKey) {
      els.apiKey.value = localStorage.getItem(STORE.APIKEY) || "";
      els.apiKey.addEventListener("input", () =>
        localStorage.setItem(STORE.APIKEY, (els.apiKey.value || "").trim())
      );
    }

    if (els.denomination) {
      const savedDenom = localStorage.getItem(STORE.DENOM);
      if (savedDenom) els.denomination.value = savedDenom;
      els.denomination.addEventListener("change", () => {
        localStorage.setItem(STORE.DENOM, els.denomination.value || "");
      });
    }

    try {
      const prev = localStorage.getItem(STORE.LAST_INPUT);
      if (prev) {
        const p = JSON.parse(prev);
        if (els.passage && p.passage_reference) els.passage.value = p.passage_reference;
        if (els.theme && p.theme) els.theme.value = p.theme;
        if (els.audience && p.audience_type) els.audience.value = p.audience_type;
        if (els.context && p.local_context) els.context.value = p.local_context;
        if (els.service && p.service_type) els.service.value = p.service_type;
        if (els.tone && p.tone) els.tone.value = p.tone;
        if (els.duration && p.duration_minutes) els.duration.value = p.duration_minutes;
        if (els.denomination && p.denomination) els.denomination.value = p.denomination;
      }
    } catch {}

    try {
      const raw = localStorage.getItem(STORE.SHARE);
      if (raw) {
        const s = JSON.parse(raw);
        if (s?.share_url) {
          setShareBox(`Last share link: ${s.share_url}`);
          if (els.copyShareBtn) els.copyShareBtn.disabled = false;
          if (els.whatsAppShareBtn) els.whatsAppShareBtn.disabled = false;
        }
      }
    } catch {}
  }

  function buildPayload() {
    const payload = {
      passage_reference: (els.passage?.value || "").trim(),
      theme: (els.theme?.value || "").trim(),
      denomination: (els.denomination?.value || "broad_evangelical").trim(),
      audience_type: els.audience?.value || "General",
      local_context: els.context?.value || "Other",
      service_type: els.service?.value || "Sunday",
      tone: els.tone?.value || "Teaching",
      duration_minutes: parseInt(els.duration?.value || "30", 10) || 30,
    };

    localStorage.setItem(STORE.LAST_INPUT, JSON.stringify(payload));
    localStorage.setItem(STORE.DENOM, payload.denomination);

    return payload;
  }

  // -------- Outline ----------
  async function generateSermon() {
    const payload = buildPayload();
    if (!payload.passage_reference || !payload.theme) {
      setStatus("Please enter Bible Passage and Theme.");
      return;
    }

    setStatus("Generating outline… (needs internet)");
    if (els.generateBtn) els.generateBtn.disabled = true;
    if (els.copyBtn) els.copyBtn.disabled = true;
    if (els.saveBtn) els.saveBtn.disabled = true;
    if (els.manuscriptBtn) els.manuscriptBtn.disabled = true;
    if (els.publishBtn) els.publishBtn.disabled = true;

    try {
      const res = await fetch("/api/v1/faith/sermon", {
        method: "POST",
        headers: apiHeadersJson(),
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || data?.error || `Request failed (${res.status})`);

      localStorage.setItem(STORE.LAST, JSON.stringify(data));
      renderPastorSermon(data);
      setStatus("Outline ready. You can now generate manuscript.");
    } catch (e) {
      setStatus(`Error: ${e.message || e}`);

      try {
        const last = localStorage.getItem(STORE.LAST);
        if (last) {
          renderPastorSermon(JSON.parse(last));
          setStatus("Network error. Showing last saved outline (offline-lite).");
        }
      } catch {}
    } finally {
      if (els.generateBtn) els.generateBtn.disabled = false;
    }
  }

  // -------- Manuscript ----------
  async function generateManuscript() {
    const rawOutline = localStorage.getItem(STORE.LAST);
    const rawInput = localStorage.getItem(STORE.LAST_INPUT);

    if (!rawOutline || !rawInput) {
      setStatus("Generate an outline first (so we have sermon_input + sermon_output).");
      return;
    }

    let sermon_output, sermon_input;
    try {
      sermon_output = JSON.parse(rawOutline);
      sermon_input = JSON.parse(rawInput);
    } catch {
      setStatus("Saved outline/input is corrupted. Please generate outline again.");
      return;
    }

    setStatus("Generating manuscript… (needs internet)");
    if (els.manuscriptBtn) els.manuscriptBtn.disabled = true;
    if (els.copyManuscriptBtn) els.copyManuscriptBtn.disabled = true;
    if (els.downloadManuscriptBtn) els.downloadManuscriptBtn.disabled = true;
    if (els.exportPdfBtn) els.exportPdfBtn.disabled = true;

    try {
      const res = await fetch("/api/v1/faith/sermon/manuscript", {
        method: "POST",
        headers: apiHeadersJson(),
        body: JSON.stringify({ sermon_input, sermon_output }),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || data?.error || `Request failed (${res.status})`);

      localStorage.setItem(STORE.LAST_MANUSCRIPT, JSON.stringify(data));
      renderManuscript(data);
      setStatus("Manuscript ready (saved locally).");
    } catch (e) {
      setStatus(`Error: ${e.message || e}`);

      try {
        const lastM = localStorage.getItem(STORE.LAST_MANUSCRIPT);
        if (lastM) {
          renderManuscript(JSON.parse(lastM));
          setStatus("Network error. Showing last saved manuscript (offline-lite).");
        }
      } catch {}
    } finally {
      if (els.manuscriptBtn) els.manuscriptBtn.disabled = false;
    }
  }

  function loadLastManuscript() {
    const raw = localStorage.getItem(STORE.LAST_MANUSCRIPT);
    if (!raw) return setStatus("No saved manuscript found yet.");
    try {
      renderManuscript(JSON.parse(raw));
      setStatus("Loaded last manuscript.");
    } catch {
      setStatus("Saved manuscript is corrupted.");
    }
  }

  function copyManuscript() {
    const raw = localStorage.getItem(STORE.LAST_MANUSCRIPT);
    if (!raw) return setStatus("No manuscript found. Generate it first.");
    try {
      const obj = JSON.parse(raw);
      const text = manuscriptToPlainText(obj.manuscript || obj);
      if (!text.trim()) return setStatus("Manuscript is empty.");
      navigator.clipboard.writeText(text).then(
        () => setStatus("Copied manuscript to clipboard."),
        () => setStatus("Could not copy manuscript.")
      );
    } catch {
      setStatus("Saved manuscript is corrupted.");
    }
  }

  function downloadManuscriptTxt() {
    const raw = localStorage.getItem(STORE.LAST_MANUSCRIPT);
    if (!raw) return setStatus("No manuscript found. Generate it first.");
    try {
      const obj = JSON.parse(raw);
      const m = obj.manuscript || obj;
      const text = manuscriptToPlainText(m);

      const filename = `sermon_manuscript_${new Date().toISOString().slice(0, 10)}.txt`;

      const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();

      URL.revokeObjectURL(url);
      setStatus("Downloaded manuscript (.txt).");
    } catch {
      setStatus("Saved manuscript is corrupted.");
    }
  }

  // -------- Export PDF ----------
  function exportManuscriptToPdf() {
    const raw = localStorage.getItem(STORE.LAST_MANUSCRIPT);
    if (!raw) {
      setStatus("No manuscript found. Generate it first.");
      return;
    }
    document.body.classList.add("print-manuscript-only");
    setTimeout(() => {
      try {
        window.print();
      } catch {
        setStatus("Print dialog blocked on this device/browser.");
      }
    }, 50);
  }

  window.addEventListener("afterprint", () => {
    document.body.classList.remove("print-manuscript-only");
  });

  // -------- Publish / Share Link ----------
  function getSavedOutlineAndInput() {
    const rawOutline = localStorage.getItem(STORE.LAST);
    const rawInput = localStorage.getItem(STORE.LAST_INPUT);
    if (!rawOutline || !rawInput) return null;

    try {
      return {
        sermon_output: JSON.parse(rawOutline),
        sermon_input: JSON.parse(rawInput),
      };
    } catch {
      return null;
    }
  }

  function getSavedManuscriptOptional() {
    const raw = localStorage.getItem(STORE.LAST_MANUSCRIPT);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  function resolveAbsoluteUrl(maybeUrl) {
    try {
      return new URL(maybeUrl, window.location.origin).toString();
    } catch {
      return maybeUrl;
    }
  }

  async function publishShareLink() {
    const base = getSavedOutlineAndInput();
    if (!base) {
      setStatus("Generate an outline first (and keep inputs saved).");
      return;
    }

    const manuscript = getSavedManuscriptOptional();
    const pastor_handle = getActivePastorHandle();

    setStatus("Publishing… (needs internet)");
    setShareBox("");

    if (els.publishBtn) els.publishBtn.disabled = true;
    if (els.copyShareBtn) els.copyShareBtn.disabled = true;
    if (els.whatsAppShareBtn) els.whatsAppShareBtn.disabled = true;

    try {
      const res = await fetch("/api/v1/faith/share", {
        method: "POST",
        headers: apiHeadersJson(),
        body: JSON.stringify({
          pastor_handle: pastor_handle,
          sermon_input: base.sermon_input,
          sermon_output: base.sermon_output,
          manuscript: manuscript || null,
          title: base.sermon_output?.sermon_structure?.title || null,
        }),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || data?.error || `Request failed (${res.status})`);

      const share_url = resolveAbsoluteUrl(data.url);
      const share_id = data.share_id;

      const stored = {
        share_id,
        share_url,
        created_at: data.created_at || null,
      };

      localStorage.setItem(STORE.SHARE, JSON.stringify(stored));
      setShareBox(`Share link: ${share_url}`);

      if (els.copyShareBtn) els.copyShareBtn.disabled = false;
      if (els.whatsAppShareBtn) els.whatsAppShareBtn.disabled = false;

      setStatus("Published. Share link ready.");
    } catch (e) {
      setStatus(`Error: ${e.message || e}`);
    } finally {
      if (els.publishBtn) els.publishBtn.disabled = false;
    }
  }

  function getShareUrlFromStorage() {
    try {
      const raw = localStorage.getItem(STORE.SHARE);
      if (!raw) return null;
      const s = JSON.parse(raw);
      return s?.share_url || null;
    } catch {
      return null;
    }
  }

  function copyShareLink() {
    const url = getShareUrlFromStorage();
    if (!url) return setStatus("No share link yet. Click Publish first.");
    navigator.clipboard.writeText(url).then(
      () => setStatus("Copied share link."),
      () => setStatus("Could not copy share link.")
    );
  }

  function shareLinkViaWhatsApp() {
    const url = getShareUrlFromStorage();
    if (!url) return setStatus("No share link yet. Click Publish first.");

    const text = `Sermon link (Xynasoft Faith): ${url}`;
    const waUrl = `https://wa.me/?text=${encodeURIComponent(text)}`;
    window.open(waUrl, "_blank", "noopener,noreferrer");
  }

  // -------- Misc ----------
  function clearAll() {
    if (els.passage) els.passage.value = "";
    if (els.theme) els.theme.value = "";
    setStatus("");
    setShareBox("");

    if (els.output) els.output.innerHTML = `<div class="muted">Your structured sermon outline will appear here.</div>`;
    if (els.manuscriptOutput) {
      els.manuscriptOutput.innerHTML = `<div class="muted">Generate a manuscript after you generate an outline.</div>`;
    }

    if (els.copyBtn) els.copyBtn.disabled = true;
    if (els.saveBtn) els.saveBtn.disabled = true;
    if (els.manuscriptBtn) els.manuscriptBtn.disabled = true;

    if (els.copyManuscriptBtn) els.copyManuscriptBtn.disabled = true;
    if (els.downloadManuscriptBtn) els.downloadManuscriptBtn.disabled = true;
    if (els.exportPdfBtn) els.exportPdfBtn.disabled = true;

    if (els.publishBtn) els.publishBtn.disabled = true;
    if (els.copyShareBtn) els.copyShareBtn.disabled = true;
    if (els.whatsAppShareBtn) els.whatsAppShareBtn.disabled = true;
  }

  function copyOutlineJson() {
    const raw = localStorage.getItem(STORE.LAST);
    if (!raw) return;
    navigator.clipboard.writeText(raw).then(
      () => setStatus("Copied outline JSON to clipboard."),
      () => setStatus("Could not copy.")
    );
  }

  function saveLocal() {
    const raw = localStorage.getItem(STORE.LAST);
    if (!raw) return;
    setStatus("Saved locally (on this phone/browser).");
  }

  function loadLastOutline() {
    const raw = localStorage.getItem(STORE.LAST);
    if (!raw) return setStatus("No saved outline found yet.");
    try {
      renderPastorSermon(JSON.parse(raw));
      setStatus("Loaded last saved outline.");
    } catch {
      setStatus("Saved outline is corrupted.");
    }
  }

  // -------- Preaching Mode ----------
  function setPreachFont(px) {
    const v = Math.max(16, Math.min(40, px));
    document.documentElement.style.setProperty("--preach-font-size", `${v}px`);
    localStorage.setItem(STORE.PREACH_FONT, String(v));
  }

  function getPreachFont() {
    const raw = localStorage.getItem(STORE.PREACH_FONT);
    const n = parseInt(raw || "22", 10);
    return Number.isFinite(n) ? n : 22;
  }

  function getBestPreachText() {
    const rawM = localStorage.getItem(STORE.LAST_MANUSCRIPT);
    if (rawM) {
      try {
        const obj = JSON.parse(rawM);
        const m = obj.manuscript || obj;
        return manuscriptToPlainText(m);
      } catch {}
    }

    const rawO = localStorage.getItem(STORE.LAST);
    if (rawO) {
      try {
        const outline = JSON.parse(rawO);
        const html = renderSermonToHtml(outline);
        const tmp = document.createElement("div");
        tmp.innerHTML = html;
        return (tmp.innerText || "").trim();
      } catch {}
    }

    return "";
  }

  function enterPreachMode() {
    if (!els.preachOverlay || !els.preachBody) return;

    const text = getBestPreachText();
    if (!text) {
      setStatus("Generate or load a manuscript (or outline) first.");
      return;
    }

    setPreachFont(getPreachFont());
    els.preachOverlay.classList.remove("hidden");
    els.preachOverlay.setAttribute("aria-hidden", "false");

    const safe = escapeHtml(text).replaceAll("\n\n", "\n").replaceAll("\n", "<br/>");
    els.preachBody.innerHTML = `<div>${safe}</div>`;

    try {
      if (document.documentElement.requestFullscreen) {
        document.documentElement.requestFullscreen().catch(() => {});
      }
    } catch {}
  }

  function exitPreachMode() {
    if (!els.preachOverlay) return;
    els.preachOverlay.classList.add("hidden");
    els.preachOverlay.setAttribute("aria-hidden", "true");

    try {
      if (document.fullscreenElement && document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      }
    } catch {}
  }

  function wirePreachMode() {
    els.preachModeBtn?.addEventListener("click", enterPreachMode);
    els.preachExitBtn?.addEventListener("click", exitPreachMode);

    els.preachBiggerBtn?.addEventListener("click", () => setPreachFont(getPreachFont() + 2));
    els.preachSmallerBtn?.addEventListener("click", () => setPreachFont(getPreachFont() - 2));

    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && els.preachOverlay && !els.preachOverlay.classList.contains("hidden")) {
        exitPreachMode();
      }
    });
  }

  // -------- Member view ----------
  async function loadMemberView(shareId) {
    if (!mvTitle || !mvBody) return;

    mvTitle.textContent = "Loading Sermon...";
    if (mvMeta) mvMeta.textContent = "";
    mvBody.innerHTML = "";
    setMemberStatus("");

    try {
      const res = await fetch(`/api/v1/faith/public/${encodeURIComponent(shareId)}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || data?.error || `Request failed (${res.status})`);

      mvTitle.textContent = data.title || "Shared Sermon";
      if (mvMeta) {
        mvMeta.textContent = data.created_at ? `Shared • ${prettyDate(data.created_at)}` : "Shared sermon";
      }

      const sermon = data.payload_output || {};
      let html = renderSermonToHtml(sermon);

      if (data.manuscript) {
        const m = data.manuscript.manuscript || data.manuscript;
        const text = manuscriptToPlainText(m);
        if (text.trim()) {
          html += `
            <div class="section">
              <h3>Manuscript</h3>
              <div style="white-space:pre-wrap;line-height:1.75">${escapeHtml(text)}</div>
            </div>
          `;
        }
      }

      mvBody.innerHTML = html;

      if (mvSubmit) {
        mvSubmit.onclick = async () => {
          const q = (mvQuestion?.value || "").trim();
          if (!q) return setMemberStatus("Please type a question.");
          setMemberStatus("Submitting…");
          mvSubmit.disabled = true;

          try {
            const payload = {
              name: (mvName?.value || "").trim() || null,
              question: q,
            };

            const r2 = await fetch(`/api/v1/faith/public/${encodeURIComponent(shareId)}/questions`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            });

            const out = await r2.json().catch(() => ({}));
            if (!r2.ok) throw new Error(out?.detail || out?.error || `Request failed (${r2.status})`);

            if (mvQuestion) mvQuestion.value = "";
            setMemberStatus("Received. Thank you—your question was sent to the pastor.");
          } catch (e) {
            setMemberStatus(`Error: ${e.message || e}`);
          } finally {
            mvSubmit.disabled = false;
          }
        };
      }
    } catch (e) {
      mvTitle.textContent = "Sermon not available";
      mvBody.innerHTML = `<div class="muted">Error: ${escapeHtml(e.message || e)}</div>`;
      setMemberStatus("");
    }
  }

  // -------- Init ----------
  function init() {
    const shareId = getShareIdFromPath();
    if (shareId) {
      if (pastorView) pastorView.style.display = "none";
      if (memberView) memberView.style.display = "block";
      loadMemberView(shareId);
      return;
    }

    restorePastorInputs();

    els.generateBtn?.addEventListener("click", generateSermon);
    els.clearBtn?.addEventListener("click", clearAll);
    els.copyBtn?.addEventListener("click", copyOutlineJson);
    els.saveBtn?.addEventListener("click", saveLocal);
    els.loadBtn?.addEventListener("click", loadLastOutline);

    els.manuscriptBtn?.addEventListener("click", generateManuscript);
    els.copyManuscriptBtn?.addEventListener("click", copyManuscript);
    els.downloadManuscriptBtn?.addEventListener("click", downloadManuscriptTxt);
    els.loadManuscriptBtn?.addEventListener("click", loadLastManuscript);

    els.exportPdfBtn?.addEventListener("click", exportManuscriptToPdf);

    els.publishBtn?.addEventListener("click", publishShareLink);
    els.copyShareBtn?.addEventListener("click", copyShareLink);
    els.whatsAppShareBtn?.addEventListener("click", shareLinkViaWhatsApp);

    wirePreachMode();

    try {
      const lastOutline = localStorage.getItem(STORE.LAST);
      if (lastOutline) renderPastorSermon(JSON.parse(lastOutline));
    } catch {}

    try {
      const lastM = localStorage.getItem(STORE.LAST_MANUSCRIPT);
      if (lastM) renderManuscript(JSON.parse(lastM));
    } catch {}
  }

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/faith/sw.js").catch(() => {});
    });
  }

  init();
})();