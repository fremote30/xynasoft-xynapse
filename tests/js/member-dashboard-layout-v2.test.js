const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const page = fs.readFileSync(
  "ui-faith-v2-unified/pages/member-dashboard.html",
  "utf8"
);

const layout = fs.readFileSync(
  "ui-faith-v2-unified/layout.html",
  "utf8"
);

const styles = fs.readFileSync(
  "ui-faith-v2-unified/css/member-dashboard-consolidated-v2.css",
  "utf8"
);

test("dashboard preserves dynamic content hooks", () => {
  const ids = [
    "topSermons",
    "suggestedPastors",
    "continueReadingSection",
    "memberPrayerCount",
    "memberAnsweredPrayerCount",
    "memberDashboardAvatar",
    "userName",
    "pastorUpgradeContainer"
  ];

  for (const id of ids) {
    assert.match(page, new RegExp(`id="${id}"`));
  }
});

test("consolidated stylesheet is linked", () => {
  assert.match(
    layout,
    /member-dashboard-consolidated-v2\.css/
  );
});

test("member profile is not restyled by consolidation", () => {
  assert.doesNotMatch(
    styles,
    /\.member-dashboard-hero\s*\{/
  );
});

test("dashboard retains established theme", () => {
  assert.match(page, /xf-member-feature-grid/);
  assert.match(page, /member-dashboard-hero/);
  assert.match(page, /member-prayer-section/);
});

test("mobile and reduced-motion rules are present", () => {
  assert.match(styles, /max-width:\s*640px/);
  assert.match(styles, /prefers-reduced-motion/);
});
