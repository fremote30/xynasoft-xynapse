(() => {
  "use strict";

  const API_BASE = "/api/v1/churches";

  const state = {
    churchId: null,
    eventId: null,
    authorized: false,
    busy: false
  };

  const $ = (id) => document.getElementById(id);

  function status(message) {
    const el = $("churchOperationsState");
    if (el) el.textContent = message;
  }

  function validId(value) {
    const id = Number(value);
    return Number.isSafeInteger(id) && id > 0 ? id : null;
  }

  function authorized() {
    return state.authorized &&
      validId(state.churchId) &&
      typeof window.apiFetch === "function";
  }

  async function request(path, options = {}) {
    if (!authorized()) {
      throw new Error("Church operations access unavailable.");
    }

    const response = await window.apiFetch(
      `${API_BASE}/${state.churchId}${path}`,
      options
    );

    if (!response.ok) {
      if (response.status === 403) {
        throw new Error("Permission or subscription required.");
      }
      throw new Error(`Request failed (${response.status}).`);
    }

    return response.json();
  }

  async function listAttendance(eventId) {
    const id = validId(eventId);
    if (!id) throw new Error("Select a valid event.");
    return request(`/events/${id}/attendance`);
  }

  async function recordAttendance(eventId, membershipId, attendanceStatus = "present") {
    const event = validId(eventId);
    const member = validId(membershipId);
    if (!event || !member) {
      throw new Error("Select a valid event and member.");
    }

    return request(`/events/${event}/attendance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        church_membership_id: member,
        status: attendanceStatus
      })
    });
  }

  async function updateAttendance(eventId, attendanceId, attendanceStatus) {
    const event = validId(eventId);
    const attendance = validId(attendanceId);
    if (!event || !attendance) {
      throw new Error("Invalid attendance record.");
    }

    return request(`/events/${event}/attendance/${attendance}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: attendanceStatus })
    });
  }

  async function listAssignments(eventId) {
    const id = validId(eventId);
    if (!id) throw new Error("Select a valid event.");
    return request(`/events/${id}/service-assignments`);
  }

  async function createAssignment(eventId, groupId, membershipId, serviceRole) {
    const event = validId(eventId);
    const group = validId(groupId);
    const member = validId(membershipId);
    const role = String(serviceRole || "").trim();

    if (!event || !group || !member || !role || role.length > 120) {
      throw new Error("Valid event, group, member and role are required.");
    }

    return request(`/events/${event}/service-assignments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        group_id: group,
        church_membership_id: member,
        service_role: role
      })
    });
  }

  async function updateAssignment(eventId, assignmentId, assignmentStatus) {
    const event = validId(eventId);
    const assignment = validId(assignmentId);
    if (!event || !assignment) {
      throw new Error("Invalid service assignment.");
    }

    return request(`/events/${event}/service-assignments/${assignment}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: assignmentStatus })
    });
  }

  function reset() {
    state.churchId = null;
    state.eventId = null;
    state.authorized = false;
    state.busy = false;

    const panel = $("churchOperationsSection");
    if (panel) panel.hidden = true;
  }

  function init(context) {
    reset();

    const permissions = context?.permissions;
    const canManage = Array.isArray(permissions)
      ? permissions.includes("groups.manage")
      : false;

    const churchId = validId(context?.church?.id);

    if (!churchId || !canManage) return false;

    state.churchId = churchId;
    state.authorized = true;

    const panel = $("churchOperationsSection");
    if (panel) panel.hidden = false;

    status("Church operations ready.");
    return true;
  }

  window.XynaFaithChurchOperationsV2 = Object.freeze({
    init,
    reset,
    listAttendance,
    recordAttendance,
    updateAttendance,
    listAssignments,
    createAssignment,
    updateAssignment
  });
})();
