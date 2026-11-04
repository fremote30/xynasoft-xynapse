const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const source = fs.readFileSync(
  path.join(__dirname, "../../ui-faith-v2-unified/js/church-navigation-v2.js"),
  "utf8"
);

function setup() {
  const ids = [
    "churchSpaceContent",
    "churchSpaceNavigation",
    "churchHomeSection",
    "churchCommunitySection",
    "churchPrayerSection",
    "churchTestimonySection",
    "churchOperationsSection",
    "churchPeopleSection",
    "churchPastoralCareWorkspace"
  ];

  const elements = new Map();

  for (const id of ids) {
    elements.set(id, {
      id,
      hidden: false,
      dataset: {},
      attributes: {},
      classes: new Set(),
      classList: {
        toggle(name, enabled) {
          if (enabled) this.owner.classes.add(name);
          else this.owner.classes.delete(name);
        },
        remove(name) {
          this.owner.classes.delete(name);
        }
      },
      setAttribute(name, value) {
        this.attributes[name] = value;
      },
      removeAttribute(name) {
        delete this.attributes[name];
      }
    });

    elements.get(id).classList.owner = elements.get(id);
  }

  const buttons = ["home", "community", "prayer", "testimonies", "management"]
    .map((view) => ({
      dataset: { churchView: view },
      hidden: view === "management",
      attributes: {},
      setAttribute(name, value) {
        this.attributes[name] = value;
      },
      removeAttribute(name) {
        delete this.attributes[name];
      }
    }));

  const nav = elements.get("churchSpaceNavigation");

  nav.querySelector = (selector) =>
    selector === '[data-church-view="management"]'
      ? buttons[4]
      : null;

  nav.querySelectorAll = () => buttons;
  nav.addEventListener = () => {};
  nav.contains = () => true;

  const context = {
    document: {
      getElementById: (id) => elements.get(id) || null
    },
    window: {}
  };

  vm.runInNewContext(source, context);

  return {
    controller: context.window.XynaFaithChurchNavigationV2,
    elements,
    buttons
  };
}

test("member sees four views but cannot access management", () => {
  const { controller, elements, buttons } = setup();

  assert.equal(controller.initialize({ capabilities: {}, permissions: [] }), true);
  assert.equal(buttons[4].hidden, true);
  assert.equal(controller.applyView("management"), false);

  assert.equal(controller.applyView("prayer"), true);
  assert.equal(
    elements.get("churchPrayerSection").classes.has("xf-church-view-inactive"),
    false
  );
  assert.equal(
    elements.get("churchHomeSection").classes.has("xf-church-view-inactive"),
    true
  );
});

test("authorized manager can access management view", () => {
  const { controller, elements, buttons } = setup();

  controller.initialize({
    capabilities: { can_view_members: true },
    permissions: []
  });

  assert.equal(buttons[4].hidden, false);
  assert.equal(controller.applyView("management"), true);

  assert.equal(
    elements.get("churchOperationsSection").classes.has("xf-church-view-inactive"),
    false
  );
});

test("reset removes inactive classes and revokes management", () => {
  const { controller, elements, buttons } = setup();

  controller.initialize({
    capabilities: { can_view_members: true }
  });

  controller.applyView("management");
  controller.reset();

  assert.equal(buttons[4].hidden, true);
  assert.equal(controller.applyView("management"), false);

  assert.equal(
    elements.get("churchHomeSection").classes.has("xf-church-view-inactive"),
    false
  );
});
