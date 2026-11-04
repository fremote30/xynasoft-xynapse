const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../../ui-faith-v2-unified/js");
const spaceSource = fs.readFileSync(
  path.join(root, "church-space.js"), "utf8"
);
const careSource = fs.readFileSync(
  path.join(root, "church-prayer-care.js"), "utf8"
);

function createHarness(response) {
  const calls = [];
  const initializations = [];
  const elements = new Map();

  const document = {
    createElement() {
      return {
        _text: "",
        set textContent(value) {
          this._text = String(value);
        },
        get textContent() {
          return this._text;
        },
        get innerHTML() {
          return this._text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
        }
      };
    },
    getElementById(id) {
      if (!elements.has(id)) {
        elements.set(id, {
          hidden: true,
          textContent: "",
          innerHTML: "",
          value: "",
          dataset: {},
          addEventListener() {},
          querySelector() { return null; },
          querySelectorAll() { return []; },
          replaceChildren() {},
          appendChild() {},
          classList: {
            add() {},
            remove() {},
            toggle() {}
          }
        });
      }
      return elements.get(id);
    }
  };

  const window = {
    apiFetch: async (url) => {
      calls.push(url);

      if (url === "/api/v1/churches/mine") {
        return response;
      }

      return {
        ok: true,
        status: 200,
        json: async () => []
      };
    },
    XynaFaithChurchPrayerCare: {
      async init(data) {
        initializations.push(data);
      }
    }
  };

  const context = vm.createContext({
    window,
    document,
    console: {
      log() {},
      error() {},
      warn() {}
    },
    setTimeout,
    clearTimeout
  });

  vm.runInContext(spaceSource, context, {
    filename: "church-space.js"
  });

  return { window, calls, initializations };
}

const churchContext = {
  church: {
    id: 42,
    name: "Test Church"
  },
  membership: {
    user_id: 7,
    role: "member"
  },
  capabilities: {
    can_create_content: false,
    can_manage_content: false,
    can_manage_pastoral_care: false,
    can_view_analytics: false,
    can_view_members: false
  }
};

test("Church Space passes authenticated context to Prayer/Care", async () => {
  const harness = createHarness({
    ok: true,
    status: 200,
    json: async () => churchContext
  });

  await harness.window.loadChurchSpace();

  assert.equal(harness.initializations.length, 1);
  assert.equal(harness.initializations[0], churchContext);

  assert.equal(
    harness.calls.filter(
      url => url === "/api/v1/churches/mine"
    ).length,
    1
  );
});

test("failed Church Space request never initializes Prayer/Care", async () => {
  const harness = createHarness({
    ok: false,
    status: 500,
    json: async () => ({})
  });

  await harness.window.loadChurchSpace();

  assert.equal(harness.initializations.length, 0);
});

test("Prayer/Care requires coordinator-provided context", () => {
  assert.match(
    careSource,
    /async function init\(data\)/
  );

  assert.doesNotMatch(
    careSource,
    /api\(["']\/api\/v1\/churches\/mine["']\)/
  );

  assert.doesNotMatch(
    careSource,
    /\n\s*init\(\);\s*\n/
  );
});

test("privileged Church Space capabilities remain checked", () => {
  assert.match(
    spaceSource,
    /capabilities\.can_manage_pastoral_care/
  );

  assert.match(
    spaceSource,
    /capabilities\.can_view_analytics/
  );

  assert.match(
    spaceSource,
    /capabilities\.can_view_members/
  );

  assert.match(
    careSource,
    /state\.capabilities\.can_manage_pastoral_care/
  );

  assert.match(
    careSource,
    /state\.capabilities\.can_manage_content/
  );
});
