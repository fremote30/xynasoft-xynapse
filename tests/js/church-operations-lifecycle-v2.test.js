const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = process.cwd();

function source(name) {
  return fs.readFileSync(
    path.join(ROOT, "ui-faith-v2-unified/js", name),
    "utf8"
  );
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function element() {
  return {
    hidden: false,
    disabled: false,
    value: "",
    textContent: "",
    innerHTML: "",
    dataset: {},
    children: [],
    listeners: {},
    classList: { add() {}, remove() {} },
    addEventListener(type, fn) {
      this.listeners[type] = fn;
    },
    async dispatch(type) {
      if (this.listeners[type]) {
        return this.listeners[type]({ target: this });
      }
    },
    replaceChildren(...items) {
      this.children = items;
    },
    append(...items) {
      this.children.push(...items);
    },
    add(item) {
      this.children.push(item);
    },
    querySelectorAll() {
      return [];
    }
  };
}

function environment(files) {
  const elements = new Map();

  const document = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, element());
      return elements.get(id);
    },
    createElement() {
      return element();
    }
  };

  function Option(text, value) {
    return { text, value, selected: false };
  }

  const window = {};
  const context = vm.createContext({
    window,
    document,
    Option,
    console,
    setTimeout,
    clearTimeout
  });

  for (const file of files) {
    vm.runInContext(source(file), context, { filename: file });
  }

  return {
    window,
    elements,
    get: document.getElementById.bind(document)
  };
}

function response(body = {}, status = 200) {
  return {
    status,
    ok: status >= 200 && status < 300,
    async json() { return body; }
  };
}

function churchContext() {
  return {
    church: { id: 77, name: "Grace Church" },
    membership: { user_id: 12, role: "pastor" },
    permissions: ["groups.manage"],
    capabilities: {}
  };
}

async function readyOperations(env, api) {
  env.window.apiFetch = async (url) => {
    if (url.endsWith("/events")) {
      return response({ events: [{ id: 9, title: "Sunday Service" }] });
    }
    if (url.endsWith("/members")) {
      return response({
        members: [{ id: 5, user: { name: "Member Five" } }]
      });
    }
    if (url.endsWith("/groups")) {
      return response({ groups: [{ id: 3, name: "Worship Team" }] });
    }
    throw new Error(`Unexpected URL: ${url}`);
  };

  env.window.XynaFaithChurchOperationsV2 = api;

  assert.equal(
    await env.window.XynaFaithChurchOperationsUIV2.init(churchContext()),
    true
  );

  env.get("churchOperationsEvent").value = "9";
  await env.get("churchOperationsEvent").dispatch("change");
}

test("unavailable Church Space resets both Operations controllers", () => {
  const env = environment(["church-space.js"]);
  let uiResets = 0;
  let apiResets = 0;

  env.window.XynaFaithChurchOperationsUIV2 = {
    reset() { uiResets++; }
  };
  env.window.XynaFaithChurchOperationsV2 = {
    reset() { apiResets++; }
  };

  // No apiFetch forces the unavailable state.
  return env.window.loadChurchSpace().then(() => {
    assert.equal(uiResets, 1);
    assert.equal(apiResets, 1);
    assert.equal(env.get("churchSpaceContent").hidden, true);
  });
});

test("failed attendance refresh never reports successful save", async () => {
  const env = environment(["church-operations-ui-v2.js"]);
  let attendanceCalls = 0;

  const api = {
    async listAttendance() {
      attendanceCalls++;
      if (attendanceCalls > 1) {
        throw new Error("Attendance refresh unavailable");
      }
      return { attendance: [] };
    },
    async listAssignments() {
      return { assignments: [] };
    },
    async recordAttendance() {}
  };

  await readyOperations(env, api);
  env.get("churchAttendanceMember").value = "5";
  env.get("churchAttendanceStatus").value = "present";

  await env.get("churchAttendanceSaveButton").dispatch("click");

  assert.match(
    env.get("churchOperationsState").textContent,
    /Attendance refresh unavailable/
  );
  assert.doesNotMatch(
    env.get("churchOperationsState").textContent,
    /Attendance saved/
  );
});

test("failed assignment refresh never reports successful save", async () => {
  const env = environment(["church-operations-ui-v2.js"]);
  let assignmentCalls = 0;

  const api = {
    async listAttendance() {
      return { attendance: [] };
    },
    async listAssignments() {
      assignmentCalls++;
      if (assignmentCalls > 1) {
        throw new Error("Assignment refresh unavailable");
      }
      return { assignments: [] };
    },
    async createAssignment() {}
  };

  await readyOperations(env, api);
  env.get("churchServiceGroup").value = "3";
  env.get("churchServiceMember").value = "5";
  env.get("churchServiceRole").value = "Singer";

  await env.get("churchServiceSaveButton").dispatch("click");

  assert.match(
    env.get("churchOperationsState").textContent,
    /Assignment refresh unavailable/
  );
  assert.doesNotMatch(
    env.get("churchOperationsState").textContent,
    /Service assignment saved/
  );
});

test("pending refresh cannot restore records after reset", async () => {
  const env = environment(["church-operations-ui-v2.js"]);
  const pending = deferred();
  let attendanceCalls = 0;

  const api = {
    async listAttendance() {
      attendanceCalls++;
      if (attendanceCalls === 2) return pending.promise;
      return { attendance: [] };
    },
    async listAssignments() {
      return { assignments: [] };
    }
  };

  await readyOperations(env, api);

  const refresh = env.get("churchOperationsEvent").dispatch("change");
  env.window.XynaFaithChurchOperationsUIV2.reset();

  pending.resolve({
    attendance: [{ id: 88, church_membership_id: 5, status: "present" }]
  });

  await refresh;

  assert.equal(env.get("churchAttendanceList").children.length, 0);
  assert.equal(env.get("churchOperationsEvent").children.length, 0);
});
