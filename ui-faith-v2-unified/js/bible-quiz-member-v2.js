(() => {
  "use strict";

  const ROOT = "xfMemberBibleQuizzes";
  let root = null;
  let generation = 0;
  let busy = false;
  let activeQuiz = null;
  let submissionUncertain = false;
  let session = null;

  function sessionIdentity() {
    return localStorage.getItem("access_token") || "";
  }

  function verifySession() {
    const current = sessionIdentity();

    if (current !== session) {
      session = current;
      invalidate();
      status(
        current
          ? "Session changed. Reload your church quizzes."
          : "Sign in to access Bible Quizzes."
      );
      return false;
    }

    return !!current;
  }


  const el = id => document.getElementById(id);

  function status(message) {
    const node = el("xfMemberQuizStatus");
    if (node) node.textContent = message;
  }

  function clearPanels() {
    for (const id of [
      "xfMemberQuizList",
      "xfMemberQuizActive",
      "xfMemberQuizResults"
    ]) {
      el(id)?.replaceChildren();
    }
  }

  function selectedChurch() {
    const id = Number(el("xfMemberQuizChurch")?.value);
    if (!Number.isSafeInteger(id) || id <= 0) {
      throw new Error("Select a valid church.");
    }
    return id;
  }

  function fillChurch() {
    const field = el("xfMemberQuizChurch");
    if (!field || field.value) return;

    for (const candidate of [
      window.currentChurchId,
      window.activeChurchId,
      window.currentChurch?.id,
      window.activeChurch?.id
    ]) {
      const id = Number(candidate);
      if (Number.isSafeInteger(id) && id > 0) {
        field.value = String(id);
        return;
      }
    }
  }

  async function request(church, path, method = "GET", body) {
    if (typeof window.apiFetch !== "function") {
      throw new Error("Sign in to access church Bible Quizzes.");
    }

    if (selectedChurch() !== church) {
      throw new Error("Church changed. Reload quizzes.");
    }

    const response = await window.apiFetch(
      "/api/v1/churches/" + encodeURIComponent(church) +
      "/bible-quizzes" + path,
      {
        method,
        headers: {"Content-Type": "application/json"},
        ...(body === undefined ? {} : {
          body: JSON.stringify(body)
        })
      }
    );

    if (response && typeof response.json === "function") {
      const data = await response.json();

      if (response.ok === false) {
        throw new Error(
          typeof data?.detail === "string"
            ? data.detail
            : "Bible Quiz request was rejected."
        );
      }

      return data;
    }

    if (!response || typeof response !== "object") {
      throw new Error("Unexpected Bible Quiz response.");
    }

    return response;
  }

  function collection(data, keys) {
    if (Array.isArray(data)) return data;

    for (const key of keys) {
      if (Array.isArray(data?.[key])) return data[key];
    }

    throw new Error("Unexpected list response from the server.");
  }

  function button(label, handler) {
    const node = document.createElement("button");
    node.type = "button";
    node.textContent = label;
    node.addEventListener("click", handler);
    return node;
  }

  function heading(text, level = "h3") {
    const node = document.createElement(level);
    node.textContent = String(text ?? "");
    return node;
  }

  function paragraph(text) {
    const node = document.createElement("p");
    node.textContent = String(text ?? "");
    return node;
  }

  function invalidate() {
    generation++;
    activeQuiz = null;
    submissionUncertain = false;
    clearPanels();
  }

  function isCurrent(version, church) {
    return version === generation &&
      root?.isConnected &&
      sessionIdentity() === session &&
      selectedChurch() === church;
  }

  async function loadQuizzes() {
    if (busy) return;

    if (!verifySession()) return;

    invalidate();
    const version = generation;
    let church;

    try {
      church = selectedChurch();
      busy = true;
      status("Loading published Bible Quizzes...");

      const data = await request(church, "");
      if (!isCurrent(version, church)) return;

      const quizzes = collection(data, ["quizzes", "items", "results"]);
      const panel = el("xfMemberQuizList");

      if (!quizzes.length) {
        panel.append(paragraph("No published quizzes yet."));
        status("No quizzes available.");
        return;
      }

      for (const quiz of quizzes) {
        const id = Number(quiz.id);
        if (!Number.isSafeInteger(id) || id <= 0) continue;

        const card = document.createElement("article");
        card.className = "xf-bq-card";

        card.append(
          heading(quiz.title || "Bible Quiz"),
          paragraph(quiz.scripture || ""),
          button("Take Quiz", () => openQuiz(id))
        );

        panel.append(card);
      }

      status("Select a quiz to begin.");
    } catch (error) {
      if (version === generation) status(error.message);
    } finally {
      busy = false;
    }
  }

  async function openQuiz(id) {
    if (busy) return;

    if (!verifySession()) return;

    invalidate();
    const version = generation;
    let church;

    try {
      church = selectedChurch();
      busy = true;
      status("Loading quiz...");

      const quiz = await request(
        church, "/" + encodeURIComponent(id)
      );

      if (!isCurrent(version, church)) return;

      if (!Array.isArray(quiz.questions) ||
          !quiz.questions.length) {
        throw new Error("This quiz has no available questions.");
      }

      activeQuiz = {id, church, version};

      const panel = el("xfMemberQuizActive");
      const form = document.createElement("form");

      form.append(heading(quiz.title || "Bible Quiz"));

      for (const question of quiz.questions) {
        const questionId = Number(question.id);

        if (!Number.isSafeInteger(questionId) ||
            questionId <= 0) {
          throw new Error("Invalid question received.");
        }

        const group = document.createElement("fieldset");
        const legend = document.createElement("legend");
        legend.textContent = question.question_text || "Question";
        group.append(legend);

        for (const [letter, key] of [
          ["A", "option_a"],
          ["B", "option_b"],
          ["C", "option_c"],
          ["D", "option_d"]
        ]) {
          const label = document.createElement("label");
          const input = document.createElement("input");

          input.type = "radio";
          input.name = "question_" + questionId;
          input.value = letter;
          input.required = true;

          label.append(
            input,
            document.createTextNode(
              " " + letter + ". " + String(question[key] || "")
            )
          );

          group.append(label);
        }

        form.append(group);
      }

      form.append(
        button("Submit Answers", () => submitQuiz(form, quiz))
      );

      panel.append(form);
      status("Answer every question before submitting.");
    } catch (error) {
      if (version === generation) status(error.message);
    } finally {
      busy = false;
    }
  }

  async function submitQuiz(form, quiz) {
    if (busy || !activeQuiz || submissionUncertain) return;
    if (!verifySession()) return;

    if (!form.reportValidity()) return;

    const {id, church, version} = activeQuiz;

    if (!isCurrent(version, church)) return;

    const answers = [];

    for (const question of quiz.questions) {
      const selected = form.querySelector(
        'input[name="question_' + Number(question.id) + '"]:checked'
      );

      if (!selected) {
        status("Please answer every question.");
        return;
      }

      answers.push({
        question_id: Number(question.id),
        selected_option: selected.value
      });
    }

    try {
      busy = true;
      submissionUncertain = true;
      status("Submitting answers...");

      const result = await request(
        church,
        "/" + encodeURIComponent(id) + "/submit",
        "POST",
        {answers}
      );

      if (!isCurrent(version, church)) return;

      const panel = el("xfMemberQuizResults");
      panel.replaceChildren();
      panel.append(heading("Quiz Submitted"));

      if (result.score !== undefined &&
          result.score !== null) {
        panel.append(paragraph("Score: " + result.score));
      }

      if (result.correct_count !== undefined &&
          result.correct_count !== null) {
        panel.append(paragraph(
          "Correct answers: " + result.correct_count
        ));
      }

      panel.append(
        paragraph("Your quiz attempt has been recorded.")
      );

      el("xfMemberQuizActive")?.replaceChildren();
      activeQuiz = null;
      submissionUncertain = false;
      status("Quiz submitted successfully.");
    } catch (error) {
      if (version === generation) {
        status(
          error.message +
          " Submission may have succeeded. Check My Results " +
          "before attempting this quiz again."
        );
      }
    } finally {
      busy = false;
    }
  }

  async function loadHistory() {
    if (busy) return;

    if (!verifySession()) return;

    invalidate();
    const version = generation;
    let church;

    try {
      church = selectedChurch();
      busy = true;
      status("Loading your quiz history...");

      const data = await request(church, "/my-attempts");
      if (!isCurrent(version, church)) return;

      const attempts = collection(
        data, ["attempts", "items", "results"]
      );

      const panel = el("xfMemberQuizResults");
      panel.append(heading("My Quiz Results"));

      if (!attempts.length) {
        panel.append(paragraph("No quiz attempts yet."));
      }

      for (const attempt of attempts) {
        const card = document.createElement("article");
        card.className = "xf-bq-card";

        card.append(
          paragraph("Quiz #" + (attempt.quiz_id ?? "")),
          paragraph(
            attempt.score === undefined
              ? "Attempt recorded"
              : "Score: " + attempt.score
          )
        );

        panel.append(card);
      }

      status("Quiz history loaded.");
    } catch (error) {
      if (version === generation) status(error.message);
    } finally {
      busy = false;
    }
  }

  function initialize() {
    const next = el(ROOT);
    if (!next || next === root) return;

    root = next;
    invalidate();
    busy = false;
    session = sessionIdentity();

    fillChurch();

    el("xfMemberQuizChurch")?.addEventListener(
      "change", () => {
        invalidate();
        status("Church changed. Load quizzes again.");
      }
    );

    el("xfMemberQuizLoad")?.addEventListener(
      "click", loadQuizzes
    );

    el("xfMemberQuizHistory")?.addEventListener(
      "click", loadHistory
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded", initialize, {once: true}
    );
  } else {
    initialize();
  }

  new MutationObserver(initialize).observe(
    document.documentElement,
    {childList: true, subtree: true}
  );
})();
