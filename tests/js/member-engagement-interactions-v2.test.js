"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.resolve(
    __dirname,
    "../../ui-faith-v2-unified/js/member-engagement-v2.js"
  ),
  "utf8"
);

class Element {
  constructor(tag = "div") {
    this.tagName = tag;
    this.children = [];
    this.textContent = "";
    this.className = "";
    this.value = "";
    this.disabled = false;
    this.listeners = {};
    this.dataset = {};
  }

  append(...nodes) {
    this.children.push(...nodes);
  }

  replaceChildren(...nodes) {
    this.children = [...nodes];
  }

  addEventListener(name, callback) {
    this.listeners[name] = callback;
  }

  querySelector() {
    return new Element("button");
  }

  focus() {}

  reset() {
    this.value = "";
  }
}

function harness(responses) {
  const elements = new Map();
  const calls = [];

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

      const result = responses[url];

      if (!result) {
        return {
          ok: false,
          status: 404,
          json: async () => ({detail: "Not found"})
        };
      }

      return {
        ok: true,
        status: 200,
        json: async () => result
      };
    }
  };

  const context = vm.createContext({
    window,
    document: {
      getElementById(id) {
        return elements.get(id) || null;
      },
      createElement(tag) {
        return new Element(tag);
      }
    },
    console,
    alert() {},
    confirm() { return true; }
  });

  vm.runInContext(source, context);

  return {window, elements, calls};
}

test("reading plans load from authenticated member endpoints", async () => {
  const h = harness({
    "/api/v1/member/reading-plans": {
      reading_plans: [{
        id: 1,
        title: "Daily Scripture",
        duration_days: 7
      }]
    },
    "/api/v1/member/reading-plans/mine": {
      reading_plans: []
    }
  });

  await h.window.initMemberReadingPlansV2();

  assert.deepEqual(
    h.calls.map(call => call.url),
    [
      "/api/v1/member/reading-plans",
      "/api/v1/member/reading-plans/mine"
    ]
  );

  assert.equal(
    h.elements.get("memberAvailablePlans").children.length,
    1
  );
});

test("sermon notes load and render without HTML injection", async () => {
  const h = harness({
    "/api/v1/member/sermon-notes": {
      notes: [{
        id: 10,
        title: "<script>alert(1)</script>",
        body: "Personal reflection"
      }]
    }
  });

  await h.window.initMemberSermonNotesV2();

  const list = h.elements.get("memberNotesList");
  assert.equal(list.children.length, 1);

  const card = list.children[0];
  assert.equal(
    card.children[0].textContent,
    "<script>alert(1)</script>"
  );
});

test("sermon note submission sends expected payload", async () => {
  const h = harness({
    "/api/v1/member/sermon-notes": {notes: []}
  });

  await h.window.initMemberSermonNotesV2();

  h.elements.get("memberNoteTitle").value = "Sunday Message";
  h.elements.get("memberNoteBody").value = "Faith and service";

  const form = h.elements.get("memberNoteForm");
  await form.listeners.submit({
    preventDefault() {}
  });

  const post = h.calls.find(
    call => call.options.method === "POST"
  );

  assert.ok(post);
  assert.equal(
    JSON.parse(post.options.body).title,
    "Sunday Message"
  );
  assert.equal(
    JSON.parse(post.options.body).body,
    "Faith and service"
  );
});
