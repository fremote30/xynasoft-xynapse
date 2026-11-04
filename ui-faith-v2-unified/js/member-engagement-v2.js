(() => {
  "use strict";

  const BASE = "/api/v1/member";
  const $ = id => document.getElementById(id);

  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) {
      node.textContent = String(text);
    }
    if (className) node.className = className;
    return node;
  }

  async function request(path, options = {}) {
    if (typeof window.apiFetch !== "function") {
      throw new Error("Authenticated API is unavailable");
    }

    const response = await window.apiFetch(BASE + path, {
      ...options,
      headers: {
        ...(options.body ? {"Content-Type": "application/json"} : {}),
        ...(options.headers || {})
      }
    });

    if (!response.ok) {
      let message = "Request failed";
      try {
        const data = await response.json();
        if (typeof data.detail === "string") message = data.detail;
      } catch (_) {}
      throw new Error(message);
    }

    if (response.status === 204) return null;
    return response.json();
  }

  function showError(container, error) {
    container.replaceChildren(
      el("p", error.message || "Unable to load data", "member-v2-error")
    );
  }

  function button(label, handler, className = "member-v2-button") {
    const control = el("button", label, className);
    control.type = "button";
    control.addEventListener("click", handler);
    return control;
  }

  async function loadReadingPlans() {
    const available = $("memberAvailablePlans");
    const enrolled = $("memberEnrolledPlans");
    if (!available || !enrolled) return;

    available.replaceChildren(el("p", "Loading reading plans…"));
    enrolled.replaceChildren(el("p", "Loading your progress…"));

    try {
      const [catalog, mine] = await Promise.all([
        request("/reading-plans"),
        request("/reading-plans/mine")
      ]);

      const enrolledPlans = mine.reading_plans || [];
      const enrolledIds = new Set(
        enrolledPlans.map(item => item.plan && item.plan.id)
      );

      enrolled.replaceChildren();

      if (!enrolledPlans.length) {
        enrolled.append(el("p", "You haven't started a reading plan yet."));
      }

      for (const enrollment of enrolledPlans) {
        const card = el("article", null, "member-v2-item");
        const title = el("h3", enrollment.plan?.title || "Reading Plan");
        const progress = el(
          "p",
          `${enrollment.completed_days || 0} of ${enrollment.total_days || 0} days completed`
        );
        const bar = el("progress");
        bar.max = Math.max(1, enrollment.total_days || 0);
        bar.value = enrollment.completed_days || 0;

        card.append(title, progress, bar);

        const days = el("div", null, "member-v2-days");

        for (const day of enrollment.days || []) {
          const row = el("div", null, "member-v2-day");
          const heading = el(
            "strong",
            `Day ${day.day_number}: ${day.title || day.scripture || "Reading"}`
          );
          const scripture = el("p", day.scripture || "");
          const reflection = el("p", day.reflection || "");
          const prompt = el("p", day.prompt || "");
          const toggle = button(
            day.completed ? "Mark incomplete" : "Mark complete",
            async () => {
              toggle.disabled = true;
              try {
                await request(
                  `/reading-plans/mine/${enrollment.id}/days/${day.id}`,
                  {
                    method: "PATCH",
                    body: JSON.stringify({completed: !day.completed})
                  }
                );
                await loadReadingPlans();
              } catch (error) {
                alert(error.message);
                toggle.disabled = false;
              }
            }
          );

          row.append(heading, scripture, reflection, prompt, toggle);
          days.append(row);
        }

        card.append(days);
        enrolled.append(card);
      }

      available.replaceChildren();

      const availablePlans = catalog.reading_plans || [];

      if (!availablePlans.length) {
        available.append(el("p", "No published plans are available yet."));
      }

      for (const plan of availablePlans) {
        const card = el("article", null, "member-v2-item");
        card.append(
          el("h3", plan.title),
          el("p", plan.description || ""),
          el("small", `${plan.duration_days || 0} days`)
        );

        if (!enrolledIds.has(plan.id)) {
          const start = button("Start plan", async () => {
            start.disabled = true;
            try {
              await request(`/reading-plans/${plan.id}/start`, {
                method: "POST"
              });
              await loadReadingPlans();
            } catch (error) {
              alert(error.message);
              start.disabled = false;
            }
          });
          card.append(start);
        } else {
          card.append(el("span", "Already enrolled", "member-v2-status"));
        }

        available.append(card);
      }
    } catch (error) {
      showError(available, error);
      showError(enrolled, error);
    }
  }

  async function loadSermonNotes() {
    const list = $("memberNotesList");
    if (!list) return;

    list.replaceChildren(el("p", "Loading notes…"));

    try {
      const data = await request("/sermon-notes");
      list.replaceChildren();

      if (!(data.notes || []).length) {
        list.append(el("p", "No notes yet. Write your first reflection."));
      }

      for (const note of data.notes || []) {
        const card = el("article", null, "member-v2-item");
        card.append(
          el("h3", note.title || "Untitled note"),
          el("p", note.body)
        );

        const actions = el("div", null, "member-v2-actions");

        actions.append(
          button("Edit", () => {
            $("memberNoteId").value = note.id;
            $("memberNoteTitle").value = note.title || "";
            $("memberNoteBody").value = note.body || "";
            $("memberNoteBody").focus();
          }),
          button("Delete", async () => {
            if (!confirm("Delete this sermon note?")) return;
            try {
              await request(`/sermon-notes/${note.id}`, {
                method: "DELETE"
              });
              await loadSermonNotes();
            } catch (error) {
              alert(error.message);
            }
          }, "member-v2-button member-v2-danger")
        );

        card.append(actions);
        list.append(card);
      }
    } catch (error) {
      showError(list, error);
    }
  }

  function bindNoteForm() {
    const form = $("memberNoteForm");
    if (!form || form.dataset.bound === "true") return;
    form.dataset.bound = "true";

    form.addEventListener("submit", async event => {
      event.preventDefault();

      const id = $("memberNoteId").value;
      const title = $("memberNoteTitle").value.trim();
      const body = $("memberNoteBody").value.trim();
      const status = $("memberNoteStatus");

      if (!body) {
        status.textContent = "Please enter a note.";
        return;
      }

      const submit = form.querySelector('[type="submit"]');
      submit.disabled = true;
      status.textContent = "Saving…";

      try {
        await request(
          id ? `/sermon-notes/${id}` : "/sermon-notes",
          {
            method: id ? "PATCH" : "POST",
            body: JSON.stringify({title, body})
          }
        );

        form.reset();
        $("memberNoteId").value = "";
        status.textContent = "Note saved.";
        await loadSermonNotes();
      } catch (error) {
        status.textContent = error.message;
      } finally {
        submit.disabled = false;
      }
    });

    $("memberNoteClear").addEventListener("click", () => {
      form.reset();
      $("memberNoteId").value = "";
      $("memberNoteStatus").textContent = "";
    });
  }

  window.initMemberReadingPlansV2 = loadReadingPlans;
  window.initMemberSermonNotesV2 = async () => {
    bindNoteForm();
    await loadSermonNotes();
  };
})();
