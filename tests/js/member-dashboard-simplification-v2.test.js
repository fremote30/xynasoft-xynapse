const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const root = "ui-faith-v2-unified";

const page = fs.readFileSync(
  `${root}/pages/member-dashboard.html`,
  "utf8"
);

const layout = fs.readFileSync(
  `${root}/layout.html`,
  "utf8"
);

test("trending sermons remains available", () => {
  assert.match(page, /id="topSermons"/);
  assert.match(page, /Trending Sermons/);
});

test("duplicate pastor discovery card is removed", () => {
  assert.doesNotMatch(page, /<h3>Find Pastors<\/h3>/);
});

test("Faith Insights is absent from the member dashboard", () => {
  assert.doesNotMatch(page, /<h3>Faith Insights<\/h3>/);
  assert.doesNotMatch(page, /id="aiInsights"/);
});

test("approved profile hooks remain intact", () => {
  for (const id of [
    "memberDashboardAvatar",
    "userName",
    "pastorUpgradeContainer",
    "pastorUpgradeCard"
  ]) {
    assert.match(page, new RegExp(`id="${id}"`));
  }
});

test("unused insight formatter is not loaded", () => {
  assert.doesNotMatch(
    layout,
    /member-dashboard-polish-v2\.js/
  );
});
