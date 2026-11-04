const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync(
  "ui-faith-v2/js/app.js",
  "utf8"
);

function setup({ token = "test-token", responses = [] } = {}) {
  const elements = new Map();
  const handlers = {};
  const requests = [];

  function element(id) {
    if (!elements.has(id)) {
      elements.set(id, {
        value: "",
        hidden: false,
        disabled: false,
        textContent: "",
        children: [],
        append(...items) {
          this.children.push(...items);
        },
        replaceChildren(...items) {
          this.children = [...items];
        },
        add(item) {
          this.children.push(item);
        },
        addEventListener(event, callback) {
          handlers[`${id}:${event}`] = callback;
        },
        querySelectorAll() {
          return this.children
            .flatMap(item => item.children || [])
            .filter(item => item.checked);
        }
      });
    }
    return elements.get(id);
  }

  const document = {
    getElementById: element,
    createElement(tag) {
      return {
        tag,
        children: [],
        checked: false,
        append(...items) {
          this.children.push(...items);
        }
      };
    },
    createTextNode(text) {
      return { text };
    },
    addEventListener(event, callback) {
      handlers[event] = callback;
    }
  };

  const storage = {
    getItem: () => token,
    setItem: (key, value) => {
      token = value;
    },
    removeItem: () => {
      token = null;
    }
  };

  const context = {
    document,
    window: {
      crypto: {
        randomUUID: () =>
          "11111111-1111-4111-8111-111111111111"
      }
    },
    sessionStorage: storage,
    Option: function(label, value) {
      return { label, value };
    },
    fetch: async (url, options) => {
      requests.push({ url, options });
      const next = await responses.shift();

      if (!next) {
        throw new Error("Unexpected fetch");
      }

      return {
        ok: next.status >= 200 && next.status < 300,
        status: next.status,
        json: async () => next.body
      };
    }
  };

  vm.runInNewContext(source, context);
  handlers.DOMContentLoaded();

  return { element, handlers, requests, storage };
}

test("saved sermons require authentication", async () => {
  const browser = setup({ token: null });

  await Promise.resolve();
  await Promise.resolve();

  assert.equal(browser.requests.length, 0);
});

test("sermon list uses authenticated endpoint", async () => {
  const browser = setup({
    responses: [
      {
        status: 200,
        body: { id: 1, email: "pastor@example.com" }
      },
      {
        status: 200,
        body: [{ id: 42, title: "Grace" }]
      }
    ]
  });

  await new Promise(resolve => setImmediate(resolve));

  assert.equal(
    browser.requests[1].url,
    "/api/v1/faith/sermon/my"
  );

  assert.equal(
    browser.requests[1].options.headers.Authorization,
    "Bearer test-token"
  );
});

test("client script never supplies trusted sermon source", () => {
  assert.equal(
    source.includes("source_content:"),
    false
  );

  assert.equal(
    source.includes("external_user_id:"),
    false
  );
});

test("AI output is rendered as text, not HTML", () => {
  assert.match(source, /content\.textContent\s*=/);
  assert.doesNotMatch(source, /\.innerHTML\s*=/);
});

test("uncertain requests preserve retry identity", () => {
  assert.match(source, /request_id:\s*pending\.requestId/);
  assert.match(source, /pending\.sermonId !== sermonId/);
  assert.match(source, /An earlier request is uncertain/);
});

test("generates a content pack from a saved sermon", async () => {
  const requestId =
    "11111111-1111-4111-8111-111111111111";

  const browser = setup({
    responses: [
      {
        status: 200,
        body: { id: 1, email: "pastor@example.com" }
      },
      {
        status: 200,
        body: [{ id: 42, title: "Grace" }]
      },
      {
        status: 200,
        body: {
          request_id: requestId,
          sermon_id: 42,
          result: {
            pieces: [
              {
                format: "whatsapp_summary",
                title: "WhatsApp Summary",
                content: "Grace for everyone"
              },
              {
                format: "discussion_questions",
                title: "Discussion Questions",
                content: "What is grace?"
              }
            ]
          }
        }
      }
    ]
  });

  await new Promise(resolve => setImmediate(resolve));

  browser.element("sermonSelect").value = "42";
  await browser.handlers["generatePack:click"]();

  await new Promise(resolve => setImmediate(resolve));

  const request = browser.requests[2];

  assert.equal(
    request.url,
    "/api/v1/faith/ministry/sermons/42/transform"
  );

  const payload = JSON.parse(request.options.body);

  assert.equal(payload.request_id, requestId);
  assert.deepEqual(
    payload.formats,
    ["whatsapp_summary", "discussion_questions"]
  );

  assert.equal(payload.source_content, undefined);
  assert.equal(browser.element("resultsPanel").hidden, false);
  assert.match(
    browser.element("status").textContent,
    /ready/
  );
});

async function flush() {
  await new Promise(resolve => setImmediate(resolve));
}

test("uncertain execution retries with the same request ID", async () => {
  const requestId =
    "11111111-1111-4111-8111-111111111111";

  const browser = setup({
    responses: [
      {
        status: 200,
        body: { id: 1, email: "pastor@example.com" }
      },
      {
        status: 200,
        body: [{ id: 42, title: "Grace" }]
      },
      {
        status: 503,
        body: {
          detail:
            "Ministry request status is uncertain; retry with the same request ID"
        }
      },
      {
        status: 200,
        body: {
          request_id: requestId,
          sermon_id: 42,
          result: {
            pieces: [
              {
                format: "whatsapp_summary",
                content: "Grace for everyone"
              },
              {
                format: "discussion_questions",
                content: "What is grace?"
              }
            ]
          }
        }
      }
    ]
  });

  await flush();

  browser.element("sermonSelect").value = "42";
  browser.handlers["generatePack:click"]();

  await flush();

  assert.equal(browser.element("retryPack").hidden, false);

  browser.handlers["retryPack:click"]();

  await flush();

  const first = JSON.parse(browser.requests[2].options.body);
  const second = JSON.parse(browser.requests[3].options.body);

  assert.deepEqual(second, first);
  assert.equal(first.request_id, requestId);
  assert.equal(browser.element("resultsPanel").hidden, false);
  assert.equal(browser.element("retryPack").hidden, true);
});

test("successful login opens the authenticated studio", async () => {
  const browser = setup({
    token: null,
    responses: [
      { status: 200, body: { access_token: "new-token" } },
      { status: 200, body: { id: 1, email: "pastor@example.com" } },
      { status: 200, body: [{ id: 42, title: "Grace" }] }
    ]
  });

  browser.element("loginEmail").value = "pastor@example.com";
  browser.element("loginPassword").value = "password";

  await browser.handlers["loginForm:submit"]({
    preventDefault() {}
  });

  assert.equal(browser.requests[0].url, "/auth/login");
  assert.equal(browser.requests[1].url, "/auth/me");
  assert.equal(browser.requests[2].url, "/api/v1/faith/sermon/my");
  assert.equal(browser.storage.getItem(), "new-token");
  assert.equal(browser.element("studioWorkspace").hidden, false);
  assert.equal(browser.element("loginPanel").hidden, true);
});

test("invalid credentials do not create a session", async () => {
  const browser = setup({
    token: null,
    responses: [
      { status: 401, body: { detail: "Invalid credentials" } }
    ]
  });

  browser.element("loginEmail").value = "pastor@example.com";
  browser.element("loginPassword").value = "wrong-password";

  await browser.handlers["loginForm:submit"]({
    preventDefault() {}
  });

  assert.equal(browser.storage.getItem(), null);
  assert.equal(browser.element("studioWorkspace").hidden, true);
  assert.match(
    browser.element("loginStatus").textContent,
    /invalid email or password/i
  );
});

test("expired sessions return users to login", async () => {
  const browser = setup({
    responses: [
      { status: 401, body: { detail: "Invalid token" } }
    ]
  });

  await flush();

  assert.equal(browser.storage.getItem(), null);
  assert.equal(browser.element("studioWorkspace").hidden, true);
  assert.equal(browser.element("loginPanel").hidden, false);
});

test("sign-out clears only the V2 session", async () => {
  const browser = setup({
    responses: [
      { status: 200, body: { id: 1 } },
      { status: 200, body: [] }
    ]
  });

  await flush();

  browser.handlers["signOut:click"]();

  assert.equal(browser.storage.getItem(), null);
  assert.equal(browser.element("studioWorkspace").hidden, true);
  assert.equal(browser.element("loginPanel").hidden, false);
});

test("sign-out during generation discards the late AI response", async () => {
  let releaseGeneration;

  const delayedResponse = new Promise(resolve => {
    releaseGeneration = resolve;
  });

  const browser = setup({
    responses: [
      { status: 200, body: { id: 1 } },
      { status: 200, body: [{ id: 42, title: "Grace" }] },
      delayedResponse
    ]
  });

  await flush();

  browser.element("sermonSelect").value = "42";

  const generation = browser.handlers["generatePack:click"]();

  await flush();

  browser.handlers["signOut:click"]();

  releaseGeneration({
    status: 200,
    body: {
      request_id: "11111111-1111-4111-8111-111111111111",
      sermon_id: 42,
      result: {
        pieces: [
          {
            format: "whatsapp_summary",
            content: "Private sermon summary"
          },
          {
            format: "discussion_questions",
            content: "Private discussion questions"
          }
        ]
      }
    }
  });

  await generation;
  await flush();

  assert.equal(browser.storage.getItem(), null);
  assert.equal(browser.element("studioWorkspace").hidden, true);
  assert.equal(browser.element("resultsPanel").hidden, true);
  assert.equal(browser.element("results").children.length, 0);
});

test("sign-out during sermon loading discards the late list", async () => {
  let releaseSermons;

  const delayedSermons = new Promise(resolve => {
    releaseSermons = resolve;
  });

  const browser = setup({
    responses: [
      { status: 200, body: { id: 1 } },
      delayedSermons
    ]
  });

  // Allow session validation to finish and sermon loading to begin.
  await flush();
  await flush();

  assert.equal(
    browser.requests[1].url,
    "/api/v1/faith/sermon/my"
  );

  browser.handlers["signOut:click"]();

  releaseSermons({
    status: 200,
    body: [{ id: 42, title: "Private Sermon" }]
  });

  await flush();
  await flush();

  const options = browser.element("sermonSelect").children;

  assert.equal(browser.storage.getItem(), null);
  assert.equal(browser.element("studioWorkspace").hidden, true);
  assert.equal(options.length, 1);
  assert.equal(options[0].value, "");
  assert.equal(browser.element("status").textContent, "");
});
