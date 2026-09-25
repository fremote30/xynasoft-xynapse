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
  const listeners = {};

  return {
    textContent: "",
    innerHTML: "",
    hidden: false,
    value: "",
    dataset: {},
    listeners,

    addEventListener(type, handler) {
      listeners[type] = handler;
    },

    async dispatch(type, target = null) {
      const handler = listeners[type];

      if (handler) {
        await handler({
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
      element(),

    churchAnnouncementCreateButton:
      element({ hidden: true }),

    churchAnnouncementForm:
      element({ hidden: true }),

    churchAnnouncementTitle:
      element(),

    churchAnnouncementBody:
      element(),

    churchAnnouncementSaveButton:
      element(),

    churchAnnouncementCancelButton:
      element(),

    churchAnnouncementFormState:
      element(),

    churchAnnouncementsList:
      element(),

    churchEventCreateButton:
      element({ hidden: true }),

    churchEventForm:
      element({ hidden: true }),

    churchEventTitle:
      element(),

    churchEventDescription:
      element(),

    churchEventStartsAt:
      element(),

    churchEventEndsAt:
      element(),

    churchEventLocation:
      element(),

    churchEventUrl:
      element(),

    churchEventSaveButton:
      element(),

    churchEventCancelButton:
      element(),

    churchEventFormState:
      element(),

    churchEventsList:
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
  const requests = [];

  const window = {
    async apiFetch(url, options = {}) {
      calls.push(url);
      requests.push({
        url,
        options
      });

      if (apiFetch) {
        return apiFetch(
          url,
          calls,
          options,
          requests
        );
      }

      if (
        url ===
        "/api/v1/churches/mine"
      ) {
        return response({
          body: churchPayload()
        });
      }

      if (
        url.endsWith("/announcements")
      ) {
        return response({
          body: {
            church_id: 77,
            announcements: [],
            count: 0
          }
        });
      }

      if (
        url.endsWith("/events")
      ) {
        return response({
          body: {
            church_id: 77,
            events: [],
            count: 0
          }
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
    calls,
    requests
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
        "/api/v1/churches/mine",
        "/api/v1/churches/77/announcements",
        "/api/v1/churches/77/events"
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

    assert.deepEqual(
      env.calls,
      [
        "/api/v1/churches/mine",
        "/api/v1/churches/77/announcements",
        "/api/v1/churches/77/events"
      ]
    );

    assert.equal(
      env.calls.some(
        (url) =>
          url.endsWith("/members")
      ),
      false
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
        "/api/v1/churches/77/announcements",
        "/api/v1/churches/77/events",
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


test(
  "member loads published community content without create controls",
  async () => {
    const env =
      createEnvironment({
        apiFetch: async (url) => {
          if (
            url ===
            "/api/v1/churches/mine"
          ) {
            return response({
              body: churchPayload()
            });
          }

          if (
            url.endsWith(
              "/announcements"
            )
          ) {
            return response({
              body: {
                church_id: 77,
                count: 1,
                announcements: [
                  {
                    id: 5,
                    title:
                      "Sunday <Update>",
                    body:
                      "Service starts at 10.",
                    status: "published",
                    published_at:
                      "2030-01-01T10:00:00"
                  }
                ]
              }
            });
          }

          return response({
            body: {
              church_id: 77,
              count: 1,
              events: [
                {
                  id: 9,
                  title: "Youth Night",
                  description:
                    "Community gathering",
                  starts_at:
                    "2030-01-02T18:00:00",
                  ends_at: null,
                  location: "Main Hall",
                  event_url:
                    "https://example.test/event",
                  status: "published"
                }
              ]
            }
          });
        }
      });

    await env.window.loadChurchSpace();

    assert.equal(
      env.elements
        .churchAnnouncementCreateButton
        .hidden,
      true
    );

    assert.equal(
      env.elements
        .churchEventCreateButton
        .hidden,
      true
    );

    assert.match(
      env.elements
        .churchAnnouncementsList
        .innerHTML,
      /Sunday &lt;Update&gt;/
    );

    assert.doesNotMatch(
      env.elements
        .churchAnnouncementsList
        .innerHTML,
      /Sunday <Update>/
    );

    assert.match(
      env.elements
        .churchEventsList
        .innerHTML,
      /Youth Night/
    );

    assert.match(
      env.elements
        .churchEventsList
        .innerHTML,
      /Main Hall/
    );

    assert.match(
      env.elements
        .churchEventsList
        .innerHTML,
      /noopener noreferrer/
    );
  }
);


test(
  "content creator receives draft creation controls",
  async () => {
    const env =
      createEnvironment({
        apiFetch: async (url) => {
          if (
            url ===
            "/api/v1/churches/mine"
          ) {
            return response({
              body: churchPayload({
                can_create_content: true
              })
            });
          }

          if (
            url.endsWith(
              "/announcements"
            )
          ) {
            return response({
              body: {
                announcements: [],
                count: 0
              }
            });
          }

          return response({
            body: {
              events: [],
              count: 0
            }
          });
        }
      });

    await env.window.loadChurchSpace();

    assert.equal(
      env.elements
        .churchAnnouncementCreateButton
        .hidden,
      false
    );

    assert.equal(
      env.elements
        .churchEventCreateButton
        .hidden,
      false
    );

    assert.equal(
      env.elements
        .churchAnnouncementForm
        .hidden,
      true
    );

    await env.elements
      .churchAnnouncementCreateButton
      .dispatch("click");

    assert.equal(
      env.elements
        .churchAnnouncementForm
        .hidden,
      false
    );
  }
);


test(
  "announcement creation always sends a draft",
  async () => {
    const payload =
      churchPayload({
        can_create_content: true
      });

    const env =
      createEnvironment({
        apiFetch: async (
          url,
          calls,
          options
        ) => {
          if (
            url ===
            "/api/v1/churches/mine"
          ) {
            return response({
              body: payload
            });
          }

          if (
            options.method === "POST"
          ) {
            return response({
              status: 201,
              body: {
                id: 20
              }
            });
          }

          if (
            url.endsWith(
              "/announcements"
            )
          ) {
            return response({
              body: {
                announcements: [],
                count: 0
              }
            });
          }

          return response({
            body: {
              events: [],
              count: 0
            }
          });
        }
      });

    await env.window.loadChurchSpace();

    env.elements
      .churchAnnouncementTitle
      .value = "Church Update";

    env.elements
      .churchAnnouncementBody
      .value = "Important news.";

    await env.elements
      .churchAnnouncementSaveButton
      .dispatch("click");

    const request =
      env.requests.find(
        (item) =>
          item.options.method === "POST" &&
          item.url.endsWith(
            "/announcements"
          )
      );

    assert.ok(request);

    assert.deepEqual(
      JSON.parse(request.options.body),
      {
        title: "Church Update",
        body: "Important news.",
        status: "draft"
      }
    );
  }
);


test(
  "event creation sends optional fields and draft status",
  async () => {
    const env =
      createEnvironment({
        apiFetch: async (
          url,
          calls,
          options
        ) => {
          if (
            url ===
            "/api/v1/churches/mine"
          ) {
            return response({
              body: churchPayload({
                can_create_content: true
              })
            });
          }

          if (
            options.method === "POST"
          ) {
            return response({
              status: 201,
              body: {
                id: 30
              }
            });
          }

          if (
            url.endsWith(
              "/announcements"
            )
          ) {
            return response({
              body: {
                announcements: [],
                count: 0
              }
            });
          }

          return response({
            body: {
              events: [],
              count: 0
            }
          });
        }
      });

    await env.window.loadChurchSpace();

    env.elements
      .churchEventTitle
      .value = "Bible Study";

    env.elements
      .churchEventDescription
      .value = "Weekly study";

    env.elements
      .churchEventStartsAt
      .value = "2030-02-01T18:00";

    env.elements
      .churchEventEndsAt
      .value = "2030-02-01T19:30";

    env.elements
      .churchEventLocation
      .value = "Fellowship Hall";

    env.elements
      .churchEventUrl
      .value =
        "https://example.test/study";

    await env.elements
      .churchEventSaveButton
      .dispatch("click");

    const request =
      env.requests.find(
        (item) =>
          item.options.method === "POST" &&
          item.url.endsWith("/events")
      );

    assert.ok(request);

    const body =
      JSON.parse(request.options.body);

    assert.equal(
      body.title,
      "Bible Study"
    );

    assert.equal(
      body.status,
      "draft"
    );

    assert.equal(
      body.location,
      "Fellowship Hall"
    );

    assert.equal(
      body.event_url,
      "https://example.test/study"
    );
  }
);


test(
  "manager receives lifecycle controls for church content",
  async () => {
    const env =
      createEnvironment({
        apiFetch: async (url) => {
          if (
            url ===
            "/api/v1/churches/mine"
          ) {
            return response({
              body: churchPayload({
                can_create_content: true,
                can_manage_content: true
              })
            });
          }

          if (
            url.endsWith(
              "/announcements"
            )
          ) {
            return response({
              body: {
                count: 1,
                announcements: [
                  {
                    id: 11,
                    title: "Draft notice",
                    body: "Draft body",
                    status: "draft",
                    published_at: null
                  }
                ]
              }
            });
          }

          return response({
            body: {
              count: 1,
              events: [
                {
                  id: 12,
                  title: "Draft event",
                  starts_at:
                    "2030-03-01T10:00:00",
                  status: "draft"
                }
              ]
            }
          });
        }
      });

    await env.window.loadChurchSpace();

    assert.match(
      env.elements
        .churchAnnouncementsList
        .innerHTML,
      /data-announcement-action="published"/
    );

    assert.match(
      env.elements
        .churchAnnouncementsList
        .innerHTML,
      /data-announcement-action="archived"/
    );

    assert.match(
      env.elements
        .churchEventsList
        .innerHTML,
      /data-event-action="published"/
    );

    assert.match(
      env.elements
        .churchEventsList
        .innerHTML,
      /data-event-action="cancelled"/
    );
  }
);


test(
  "manager lifecycle action uses scoped PATCH endpoint",
  async () => {
    const env =
      createEnvironment({
        apiFetch: async (
          url,
          calls,
          options
        ) => {
          if (
            url ===
            "/api/v1/churches/mine"
          ) {
            return response({
              body: churchPayload({
                can_manage_content: true
              })
            });
          }

          if (
            options.method === "PATCH"
          ) {
            return response({
              body: {}
            });
          }

          if (
            url.endsWith(
              "/announcements"
            )
          ) {
            return response({
              body: {
                announcements: [],
                count: 0
              }
            });
          }

          return response({
            body: {
              events: [],
              count: 0
            }
          });
        }
      });

    await env.window.loadChurchSpace();

    const target = {
      dataset: {
        announcementId: "44",
        announcementAction:
          "published"
      },

      closest(selector) {
        if (
          selector ===
          "[data-announcement-action]"
        ) {
          return this;
        }

        return null;
      }
    };

    await env.elements
      .churchAnnouncementsList
      .dispatch(
        "click",
        target
      );

    const patch =
      env.requests.find(
        (item) =>
          item.options.method === "PATCH"
      );

    assert.ok(patch);

    assert.equal(
      patch.url,
      "/api/v1/churches/77/announcements/44"
    );

    assert.deepEqual(
      JSON.parse(patch.options.body),
      {
        status: "published"
      }
    );
  }
);


test(
  "community load failures do not hide Church Space",
  async () => {
    const env =
      createEnvironment({
        apiFetch: async (url) => {
          if (
            url ===
            "/api/v1/churches/mine"
          ) {
            return response({
              body: churchPayload()
            });
          }

          return response({
            status: 500
          });
        }
      });

    await env.window.loadChurchSpace();

    assert.equal(
      env.elements
        .churchSpaceContent
        .hidden,
      false
    );

    assert.match(
      env.elements
        .churchAnnouncementsList
        .innerHTML,
      /could not be loaded/
    );

    assert.match(
      env.elements
        .churchEventsList
        .innerHTML,
      /could not be loaded/
    );
  }
);


test(
  "creator can edit own draft but not another creator draft",
  async () => {
    const env =
      createEnvironment({
        apiFetch: async (url) => {
          if (url === "/api/v1/churches/mine") {
            return response({
              body: churchPayload({
                can_create_content: true
              })
            });
          }

          if (url.endsWith("/announcements")) {
            return response({
              body: {
                count: 2,
                announcements: [
                  {
                    id: 51,
                    author_user_id: 123,
                    title: "My Draft",
                    body: "Mine",
                    status: "draft"
                  },
                  {
                    id: 52,
                    author_user_id: 999,
                    title: "Other Draft",
                    body: "Other",
                    status: "draft"
                  }
                ]
              }
            });
          }

          return response({
            body: {
              events: [],
              count: 0
            }
          });
        }
      });

    await env.window.loadChurchSpace();

    const html =
      env.elements
        .churchAnnouncementsList
        .innerHTML;

    assert.match(
      html,
      /data-announcement-edit="51"/
    );

    assert.doesNotMatch(
      html,
      /data-announcement-edit="52"/
    );

    assert.doesNotMatch(
      html,
      /data-announcement-action="published"/
    );
  }
);


test(
  "creator edits own announcement through scoped PATCH without status transition",
  async () => {
    let loadCount = 0;

    const env =
      createEnvironment({
        apiFetch: async (
          url,
          calls,
          options
        ) => {
          if (url === "/api/v1/churches/mine") {
            return response({
              body: churchPayload({
                can_create_content: true
              })
            });
          }

          if (
            url.endsWith("/announcements") &&
            !options.method
          ) {
            loadCount += 1;

            return response({
              body: {
                count: 1,
                announcements: [
                  {
                    id: 61,
                    author_user_id: 123,
                    title: "Original",
                    body: "Original body",
                    status: "draft"
                  }
                ]
              }
            });
          }

          if (options.method === "PATCH") {
            return response({
              body: {}
            });
          }

          return response({
            body: {
              events: [],
              count: 0
            }
          });
        }
      });

    await env.window.loadChurchSpace();

    const editTarget = {
      dataset: {
        announcementEdit: "61"
      },

      closest(selector) {
        if (
          selector ===
          "[data-announcement-edit]"
        ) {
          return this;
        }

        return null;
      }
    };

    await env.elements
      .churchAnnouncementsList
      .dispatch("click", editTarget);

    assert.equal(
      env.elements
        .churchAnnouncementTitle
        .value,
      "Original"
    );

    assert.equal(
      env.elements
        .churchAnnouncementBody
        .value,
      "Original body"
    );

    env.elements
      .churchAnnouncementTitle
      .value = "Updated";

    env.elements
      .churchAnnouncementBody
      .value = "Updated body";

    await env.elements
      .churchAnnouncementSaveButton
      .dispatch("click");

    const patch =
      env.requests.find(
        (item) =>
          item.options.method === "PATCH"
      );

    assert.ok(patch);

    assert.equal(
      patch.url,
      "/api/v1/churches/77/announcements/61"
    );

    assert.deepEqual(
      JSON.parse(patch.options.body),
      {
        title: "Updated",
        body: "Updated body"
      }
    );

    assert.equal(
      loadCount >= 2,
      true
    );
  }
);


test(
  "creator can edit only own draft event",
  async () => {
    const env =
      createEnvironment({
        apiFetch: async (url) => {
          if (url === "/api/v1/churches/mine") {
            return response({
              body: churchPayload({
                can_create_content: true
              })
            });
          }

          if (url.endsWith("/announcements")) {
            return response({
              body: {
                announcements: [],
                count: 0
              }
            });
          }

          return response({
            body: {
              count: 2,
              events: [
                {
                  id: 71,
                  created_by_user_id: 123,
                  title: "My Event",
                  starts_at:
                    "2030-05-01T18:00:00",
                  status: "draft"
                },
                {
                  id: 72,
                  created_by_user_id: 999,
                  title: "Other Event",
                  starts_at:
                    "2030-05-02T18:00:00",
                  status: "draft"
                }
              ]
            }
          });
        }
      });

    await env.window.loadChurchSpace();

    const html =
      env.elements
        .churchEventsList
        .innerHTML;

    assert.match(
      html,
      /data-event-edit="71"/
    );

    assert.doesNotMatch(
      html,
      /data-event-edit="72"/
    );

    assert.doesNotMatch(
      html,
      /data-event-action="published"/
    );
  }
);


test(
  "event edit prepopulates form and PATCHes existing event",
  async () => {
    const env =
      createEnvironment({
        apiFetch: async (
          url,
          calls,
          options
        ) => {
          if (url === "/api/v1/churches/mine") {
            return response({
              body: churchPayload({
                can_create_content: true
              })
            });
          }

          if (url.endsWith("/announcements")) {
            return response({
              body: {
                announcements: [],
                count: 0
              }
            });
          }

          if (
            url.endsWith("/events") &&
            !options.method
          ) {
            return response({
              body: {
                count: 1,
                events: [
                  {
                    id: 81,
                    created_by_user_id: 123,
                    title: "Prayer Night",
                    description: "Original",
                    starts_at:
                      "2030-06-01T18:00:00",
                    ends_at:
                      "2030-06-01T20:00:00",
                    location: "Main Hall",
                    event_url:
                      "https://example.test/prayer",
                    status: "draft"
                  }
                ]
              }
            });
          }

          if (options.method === "PATCH") {
            return response({
              body: {}
            });
          }

          return response({
            body: {
              events: [],
              count: 0
            }
          });
        }
      });

    await env.window.loadChurchSpace();

    const editTarget = {
      dataset: {
        eventEdit: "81"
      },

      closest(selector) {
        if (
          selector ===
          "[data-event-edit]"
        ) {
          return this;
        }

        return null;
      }
    };

    await env.elements
      .churchEventsList
      .dispatch("click", editTarget);

    assert.equal(
      env.elements.churchEventTitle.value,
      "Prayer Night"
    );

    assert.equal(
      env.elements.churchEventLocation.value,
      "Main Hall"
    );

    env.elements.churchEventTitle.value =
      "Updated Prayer Night";

    await env.elements
      .churchEventSaveButton
      .dispatch("click");

    const patch =
      env.requests.find(
        (item) =>
          item.options.method === "PATCH"
      );

    assert.ok(patch);

    assert.equal(
      patch.url,
      "/api/v1/churches/77/events/81"
    );

    const body =
      JSON.parse(patch.options.body);

    assert.equal(
      body.title,
      "Updated Prayer Night"
    );

    assert.equal(
      Object.hasOwn(body, "status"),
      false
    );
  }
);
