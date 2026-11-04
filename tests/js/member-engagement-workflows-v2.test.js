"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.resolve(__dirname,
    "../../ui-faith-v2-unified/js/member-engagement-v2.js"),
  "utf8"
);

class Element {
  constructor(tag = "div") {
    this.tagName = tag;
    this.children = [];
    this.textContent = "";
    this.className = "";
    this._value = "";
    this.disabled = false;
    this.dataset = {};
    this.listeners = {};
  }

  get value() {
    return this._value;
  }

  set value(next) {
    this._value = String(next);
  }

  querySelector(selector) {
    if (
      typeof selector === "string" &&
      (
        selector.includes("submit") ||
        selector.includes("button")
      )
    ) {
      if (!this._submitButton) {
        this._submitButton = new Element("button");
      }
      return this._submitButton;
    }
    return null;
  }

  append(...nodes) {
    this.children.push(...nodes);
  }

  appendChild(node) {
    this.children.push(node);
    return node;
  }

  replaceChildren(...nodes) {
    this.children = [...nodes];
  }

  addEventListener(event, handler) {
    this.listeners[event] = handler;
  }

  async click() {
    if (this.listeners.click) {
      return await this.listeners.click({
        preventDefault() {}
      });
    }
  }

  reset() {
    this.value = "";
  }

  focus() {}
}

function harness(handler) {
  const elements = new Map();
  const calls = [];
  const alerts = [];

  for (const id of [
    "memberAvailablePlans",
    "memberEnrolledPlans",
    "memberNotesList",
    "memberNoteForm",
    "memberNoteId",
    "memberNoteTitle",
    "memberNoteBody",
    "memberNoteStatus",
    "memberNoteClear"
  ]) {
    elements.set(id, new Element());
  }

  const window = {
    apiFetch: async (url, options = {}) => {
      calls.push({url, options});

      const result = await handler(url, options);

      if (result && result.response) {
        return result.response;
      }

      return {
        ok: !(result && result.error),
        status: result && result.error ? 500 : 200,
        json: async () => result && result.error
          ? {detail: result.error}
          : (result || {})
      };
    }
  };

  const context = vm.createContext({
    window,
    document: {
      getElementById: id => elements.get(id) || null,
      createElement: tag => new Element(tag)
    },
    console,
    alert: message => alerts.push(message),
    confirm: () => true
  });

  vm.runInContext(source, context);

  return {window, elements, calls, alerts};
}

function descendants(element) {
  return [
    element,
    ...element.children.flatMap(descendants)
  ];
}

function buttons(element) {
  return descendants(element).filter(
    item => item.tagName === "button"
  );
}

const plan = {
  id: 7,
  title: "Seven Days of Faith",
  description: "Daily Bible reflection",
  duration_days: 7
};

const enrollment = {
  id: 19,
  plan: {id: 7, title: plan.title},
  days: [{
    id: 23,
    day_number: 1,
    title: "Faith",
    scripture: "Hebrews 11:1",
    reflection: "Trust God",
    completed: false
  }],
  completed_days: 0,
  total_days: 7
};

test("member can start a reading plan", async () => {
  const h = harness((url, options) => {
    if (url.endsWith("/reading-plans/mine")) {
      return {reading_plans: []};
    }
    if (url.endsWith("/reading-plans/7/start")) {
      return enrollment;
    }
    return {reading_plans: [plan]};
  });

  await h.window.initMemberReadingPlansV2();

  const actions = buttons(
    h.elements.get("memberAvailablePlans")
  );

  assert.ok(actions.length, "Start action not rendered");
  await actions[0].click();

  assert.ok(
    h.calls.some(c =>
      c.url.endsWith("/reading-plans/7/start") &&
      c.options.method === "POST"
    ),
    "Expected enrollment POST request"
  );
});

test("member can mark a reading day completed", async () => {
  const h = harness((url, options) => {
    if (url.endsWith("/reading-plans/mine")) {
      return {reading_plans: [enrollment]};
    }
    if (url.includes("/days/23")) {
      return enrollment;
    }
    return {reading_plans: []};
  });

  await h.window.initMemberReadingPlansV2();

  const actions = buttons(
    h.elements.get("memberEnrolledPlans")
  );

  assert.ok(actions.length, "Reading day action not rendered");
  await actions[0].click();

  const patch = h.calls.find(c => c.options.method === "PATCH");

  assert.ok(patch, "Expected progress PATCH");
  assert.equal(JSON.parse(patch.options.body).completed, true);
});

test("member can undo reading completion", async () => {
  const completed = {
    ...enrollment,
    days: [{...enrollment.days[0], completed: true}]
  };

  const h = harness((url) => {
    if (url.endsWith("/reading-plans/mine")) {
      return {reading_plans: [completed]};
    }
    if (url.includes("/days/23")) {
      return completed;
    }
    return {reading_plans: []};
  });

  await h.window.initMemberReadingPlansV2();

  const actions = buttons(
    h.elements.get("memberEnrolledPlans")
  );

  assert.ok(actions.length);
  await actions[0].click();

  const patch = h.calls.find(c => c.options.method === "PATCH");

  assert.ok(patch);
  assert.equal(JSON.parse(patch.options.body).completed, false);
});

test("member can load an existing sermon note for editing", async () => {
  const h = harness(() => ({
    notes: [{
      id: 42,
      title: "Sunday Reflection",
      body: "Serve with compassion"
    }]
  }));

  await h.window.initMemberSermonNotesV2();

  const actions = buttons(
    h.elements.get("memberNotesList")
  );

  assert.ok(actions.length, "Edit action missing");
  await actions[0].click();

  assert.equal(h.elements.get("memberNoteId").value, "42");
  assert.equal(
    h.elements.get("memberNoteTitle").value,
    "Sunday Reflection"
  );
});

test("member can save edits to a sermon note", async () => {
  const h = harness(() => ({notes: []}));

  await h.window.initMemberSermonNotesV2();

  h.elements.get("memberNoteId").value = "42";
  h.elements.get("memberNoteTitle").value = "Updated Reflection";
  h.elements.get("memberNoteBody").value = "New insight";

  await h.elements.get("memberNoteForm")
    .listeners.submit({preventDefault() {}});

  const patch = h.calls.find(c => c.options.method === "PATCH");

  assert.ok(patch);
  assert.ok(patch.url.endsWith("/sermon-notes/42"));
  assert.equal(
    JSON.parse(patch.options.body).body,
    "New insight"
  );
});

test("member can delete a sermon note", async () => {
  const h = harness(() => ({
    notes: [{
      id: 42,
      title: "Delete Me",
      body: "Old reflection"
    }]
  }));

  await h.window.initMemberSermonNotesV2();

  const actions = buttons(
    h.elements.get("memberNotesList")
  );

  assert.ok(actions.length >= 2, "Delete action missing");
  await actions[1].click();

  assert.ok(
    h.calls.some(c =>
      c.options.method === "DELETE" &&
      c.url.endsWith("/sermon-notes/42")
    )
  );
});

test("reading plans handle API failures without crashing", async () => {
  const h = harness(() => ({error: "Service unavailable"}));

  await assert.doesNotReject(
    h.window.initMemberReadingPlansV2()
  );
});

test("sermon notes handle API failures without crashing", async () => {
  const h = harness(() => ({error: "Service unavailable"}));

  await assert.doesNotReject(
    h.window.initMemberSermonNotesV2()
  );
});
