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
      "ui-faith/js/utils/auth.js"
    ),
    "utf8"
  );


function createEnvironment() {

  const values =
    new Map([
      [
        "latest_sermon_123",
        '{"title":"Draft"}'
      ],
      [
        "latest_sermon_999",
        '{"title":"Other User"}'
      ],
      [
        "last_saved_sermon_id",
        "42"
      ],
      [
        "unrelated_preference",
        "keep-me"
      ],
      [
        "access_token",
        "token"
      ],
      [
        "user",
        '{"id":123}'
      ],
      [
        "userRole",
        "pastor"
      ]
    ]);

  const removed = [];

  const localStorage = {

    getItem(key) {
      return values.has(key)
        ? values.get(key)
        : null;
    },

    setItem(
      key,
      value
    ) {
      values.set(
        key,
        String(value)
      );
    },

    removeItem(key) {
      removed.push(key);
      values.delete(key);
    }

  };

  let resetCalls = 0;

  const window = {

    currentUser: {
      id: 123,
      role: "pastor"
    },

    currentGeneratedSermon: {
      id: 42,
      title: "Draft"
    },

    currentSermonId: 42,

    XynivaStudio: {
      reset() {
        resetCalls += 1;
      }
    },

    NotificationService: {
      async unregisterToken() {}
    },

    navigate() {},

    location: {
      href: ""
    }
  };

  const context = {
    window,
    localStorage,
    console,

    storage: {
      get() {},
      set() {},
      remove() {}
    },

    apiFetch:
      async () => ({
        ok: true,
        json:
          async () => ({})
      }),

    fetch:
      async () => ({
        ok: true,
        json:
          async () => ({})
      }),

    renderNavbar() {},

    navigate() {},

    showToast() {},

    async removeToken() {
      localStorage.removeItem(
        "access_token"
      );
    },

    setTimeout,

    clearTimeout,

    document: {
      getElementById() {
        return null;
      },
      querySelectorAll() {
        return [];
      },
      addEventListener() {}
    }
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
    localStorage,
    values,
    removed,
    getResetCalls:
      () => resetCalls
  };

}


test(
  "logout clears only the current user's transient sermon draft",
  async () => {

    const env =
      createEnvironment();

    await env.window.logout();

    assert.equal(
      env.values.has(
        "latest_sermon_123"
      ),
      false
    );

    assert.equal(
      env.values.has(
        "last_saved_sermon_id"
      ),
      false
    );

    assert.equal(
      env.values.get(
        "latest_sermon_999"
      ),
      '{"title":"Other User"}'
    );

    assert.equal(
      env.values.get(
        "unrelated_preference"
      ),
      "keep-me"
    );

    assert.equal(
      env.window
        .currentGeneratedSermon,
      null
    );

    assert.equal(
      env.window
        .currentSermonId,
      null
    );

    assert.equal(
      env.window.currentUser,
      null
    );

    assert.equal(
      env.getResetCalls(),
      1
    );

  }
);
