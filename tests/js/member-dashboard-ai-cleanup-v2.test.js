const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const root = "ui-faith-v2-unified";

const source = fs.readFileSync(
  `${root}/js/dashboard.js`,
  "utf8"
);

const page = fs.readFileSync(
  `${root}/pages/member-dashboard.html`,
  "utf8"
);

test("member dashboard does not request AI Insights", () => {
  const start = source.indexOf(
    "async function loadMemberDashboard()"
  );

  const end = source.indexOf(
    "async function loadTopSermons()"
  );

  assert.ok(start >= 0);
  assert.ok(end > start);

  const memberSource = source.slice(start, end);

  assert.doesNotMatch(
    memberSource,
    /loadAIInsights\s*\(/
  );
});

test("pastor dashboard retains AI Insights", () => {
  assert.match(
    source,
    /await loadAIInsights\(\);/
  );

  assert.match(
    source,
    /window\.loadAIInsights\s*=/
  );
});

test("member dashboard has no AI Insights container", () => {
  assert.doesNotMatch(
    page,
    /id="aiInsights"/
  );
});

test("trending sermons remains available", () => {
  assert.match(page, /id="topSermons"/);
  assert.match(
    source,
    /await loadTopSermons\(\);/
  );
});
