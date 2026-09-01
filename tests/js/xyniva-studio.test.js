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


const REQUEST_ID =
  "66666666-7777-4888-8999-aaaaaaaaaaaa";


const SOURCE =
  fs.readFileSync(
    path.join(
      process.cwd(),
      "ui-faith/js/xyniva-studio.js"
    ),
    "utf8"
  );


function element(
  overrides = {}
) {

  const listeners = {};
  const children = [];

  return {
    value: "",
    textContent: "",
    className: "",
    hidden: false,
    disabled: false,
    scrollTop: 0,
    scrollHeight: 0,
    dataset: {},
    children,

    addEventListener(
      name,
      handler
    ) {
      listeners[name] =
        handler;
    },

    appendChild(child) {
      children.push(child);
      this.scrollHeight =
        children.length;
      return child;
    },

    querySelector(selector) {

      if (
        selector ===
        ".xyniva-studio-welcome"
      ) {
        return null;
      }

      return null;
    },

    focus() {},

    _listeners: listeners,

    ...overrides
  };

}


function createEnvironment({
  sermon = null
} = {}) {

  const elements = {
    xynivaStudioForm:
      element(),

    xynivaStudioInput:
      element(),

    xynivaStudioMessages:
      element(),

    xynivaStudioStatus:
      element({
        hidden: true
      }),

    xynivaStudioSend:
      element(),

    denomination:
      element({
        value: "pentecostal"
      }),

    audience:
      element({
        value: "Church"
      }),

    context:
      element({
        value: "Uncertainty"
      }),

    tone:
      element({
        value: "passionate"
      }),

    duration:
      element({
        value: "30"
      })
  };

  const calls = {
    create: [],
    turn: [],
    render: [],
    save: 0,
    update: 0,
    storage: []
  };

  const window = {
    currentGeneratedSermon:
      sermon,

    currentSermonId:
      sermon?.id ?? null,

    currentUser: {
      id: 7
    },

    crypto: {
      randomUUID() {
        return REQUEST_ID;
      }
    },

    localStorage: {
      setItem(key, value) {
        calls.storage.push({
          key,
          value
        });
      }
    },

    XynivaConversation: {

      async create(title) {

        calls.create.push(
          title
        );

        return {
          id: "conversation-1"
        };
      },

      async turn(
        conversationId,
        content,
        options
      ) {

        calls.turn.push({
          conversationId,
          content,
          options
        });

        return {
          assistant_content:
            JSON.stringify({
              title:
                "Refined Sermon",
              scripture:
                "Proverbs 3:5-6",
              introduction:
                "A stronger introduction.",
              main_points: [
                {
                  title:
                    "Trust God",
                  content:
                    "Trust Him completely."
                }
              ],
              application:
                "Walk by faith.",
              conclusion:
                "Trust the Lord."
            })
        };
      }
    },

    renderCurrentSermon(
      value,
      scroll
    ) {

      calls.render.push({
        value,
        scroll
      });

    },

    saveCurrentSermon() {
      calls.save += 1;
    },

    updateCurrentSermon() {
      calls.update += 1;
    }
  };

  const document = {

    getElementById(id) {
      return (
        elements[id] ||
        null
      );
    },

    createElement() {
      return element();
    },

    querySelectorAll() {
      return [];
    }

  };

  const context = {
    window,
    document,
    console,
    JSON,
    String,
    Boolean,
    Array,
    Object,
    Error
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
    elements,
    calls
  };

}


function existingSermon() {

  return {
    id: 42,
    author_id: 7,
    title:
      "Trusting God",
    scripture:
      "Proverbs 3:5-6",
    introduction:
      "Original introduction.",
    main_points: [
      {
        title:
          "Trust",
        content:
          "Trust God."
      }
    ],
    application:
      "Apply trust.",
    conclusion:
      "Keep trusting.",
    denomination:
      "pentecostal",
    audience:
      "Church",
    context:
      "Uncertainty",
    tone:
      "passionate",
    duration:
      "30"
  };

}


test(
  "exposes Xyniva Studio controller",
  () => {

    const { window } =
      createEnvironment();

    assert.equal(
      typeof window.XynivaStudio,
      "object"
    );

    assert.equal(
      typeof window.XynivaStudio.bind,
      "function"
    );

    assert.equal(
      typeof window.XynivaStudio.send,
      "function"
    );

  }
);


test(
  "first Studio turn seeds current sermon context",
  async () => {

    const {
      window,
      calls
    } =
      createEnvironment({
        sermon:
          existingSermon()
      });

    await window.XynivaStudio.send(
      "Strengthen the introduction."
    );

    assert.equal(
      calls.create.length,
      1
    );

    assert.equal(
      calls.turn.length,
      1
    );

    assert.match(
      calls.turn[0].content,
      /CURRENT SERMON:/
    );

    assert.match(
      calls.turn[0].content,
      /Trusting God/
    );

    assert.equal(
      calls.turn[0].options.requestId,
      REQUEST_ID
    );

    assert.equal(
      calls.turn[0].options.sermon.id,
      42
    );

    assert.equal(
      calls.turn[0].options.sermon.data.title,
      "Trusting God"
    );

    assert.equal(
      calls.turn[0].options.sermon.data.scripture,
      "Proverbs 3:5-6"
    );

    assert.match(
      calls.turn[0].content,
      /Strengthen the introduction\./
    );

  }
);


test(
  "unsaved Studio sermon is transported with null id",
  async () => {

    const unsaved = {
      ...existingSermon()
    };

    delete unsaved.id;
    delete unsaved.author_id;

    const {
      window,
      calls
    } =
      createEnvironment({
        sermon: unsaved
      });

    await window.XynivaStudio.send(
      "Strengthen the introduction."
    );

    assert.equal(
      calls.turn.length,
      1
    );

    assert.equal(
      calls.turn[0].options.requestId,
      REQUEST_ID
    );

    assert.equal(
      calls.turn[0].options.sermon.id,
      null
    );

    assert.equal(
      calls.turn[0].options.sermon.data.title,
      "Trusting God"
    );

  }
);


test(
  "follow-up reuses conversation without reseeding sermon",
  async () => {

    const {
      window,
      calls
    } =
      createEnvironment({
        sermon:
          existingSermon()
      });

    await window.XynivaStudio.send(
      "Strengthen the introduction."
    );

    await window.XynivaStudio.send(
      "Add more Scripture."
    );

    assert.equal(
      calls.create.length,
      1
    );

    assert.equal(
      calls.turn.length,
      2
    );

    assert.equal(
      calls.turn[1].content,
      "Add more Scripture."
    );

    assert.doesNotMatch(
      calls.turn[1].content,
      /CURRENT SERMON:/
    );

  }
);


test(
  "structured response updates existing Studio sermon",
  async () => {

    const {
      window,
      calls
    } =
      createEnvironment({
        sermon:
          existingSermon()
      });

    await window.XynivaStudio.send(
      "Improve this sermon."
    );

    assert.equal(
      calls.render.length,
      1
    );

    assert.equal(
      calls.render[0].value.title,
      "Refined Sermon"
    );

    assert.equal(
      calls.render[0].scroll,
      false
    );

    assert.equal(
      window
        .currentGeneratedSermon
        .title,
      "Refined Sermon"
    );

  }
);


test(
  "refinement preserves saved sermon identity metadata",
  async () => {

    const {
      window,
      calls
    } =
      createEnvironment({
        sermon:
          existingSermon()
      });

    await window.XynivaStudio.send(
      "Make point one stronger."
    );

    const refined =
      calls.render[0].value;

    assert.equal(
      refined.id,
      42
    );

    assert.equal(
      refined.author_id,
      7
    );

  }
);


test(
  "trusted sermon save action synchronizes Studio state",
  async () => {

    const unsaved = {
      ...existingSermon()
    };

    delete unsaved.id;
    delete unsaved.author_id;

    const {
      window,
      calls
    } =
      createEnvironment({
        sermon: unsaved
      });

    window.XynivaConversation.turn =
      async (
        conversationId,
        content,
        options
      ) => {

        calls.turn.push({
          conversationId,
          content,
          options
        });

        return {
          conversation_id:
            "conversation-1",
          user_message_id:
            "aaaaaaaa-2222-3333-4444-555555555555",
          action: {
            name: "sermon.save",
            status: "completed",
            result: {
              sermon_id: 91
            }
          }
        };

      };

    await window.XynivaStudio.send(
      "Save this."
    );

    assert.equal(
      calls.turn.length,
      1
    );

    assert.equal(
      calls.turn[0].options.requestId,
      REQUEST_ID
    );

    assert.equal(
      calls.turn[0].options.sermon.id,
      null
    );

    assert.equal(
      window.currentSermonId,
      91
    );

    assert.equal(
      window.currentGeneratedSermon.id,
      91
    );

    assert.equal(
      window.currentGeneratedSermon.author_id,
      7
    );

    assert.equal(
      calls.render.length,
      1
    );

    assert.equal(
      calls.render[0].value.id,
      91
    );

    assert.equal(
      calls.save,
      0
    );

    assert.equal(
      calls.update,
      0
    );

    assert.ok(
      calls.storage.some(
        entry =>
          entry.key ===
            "last_saved_sermon_id" &&
          entry.value === "91"
      )
    );

    assert.ok(
      calls.storage.some(
        entry =>
          entry.key ===
            "latest_sermon_7" &&
          JSON.parse(entry.value).id ===
            91
      )
    );

  }
);


test(
  "Xyniva refinement never saves or updates automatically",
  async () => {

    const {
      window,
      calls
    } =
      createEnvironment({
        sermon:
          existingSermon()
      });

    await window.XynivaStudio.send(
      "Shorten the conclusion."
    );

    assert.equal(
      calls.save,
      0
    );

    assert.equal(
      calls.update,
      0
    );

  }
);


test(
  "without an open sermon the first turn remains conversational",
  async () => {

    const {
      window,
      calls
    } =
      createEnvironment({
        sermon: null
      });

    await window.XynivaStudio.send(
      "Create a sermon on grace."
    );

    assert.equal(
      calls.turn[0].content,
      "Create a sermon on grace."
    );

  }
);


test(
  "new Studio page starts a fresh conversation context",
  async () => {

    const {
      window,
      elements,
      calls
    } =
      createEnvironment({
        sermon:
          existingSermon()
      });

    window.XynivaStudio.bind();

    await window.XynivaStudio.send(
      "Strengthen the introduction."
    );

    assert.equal(
      calls.create.length,
      1
    );

    const replacementForm =
      element();

    const replacementInput =
      element();

    elements.xynivaStudioForm =
      replacementForm;

    elements.xynivaStudioInput =
      replacementInput;

    window.currentGeneratedSermon = {
      ...existingSermon(),
      id: 99,
      title:
        "A Different Sermon"
    };

    window.XynivaStudio.bind();

    await window.XynivaStudio.send(
      "Strengthen the conclusion."
    );

    assert.equal(
      calls.create.length,
      2
    );

    assert.equal(
      calls.turn.length,
      2
    );

    assert.match(
      calls.turn[1].content,
      /CURRENT SERMON:/
    );

    assert.match(
      calls.turn[1].content,
      /A Different Sermon/
    );

    assert.doesNotMatch(
      calls.turn[1].content,
      /"title":"Trusting God"/
    );

  }
);


test(
  "shows visible working status while Xyniva is responding",
  async () => {

    const {
      window,
      elements
    } =
      createEnvironment({
        sermon:
          existingSermon()
      });

    elements.xynivaStudioStatusText =
      element();

    elements.xynivaStudioProgressBar =
      element({
        classList: {
          add() {},
          remove() {}
        },
        offsetWidth: 100
      });

    let releaseTurn;

    window.XynivaConversation.turn =
      async () =>
        new Promise(resolve => {

          releaseTurn = () =>
            resolve({
              assistant_content:
                JSON.stringify({
                  title:
                    "Refined Sermon",
                  scripture:
                    "Proverbs 3:5-6",
                  introduction:
                    "Updated introduction.",
                  main_points: [
                    {
                      title:
                        "Trust God",
                      content:
                        "Trust Him."
                    }
                  ],
                  application:
                    "Walk by faith.",
                  conclusion:
                    "Trust the Lord."
                })
            });

        });

    const pending =
      window.XynivaStudio.send(
        "Strengthen the introduction."
      );

    for (
      let attempt = 0;
      attempt < 20 &&
      typeof releaseTurn !== "function";
      attempt += 1
    ) {
      await new Promise(resolve =>
        setImmediate(resolve)
      );
    }

    assert.equal(
      typeof releaseTurn,
      "function"
    );

    assert.equal(
      elements
        .xynivaStudioStatus
        .hidden,
      false
    );

    assert.equal(
      elements
        .xynivaStudioSend
        .disabled,
      true
    );

    assert.equal(
      elements
        .xynivaStudioInput
        .disabled,
      true
    );

    assert.match(
      elements
        .xynivaStudioStatusText
        .textContent,
      /Understanding your request/
    );

    releaseTurn();

    await pending;

    assert.equal(
      elements
        .xynivaStudioStatus
        .hidden,
      true
    );

    assert.equal(
      elements
        .xynivaStudioSend
        .disabled,
      false
    );

    assert.equal(
      elements
        .xynivaStudioInput
        .disabled,
      false
    );

  }
);
