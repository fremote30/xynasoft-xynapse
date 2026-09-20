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
      "ui-faith/js/sermon.js"
    ),
    "utf8"
  );


function element(
  overrides = {}
) {

  return {
    value: "",
    textContent: "",
    innerHTML: "",
    hidden: false,
    disabled: false,

    style: {
      display: "",

      removeProperty() {},

      setProperty() {}
    },

    options: [],

    addEventListener() {},

    querySelector() {
      return null;
    },

    ...overrides
  };
}


function sermon() {

  return {
    id: 44,
    author_id: 7,

    title:
      "Walking by Faith",

    scripture:
      "Hebrews 11:1",

    introduction:
      "Faith shapes the believer's walk.",

    main_points: [
      {
        title:
          "Faith trusts God",

        content:
          "Faith rests in God's character."
      }
    ],

    application:
      "Trust God in daily decisions.",

    conclusion:
      "Continue walking by faith.",

    input:
      "Faith",

    message:
      "Faith",

    denomination:
      "pentecostal",

    audience:
      "Church",

    context:
      "Sunday service",

    local_context:
      "Sunday service",

    tone:
      "passionate",

    duration:
      "30"
  };
}


function researchResult() {

  return {
    title:
      "Research on Hebrews 11:1",

    scripture:
      "Hebrews 11:1",

    summary:
      "The passage introduces faith within the argument of Hebrews.",

    observations: [
      {
        heading:
          "Literary setting",

        content:
          "The verse opens a chapter of examples."
      }
    ],

    interpretation: [
      {
        heading:
          "Meaning",

        content:
          "Faith is presented as confident trust."
      }
    ],

    theological_perspectives: [
      {
        heading:
          "Traditions",

        content:
          "Christian traditions may emphasize different dimensions."
      }
    ],

    ministry_application: [
      {
        heading:
          "Pastoral use",

        content:
          "Encourage trust grounded in God."
      }
    ],

    cautions: [
      "Do not reduce faith to positive thinking."
    ]
  };
}


function createEnvironment({
  ministryExecute
} = {}) {

  const current =
    sermon();

  const elements = {
    denomination:
      element({
        value:
          "pentecostal",

        options: [
          {
            value:
              "pentecostal"
          }
        ]
      }),

    audience:
      element({
        value:
          "Church"
      }),

    context:
      element({
        value:
          "Sunday service"
      }),

    tone:
      element({
        value:
          "passionate",

        options: [
          {
            value:
              "passionate"
          }
        ]
      }),

    duration:
      element({
        value:
          "30",

        options: [
          {
            value:
              "30"
          }
        ]
      }),

    userInput:
      element({
        value:
          "Faith"
      }),

    bibleInput:
      element({
        value:
          "Hebrews 11:1"
      }),

    biblicalResearchQuestion:
      element({
        value:
          "What is the context?"
      }),

    biblicalResearchBtn:
      element(),

    biblicalResearchStatus:
      element({
        hidden: true
      }),

    biblicalResearchOutput:
      element({
        hidden: true
      }),

    sermonOutput:
      element(),

    saveSermonBtn:
      element(),

    updateSermonBtn:
      element(),

    emptyState:
      element(),

    collaborationSection:
      element()
  };

  const calls = {
    execute: [],
    render: [],
    storage: [],
    toast: [],
    save: 0,
    update: 0
  };

  const window = {
    currentUser: {
      id: 7,
      role: "pastor"
    },

    currentGeneratedSermon:
      current,

    currentSermonId:
      44,

    XynaFaithMinistry: {
      async execute(
        skill,
        input
      ) {

        calls.execute.push({
          skill,
          input
        });

        if (ministryExecute) {
          return ministryExecute(
            skill,
            input
          );
        }

        throw new Error(
          "Unexpected ministry execution"
        );
      }
    },

    localStorage: {
      setItem(
        key,
        value
      ) {
        calls.storage.push({
          key,
          value
        });
      },

      getItem() {
        return null;
      },

      removeItem() {}
    },

    addEventListener() {},

    scrollTo() {},

    location: {
      href: ""
    }
  };


  const document = {

    getElementById(id) {
      return (
        elements[id] ||
        null
      );
    },

    querySelectorAll(
      selector
    ) {

      if (
        selector ===
        "[data-refine-action]"
      ) {
        return [];
      }

      return [];
    },

    querySelector() {
      return null;
    },

    createElement() {
      return element();
    },

    addEventListener() {}
  };


  const storage = {
    getItem(
      key
    ) {
      return window.localStorage
        .getItem(key);
    },

    setItem(
      key,
      value
    ) {
      return window.localStorage
        .setItem(
          key,
          value
        );
    },

    removeItem(
      key
    ) {
      return window.localStorage
        .removeItem(key);
    }
  };


  const context = {
    window,
    document,
    storage,

    localStorage:
      window.localStorage,

    console,

    setTimeout,
    clearTimeout,

    Blob:
      function Blob() {},

    URL: {
      createObjectURL() {
        return "";
      },

      revokeObjectURL() {}
    }
  };


  context.showToast =
    function (
      message,
      type
    ) {
      calls.toast.push({
        message,
        type
      });
    };


  vm.createContext(
    context
  );

  vm.runInContext(
    SOURCE,
    context
  );


  // Override the renderer so the test observes
  // refinement without depending on DOM-heavy
  // sermon rendering behavior.
  window.renderCurrentSermon =
    function (
      value,
      scroll
    ) {
      calls.render.push({
        value,
        scroll
      });

      window.currentGeneratedSermon =
        value;

      window.currentSermonId =
        value?.id
          ? Number(value.id)
          : null;
    };


  window.saveCurrentSermon =
    function () {
      calls.save += 1;
    };


  window.updateCurrentSermon =
    function () {
      calls.update += 1;
    };


  return {
    window,
    elements,
    calls,
    originalSermon:
      current
  };
}


test(
  "structured refine preserves saved sermon identity without persisting",
  async () => {

    const env =
      createEnvironment({
        ministryExecute:
          async (
            skill
          ) => {

            assert.equal(
              skill,
              "sermon.refine"
            );

            return {
              result: {
                title:
                  "Walking by Deeper Faith",

                scripture:
                  "Hebrews 11:1",

                introduction:
                  "A deeper introduction.",

                main_points: [
                  {
                    title:
                      "Faith trusts God's character",

                    content:
                      "A deeper explanation."
                  }
                ],

                application:
                  "Trust God deliberately.",

                conclusion:
                  "Walk forward in faith."
              }
            };
          }
      });


    await env.window.refine(
      "deepen"
    );


    assert.equal(
      env.calls.execute.length,
      1
    );

    const request =
      env.calls.execute[0];

    assert.equal(
      request.skill,
      "sermon.refine"
    );

    assert.equal(
      request.input.sermon.id,
      undefined
    );

    assert.equal(
      request.input.sermon.author_id,
      undefined
    );

    assert.equal(
      request.input.sermon.title,
      "Walking by Faith"
    );


    const refined =
      env.window
        .currentGeneratedSermon;

    assert.equal(
      refined.id,
      44
    );

    assert.equal(
      refined.author_id,
      7
    );

    assert.equal(
      env.window.currentSermonId,
      44
    );

    assert.equal(
      refined.title,
      "Walking by Deeper Faith"
    );

    assert.equal(
      env.calls.save,
      0
    );

    assert.equal(
      env.calls.update,
      0
    );

    assert.equal(
      env.calls.render.length,
      1
    );
  }
);


test(
  "failed refinement leaves current sermon unchanged",
  async () => {

    const env =
      createEnvironment({
        ministryExecute:
          async () => {
            const error =
              new Error(
                "Refinement unavailable"
              );

            throw error;
          }
      });


    const before =
      env.window
        .currentGeneratedSermon;


    await env.window.refine(
      "simplify"
    );


    assert.equal(
      env.window
        .currentGeneratedSermon,
      before
    );

    assert.equal(
      env.window.currentSermonId,
      44
    );

    assert.equal(
      env.calls.render.length,
      0
    );

    assert.equal(
      env.calls.save,
      0
    );

    assert.equal(
      env.calls.update,
      0
    );
  }
);


test(
  "biblical research uses sermon context without mutating sermon",
  async () => {

    const result =
      researchResult();

    const env =
      createEnvironment({
        ministryExecute:
          async (
            skill
          ) => {

            assert.equal(
              skill,
              "biblical.research"
            );

            return {
              result
            };
          }
      });


    const before =
      env.window
        .currentGeneratedSermon;


    await env.window
      .researchCurrentSermon();


    assert.equal(
      env.calls.execute.length,
      1
    );

    const request =
      env.calls.execute[0];

    assert.equal(
      request.skill,
      "biblical.research"
    );

    assert.equal(
      request.input.scripture,
      "Hebrews 11:1"
    );

    assert.equal(
      request.input.topic,
      "Faith"
    );

    assert.equal(
      request.input.question,
      "What is the context?"
    );

    assert.equal(
      request.input.denomination,
      "pentecostal"
    );


    assert.equal(
      env.window
        .currentGeneratedSermon,
      before
    );

    assert.equal(
      env.window.currentSermonId,
      44
    );

    assert.equal(
      env.calls.render.length,
      0
    );

    assert.equal(
      env.calls.save,
      0
    );

    assert.equal(
      env.calls.update,
      0
    );


    assert.equal(
      env.elements
        .biblicalResearchOutput
        .hidden,
      false
    );

    assert.match(
      env.elements
        .biblicalResearchOutput
        .innerHTML,
      /Textual Observations/
    );

    assert.match(
      env.elements
        .biblicalResearchOutput
        .innerHTML,
      /Theological Perspectives/
    );

    assert.match(
      env.elements
        .biblicalResearchOutput
        .innerHTML,
      /Interpretive Cautions/
    );
  }
);


test(
  "research rendering escapes model supplied HTML",
  async () => {

    const result =
      researchResult();

    result.summary =
      "<script>alert('x')</script>";

    result.observations[0].content =
      "<img src=x onerror=alert(1)>";


    const env =
      createEnvironment({
        ministryExecute:
          async () => ({
            result
          })
      });


    await env.window
      .researchCurrentSermon();


    const html =
      env.elements
        .biblicalResearchOutput
        .innerHTML;


    assert.equal(
      html.includes(
        "<script>"
      ),
      false
    );

    assert.equal(
      html.includes(
        "<img src=x"
      ),
      false
    );

    assert.match(
      html,
      /&lt;script&gt;/
    );

    assert.match(
      html,
      /&lt;img src=x/
    );
  }
);
