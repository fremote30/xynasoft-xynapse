"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../../ui-faith-v2-unified");
const read = file => fs.readFileSync(path.join(root, file), "utf8");

const moduleSource = read("js/member-engagement-v2.js");
const routerSource = read("js/router.js");
const layoutSource = read("layout.html");
const dashboardSource = read("pages/member-dashboard.html");

test("reading plans and sermon notes routes are registered", () => {
  for (const route of ["reading-plans", "sermon-notes"]) {
    assert.match(routerSource, new RegExp(`"${route}"\\s*:`));
    assert.match(routerSource, new RegExp(`"${route}"\\s*,`));
  }
});

test("member routes initialize their workspaces", () => {
  assert.match(routerSource, /window\.initMemberReadingPlansV2\(\)/);
  assert.match(routerSource, /window\.initMemberSermonNotesV2\(\)/);
});

test("member script is loaded with defer", () => {
  assert.match(
    layoutSource,
    /<script\s+defer\s+src="\/ui-faith-v2-unified\/js\/member-engagement-v2\.js"><\/script>/
  );
});

test("dashboard preserves existing member data hooks", () => {
  const required = [
    "memberDashboardAvatar", "userName",
    "memberDashboardLocation", "memberFavoriteVerse",
    "pastorStatusBadge", "pastorUpgradeContainer",
    "pastorUpgradeCard", "pastorCardTitle",
    "pastorUpgradeMessage", "upgradePastorBtn",
    "dailyVersePreview", "memberFeed", "topSermons",
    "followingPastorsCount",
    "savedSermonsCount", "memberPrayerCount",
    "memberAnsweredPrayerCount", "suggestedPastors",
    "continueReadingSection", "dashboardPrayerTotal",
    "dashboardPrayerAnswered", "dashboardPrayerToday",
    "prayerWall"
  ];

  for (const id of required) {
    assert.ok(
      dashboardSource.includes(`id="${id}"`),
      `Missing dashboard element: ${id}`
    );
  }
});

test("reading plan workspace has required containers", () => {
  const page = read("pages/reading-plans.html");

  assert.match(page, /id="memberAvailablePlans"/);
  assert.match(page, /id="memberEnrolledPlans"/);
});

test("sermon notes workspace has required controls", () => {
  const page = read("pages/sermon-notes.html");

  for (const id of [
    "memberNoteForm", "memberNoteId", "memberNoteTitle",
    "memberNoteBody", "memberNoteClear", "memberNotesList",
    "memberNoteStatus"
  ]) {
    assert.ok(page.includes(`id="${id}"`));
  }
});

test("member module uses authenticated API access", () => {
  assert.match(moduleSource, /window\.apiFetch/);
  assert.match(moduleSource, /\/api\/v1\/member/);
});

test("reading progress uses boolean completion updates", () => {
  assert.match(
    moduleSource,
    /JSON\.stringify\(\{completed:\s*!day\.completed\}\)/
  );
});

test("sermon notes support create and update", () => {
  assert.match(
    moduleSource,
    /method:\s*id\s*\?\s*"PATCH"\s*:\s*"POST"/
  );
  assert.match(
    moduleSource,
    /JSON\.stringify\(\{title,\s*body\}\)/
  );
});

test("member module exposes both initializers", () => {
  const window = {};

  const context = vm.createContext({
    window,
    document: {
      getElementById() { return null; },
      createElement(tag) {
        return {
          tagName: tag,
          textContent: "",
          className: "",
          addEventListener() {}
        };
      }
    },
    console
  });

  vm.runInContext(moduleSource, context);

  assert.equal(typeof window.initMemberReadingPlansV2, "function");
  assert.equal(typeof window.initMemberSermonNotesV2, "function");
});

test("responsive member stylesheets exist", () => {
  const css = read("css/member-experience-v2.css");
  const dashboardCss = read("css/member-dashboard-v2.css");

  assert.match(css, /@media\s*\(max-width:\s*760px\)/);
  assert.match(dashboardCss, /@media\s*\(max-width:\s*640px\)/);
});

test("dashboard uses existing local hero asset", () => {
  assert.ok(
    fs.existsSync(path.join(root, "assets/hero.webp"))
  );

  assert.match(
    read("css/member-dashboard-v2.css"),
    /assets\/hero\.webp/
  );
});
