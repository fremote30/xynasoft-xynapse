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
      "ui-faith/js/ministry-studios.js"
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
    ...overrides
  };
}


function createEnvironment({
  ministryExecute
} = {}) {

  const elements = {
    seriesTopic:
      element({
        value: "Walking by Faith"
      }),

    seriesScripture:
      element({
        value: "Hebrews 11"
      }),

    seriesPurpose:
      element({
        value:
          "Help the church grow in faithful living."
      }),

    seriesCount:
      element({
        value: "4"
      }),

    seriesAudience:
      element({
        value: "Entire church"
      }),

    seriesDenomination:
      element({
        value: "pentecostal"
      }),

    seriesTone:
      element({
        value: "teaching"
      }),

    seriesContext:
      element({
        value: "Sunday services"
      }),

    seriesGenerateBtn:
      element(),

    seriesStatus:
      element({
        hidden: true
      }),

    seriesOutput:
      element({
        hidden: true
      }),

    studyScripture:
      element({
        value: "Romans 8:1-17"
      }),

    studyTopic:
      element({
        value: "Life in the Spirit"
      }),

    studyAudience:
      element({
        value: "Young adults"
      }),

    studyDenomination:
      element({
        value: "pentecostal"
      }),

    studyLength:
      element({
        value: "60"
      }),

    studyContext:
      element({
        value: "Wednesday Bible study"
      }),

    studyGenerateBtn:
      element(),

    studyStatus:
      element({
        hidden: true
      }),

    studyOutput:
      element({
        hidden: true
      }),

    devotionalTopic:
      element({
        value: "Trusting God"
      }),

    devotionalScripture:
      element({
        value: "Proverbs 3:5-6"
      }),

    devotionalDays:
      element({
        value: "3"
      }),

    devotionalAudience:
      element({
        value: "Church members"
      }),

    devotionalDenomination:
      element({
        value: "pentecostal"
      }),

    devotionalTone:
      element({
        value: "encouraging"
      }),

    devotionalContext:
      element({
        value: "Weekday discipleship"
      }),

    devotionalGenerateBtn:
      element(),

    devotionalStatus:
      element({
        hidden: true
      }),

    devotionalOutput:
      element({
        hidden: true
      })
  };


  const calls = {
    execute: [],
    toast: []
  };


  const window = {
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

    showToast(
      message,
      type
    ) {
      calls.toast.push({
        message,
        type
      });
    }
  };


  const document = {
    getElementById(id) {
      return (
        elements[id] ||
        null
      );
    }
  };


  const context = {
    window,
    document,
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
    elements,
    calls
  };
}


function seriesResult(
  count = 4
) {
  return {
    title:
      "Walking by Faith",

    description:
      "A connected series about faithful Christian living.",

    sermons:
      Array.from(
        {
          length: count
        },
        (_, index) => ({
          sequence:
            index + 1,

          title:
            `Faith Part ${index + 1}`,

          scripture:
            `Hebrews 11:${index + 1}`,

          theme:
            "Trusting God",

          summary:
            "Explore faithful trust in God.",

          key_points: [
            "Trust God's character",
            "Live by faith"
          ]
        })
      )
  };
}


test(
  "sermon series sends typed ministry input",
  async () => {

    let captured;

    const env =
      createEnvironment({
        ministryExecute:
          async (
            skill,
            input
          ) => {

            assert.equal(
              skill,
              "sermon.series.generate"
            );

            captured =
              input;

            return {
              result:
                seriesResult(4)
            };
          }
      });


    await env.window
      .generateSermonSeries();


    assert.equal(
      captured.topic,
      "Walking by Faith"
    );

    assert.equal(
      captured.scripture,
      "Hebrews 11"
    );

    assert.equal(
      captured.purpose,
      "Help the church grow in faithful living."
    );

    assert.equal(
      captured.number_of_sermons,
      4
    );

    assert.equal(
      captured.denomination,
      "pentecostal"
    );

    assert.equal(
      captured.audience,
      "Entire church"
    );

    assert.equal(
      captured.context,
      "Sunday services"
    );

    assert.equal(
      captured.tone,
      "teaching"
    );

    assert.equal(
      env.elements
        .seriesStatus
        .textContent,
      "Series ready"
    );

    assert.equal(
      env.elements
        .seriesOutput
        .hidden,
      false
    );
  }
);


test(
  "sermon series requires topic or scripture",
  async () => {

    const env =
      createEnvironment();

    env.elements
      .seriesTopic
      .value = "";

    env.elements
      .seriesScripture
      .value = "";


    await env.window
      .generateSermonSeries();


    assert.equal(
      env.calls.execute.length,
      0
    );

    assert.equal(
      env.calls.toast.at(-1)?.type,
      "error"
    );

    assert.match(
      env.calls.toast.at(-1)?.message ||
        "",
      /topic or scripture/
    );
  }
);


test(
  "sermon series rejects wrong sermon count",
  async () => {

    const env =
      createEnvironment({
        ministryExecute:
          async () => ({
            result:
              seriesResult(3)
          })
      });


    await env.window
      .generateSermonSeries();


    assert.match(
      env.elements
        .seriesStatus
        .textContent,
      /Invalid sermon series response/
    );

    assert.equal(
      env.elements
        .seriesOutput
        .hidden,
      true
    );
  }
);


test(
  "sermon series rejects invalid sequence",
  async () => {

    const result =
      seriesResult(4);

    result.sermons[1]
      .sequence = 7;


    const env =
      createEnvironment({
        ministryExecute:
          async () => ({
            result
          })
      });


    await env.window
      .generateSermonSeries();


    assert.match(
      env.elements
        .seriesStatus
        .textContent,
      /Invalid sermon series response/
    );
  }
);


test(
  "sermon series rejects blank key points",
  async () => {

    const result =
      seriesResult(4);

    result.sermons[0]
      .key_points = [
        "Valid point",
        "   "
      ];


    const env =
      createEnvironment({
        ministryExecute:
          async () => ({
            result
          })
      });


    await env.window
      .generateSermonSeries();


    assert.match(
      env.elements
        .seriesStatus
        .textContent,
      /Invalid sermon series response/
    );
  }
);


test(
  "sermon series escapes model supplied HTML",
  async () => {

    const result =
      seriesResult(4);

    result.title =
      "<script>alert('x')</script>";

    result.sermons[0]
      .title =
        "<img src=x onerror=alert(1)>";

    result.sermons[0]
      .key_points = [
        "<b>unsafe</b>"
      ];


    const env =
      createEnvironment({
        ministryExecute:
          async () => ({
            result
          })
      });


    await env.window
      .generateSermonSeries();


    const html =
      env.elements
        .seriesOutput
        .innerHTML;


    assert.doesNotMatch(
      html,
      /<script>/
    );

    assert.doesNotMatch(
      html,
      /<img src=x/
    );

    assert.doesNotMatch(
      html,
      /<b>unsafe<\/b>/
    );

    assert.match(
      html,
      /&lt;script&gt;/
    );

    assert.match(
      html,
      /&lt;img src=x/
    );

    assert.match(
      html,
      /&lt;b&gt;unsafe&lt;\/b&gt;/
    );
  }
);


test(
  "sermon series restores button after uncertain failure",
  async () => {

    const error =
      new Error(
        "Request outcome uncertain"
      );

    error.uncertain =
      true;


    const env =
      createEnvironment({
        ministryExecute:
          async () => {
            throw error;
          }
      });


    await env.window
      .generateSermonSeries();


    assert.equal(
      env.elements
        .seriesGenerateBtn
        .disabled,
      false
    );

    assert.match(
      env.elements
        .seriesStatus
        .textContent,
      /could not be confirmed/
    );
  }
);


function bibleStudyResult() {
  return {
    title:
      "Life in the Spirit",

    scripture:
      "Romans 8:1-17",

    objective:
      "Understand life in the Spirit.",

    opening:
      "Begin by considering the hope of Romans 8.",

    sections: [
      {
        heading:
          "No Condemnation",

        content:
          "Explore the opening movement of the passage."
      },
      {
        heading:
          "Life by the Spirit",

        content:
          "Consider how Paul describes life in the Spirit."
      }
    ],

    discussion_questions: [
      "What stands out in this passage?",
      "How should this shape daily Christian life?"
    ],

    application:
      "Identify one way to walk faithfully this week.",

    closing_prayer_prompt:
      "Invite the group to pray for faithful dependence on God."
  };
}


function devotionalResult(
  days = 3
) {
  return {
    title:
      "Trusting God",

    entries:
      Array.from(
        {
          length: days
        },
        (_, index) => ({
          day:
            index + 1,

          title:
            `Trusting God — Day ${index + 1}`,

          scripture:
            "Proverbs 3:5-6",

          reflection:
            "Reflect on trusting God rather than relying only on yourself.",

          application:
            "Entrust one decision to God today.",

          prayer:
            "A suggested prayer for deeper trust in God."
        })
      )
  };
}


test(
  "Bible study sends typed ministry input",
  async () => {

    let captured;

    const env =
      createEnvironment({
        ministryExecute:
          async (
            skill,
            input
          ) => {

            assert.equal(
              skill,
              "bible_study.generate"
            );

            captured =
              input;

            return {
              result:
                bibleStudyResult()
            };
          }
      });


    await env.window
      .generateBibleStudy();


    assert.equal(
      captured.scripture,
      "Romans 8:1-17"
    );

    assert.equal(
      captured.topic,
      "Life in the Spirit"
    );

    assert.equal(
      captured.audience,
      "Young adults"
    );

    assert.equal(
      captured.denomination,
      "pentecostal"
    );

    assert.equal(
      captured.context,
      "Wednesday Bible study"
    );

    assert.equal(
      captured.session_length_minutes,
      60
    );

    assert.equal(
      env.elements
        .studyStatus
        .textContent,
      "Bible study ready"
    );

    assert.equal(
      env.elements
        .studyOutput
        .hidden,
      false
    );
  }
);


test(
  "Bible study requires scripture or topic",
  async () => {

    const env =
      createEnvironment();

    env.elements
      .studyScripture
      .value = "";

    env.elements
      .studyTopic
      .value = "";


    await env.window
      .generateBibleStudy();


    assert.equal(
      env.calls.execute.length,
      0
    );

    assert.match(
      env.calls.toast.at(-1)?.message ||
        "",
      /scripture or topic/
    );
  }
);


test(
  "Bible study rejects malformed structured content",
  async () => {

    const result =
      bibleStudyResult();

    result.sections[0]
      .content = "   ";


    const env =
      createEnvironment({
        ministryExecute:
          async () => ({
            result
          })
      });


    await env.window
      .generateBibleStudy();


    assert.match(
      env.elements
        .studyStatus
        .textContent,
      /Invalid Bible study response/
    );

    assert.equal(
      env.elements
        .studyOutput
        .hidden,
      true
    );
  }
);


test(
  "Bible study escapes model supplied HTML",
  async () => {

    const result =
      bibleStudyResult();

    result.title =
      "<script>alert('x')</script>";

    result.sections[0]
      .heading =
        "<img src=x onerror=alert(1)>";

    result.discussion_questions[0] =
      "<b>unsafe question</b>";


    const env =
      createEnvironment({
        ministryExecute:
          async () => ({
            result
          })
      });


    await env.window
      .generateBibleStudy();


    const html =
      env.elements
        .studyOutput
        .innerHTML;


    assert.doesNotMatch(
      html,
      /<script>/
    );

    assert.doesNotMatch(
      html,
      /<img src=x/
    );

    assert.doesNotMatch(
      html,
      /<b>unsafe question<\/b>/
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


test(
  "devotional sends typed ministry input",
  async () => {

    let captured;

    const env =
      createEnvironment({
        ministryExecute:
          async (
            skill,
            input
          ) => {

            assert.equal(
              skill,
              "devotional.generate"
            );

            captured =
              input;

            return {
              result:
                devotionalResult(3)
            };
          }
      });


    await env.window
      .generateDevotional();


    assert.equal(
      captured.topic,
      "Trusting God"
    );

    assert.equal(
      captured.scripture,
      "Proverbs 3:5-6"
    );

    assert.equal(
      captured.days,
      3
    );

    assert.equal(
      captured.audience,
      "Church members"
    );

    assert.equal(
      captured.denomination,
      "pentecostal"
    );

    assert.equal(
      captured.context,
      "Weekday discipleship"
    );

    assert.equal(
      captured.tone,
      "encouraging"
    );

    assert.equal(
      env.elements
        .devotionalStatus
        .textContent,
      "Devotional ready"
    );

    assert.equal(
      env.elements
        .devotionalOutput
        .hidden,
      false
    );
  }
);


test(
  "devotional requires topic or scripture",
  async () => {

    const env =
      createEnvironment();

    env.elements
      .devotionalTopic
      .value = "";

    env.elements
      .devotionalScripture
      .value = "";


    await env.window
      .generateDevotional();


    assert.equal(
      env.calls.execute.length,
      0
    );

    assert.match(
      env.calls.toast.at(-1)?.message ||
        "",
      /topic or scripture/
    );
  }
);


test(
  "devotional rejects wrong entry count",
  async () => {

    const env =
      createEnvironment({
        ministryExecute:
          async () => ({
            result:
              devotionalResult(2)
          })
      });


    await env.window
      .generateDevotional();


    assert.match(
      env.elements
        .devotionalStatus
        .textContent,
      /Invalid devotional response/
    );

    assert.equal(
      env.elements
        .devotionalOutput
        .hidden,
      true
    );
  }
);


test(
  "devotional rejects invalid day sequence",
  async () => {

    const result =
      devotionalResult(3);

    result.entries[1]
      .day = 8;


    const env =
      createEnvironment({
        ministryExecute:
          async () => ({
            result
          })
      });


    await env.window
      .generateDevotional();


    assert.match(
      env.elements
        .devotionalStatus
        .textContent,
      /Invalid devotional response/
    );
  }
);


test(
  "devotional escapes model supplied HTML",
  async () => {

    const result =
      devotionalResult(3);

    result.title =
      "<script>alert('x')</script>";

    result.entries[0]
      .title =
        "<img src=x onerror=alert(1)>";

    result.entries[0]
      .reflection =
        "<b>unsafe reflection</b>";


    const env =
      createEnvironment({
        ministryExecute:
          async () => ({
            result
          })
      });


    await env.window
      .generateDevotional();


    const html =
      env.elements
        .devotionalOutput
        .innerHTML;


    assert.doesNotMatch(
      html,
      /<script>/
    );

    assert.doesNotMatch(
      html,
      /<img src=x/
    );

    assert.doesNotMatch(
      html,
      /<b>unsafe reflection<\/b>/
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
