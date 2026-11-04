const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "../..");

const script = fs.readFileSync(
  path.join(root, "ui-faith-v2-unified/js/bible-quiz-member-v2.js"),
  "utf8"
);

const page = fs.readFileSync(
  path.join(root, "ui-faith-v2-unified/pages/bible-study.html"),
  "utf8"
);

const layout = fs.readFileSync(
  path.join(root, "ui-faith-v2-unified/layout.html"),
  "utf8"
);

test("member quiz workspace is registered", () => {
  assert.match(page, /id="xfMemberBibleQuizzes"/);
  assert.match(layout, /bible-quiz-member-v2\.js/);
});

test("member quiz uses authenticated church-scoped API", () => {
  assert.match(script, /window\.apiFetch/);
  assert.match(script, /encodeURIComponent\(church\)/);
});

test("member quiz submits only selected answers", () => {
  assert.match(script, /selected_option: selected\.value/);
  assert.match(script, /question_id: Number\(question\.id\)/);
  assert.doesNotMatch(script, /innerHTML\s*=/);
});

test("member quiz handles previous attempts", () => {
  assert.match(script, /\/my-attempts/);
});

test("member quiz invalidates stale church responses", () => {
  assert.match(script, /version === generation/);
  assert.match(script, /selectedChurch\(\) === church/);
});

test("member quiz tracks session identity", () => {
  assert.match(script, /function sessionIdentity\(\)/);
  assert.match(script, /sessionIdentity\(\) === session/);
  assert.match(script, /function verifySession\(\)/);
});

test("member quiz blocks uncertain duplicate submission", () => {
  assert.match(script, /submissionUncertain = true/);
  assert.match(script, /submissionUncertain = false/);
  assert.match(script, /busy \|\| !activeQuiz \|\| submissionUncertain/);
});

test("member quiz preserves uncertainty warning", () => {
  assert.match(script, /Submission may have succeeded/);
  assert.match(script, /Check My Results/);
});
