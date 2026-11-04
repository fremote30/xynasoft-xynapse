const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const SOURCE = fs.readFileSync(
  path.join(
    process.cwd(),
    "ui-faith-v2-unified/js/church-prayer-care.js"
  ),
  "utf8"
);

function element() {
  const listeners = {};
  return {
    hidden: false,
    innerHTML: "",
    textContent: "",
    value: "",
    checked: false,
    listeners,
    addEventListener(type, handler) {
      (listeners[type] ||= []).push(handler);
    }
  };
}

function deferred() {
  let resolve;
  const promise = new Promise((r) => { resolve = r; });
  return { promise, resolve };
}

function response(body) {
  return { ok: true, json: async () => body };
}

async function waitForHandler(control, name) {
  for (let attempt = 0; attempt < 20; attempt++) {
    if (control?.listeners?.click?.length) {
      return control.listeners.click[0];
    }
    await Promise.resolve();
  }

  throw new Error(
    `Timed out waiting for ${name} click handler`
  );
}

function environment(fetch) {
  const ids = [
    "churchPrayerSection",
    "churchPrayerCreateButton",
    "churchPrayerForm",
    "churchPrayerMessage",
    "churchPrayerCategory",
    "churchPrayerVisibility",
    "churchPrayerAnonymous",
    "churchPrayerPastoralCare",
    "churchPrayerCancelButton",
    "churchPrayerFormState",
    "churchPrayerList",
    "churchTestimonySection",
    "churchTestimonyList",
    "churchTestimonyModeration",
    "churchPendingTestimonyList",
    "churchPastoralCareWorkspace",
    "churchPastoralCareList",
    "churchPastoralCareDetail",
    "churchCareCloseDetail",
    "churchCarePriority",
    "churchCareStatus",
    "churchCareAssignee",
    "churchCareFollowUp",
    "churchCareSave",
    "churchCareSaveState",
    "churchCareNotes",
    "churchCareNoteBody",
    "churchCareAddNote",
    "churchCareActivities"
  ];
  const elements = Object.fromEntries(
    ids.map((id) => [id, element()])
  );
  const window = { apiFetch: fetch };
  const document = {
    getElementById: (id) => elements[id] || null
  };
  vm.runInNewContext(SOURCE, { window, document, console });
  return {
    controller: window.XynaFaithChurchPrayerCare,
    elements
  };
}

function context(id = 77, capabilities = {}) {
  return {
    church: { id },
    membership: { user_id: 123, role: "member" },
    capabilities: {
      can_manage_content: false,
      can_manage_pastoral_care: false,
      ...capabilities
    }
  };
}

test("reset clears church-scoped sections and records", async () => {
  const { controller, elements } = environment(
    async (url) => response(
      url.endsWith("/prayers")
        ? { prayers: [{ id: 1, message: "Private prayer" }] }
        : { testimonies: [] }
    )
  );

  await controller.init(context());
  controller.reset();

  assert.equal(elements.churchPrayerSection.hidden, true);
  assert.equal(elements.churchTestimonySection.hidden, true);
  assert.equal(elements.churchPrayerList.innerHTML, "");
  assert.equal(elements.churchTestimonyList.innerHTML, "");
});

test("late prayer response cannot restore data after reset", async () => {
  const pending = deferred();
  const { controller, elements } = environment(
    async (url) => url.endsWith("/prayers")
      ? pending.promise
      : response({ testimonies: [] })
  );

  const loading = controller.init(context());
  await Promise.resolve();
  controller.reset();
  pending.resolve(response({
    prayers: [{ id: 1, message: "Old church prayer" }]
  }));
  await loading;

  assert.equal(elements.churchPrayerList.innerHTML, "");
  assert.equal(elements.churchPrayerSection.hidden, true);
});

test("late testimony response cannot restore data after reset", async () => {
  const pending = deferred();
  const { controller, elements } = environment(
    async (url) => url.endsWith("/testimonies")
      ? pending.promise
      : response({ prayers: [] })
  );

  const loading = controller.init(context());
  await Promise.resolve();
  controller.reset();
  pending.resolve(response({
    testimonies: [{ id: 1, testimony: "Old testimony" }]
  }));
  await loading;

  assert.equal(elements.churchTestimonyList.innerHTML, "");
});

test("reinitialization restores member sections without duplicate handlers", async () => {
  const { controller, elements } = environment(
    async (url) => response(
      url.endsWith("/prayers")
        ? { prayers: [] }
        : { testimonies: [] }
    )
  );

  await controller.init(context());
  controller.reset();
  await controller.init(context(88));

  assert.equal(elements.churchPrayerSection.hidden, false);
  assert.equal(elements.churchTestimonySection.hidden, false);
  assert.equal(
    elements.churchPrayerCreateButton.listeners.click.length,
    1
  );
  assert.equal(
    elements.churchPrayerForm.listeners.submit.length,
    1
  );
});


test("replaced Prayer Wall rebinds partial status action", async () => {
  const calls = [];
  const fetch = async (url, options = {}) => {
    calls.push({ url, options });

    if (url.endsWith("/prayers")) {
      return response({ prayers: [{
        id: 76,
        church_id: 77,
        user_id: 123,
        message: "Test prayer",
        status: "still_praying",
        visibility: "community"
      }] });
    }

    if (url.endsWith("/testimonies")) {
      return response({ testimonies: [] });
    }

    return response({});
  };

  const { controller, elements } = environment(fetch);

  await controller.init(context());

  const oldList = elements.churchPrayerList;

  // Simulate SPA router replacing the Church Space DOM.
  controller.reset();
  elements.churchPrayerList = element();

  await controller.init(context());

  const newList = elements.churchPrayerList;

  assert.notEqual(newList, oldList);
  assert.equal(newList.listeners.click.length, 1);

  const partialButton = {
    dataset: { prayerPartial: "76" }
  };

  await newList.listeners.click[0]({
    target: {
      closest(selector) {
        return selector === "[data-prayer-partial]"
          ? partialButton
          : null;
      }
    }
  });

  const patches = calls.filter(
    (call) => call.options.method === "PATCH"
  );

  assert.equal(patches.length, 1);
  assert.equal(
    patches[0].url,
    "/api/v1/churches/77/prayers/76/status"
  );
  assert.equal(
    JSON.parse(patches[0].options.body).status,
    "partially_answered"
  );
});

test("late pastoral-care list cannot restore records after reset", async () => {
  const pending = deferred();
  const { controller, elements } = environment(
    async (url) => {
      if (url.endsWith("/pastoral-care")) {
        return pending.promise;
      }
      if (url.endsWith("/pastoral-care-assignees")) {
        return response({ assignees: [] });
      }
      if (url.endsWith("/prayers")) {
        return response({ prayers: [] });
      }
      return response({ testimonies: [] });
    }
  );

  const loading = controller.init(context(77, {
    can_manage_pastoral_care: true
  }));

  await Promise.resolve();
  controller.reset();

  pending.resolve(response({
    cases: [{
      id: 999,
      status: "open",
      priority: "urgent",
      member_user_id: 123
    }]
  }));

  await loading;

  assert.equal(elements.churchPastoralCareList.innerHTML, "");
  assert.equal(elements.churchPastoralCareWorkspace.hidden, true);
});

test("late pastoral-care detail cannot reopen private notes", async () => {
  const pending = deferred();
  const { controller, elements } = environment(
    async (url) => {
      if (url.endsWith("/pastoral-care/999")) {
        return pending.promise;
      }
      if (url.endsWith("/pastoral-care")) {
        return response({ cases: [] });
      }
      if (url.endsWith("/pastoral-care-assignees")) {
        return response({ assignees: [] });
      }
      if (url.endsWith("/prayers")) {
        return response({ prayers: [] });
      }
      return response({ testimonies: [] });
    }
  );

  await controller.init(context(77, {
    can_manage_pastoral_care: true
  }));

  const opening = controller.loadCases();
  await opening;

  // Trigger the delegated click handler for a care record.
  const handlers = elements.churchPastoralCareList.listeners.click;
  assert.equal(handlers.length, 1);

  await handlers[0]({
    target: {
      closest(selector) {
        if (selector === "[data-care-open]") {
          return { dataset: { careOpen: "999" } };
        }
        return null;
      }
    }
  });

  controller.reset();

  pending.resolve(response({
    case: { id: 999, status: "open", priority: "urgent" },
    prayer: { message: "Confidential prayer" },
    notes: [{ body: "Private pastoral note" }],
    activities: []
  }));

  await Promise.resolve();
  await Promise.resolve();

  assert.equal(elements.churchPastoralCareDetail.hidden, true);
  assert.equal(elements.churchPastoralCareDetail.innerHTML, "");
});

test("ordinary member cannot request private pastoral-care detail", async () => {
  const calls = [];
  const { controller, elements } = environment(
    async (url) => {
      calls.push(url);
      if (url.endsWith("/prayers")) {
        return response({ prayers: [] });
      }
      return response({ testimonies: [] });
    }
  );

  await controller.init(context());

  const handlers = elements.churchPastoralCareList.listeners.click;
  assert.equal(handlers.length, 1);

  await handlers[0]({
    target: {
      closest(selector) {
        if (selector === "[data-care-open]") {
          return { dataset: { careOpen: "999" } };
        }
        return null;
      }
    }
  });

  await Promise.resolve();

  assert.equal(
    calls.some((url) => url.endsWith("/pastoral-care/999")),
    false
  );
});

test("late prayer submission cannot clear a new church form", async () => {
  const pending = deferred();
  const calls = [];

  const { controller, elements } = environment(
    async (url, options = {}) => {
      calls.push({ url, method: options.method || "GET" });

      if (options.method === "POST" && url.endsWith("/prayers")) {
        return pending.promise;
      }
      if (url.endsWith("/prayers")) {
        return response({ prayers: [] });
      }
      return response({ testimonies: [] });
    }
  );

  await controller.init(context(77));

  elements.churchPrayerMessage.value = "Original church prayer";

  const submit = elements.churchPrayerForm.listeners.submit[0]({
    preventDefault() {}
  });

  controller.reset();
  await controller.init(context(88));

  elements.churchPrayerMessage.value = "New church draft";
  elements.churchPrayerForm.hidden = false;

  pending.resolve(response({ id: 555 }));
  await submit;

  assert.equal(
    elements.churchPrayerMessage.value,
    "New church draft"
  );
  assert.equal(elements.churchPrayerForm.hidden, false);

  assert.equal(
    calls.some((call) =>
      call.method === "GET" &&
      call.url.includes("/churches/88/prayers") &&
      call.url.includes("555")
    ),
    false
  );
});

test("late moderation response cannot refresh another church", async () => {
  const pending = deferred();
  const calls = [];

  const { controller, elements } = environment(
    async (url, options = {}) => {
      calls.push({ url, method: options.method || "GET" });

      if (options.method === "PATCH" && url.includes("/testimonies/")) {
        return pending.promise;
      }
      if (url.endsWith("/prayers")) {
        return response({ prayers: [] });
      }
      return response({ testimonies: [] });
    }
  );

  await controller.init(context(77, {
    can_manage_content: true
  }));

  const handlers = elements.churchPendingTestimonyList.listeners.click;
  assert.equal(handlers.length, 1);

  const moderation = handlers[0]({
    target: {
      closest(selector) {
        if (selector === "[data-testimony-approve]") {
          return { dataset: { testimonyApprove: "123" } };
        }
        return null;
      }
    }
  });

  controller.reset();
  await controller.init(context(88));

  const countBefore = calls.length;
  pending.resolve(response({ ok: true }));
  await moderation;

  assert.equal(calls.length, countBefore);
});

test("ordinary member cannot send testimony moderation mutation", async () => {
  const calls = [];

  const { controller, elements } = environment(
    async (url, options = {}) => {
      calls.push({ url, method: options.method || "GET" });
      if (url.endsWith("/prayers")) {
        return response({ prayers: [] });
      }
      return response({ testimonies: [] });
    }
  );

  await controller.init(context(77));

  await elements.churchPendingTestimonyList.listeners.click[0]({
    target: {
      closest(selector) {
        if (selector === "[data-testimony-approve]") {
          return { dataset: { testimonyApprove: "123" } };
        }
        return null;
      }
    }
  });

  assert.equal(
    calls.some((call) => call.method === "PATCH"),
    false
  );
});

test("reset invalidates a pending prayer submission error", async () => {
  const pending = deferred();

  const { controller, elements } = environment(
    async (url, options = {}) => {
      if (options.method === "POST") {
        return pending.promise;
      }
      if (url.endsWith("/prayers")) {
        return response({ prayers: [] });
      }
      return response({ testimonies: [] });
    }
  );

  await controller.init(context(77));
  elements.churchPrayerMessage.value = "Original prayer";

  const submit = elements.churchPrayerForm.listeners.submit[0]({
    preventDefault() {}
  });

  controller.reset();
  await controller.init(context(88));

  pending.resolve({
    ok: false,
    json: async () => ({ detail: "Old church error" })
  });

  await submit;

  assert.notEqual(
    elements.churchPrayerFormState.textContent,
    "Old church error"
  );
});

test("late care-plan save cannot reopen a case in another church", async () => {
  const pending = deferred();
  const calls = [];

  const { controller, elements } = environment(
    async (url, options = {}) => {
      calls.push({ url, method: options.method || "GET" });

      if (
        options.method === "PATCH" &&
        url.endsWith("/pastoral-care/999")
      ) {
        return pending.promise;
      }
      if (url.endsWith("/pastoral-care/999")) {
        return response({
          case: { id: 999, status: "open", priority: "routine" },
          prayer: { message: "Care request" },
          notes: [],
          activities: []
        });
      }
      if (url.endsWith("/pastoral-care-assignees")) {
        return response({ assignees: [] });
      }
      if (url.endsWith("/pastoral-care")) {
        return response({ cases: [] });
      }
      if (url.endsWith("/prayers")) {
        return response({ prayers: [] });
      }
      return response({ testimonies: [] });
    }
  );

  await controller.init(context(77, {
    can_manage_pastoral_care: true
  }));

  elements.churchPastoralCareList.listeners.click[0]({
    target: {
      closest(selector) {
        return selector === "[data-care-open]"
          ? { dataset: { careOpen: "999" } }
          : null;
      }
    }
  });

  await Promise.resolve();
  await Promise.resolve();

  const saveHandler = await waitForHandler(
    elements.churchCareSave,
    "churchCareSave"
  );

  const save = saveHandler();

  controller.reset();
  await controller.init(context(88, {
    can_manage_pastoral_care: true
  }));

  const before = calls.length;
  pending.resolve(response({ ok: true }));
  await save;

  assert.equal(calls.length, before);
  assert.equal(elements.churchPastoralCareDetail.hidden, true);
});

test("late private-note submission cannot reopen an old care record", async () => {
  const pending = deferred();
  const calls = [];

  const { controller, elements } = environment(
    async (url, options = {}) => {
      calls.push({ url, method: options.method || "GET" });

      if (
        options.method === "POST" &&
        url.endsWith("/pastoral-care/999/notes")
      ) {
        return pending.promise;
      }
      if (url.endsWith("/pastoral-care/999")) {
        return response({
          case: { id: 999, status: "open", priority: "routine" },
          prayer: { message: "Care request" },
          notes: [],
          activities: []
        });
      }
      if (url.endsWith("/pastoral-care-assignees")) {
        return response({ assignees: [] });
      }
      if (url.endsWith("/pastoral-care")) {
        return response({ cases: [] });
      }
      if (url.endsWith("/prayers")) {
        return response({ prayers: [] });
      }
      return response({ testimonies: [] });
    }
  );

  await controller.init(context(77, {
    can_manage_pastoral_care: true
  }));

  elements.churchPastoralCareList.listeners.click[0]({
    target: {
      closest(selector) {
        return selector === "[data-care-open]"
          ? { dataset: { careOpen: "999" } }
          : null;
      }
    }
  });

  await Promise.resolve();
  await Promise.resolve();

  assert.ok(elements.churchCareNoteBody);
  elements.churchCareNoteBody.value = "Private note";

  const noteHandler = await waitForHandler(
    elements.churchCareAddNote,
    "churchCareAddNote"
  );

  const addNote = noteHandler();

  controller.reset();
  await controller.init(context(88, {
    can_manage_pastoral_care: true
  }));

  const before = calls.length;
  pending.resolve(response({ ok: true }));
  await addNote;

  assert.equal(calls.length, before);
  assert.equal(elements.churchPastoralCareDetail.hidden, true);
});

test("permission downgrade removes previously rendered private care details", async () => {
  const { controller, elements } = environment(async (url) => {
    if (url.endsWith("/pastoral-care/999")) {
      return response({
        case: { id: 999, status: "open", priority: "routine" },
        prayer: { message: "Confidential care request" },
        notes: [{ id: 1, body: "Sensitive pastoral note" }],
        activities: []
      });
    }
    if (url.endsWith("/pastoral-care-assignees")) {
      return response({ assignees: [] });
    }
    if (url.endsWith("/pastoral-care")) {
      return response({ cases: [] });
    }
    if (url.endsWith("/prayers")) {
      return response({ prayers: [] });
    }
    return response({ testimonies: [] });
  });

  await controller.init(context(77, {
    can_manage_pastoral_care: true
  }));

  elements.churchPastoralCareList.listeners.click[0]({
    target: {
      closest(selector) {
        return selector === "[data-care-open]"
          ? { dataset: { careOpen: "999" } }
          : null;
      }
    }
  });

  await waitForHandler(
    elements.churchCareSave,
    "churchCareSave"
  );

  assert.match(
    elements.churchPastoralCareDetail.innerHTML,
    /Sensitive pastoral note/
  );

  const transition = controller.init(context(77, {
    can_manage_pastoral_care: false
  }));

  // Cleanup must occur synchronously, before new reads finish.
  assert.equal(elements.churchPastoralCareDetail.hidden, true);
  assert.equal(elements.churchPastoralCareDetail.innerHTML, "");
  assert.equal(elements.churchPastoralCareWorkspace.hidden, true);

  await transition;
});

test("permission downgrade clears pending testimony moderation markup", async () => {
  const { controller, elements } = environment(async (url) => {
    if (url.endsWith("/testimonies/pending")) {
      return response({
        testimonies: [{
          id: 123,
          prayer_id: 123,
          answer_testimony: "Pending private testimony",
          status: "pending"
        }]
      });
    }
    if (url.endsWith("/prayers")) {
      return response({ prayers: [] });
    }
    return response({ testimonies: [] });
  });

  await controller.init(context(77, {
    can_manage_content: true
  }));

  // Confirm privileged moderation controls exist before downgrade.
  assert.match(
    elements.churchPendingTestimonyList.innerHTML,
    /data-testimony-approve="123"/
  );
  assert.match(
    elements.churchPendingTestimonyList.innerHTML,
    /data-testimony-reject="123"/
  );

  const transition = controller.init(context(77, {
    can_manage_content: false
  }));

  assert.equal(elements.churchPendingTestimonyList.innerHTML, "");
  assert.equal(elements.churchTestimonyModeration.hidden, true);

  await transition;
});
