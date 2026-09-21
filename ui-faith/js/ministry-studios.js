/**
 * XynaFaith V2 — Ministry Studios
 *
 * Standalone Xyniva creation experiences:
 * - Sermon Series Builder
 * - Bible Study Generator
 * - Devotional Studio
 *
 * Commercial policy, entitlement selection,
 * metering and trusted identity remain server-side.
 */
(() => {
  "use strict";

  const $ = id =>
    document.getElementById(id);


  function value(id) {
    return String(
      $(id)?.value || ""
    ).trim();
  }


  function escapeHTML(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }


  function ministry() {
    const client =
      window.XynaFaithMinistry;

    if (
      !client ||
      typeof client.execute !== "function"
    ) {
      throw new Error(
        "Xyniva ministry service is unavailable"
      );
    }

    return client;
  }


  function setBusy(
    button,
    status,
    busy,
    message = ""
  ) {
    if (button) {
      button.disabled =
        Boolean(busy);
    }

    if (status && message) {
      status.hidden =
        false;

      status.textContent =
        message;
    }
  }


  function renderSeries(result) {
    const output =
      $("seriesOutput");

    if (!output) {
      return;
    }

    const sermons =
      Array.isArray(result?.sermons)
        ? result.sermons
        : [];

    output.innerHTML = `
      <div class="action-card">
        <span class="eyebrow">
          Sermon Series
        </span>

        <h2>
          ${escapeHTML(result.title)}
        </h2>

        <p>
          ${escapeHTML(result.description)}
        </p>
      </div>

      ${sermons.map(item => `
        <article
          class="action-card"
          data-series-sequence="${Number(
            item.sequence
          )}"
        >
          <span class="eyebrow">
            Sermon ${Number(item.sequence)}
          </span>

          <h3>
            ${escapeHTML(item.title)}
          </h3>

          ${
            item.scripture
              ? `
                <p>
                  <strong>Scripture:</strong>
                  ${escapeHTML(item.scripture)}
                </p>
              `
              : ""
          }

          <p>
            <strong>Theme:</strong>
            ${escapeHTML(item.theme)}
          </p>

          <p>
            ${escapeHTML(item.summary)}
          </p>

          <h4>
            Key Points
          </h4>

          <ul>
            ${
              Array.isArray(item.key_points)
                ? item.key_points
                    .map(point => `
                      <li>
                        ${escapeHTML(point)}
                      </li>
                    `)
                    .join("")
                : ""
            }
          </ul>
        </article>
      `).join("")}
    `;

    output.hidden =
      false;
  }


  function validSeries(
    result,
    expectedCount
  ) {
    if (
      !result ||
      typeof result !== "object" ||
      !String(result.title || "").trim() ||
      !String(
        result.description || ""
      ).trim() ||
      !Array.isArray(result.sermons) ||
      result.sermons.length !==
        expectedCount
    ) {
      return false;
    }

    return result.sermons.every(
      (item, index) =>
        Number(item?.sequence) ===
          index + 1 &&
        Boolean(
          String(
            item?.title || ""
          ).trim()
        ) &&
        Boolean(
          String(
            item?.theme || ""
          ).trim()
        ) &&
        Boolean(
          String(
            item?.summary || ""
          ).trim()
        ) &&
        Array.isArray(
          item?.key_points
        ) &&
        item.key_points.length > 0 &&
        item.key_points.every(
          point =>
            Boolean(
              String(
                point || ""
              ).trim()
            )
        )
    );
  }


  async function generateSermonSeries() {
    const button =
      $("seriesGenerateBtn");

    const status =
      $("seriesStatus");

    const topic =
      value("seriesTopic");

    const scripture =
      value("seriesScripture");

    if (
      !topic &&
      !scripture
    ) {
      window.showToast?.(
        "Enter a topic or scripture first",
        "error"
      );

      return;
    }

    const numberOfSermons =
      Number(
        value("seriesCount") || 4
      );

    if (
      !Number.isInteger(
        numberOfSermons
      ) ||
      numberOfSermons < 2 ||
      numberOfSermons > 12
    ) {
      window.showToast?.(
        "Choose between 2 and 12 sermons",
        "error"
      );

      return;
    }

    try {
      const client =
        ministry();

      setBusy(
        button,
        status,
        true,
        "Xyniva is building your sermon series…"
      );

      const execution =
        await client.execute(
          "sermon.series.generate",
          {
            topic,
            scripture,

            purpose:
              value("seriesPurpose"),

            number_of_sermons:
              numberOfSermons,

            denomination:
              value(
                "seriesDenomination"
              ) || "general",

            audience:
              value("seriesAudience"),

            context:
              value("seriesContext"),

            tone:
              value("seriesTone") ||
              "balanced"
          }
        );

      const result =
        execution?.result;

      if (
        !validSeries(
          result,
          numberOfSermons
        )
      ) {
        throw new Error(
          "Invalid sermon series response"
        );
      }

      renderSeries(
        result
      );

      if (status) {
        status.textContent =
          "Series ready";
      }

      window.showToast?.(
        "✨ Sermon series ready",
        "success"
      );

    } catch (err) {
      console.error(
        "Sermon series error:",
        err
      );

      if (status) {
        status.hidden =
          false;

        status.textContent =
          err?.uncertain
            ? (
                "Series generation status "
                + "could not be confirmed."
              )
            : (
                err?.message ||
                "Sermon series generation failed"
              );
      }

      window.showToast?.(
        err?.uncertain
          ? (
              "Series generation status "
              + "could not be confirmed"
            )
          : (
              err?.message ||
              "Sermon series generation failed"
            ),
        "error"
      );

    } finally {
      if (button) {
        button.disabled =
          false;
      }
    }
  }


  function validBibleStudy(
    result
  ) {
    if (
      !result ||
      typeof result !== "object" ||
      !String(result.title || "").trim() ||
      !String(result.objective || "").trim() ||
      !String(result.opening || "").trim() ||
      !Array.isArray(result.sections) ||
      result.sections.length < 1 ||
      !Array.isArray(
        result.discussion_questions
      ) ||
      result.discussion_questions.length < 1 ||
      !String(result.application || "").trim() ||
      !String(
        result.closing_prayer_prompt || ""
      ).trim()
    ) {
      return false;
    }

    const validSections =
      result.sections.every(
        section =>
          Boolean(
            String(
              section?.heading || ""
            ).trim()
          ) &&
          Boolean(
            String(
              section?.content || ""
            ).trim()
          )
      );

    const validQuestions =
      result.discussion_questions.every(
        question =>
          Boolean(
            String(
              question || ""
            ).trim()
          )
      );

    return (
      validSections &&
      validQuestions
    );
  }


  function renderBibleStudy(
    result
  ) {
    const output =
      $("studyOutput");

    if (!output) {
      return;
    }

    output.innerHTML = `
      <div class="action-card">
        <span class="eyebrow">
          Bible Study
        </span>

        <h2>
          ${escapeHTML(result.title)}
        </h2>

        ${
          result.scripture
            ? `
              <p>
                <strong>Scripture:</strong>
                ${escapeHTML(result.scripture)}
              </p>
            `
            : ""
        }

        <p>
          <strong>Objective:</strong>
          ${escapeHTML(result.objective)}
        </p>

        <h3>Opening</h3>

        <p>
          ${escapeHTML(result.opening)}
        </p>
      </div>

      ${result.sections.map(section => `
        <section class="action-card">
          <h3>
            ${escapeHTML(section.heading)}
          </h3>

          <p>
            ${escapeHTML(section.content)}
          </p>
        </section>
      `).join("")}

      <section class="action-card">
        <h3>
          Discussion Questions
        </h3>

        <ol>
          ${result.discussion_questions
            .map(question => `
              <li>
                ${escapeHTML(question)}
              </li>
            `)
            .join("")}
        </ol>

        <h3>
          Application
        </h3>

        <p>
          ${escapeHTML(result.application)}
        </p>

        <h3>
          Suggested Closing Prayer
        </h3>

        <p>
          ${escapeHTML(
            result.closing_prayer_prompt
          )}
        </p>
      </section>
    `;

    output.hidden =
      false;
  }


  async function generateBibleStudy() {
    const button =
      $("studyGenerateBtn");

    const status =
      $("studyStatus");

    const scripture =
      value("studyScripture");

    const topic =
      value("studyTopic");

    if (
      !scripture &&
      !topic
    ) {
      window.showToast?.(
        "Enter a scripture or topic first",
        "error"
      );

      return;
    }

    const sessionLength =
      Number(
        value("studyLength") || 60
      );

    if (
      !Number.isInteger(sessionLength) ||
      sessionLength < 15 ||
      sessionLength > 180
    ) {
      window.showToast?.(
        "Choose a session length between 15 and 180 minutes",
        "error"
      );

      return;
    }

    try {
      const client =
        ministry();

      setBusy(
        button,
        status,
        true,
        "Xyniva is preparing your Bible study…"
      );

      const execution =
        await client.execute(
          "bible_study.generate",
          {
            scripture,
            topic,

            audience:
              value("studyAudience"),

            denomination:
              value(
                "studyDenomination"
              ) || "general",

            context:
              value("studyContext"),

            session_length_minutes:
              sessionLength
          }
        );

      const result =
        execution?.result;

      if (
        !validBibleStudy(
          result
        )
      ) {
        throw new Error(
          "Invalid Bible study response"
        );
      }

      renderBibleStudy(
        result
      );

      if (status) {
        status.textContent =
          "Bible study ready";
      }

      window.showToast?.(
        "✨ Bible study ready",
        "success"
      );

    } catch (err) {
      console.error(
        "Bible study error:",
        err
      );

      if (status) {
        status.hidden =
          false;

        status.textContent =
          err?.uncertain
            ? (
                "Bible study generation status "
                + "could not be confirmed."
              )
            : (
                err?.message ||
                "Bible study generation failed"
              );
      }

      window.showToast?.(
        err?.uncertain
          ? (
              "Bible study generation status "
              + "could not be confirmed"
            )
          : (
              err?.message ||
              "Bible study generation failed"
            ),
        "error"
      );

    } finally {
      if (button) {
        button.disabled =
          false;
      }
    }
  }


  function validDevotional(
    result,
    expectedDays
  ) {
    if (
      !result ||
      typeof result !== "object" ||
      !String(result.title || "").trim() ||
      !Array.isArray(result.entries) ||
      result.entries.length !==
        expectedDays
    ) {
      return false;
    }

    return result.entries.every(
      (entry, index) =>
        Number(entry?.day) ===
          index + 1 &&
        Boolean(
          String(
            entry?.title || ""
          ).trim()
        ) &&
        Boolean(
          String(
            entry?.reflection || ""
          ).trim()
        ) &&
        Boolean(
          String(
            entry?.application || ""
          ).trim()
        ) &&
        Boolean(
          String(
            entry?.prayer || ""
          ).trim()
        )
    );
  }


  function renderDevotional(
    result
  ) {
    const output =
      $("devotionalOutput");

    if (!output) {
      return;
    }

    output.innerHTML = `
      <div class="action-card">
        <span class="eyebrow">
          Devotional
        </span>

        <h2>
          ${escapeHTML(result.title)}
        </h2>
      </div>

      ${result.entries.map(entry => `
        <article
          class="action-card"
          data-devotional-day="${Number(
            entry.day
          )}"
        >
          <span class="eyebrow">
            Day ${Number(entry.day)}
          </span>

          <h3>
            ${escapeHTML(entry.title)}
          </h3>

          ${
            entry.scripture
              ? `
                <p>
                  <strong>Scripture:</strong>
                  ${escapeHTML(entry.scripture)}
                </p>
              `
              : ""
          }

          <h4>
            Reflection
          </h4>

          <p>
            ${escapeHTML(entry.reflection)}
          </p>

          <h4>
            Application
          </h4>

          <p>
            ${escapeHTML(entry.application)}
          </p>

          <h4>
            Suggested Prayer
          </h4>

          <p>
            ${escapeHTML(entry.prayer)}
          </p>
        </article>
      `).join("")}
    `;

    output.hidden =
      false;
  }


  async function generateDevotional() {
    const button =
      $("devotionalGenerateBtn");

    const status =
      $("devotionalStatus");

    const topic =
      value("devotionalTopic");

    const scripture =
      value("devotionalScripture");

    if (
      !topic &&
      !scripture
    ) {
      window.showToast?.(
        "Enter a topic or scripture first",
        "error"
      );

      return;
    }

    const days =
      Number(
        value("devotionalDays") || 1
      );

    if (
      !Number.isInteger(days) ||
      days < 1 ||
      days > 31
    ) {
      window.showToast?.(
        "Choose between 1 and 31 devotional days",
        "error"
      );

      return;
    }

    try {
      const client =
        ministry();

      setBusy(
        button,
        status,
        true,
        "Xyniva is creating your devotional…"
      );

      const execution =
        await client.execute(
          "devotional.generate",
          {
            topic,
            scripture,

            audience:
              value(
                "devotionalAudience"
              ),

            denomination:
              value(
                "devotionalDenomination"
              ) || "general",

            context:
              value(
                "devotionalContext"
              ),

            tone:
              value(
                "devotionalTone"
              ) || "encouraging",

            days
          }
        );

      const result =
        execution?.result;

      if (
        !validDevotional(
          result,
          days
        )
      ) {
        throw new Error(
          "Invalid devotional response"
        );
      }

      renderDevotional(
        result
      );

      if (status) {
        status.textContent =
          "Devotional ready";
      }

      window.showToast?.(
        "✨ Devotional ready",
        "success"
      );

    } catch (err) {
      console.error(
        "Devotional generation error:",
        err
      );

      if (status) {
        status.hidden =
          false;

        status.textContent =
          err?.uncertain
            ? (
                "Devotional generation status "
                + "could not be confirmed."
              )
            : (
                err?.message ||
                "Devotional generation failed"
              );
      }

      window.showToast?.(
        err?.uncertain
          ? (
              "Devotional generation status "
              + "could not be confirmed"
            )
          : (
              err?.message ||
              "Devotional generation failed"
            ),
        "error"
      );

    } finally {
      if (button) {
        button.disabled =
          false;
      }
    }
  }


  window.generateSermonSeries =
    generateSermonSeries;

  window.generateBibleStudy =
    generateBibleStudy;

  window.generateDevotional =
    generateDevotional;

})();
