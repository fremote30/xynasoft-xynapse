const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");


const SOURCE = fs.readFileSync(
  path.join(
    process.cwd(),
    "ui-faith/js/church-prayer-care.js"
  ),
  "utf8"
);


function element(overrides = {}) {
  const listeners = {};

  return {
    textContent: "",
    innerHTML: "",
    hidden: false,
    value: "",
    checked: false,
    dataset: {},
    listeners,

    addEventListener(type, handler) {
      listeners[type] = handler;
    },

    async dispatch(type, target = null) {
      const handler = listeners[type];

      if (handler) {
        await handler({
          preventDefault() {},
          target: target || this
        });
      }
    },

    closest() {
      return null;
    },

    ...overrides
  };
}


function response({
  status = 200,
  body = {}
} = {}) {
  return {
    status,
    ok: status >= 200 && status < 300,

    async json() {
      return body;
    }
  };
}


function churchPayload(
  capabilityOverrides = {}
) {
  return {
    church: {
      id: 77,
      name: "Grace Church"
    },
    membership: {
      user_id: 123,
      role: "member",
      status: "active"
    },
    capabilities: {
      can_manage_content: false,
      can_manage_pastoral_care: false,
      can_view_prayer: true,
      ...capabilityOverrides
    }
  };
}


function createEnvironment({
  capabilityOverrides = {},
  apiFetch
} = {}) {
  const elements = {
    churchPrayerSection: element(),

    churchPrayerCreateButton: element(),
    churchPrayerForm: element({ hidden: true }),
    churchPrayerMessage: element(),
    churchPrayerCategory: element(),
    churchPrayerVisibility: element({
      value: "community"
    }),
    churchPrayerAnonymous: element(),
    churchPrayerPastoralCare: element(),
    churchPrayerCancelButton: element(),
    churchPrayerFormState: element(),
    churchPrayerList: element(),

    churchTestimonySection: element(),
    churchTestimonyList: element(),
    churchTestimonyModeration: element({
      hidden: true
    }),
    churchPendingTestimonyList: element(),

    churchPastoralCareWorkspace: element({
      hidden: true
    }),
    churchPastoralCareList: element(),
    churchPastoralCareDetail: element({
      hidden: true
    })
  };

  const calls = [];

  const fetch =
    apiFetch ||
    (async (url, options = {}) => {
      calls.push({
        url,
        options
      });

      if (url === "/api/v1/churches/mine") {
        return response({
          body: churchPayload(
            capabilityOverrides
          )
        });
      }

      if (
        url ===
        "/api/v1/churches/77/prayers"
      ) {
        return response({
          body: {
            prayers: []
          }
        });
      }

      if (
        url ===
        "/api/v1/churches/77/testimonies"
      ) {
        return response({
          body: {
            testimonies: []
          }
        });
      }

      if (
        url ===
        "/api/v1/churches/77/testimonies/pending"
      ) {
        return response({
          body: {
            testimonies: []
          }
        });
      }

      if (
        url ===
        "/api/v1/churches/77/pastoral-care-assignees"
      ) {
        return response({
          body: {
            assignees: []
          }
        });
      }

      if (
        url ===
        "/api/v1/churches/77/pastoral-care"
      ) {
        return response({
          body: {
            cases: []
          }
        });
      }

      return response({
        status: 404,
        body: {
          detail: "Not found"
        }
      });
    });

  const document = {
    getElementById(id) {
      return elements[id] || null;
    }
  };

  const window = {
    apiFetch: fetch,

    prompt() {
      return null;
    },

    confirm() {
      return false;
    }
  };

  const context = {
    window,
    document,
    console,
    setTimeout,
    clearTimeout
  };

  vm.createContext(context);
  vm.runInContext(SOURCE, context);

  return {
    window,
    elements,
    calls
  };
}


test(
  "member loads Prayer Wall and Testimony Wall",
  async () => {
    const env = createEnvironment();

    await new Promise((resolve) =>
      setTimeout(resolve, 0)
    );

    const urls = env.calls.map(
      (item) => item.url
    );

    assert.ok(
      urls.includes(
        "/api/v1/churches/77/prayers"
      )
    );

    assert.ok(
      urls.includes(
        "/api/v1/churches/77/testimonies"
      )
    );

    assert.equal(
      env.elements.churchTestimonyModeration.hidden,
      true
    );

    assert.equal(
      env.elements.churchPastoralCareWorkspace.hidden,
      true
    );
  }
);


test(
  "content manager loads pending testimony queue",
  async () => {
    const env = createEnvironment({
      capabilityOverrides: {
        can_manage_content: true
      }
    });

    await new Promise((resolve) =>
      setTimeout(resolve, 0)
    );

    const urls = env.calls.map(
      (item) => item.url
    );

    assert.ok(
      urls.includes(
        "/api/v1/churches/77/testimonies/pending"
      )
    );

    assert.equal(
      env.elements.churchTestimonyModeration.hidden,
      false
    );
  }
);


test(
  "pastoral-care manager loads assignees and cases",
  async () => {
    const env = createEnvironment({
      capabilityOverrides: {
        can_manage_pastoral_care: true
      }
    });

    await new Promise((resolve) =>
      setTimeout(resolve, 0)
    );

    const urls = env.calls.map(
      (item) => item.url
    );

    assert.ok(
      urls.includes(
        "/api/v1/churches/77/pastoral-care-assignees"
      )
    );

    assert.ok(
      urls.includes(
        "/api/v1/churches/77/pastoral-care"
      )
    );

    assert.equal(
      env.elements.churchPastoralCareWorkspace.hidden,
      false
    );
  }
);


test(
  "approved testimony renders without source prayer",
  async () => {
    const calls = [];

    const env = createEnvironment({
      apiFetch: async (url, options = {}) => {
        calls.push({ url, options });

        if (url === "/api/v1/churches/mine") {
          return response({
            body: churchPayload()
          });
        }

        if (
          url ===
          "/api/v1/churches/77/prayers"
        ) {
          return response({
            body: {
              prayers: []
            }
          });
        }

        if (
          url ===
          "/api/v1/churches/77/testimonies"
        ) {
          return response({
            body: {
              testimonies: [
                {
                  prayer_id: 44,
                  user_name: "Ama",
                  is_anonymous: false,
                  testimony:
                    "God answered our prayer.",
                  shared_at:
                    "2026-09-25T12:00:00"
                }
              ]
            }
          });
        }

        return response({
          status: 404
        });
      }
    });

    await new Promise((resolve) =>
      setTimeout(resolve, 0)
    );

    const html =
      env.elements.churchTestimonyList.innerHTML;

    assert.match(
      html,
      /God answered our prayer\./
    );

    assert.match(html, /Ama/);

    assert.doesNotMatch(
      html,
      /source prayer/i
    );
  }
);


test(
  "anonymous testimony renders anonymously",
  async () => {
    const env = createEnvironment({
      apiFetch: async (url) => {
        if (url === "/api/v1/churches/mine") {
          return response({
            body: churchPayload()
          });
        }

        if (
          url ===
          "/api/v1/churches/77/prayers"
        ) {
          return response({
            body: {
              prayers: []
            }
          });
        }

        if (
          url ===
          "/api/v1/churches/77/testimonies"
        ) {
          return response({
            body: {
              testimonies: [
                {
                  prayer_id: 50,
                  user_name: "Hidden Name",
                  is_anonymous: true,
                  testimony: "Answered.",
                  shared_at:
                    "2026-09-25T12:00:00"
                }
              ]
            }
          });
        }

        return response({
          status: 404
        });
      }
    });

    await new Promise((resolve) =>
      setTimeout(resolve, 0)
    );

    const html =
      env.elements.churchTestimonyList.innerHTML;

    assert.match(html, /Anonymous/);

    assert.doesNotMatch(
      html,
      /Hidden Name/
    );
  }
);


test(
  "pending testimony renders moderation controls",
  async () => {
    const env = createEnvironment({
      capabilityOverrides: {
        can_manage_content: true
      },

      apiFetch: async (url) => {
        if (url === "/api/v1/churches/mine") {
          return response({
            body: churchPayload({
              can_manage_content: true
            })
          });
        }

        if (
          url ===
          "/api/v1/churches/77/prayers"
        ) {
          return response({
            body: {
              prayers: []
            }
          });
        }

        if (
          url ===
          "/api/v1/churches/77/testimonies"
        ) {
          return response({
            body: {
              testimonies: []
            }
          });
        }

        if (
          url ===
          "/api/v1/churches/77/testimonies/pending"
        ) {
          return response({
            body: {
              testimonies: [
                {
                  prayer_id: 88,
                  user_name: "Kojo",
                  is_anonymous: false,
                  testimony:
                    "My prayer was answered.",
                  submitted_at:
                    "2026-09-25T12:00:00"
                }
              ]
            }
          });
        }

        return response({
          status: 404
        });
      }
    });

    await new Promise((resolve) =>
      setTimeout(resolve, 0)
    );

    const html =
      env.elements.churchPendingTestimonyList
        .innerHTML;

    assert.match(
      html,
      /My prayer was answered\./
    );

    assert.match(
      html,
      /data-testimony-approve="88"/
    );

    assert.match(
      html,
      /data-testimony-reject="88"/
    );
  }
);


test(
  "moderation sends server decision and refreshes views",
  async () => {
    const calls = [];

    const env = createEnvironment({
      capabilityOverrides: {
        can_manage_content: true
      },

      apiFetch: async (url, options = {}) => {
        calls.push({
          url,
          options
        });

        if (url === "/api/v1/churches/mine") {
          return response({
            body: churchPayload({
              can_manage_content: true
            })
          });
        }

        if (
          url ===
          "/api/v1/churches/77/prayers"
        ) {
          return response({
            body: {
              prayers: []
            }
          });
        }

        if (
          url ===
          "/api/v1/churches/77/testimonies"
        ) {
          return response({
            body: {
              testimonies: []
            }
          });
        }

        if (
          url ===
          "/api/v1/churches/77/testimonies/pending"
        ) {
          return response({
            body: {
              testimonies: [
                {
                  prayer_id: 91,
                  user_name: "Member",
                  is_anonymous: false,
                  testimony: "Answered",
                  submitted_at:
                    "2026-09-25T12:00:00"
                }
              ]
            }
          });
        }

        if (
          url ===
          "/api/v1/churches/77/testimonies/91"
        ) {
          return response({
            body: {
              prayer_id: 91,
              testimony_status: "approved"
            }
          });
        }

        return response({
          status: 404
        });
      }
    });

    await new Promise((resolve) =>
      setTimeout(resolve, 0)
    );

    const button = element({
      dataset: {
        testimonyApprove: "91"
      },

      closest(selector) {
        if (
          selector ===
          "[data-testimony-approve]"
        ) {
          return this;
        }

        return null;
      }
    });

    await env.elements.churchPendingTestimonyList
      .dispatch(
        "click",
        button
      );

    const moderation = calls.find(
      (item) =>
        item.url ===
        "/api/v1/churches/77/testimonies/91"
    );

    assert.ok(moderation);
    assert.equal(
      moderation.options.method,
      "PATCH"
    );

    assert.deepEqual(
      JSON.parse(moderation.options.body),
      {
        status: "approved"
      }
    );
  }
);


test(
  "member cannot trigger moderation API through UI",
  async () => {
    const env = createEnvironment();

    await new Promise((resolve) =>
      setTimeout(resolve, 0)
    );

    const urls = env.calls.map(
      (item) => item.url
    );

    assert.equal(
      urls.some(
        (url) =>
          url.includes(
            "/testimonies/pending"
          )
      ),
      false
    );
  }
);
