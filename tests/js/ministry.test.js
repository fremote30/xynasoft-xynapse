const test =
  require("node:test");

const assert =
  require("node:assert/strict");

const fs =
  require("node:fs");

const vm =
  require("node:vm");

const path =
  require("node:path");

const SOURCE =
  fs.readFileSync(
    path.join(
      process.cwd(),
      "ui-faith/js/ministry.js"
    ),
    "utf8"
  );

const REQUEST_ID =
  "77777777-8888-4999-8aaa-bbbbbbbbbbbb";

function environment(
  responder
) {
  const calls = [];

  const window = {
    crypto: {
      randomUUID() {
        return REQUEST_ID;
      }
    },

    async apiFetch(
      url,
      options
    ) {
      calls.push({
        url,
        options
      });

      return responder(
        url,
        options,
        calls.length
      );
    }
  };

  const context = {
    window,
    console
  };

  vm.createContext(
    context
  );

  vm.runInContext(
    SOURCE,
    context
  );

  return {
    window,
    calls
  };
}

function response(
  status,
  payload
) {
  return {
    status,

    ok:
      status >= 200 &&
      status < 300,

    async json() {
      return payload;
    }
  };
}

test(
  "executes ministry skill with only browser-owned fields",
  async () => {
    const env =
      environment(
        async () =>
          response(
            200,
            {
              request_id:
                REQUEST_ID,
              skill:
                "sermon.generate",
              result: {
                title:
                  "Faith"
              }
            }
          )
      );

    const result =
      await env.window
        .XynaFaithMinistry
        .execute(
          "sermon.generate",
          {
            input:
              "Faith"
          }
        );

    assert.equal(
      result.result.title,
      "Faith"
    );

    assert.equal(
      env.calls.length,
      1
    );

    assert.equal(
      env.calls[0].url,
      "/api/v1/faith/ministry/execute"
    );

    const body =
      JSON.parse(
        env.calls[0]
          .options
          .body
      );

    assert.deepEqual(
      Object.keys(body).sort(),
      [
        "input",
        "request_id",
        "skill"
      ]
    );

    assert.equal(
      body.request_id,
      REQUEST_ID
    );

    assert.equal(
      body.external_user_id,
      undefined
    );

    assert.equal(
      body.entitlement_key,
      undefined
    );

    assert.equal(
      body.metric,
      undefined
    );
  }
);

test(
  "retains request identity after uncertain response",
  async () => {
    const env =
      environment(
        async (
          _url,
          _options,
          count
        ) => {
          if (count === 1) {
            return response(
              503,
              {
                detail:
                  "Execution status is uncertain; retry with the same request ID"
              }
            );
          }

          return response(
            200,
            {
              request_id:
                REQUEST_ID,
              skill:
                "sermon.generate",
              result: {
                title:
                  "Recovered"
              }
            }
          );
        }
      );

    await assert.rejects(
      () =>
        env.window
          .XynaFaithMinistry
          .execute(
            "sermon.generate",
            {
              input:
                "Faith"
            }
          ),
      error => {
        assert.equal(
          error.uncertain,
          true
        );

        assert.equal(
          error.requestId,
          REQUEST_ID
        );

        return true;
      }
    );

    assert.equal(
      env.window
        .XynaFaithMinistry
        .canRetry(
          "sermon.generate"
        ),
      true
    );

    await env.window
      .XynaFaithMinistry
      .execute(
        "sermon.generate",
        {
          input:
            "Faith"
        },
        {
          retry: true
        }
      );

    const first =
      JSON.parse(
        env.calls[0]
          .options
          .body
      );

    const second =
      JSON.parse(
        env.calls[1]
          .options
          .body
      );

    assert.equal(
      first.request_id,
      second.request_id
    );

    assert.equal(
      env.window
        .XynaFaithMinistry
        .canRetry(
          "sermon.generate"
        ),
      false
    );
  }
);

test(
  "does not retain request identity for definite failure",
  async () => {
    const env =
      environment(
        async () =>
          response(
            403,
            {
              detail:
                "AI allowance exhausted"
            }
          )
      );

    await assert.rejects(
      () =>
        env.window
          .XynaFaithMinistry
          .execute(
            "sermon.generate",
            {}
          ),
      error => {
        assert.equal(
          error.status,
          403
        );

        assert.equal(
          error.uncertain,
          false
        );

        return true;
      }
    );

    assert.equal(
      env.window
        .XynaFaithMinistry
        .canRetry(
          "sermon.generate"
        ),
      false
    );
  }
);

test(
  "rejects mismatched successful response",
  async () => {
    const env =
      environment(
        async () =>
          response(
            200,
            {
              request_id:
                "99999999-9999-4999-8999-999999999999",
              skill:
                "sermon.generate",
              result: {
                title:
                  "Wrong request"
              }
            }
          )
      );

    await assert.rejects(
      () =>
        env.window
          .XynaFaithMinistry
          .execute(
            "sermon.generate",
            {}
          ),
      /invalid ministry response/
    );
  }
);
