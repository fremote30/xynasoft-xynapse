const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const MODULE_PATH = path.resolve(
  __dirname,
  "../../ui-faith/js/conversation.js"
);


const REQUEST_ID =
  "66666666-7777-4888-8999-aaaaaaaaaaaa";

function loadConversation(apiFetch) {
  global.window = {
    apiFetch
  };

  delete require.cache[MODULE_PATH];
  require(MODULE_PATH);

  return global.window.XynivaConversation;
}

function jsonResponse(data, options = {}) {
  const {
    ok = true,
    status = 200
  } = options;

  return {
    ok,
    status,
    async json() {
      return data;
    }
  };
}

test("create creates an authenticated XynaFaith conversation", async () => {
  let captured;

  const client = loadConversation(
    async (url, options = {}) => {
      captured = { url, options };

      return jsonResponse({
        id: "conversation-1",
        title: "Sunday sermon"
      });
    }
  );

  const result = await client.create("Sunday sermon");

  assert.equal(
    captured.url,
    "/api/v1/faith/conversations"
  );

  assert.equal(
    captured.options.method,
    "POST"
  );

  assert.deepEqual(
    JSON.parse(captured.options.body),
    {
      title: "Sunday sermon"
    }
  );

  assert.equal(
    result.id,
    "conversation-1"
  );
});

test("create allows an omitted title", async () => {
  let captured;

  const client = loadConversation(
    async (url, options = {}) => {
      captured = { url, options };

      return jsonResponse({
        id: "conversation-2",
        title: null
      });
    }
  );

  await client.create();

  assert.deepEqual(
    JSON.parse(captured.options.body),
    {
      title: null
    }
  );
});

test("list returns the authenticated user's conversations", async () => {
  let captured;

  const client = loadConversation(
    async (url, options = {}) => {
      captured = { url, options };

      return jsonResponse([
        {
          id: "conversation-1"
        },
        {
          id: "conversation-2"
        }
      ]);
    }
  );

  const result = await client.list();

  assert.equal(
    captured.url,
    "/api/v1/faith/conversations"
  );

  assert.equal(
    captured.options.method,
    undefined
  );

  assert.equal(result.length, 2);
});

test("get encodes the conversation id", async () => {
  let captured;

  const client = loadConversation(
    async (url, options = {}) => {
      captured = { url, options };

      return jsonResponse({
        id: "abc/123"
      });
    }
  );

  await client.get("abc/123");

  assert.equal(
    captured.url,
    "/api/v1/faith/conversations/abc%2F123"
  );
});

test("turn sends request identity without trusted identity", async () => {
  let captured;

  const client = loadConversation(
    async (url, options = {}) => {
      captured = { url, options };

      return jsonResponse({
        conversation_id: "conversation-1",
        assistant_message: {
          content: "Generated sermon"
        }
      });
    }
  );

  const result = await client.turn(
    "conversation-1",
    "Create a Pentecostal sermon on Proverbs 3.",
    {
      requestId: REQUEST_ID
    }
  );

  assert.equal(
    captured.url,
    "/api/v1/faith/conversations/conversation-1/turns"
  );

  assert.equal(
    captured.options.method,
    "POST"
  );

  assert.deepEqual(
    JSON.parse(captured.options.body),
    {
      content:
        "Create a Pentecostal sermon on Proverbs 3.",
      request_id: REQUEST_ID
    }
  );

  assert.ok(
    !captured.options.body.includes(
      "external_user_id"
    )
  );

  assert.ok(
    !captured.options.body.includes(
      "product"
    )
  );

  assert.ok(
    !captured.options.body.includes(
      "service_token"
    )
  );

  assert.equal(
    result.assistant_message.content,
    "Generated sermon"
  );
});


test("turn includes optional sermon context", async () => {
  let captured;

  const client = loadConversation(
    async (url, options = {}) => {
      captured = { url, options };

      return jsonResponse({
        conversation_id: "conversation-1"
      });
    }
  );

  const sermon = {
    id: 42,
    data: {
      title: "Trust the Lord",
      scripture: "Proverbs 3:5-6"
    }
  };

  await client.turn(
    "conversation-1",
    "Save this.",
    {
      requestId: REQUEST_ID,
      sermon
    }
  );

  assert.deepEqual(
    JSON.parse(captured.options.body),
    {
      content: "Save this.",
      request_id: REQUEST_ID,
      sermon
    }
  );
});


test("turn requires caller supplied request id", async () => {
  let called = false;

  const client = loadConversation(
    async () => {
      called = true;
      return jsonResponse({});
    }
  );

  await assert.rejects(
    () =>
      client.turn(
        "conversation-1",
        "Create a sermon."
      ),
    /Request ID is required/
  );

  assert.equal(called, false);
});


test("turn rejects an invalid request id", async () => {
  let called = false;

  const client = loadConversation(
    async () => {
      called = true;
      return jsonResponse({});
    }
  );

  await assert.rejects(
    () =>
      client.turn(
        "conversation-1",
        "Create a sermon.",
        {
          requestId: "not-a-uuid"
        }
      ),
    /Request ID must be a UUID/
  );

  assert.equal(called, false);
});


test("throws the server detail for an unsuccessful response", async () => {
  const client = loadConversation(
    async () =>
      jsonResponse(
        {
          detail:
            "Conversation service is temporarily unavailable"
        },
        {
          ok: false,
          status: 503
        }
      )
  );

  await assert.rejects(
    () =>
      client.turn(
        "conversation-1",
        "Create a sermon.",
        {
          requestId: REQUEST_ID
        }
      ),
    /Conversation service is temporarily unavailable/
  );
});

test("falls back safely when an error response is not JSON", async () => {
  const client = loadConversation(
    async () => ({
      ok: false,
      status: 500,
      async json() {
        throw new Error("invalid json");
      }
    })
  );

  await assert.rejects(
    () =>
      client.list(),
    /Xyniva request failed/
  );
});

test("rejects blank conversation ids before making a request", async () => {
  let called = false;

  const client = loadConversation(
    async () => {
      called = true;
      return jsonResponse({});
    }
  );

  await assert.rejects(
    () => client.get("   "),
    /Conversation ID is required/
  );

  assert.equal(called, false);
});

test("rejects blank turn content before making a request", async () => {
  let called = false;

  const client = loadConversation(
    async () => {
      called = true;
      return jsonResponse({});
    }
  );

  await assert.rejects(
    () =>
      client.turn(
        "conversation-1",
        "   "
      ),
    /Message is required/
  );

  assert.equal(called, false);
});
