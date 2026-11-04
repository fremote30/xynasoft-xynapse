const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync(
  "ui-faith-v2-unified/js/church-intelligence-v2.js",
  "utf8"
);

function makeElement() {
  return {
    hidden: false,
    textContent: "",
    className: "",
    children: [],
    append(...items) {
      this.children.push(...items);
    },
    appendChild(item) {
      this.children.push(item);
    },
    replaceChildren(...items) {
      this.children = [...items];
    }
  };
}

function harness(apiFetch) {
  const elements = {
    churchAnalyticsCard: makeElement(),
    churchIntelligenceState: makeElement(),
    churchIntelligenceMetrics: makeElement()
  };

  const context = {
    window: { apiFetch },
    document: {
      getElementById(id) {
        return elements[id] || null;
      },
      createElement() {
        return makeElement();
      }
    },
    console: { error() {} }
  };

  vm.runInNewContext(source, context);

  return {
    elements,
    load: context.window.loadChurchIntelligenceV2
  };
}

test("renders nested backend intelligence metrics", async () => {
  const calls = [];

  const app = harness(async url => {
    calls.push(url);

    return {
      ok: true,
      status: 200,
      async json() {
        return {
          church_id: 7,
          members: { active: 120 },
          ministry: {
            published_announcements: 8,
            upcoming_events: 3
          },
          groups: { active: 6 },
          pastoral_care: {
            active_cases: 4,
            overdue_follow_ups: 2
          }
        };
      }
    };
  });

  await app.load(7);

  assert.deepEqual(calls, [
    "/api/v1/churches/7/intelligence/summary"
  ]);

  const container = app.elements.churchIntelligenceMetrics;

  assert.equal(container.hidden, false);
  assert.equal(container.children.length, 6);

  const values = container.children.map(
    card => card.children[0].textContent
  );

  assert.deepEqual(values, [
    "120", "8", "3", "6", "4", "2"
  ]);
});

test("denied entitlement does not render metrics", async () => {
  const app = harness(async () => ({
    ok: false,
    status: 403
  }));

  await app.load(7);

  assert.equal(
    app.elements.churchIntelligenceMetrics.children.length,
    0
  );

  assert.match(
    app.elements.churchIntelligenceState.textContent,
    /eligible plan/i
  );
});

test("network failure displays a safe error", async () => {
  const app = harness(async () => {
    throw new Error("Network unavailable");
  });

  await app.load(7);

  assert.match(
    app.elements.churchIntelligenceState.textContent,
    /could not be loaded/i
  );
});

test("invalid church ID does not trigger an API call", async () => {
  let calls = 0;

  const app = harness(async () => {
    calls++;
    throw new Error("Unexpected API call");
  });

  await app.load(-1);

  assert.equal(calls, 0);
});

test("missing nested metrics produce an empty state", async () => {
  const app = harness(async () => ({
    ok: true,
    status: 200,
    async json() {
      return { members: {}, ministry: {} };
    }
  }));

  await app.load(7);

  assert.equal(
    app.elements.churchIntelligenceMetrics.hidden,
    true
  );

  assert.match(
    app.elements.churchIntelligenceState.textContent,
    /no summary metrics/i
  );
});
