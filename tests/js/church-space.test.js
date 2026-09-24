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
      "ui-faith/js/church-space.js"
    ),
    "utf8"
  );


function element(
  overrides = {}
) {
  return {
    textContent: "",
    innerHTML: "",
    hidden: false,
    ...overrides
  };
}


function response({
  status = 200,
  body = {}
} = {}) {
  return {
    status,
    ok:
      status >= 200 &&
      status < 300,
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
      name: "Grace Church",
      denomination: "Pentecostal",
      city: "Accra",
      country: "Ghana",
      is_verified: true
    },
    membership: {
      id: 10,
      church_id: 77,
      user_id: 123,
      role: "member",
      status: "active",
      is_primary: true
    },
    permissions: [
      "church.view",
      "prayer.view"
    ],
    capabilities: {
      can_manage_church: false,
      can_view_members: false,
      can_manage_members: false,
      can_create_content: false,
      can_manage_content: false,
      can_view_prayer: true,
      can_manage_pastoral_care: false,
      can_view_analytics: false,
      ...capabilityOverrides
    }
  };
}


function createEnvironment({
  apiFetch
} = {}) {
  const elements = {
    churchSpaceName:
      element({
        textContent: "My Church"
      }),

    churchSpaceIdentity:
      element(),

    churchSpaceRole:
      element({
        hidden: true
      }),

    churchSpaceState:
      element(),

    churchSpaceContent:
      element({
        hidden: true
      }),

    churchContentCard:
      element({
        hidden: true
      }),

    churchPastoralCareCard:
      element({
        hidden: true
      }),

    churchAnalyticsCard:
      element({
        hidden: true
      }),

    churchPeopleSection:
      element({
        hidden: true
      }),

    churchPeopleList:
      element()
  };

  const document = {
    getElementById(id) {
      return elements[id] || null;
    },

    createElement() {
      return {
        _textContent: "",
        innerHTML: "",

        set textContent(value) {
          this._textContent =
            String(value ?? "");

          this.innerHTML =
            this._textContent
              .replaceAll("&", "&amp;")
              .replaceAll("<", "&lt;")
              .replaceAll(">", "&gt;")
              .replaceAll('"', "&quot;")
              .replaceAll("'", "&#39;");
        },

        get textContent() {
          return this._textContent;
        }
      };
    }
  };

  const calls = [];

  const window = {
    async apiFetch(url) {
      calls.push(url);

      if (apiFetch) {
        return apiFetch(
          url,
          calls
        );
      }

      return response({
        body: churchPayload()
      });
    }
  };

  const context = {
    window,
    document,
    console
  };

  vm.createContext(context);
  vm.runInContext(
    SOURCE,
    context,
    {
      filename:
        "church-space.js"
    }
  );

  return {
    window,
    elements,
    calls
  };
}


test(
  "loads primary Church Space and renders identity",
  async () => {
    const env =
      createEnvironment();

    await env.window.loadChurchSpace();

    assert.deepEqual(
      env.calls,
      [
        "/api/v1/churches/mine"
      ]
    );

    assert.equal(
      env.elements
        .churchSpaceName
        .textContent,
      "Grace Church"
    );

    assert.equal(
      env.elements
        .churchSpaceIdentity
        .textContent,
      "Pentecostal • Accra, Ghana"
    );

    assert.equal(
      env.elements
        .churchSpaceRole
        .textContent,
      "Member"
    );

    assert.equal(
      env.elements
        .churchSpaceRole
        .hidden,
      false
    );

    assert.equal(
      env.elements
        .churchSpaceState
        .hidden,
      true
    );

    assert.equal(
      env.elements
        .churchSpaceContent
        .hidden,
      false
    );
  }
);


test(
  "member capabilities keep privileged cards hidden",
  async () => {
    const env =
      createEnvironment();

    await env.window.loadChurchSpace();

    assert.equal(
      env.elements
        .churchContentCard
        .hidden,
      true
    );

    assert.equal(
      env.elements
        .churchPastoralCareCard
        .hidden,
      true
    );

    assert.equal(
      env.elements
        .churchAnalyticsCard
        .hidden,
      true
    );

    assert.equal(
      env.elements
        .churchPeopleSection
        .hidden,
      true
    );
  }
);


test(
  "member without members.view never requests directory",
  async () => {
    const env =
      createEnvironment();

    await env.window.loadChurchSpace();

    assert.equal(
      env.calls.length,
      1
    );

    assert.equal(
      env.calls[0],
      "/api/v1/churches/mine"
    );
  }
);


test(
  "backend capabilities reveal authorized ministry features",
  async () => {
    const payload =
      churchPayload({
        can_view_members: true,
        can_create_content: true,
        can_manage_pastoral_care: true,
        can_view_analytics: true
      });

    payload.membership.role =
      "pastor";

    const env =
      createEnvironment({
        apiFetch: async (url) => {
          if (
            url ===
            "/api/v1/churches/mine"
          ) {
            return response({
              body: payload
            });
          }

          return response({
            body: {
              church_id: 77,
              members: [],
              count: 0
            }
          });
        }
      });

    await env.window.loadChurchSpace();

    assert.equal(
      env.elements
        .churchContentCard
        .hidden,
      false
    );

    assert.equal(
      env.elements
        .churchPastoralCareCard
        .hidden,
      false
    );

    assert.equal(
      env.elements
        .churchAnalyticsCard
        .hidden,
      false
    );

    assert.equal(
      env.elements
        .churchPeopleSection
        .hidden,
      false
    );

    assert.equal(
      env.elements
        .churchSpaceRole
        .textContent,
      "Pastor"
    );
  }
);


test(
  "authorized directory uses church id returned by backend",
  async () => {
    const payload =
      churchPayload({
        can_view_members: true
      });

    const env =
      createEnvironment({
        apiFetch: async (url) => {
          if (
            url ===
            "/api/v1/churches/mine"
          ) {
            return response({
              body: payload
            });
          }

          return response({
            body: {
              church_id: 77,
              members: [],
              count: 0
            }
          });
        }
      });

    await env.window.loadChurchSpace();

    assert.deepEqual(
      env.calls,
      [
        "/api/v1/churches/mine",
        "/api/v1/churches/77/members"
      ]
    );
  }
);


test(
  "authorized directory renders member names and roles safely",
  async () => {
    const payload =
      churchPayload({
        can_view_members: true
      });

    const env =
      createEnvironment({
        apiFetch: async (url) => {
          if (
            url ===
            "/api/v1/churches/mine"
          ) {
            return response({
              body: payload
            });
          }

          return response({
            body: {
              church_id: 77,
              count: 2,
              members: [
                {
                  membership_id: 1,
                  user_id: 1,
                  role: "pastor",
                  user: {
                    id: 1,
                    name:
                      "Pastor <Leader>"
                  }
                },
                {
                  membership_id: 2,
                  user_id: 2,
                  role:
                    "ministry_leader",
                  user: {
                    id: 2,
                    name: "Ama Mensah"
                  }
                }
              ]
            }
          });
        }
      });

    await env.window.loadChurchSpace();

    const html =
      env.elements
        .churchPeopleList
        .innerHTML;

    assert.match(
      html,
      /Pastor &lt;Leader&gt;/
    );

    assert.match(
      html,
      /Ama Mensah/
    );

    assert.match(
      html,
      /Ministry Leader/
    );

    assert.doesNotMatch(
      html,
      /Pastor <Leader>/
    );
  }
);


test(
  "404 shows no primary Church Space state",
  async () => {
    const env =
      createEnvironment({
        apiFetch: async () =>
          response({
            status: 404,
            body: {
              detail:
                "No primary Church Space found"
            }
          })
      });

    await env.window.loadChurchSpace();

    assert.equal(
      env.elements
        .churchSpaceContent
        .hidden,
      true
    );

    assert.equal(
      env.elements
        .churchSpaceState
        .hidden,
      false
    );

    assert.match(
      env.elements
        .churchSpaceState
        .innerHTML,
      /do not have a primary Church Space yet/
    );
  }
);


test(
  "API failure fails gracefully",
  async () => {
    const env =
      createEnvironment({
        apiFetch: async () =>
          response({
            status: 500
          })
      });

    await env.window.loadChurchSpace();

    assert.equal(
      env.elements
        .churchSpaceContent
        .hidden,
      true
    );

    assert.match(
      env.elements
        .churchSpaceState
        .innerHTML,
      /could not load your Church Space/
    );
  }
);


test(
  "missing apiFetch fails closed",
  async () => {
    const env =
      createEnvironment();

    delete env.window.apiFetch;

    await env.window.loadChurchSpace();

    assert.equal(
      env.elements
        .churchSpaceContent
        .hidden,
      true
    );

    assert.match(
      env.elements
        .churchSpaceState
        .innerHTML,
      /could not connect/
    );
  }
);
