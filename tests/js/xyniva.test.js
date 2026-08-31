const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const MODULE_PATH = path.resolve(
  __dirname,
  "../../ui-faith/js/xyniva.js"
);

function element(overrides = {}) {
  const children = [];

  return {
    value: "",
    textContent: "",
    innerHTML: "",
    disabled: false,
    hidden: false,
    style: {},
    dataset: {},
    children,
    classList: {
      add() {},
      remove() {},
      toggle() {}
    },
    addEventListener() {},
    appendChild(child) {
      children.push(child);
      return child;
    },
    focus() {},
    ...overrides
  };
}

function setup(options = {}) {
  const elements = {
    xynivaForm: element(),
    xynivaInput: element(),
    xynivaSend: element(),
    xynivaMessages: element(),
    xynivaWelcome: element()
  };

  global.document = {
    getElementById(id) {
      return elements[id] || null;
    },
    querySelectorAll() {
      return [];
    },
    createElement() {
      return element();
    }
  };

  global.window = {
    XynivaConversation:
      options.client || {
        async create() {
          return {
            id: "conversation-1"
          };
        },

        async turn() {
          return {
            assistant_message: {
              content: "Generated response"
            }
          };
        }
      }
  };

  delete require.cache[MODULE_PATH];
  require(MODULE_PATH);

  return {
    elements,
    api: global.window.XynivaUI
  };
}

test("exposes Xyniva UI controller", () => {
  const { api } = setup();

  assert.equal(
    typeof api,
    "object"
  );

  assert.equal(
    typeof api.send,
    "function"
  );
});

test("first message creates a conversation before sending turn", async () => {
  const calls = [];

  const { api } = setup({
    client: {
      async create() {
        calls.push("create");

        return {
          id: "conversation-42"
        };
      },

      async turn(id, content) {
        calls.push([
          "turn",
          id,
          content
        ]);

        return {
          assistant_message: {
            content: "Here is your sermon."
          }
        };
      }
    }
  });

  await api.send(
    "Create a Pentecostal sermon on Proverbs 3."
  );

  assert.deepEqual(
    calls,
    [
      "create",
      [
        "turn",
        "conversation-42",
        "Create a Pentecostal sermon on Proverbs 3."
      ]
    ]
  );

  assert.equal(
    api.getConversationId(),
    "conversation-42"
  );
});

test("follow-up reuses the same conversation", async () => {
  let creates = 0;
  const turns = [];

  const { api } = setup({
    client: {
      async create() {
        creates += 1;

        return {
          id: "conversation-7"
        };
      },

      async turn(id, content) {
        turns.push({
          id,
          content
        });

        return {
          assistant_message: {
            content: "Updated sermon."
          }
        };
      }
    }
  });

  await api.send(
    "Create a sermon on Proverbs 3."
  );

  await api.send(
    "Make the opening more powerful."
  );

  assert.equal(
    creates,
    1
  );

  assert.deepEqual(
    turns,
    [
      {
        id: "conversation-7",
        content:
          "Create a sermon on Proverbs 3."
      },
      {
        id: "conversation-7",
        content:
          "Make the opening more powerful."
      }
    ]
  );
});

test("rejects blank messages without calling the API", async () => {
  let called = false;

  const { api } = setup({
    client: {
      async create() {
        called = true;
        return {};
      }
    }
  });

  await assert.rejects(
    () => api.send("   "),
    /Message is required/
  );

  assert.equal(
    called,
    false
  );
});

test("fails clearly if conversation client is unavailable", async () => {
  const { api } = setup({
    client: null
  });

  global.window.XynivaConversation = null;

  await assert.rejects(
    () => api.send("Create a sermon."),
    /Xyniva conversation service is unavailable/
  );
});

test("renders canonical assistant_content from XynAssist turn response", async () => {
  const rendered = [];

  const { api, elements } = setup({
    client: {
      async create() {
        return {
          id: "conversation-contract"
        };
      },

      async turn() {
        return {
          assistant_message_id: "message-1",
          assistant_content:
            "Canonical sermon response."
        };
      }
    }
  });

  elements.xynivaMessages.appendChild =
    (node) => {
      rendered.push(node);
    };

  await api.send(
    "Create a sermon on Proverbs 3."
  );

  const assistantMessage =
    rendered.find(
      (node) =>
        node.className ===
        "xyniva-message xyniva-message-assistant"
    );

  assert.ok(
    assistantMessage,
    "assistant message should be rendered"
  );

  const body =
    assistantMessage.children?.find?.(
      (child) =>
        child.className ===
        "xyniva-message-body"
    );

  assert.equal(
    body?.textContent,
    "Canonical sermon response."
  );
});
