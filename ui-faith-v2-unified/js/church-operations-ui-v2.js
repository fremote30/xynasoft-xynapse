(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const validId = (value) => {
    const id = Number(value);
    return Number.isSafeInteger(id) && id > 0 ? id : null;
  };

  let generation = 0;
  let contextGeneration = 0;
  let busy = false;
  let churchId = null;
  let eventId = null;
  let members = [];
  let groups = [];
  let attendance = [];
  let assignments = [];

  function message(value) {
    const el = $("churchOperationsState");
    if (el) el.textContent = value;
  }

  function setBusy(value) {
    busy = value;
    ["churchAttendanceSaveButton", "churchServiceSaveButton"]
      .forEach((id) => {
        const button = $(id);
        if (button) button.disabled = value;
      });

    ["churchAttendanceList", "churchServiceAssignmentList"]
      .forEach((id) => {
        $(id)?.querySelectorAll("button").forEach((button) => {
          button.disabled = value;
        });
      });

    const eventSelect = $("churchOperationsEvent");
    if (eventSelect) eventSelect.disabled = value;
  }

  function populate(id, rows, placeholder, label) {
    const select = $(id);
    if (!select) return;

    select.replaceChildren(new Option(placeholder, ""));

    rows.forEach((row) => {
      if (!validId(row?.id)) return;
      select.add(new Option(label(row), String(row.id)));
    });
  }

  async function fetchList(path, key) {
    const response = await window.apiFetch(path);

    if (!response.ok) {
      throw new Error(`Could not load ${key} (${response.status}).`);
    }

    const data = await response.json();
    return Array.isArray(data[key]) ? data[key] : [];
  }

  function memberName(id) {
    const member = members.find(
      (item) => Number(item.id) === Number(id)
    );
    return member?.user?.name || `Member #${id}`;
  }

  function groupName(id) {
    const group = groups.find(
      (item) => Number(item.id) === Number(id)
    );
    return group?.name || `Group #${id}`;
  }

  function renderRows(containerId, rows, render) {
    const container = $(containerId);
    if (!container) return;

    container.replaceChildren();

    if (!rows.length) {
      const p = document.createElement("p");
      p.textContent = "No records for this event.";
      container.append(p);
      return;
    }

    rows.forEach((row) => container.append(render(row)));
  }

  function makeSelect(values, current) {
    const select = document.createElement("select");

    values.forEach((value) => {
      const option = new Option(value, value);
      option.selected = value === current;
      select.add(option);
    });

    return select;
  }

  function attendanceRow(record) {
    const article = document.createElement("article");
    article.className = "church-community-item";

    const name = document.createElement("strong");
    name.textContent = memberName(record.church_membership_id);

    const select = makeSelect(
      ["present", "absent", "excused"],
      record.status
    );

    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn";
    button.textContent = "Update";

    button.addEventListener("click", async () => {
      await mutate(async (selectedEvent) => {
        await window.XynaFaithChurchOperationsV2.updateAttendance(
          selectedEvent, record.id, select.value
        );
      }, "Attendance updated.");
    });

    article.append(name, select, button);
    return article;
  }

  function assignmentRow(record) {
    const article = document.createElement("article");
    article.className = "church-community-item";

    const title = document.createElement("strong");
    title.textContent =
      `${memberName(record.church_membership_id)} — ` +
      `${groupName(record.group_id)} — ${record.service_role}`;

    const select = makeSelect(
      ["assigned", "confirmed", "declined", "completed", "cancelled"],
      record.status
    );

    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn";
    button.textContent = "Update";

    button.addEventListener("click", async () => {
      await mutate(async (selectedEvent) => {
        await window.XynaFaithChurchOperationsV2.updateAssignment(
          selectedEvent, record.id, select.value
        );
      }, "Assignment updated.");
    });

    article.append(title, select, button);
    return article;
  }

  async function loadRecords() {
    const token = ++generation;
    eventId = validId($("churchOperationsEvent")?.value);

    attendance = [];
    assignments = [];
    renderRows("churchAttendanceList", [], attendanceRow);
    renderRows("churchServiceAssignmentList", [], assignmentRow);

    if (!eventId) {
      renderRows("churchAttendanceList", [], attendanceRow);
      renderRows("churchServiceAssignmentList", [], assignmentRow);
      message("Select an event to manage attendance and teams.");
      return;
    }

    message("Loading event records...");

    try {
      const api = window.XynaFaithChurchOperationsV2;

      const [attendanceData, assignmentData] = await Promise.all([
        api.listAttendance(eventId),
        api.listAssignments(eventId)
      ]);

      if (token !== generation) return;

      attendance = attendanceData.attendance || [];
      assignments = assignmentData.assignments || [];

      renderRows("churchAttendanceList", attendance, attendanceRow);
      renderRows("churchServiceAssignmentList", assignments, assignmentRow);

      message("Event records loaded.");
    } catch (error) {
      if (token !== generation) return;
      message(error.message || "Could not load event records.");
      throw error;
    }
  }

  async function mutate(action, successMessage) {
    if (busy || !eventId || !churchId) return;

    const selectedEvent = eventId;
    const selectedChurch = churchId;
    const contextToken = contextGeneration;

    setBusy(true);

    try {
      await action(selectedEvent);

      if (
        contextToken !== contextGeneration ||
        selectedChurch !== churchId ||
        selectedEvent !== eventId
      ) return;

      await loadRecords();

      if (
        contextToken === contextGeneration &&
        selectedChurch === churchId &&
        selectedEvent === eventId
      ) {
        message(successMessage);
      }
    } catch (error) {
      if (
        contextToken === contextGeneration &&
        selectedChurch === churchId
      ) {
        message(error.message || "Operation failed.");
      }
    } finally {
      if (contextToken === contextGeneration) {
        setBusy(false);
      }
    }
  }

  function bind() {
    const eventSelect = $("churchOperationsEvent");
    if (!eventSelect || eventSelect.dataset.operationsBound) return;

    eventSelect.dataset.operationsBound = "1";
    eventSelect.addEventListener("change", loadRecords);

    $("churchAttendanceSaveButton")?.addEventListener(
      "click",
      () => mutate(async (selectedEvent) => {
        const member = validId($("churchAttendanceMember")?.value);
        if (!member) throw new Error("Select a church member.");

        const existing = attendance.find(
          (row) => Number(row.church_membership_id) === member
        );

        const api = window.XynaFaithChurchOperationsV2;
        const selectedStatus = $("churchAttendanceStatus")?.value;

        if (existing) {
          await api.updateAttendance(
            selectedEvent, existing.id, selectedStatus
          );
        } else {
          await api.recordAttendance(
            selectedEvent, member, selectedStatus
          );
        }
      }, "Attendance saved.")
    );

    $("churchServiceSaveButton")?.addEventListener(
      "click",
      () => mutate(async (selectedEvent) => {
        const group = validId($("churchServiceGroup")?.value);
        const member = validId($("churchServiceMember")?.value);
        const role = $("churchServiceRole")?.value?.trim();

        await window.XynaFaithChurchOperationsV2.createAssignment(
          selectedEvent, group, member, role
        );
      }, "Service assignment saved.")
    );
  }

  function resetContext() {
    ++generation;
    ++contextGeneration;

    churchId = null;
    eventId = null;
    members = [];
    groups = [];
    attendance = [];
    assignments = [];

    setBusy(false);

    [
      "churchOperationsEvent",
      "churchAttendanceMember",
      "churchServiceMember",
      "churchServiceGroup"
    ].forEach((id) => {
      const select = $(id);
      if (select) select.replaceChildren();
    });

    ["churchAttendanceList", "churchServiceAssignmentList"]
      .forEach((id) => $(id)?.replaceChildren());
  }

  async function init(context) {
    resetContext();
    const token = generation;
    const contextToken = contextGeneration;

    churchId = validId(context?.church?.id);
    const permissions = context?.permissions || [];

    if (
      !churchId ||
      !Array.isArray(permissions) ||
      !permissions.includes("groups.manage")
    ) {
      return false;
    }

    bind();
    message("Loading church events, members and groups...");

    try {
      const base = `/api/v1/churches/${churchId}`;

      const [events, loadedMembers, loadedGroups] = await Promise.all([
        fetchList(`${base}/events`, "events"),
        fetchList(`${base}/members`, "members"),
        fetchList(`${base}/groups`, "groups")
      ]);

      if (token !== generation || contextToken !== contextGeneration) return false;

      members = loadedMembers;
      groups = loadedGroups;

      populate("churchOperationsEvent", events, "Select event",
        (item) => item.title || `Event #${item.id}`);

      populate("churchAttendanceMember", members, "Select member",
        (item) => item.user?.name || `Member #${item.id}`);

      populate("churchServiceMember", members, "Select member",
        (item) => item.user?.name || `Member #${item.id}`);

      populate("churchServiceGroup", groups, "Select group",
        (item) => item.name || `Group #${item.id}`);

      message("Select an event to manage attendance and teams.");
      return true;
    } catch (error) {
      if (token === generation && contextToken === contextGeneration) {
        message(error.message || "Church operations failed to load.");
      }
      return false;
    }
  }

  window.XynaFaithChurchOperationsUIV2 = Object.freeze({
    init,
    reset: resetContext
  });
})();
