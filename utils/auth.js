// =========================
// AUTH UTILS (SAFE + GLOBAL)
// =========================
const AUTH = {
  TOKEN_KEY: "access_token",

  isLoggedIn() {
    return !!localStorage.getItem(this.TOKEN_KEY);
  },

  login(token) {
    localStorage.setItem(this.TOKEN_KEY, token);
  },

  logout() {
    localStorage.removeItem(this.TOKEN_KEY);
    window.location.href = "/faith/login.html";
  }
};