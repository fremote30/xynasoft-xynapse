// =====================================
// STORAGE HELPERS
// =====================================

window.storage = {

  set(key, value) {

    localStorage.setItem(
      key,
      JSON.stringify(value)
    );
  },

  get(key) {

    const item =
      localStorage.getItem(key);

    if (!item) return null;

    try {

      return JSON.parse(item);

    } catch {

      return item;
    }
  },

  remove(key) {

    localStorage.removeItem(key);
  }
};