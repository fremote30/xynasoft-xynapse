// =====================================
// TOKEN HELPERS
// =====================================

window.getToken =
  function () {

    if (window.MobileAuthService) {
      return MobileAuthService.getToken();
    }

    return localStorage.getItem(
      "access_token"
    );
  };

window.setToken =
  async function (token) {

    if (window.MobileAuthService) {
      return await MobileAuthService.saveToken(token);
    }

    localStorage.setItem(
      "access_token",
      token
    );
  };

window.removeToken =
  async function () {

    if (window.MobileAuthService) {
      return await MobileAuthService.removeToken();
    }

    localStorage.removeItem(
      "access_token"
    );
  };


// =====================================
// AUTH STATUS
// =====================================

window.isAuthenticated =
  function () {

    return !!getToken();
  };


// =====================================
// AUTH HEADERS
// =====================================

window.getAuthHeaders =
  function (
    extra = {}
  ) {

    const token =
      getToken();

    return {

      ...(token
        ? {
            Authorization:
              `Bearer ${token}`
          }
        : {}),

      ...extra
    };
  };


// =====================================
// API FETCH
// =====================================

window.apiFetch =
  async function (
    url,
    options = {}
  ) {

    // =================================
    // MOBILE SDK
    // =================================

    if (window.MobileApi) {

      const method =
        (options.method || "GET").toUpperCase();

      switch (method) {

        case "POST":

          return MobileApi.post(
            url,
            options.body
              ? JSON.parse(options.body)
              : {}
          );

        case "PUT":

          return MobileApi.put(
            url,
            options.body
              ? JSON.parse(options.body)
              : {}
          );

        case "DELETE":

          return MobileApi.delete(
            url
          );

        default:

          return MobileApi.get(
            url
          );

      }

    }

    // =================================
    // WEB FALLBACK
    // =================================

    const headers = {

      "Content-Type":
        "application/json",

      ...getAuthHeaders(),

      ...(options.headers || {})

    };

    return fetch(
      url,
      {

        ...options,

        headers

      }
    );

  };


// =====================================
// HANDLE LOGIN SUCCESS
// =====================================

window.handleAuthSuccess =
  async function (
    data
  ) {

    if (
      !data ||
      !data.access_token
    ) {

      showToast(
        "Invalid auth response",
        "error"
      );

      return;
    }

    // =========================
    // SAVE TOKEN
    // =========================
    await setToken(
      data.access_token
    );
    // =========================
    // FETCH USER
    // =========================
    try {

      const user =
        await getCurrentUser();

      if (user) {

        window.currentUser =
          user;

        // =========================
        // MOBILE DRAWER USER
        // =========================
        if (
          typeof loadMobileDrawerUser ===
          "function"
        ) {

          loadMobileDrawerUser();
        }

        localStorage.setItem(
          "user",
          JSON.stringify(user)
        );

        localStorage.setItem(
          "userRole",
          user.role
        );
      }

    } catch (err) {

      console.error(
        "User fetch failed:",
        err
      );
    }

    showToast(
      "✅ Login successful",
      "success"
    );

    // =========================
    // ROUTE
    // =========================
    if (
      window.currentUser?.role ===
      "member"
    ) {

      navigate(
        "member-dashboard"
      );

    } else {

      navigate(
        "dashboard"
      );
    }
  };


// =====================================
// LOGOUT
// =====================================

window.logout =
  async function () {

    try {

      // =========================
      // CLEAR AUTH
      // =========================
      await removeToken();
      localStorage.removeItem(
        "user"
      );

      localStorage.removeItem(
        "userRole"
      );

      // =========================
      // CLEAR ACTIVE SESSION
      // =========================
      window.currentUser =
        null;

      window.currentGeneratedSermon =
        null;

      window.currentSermonId =
        null;

      // =========================
      // DO NOT REMOVE
      // USER DRAFTS
      // =========================
      // latest_sermon_<userId>
      // remains intact so users
      // can restore drafts later

      // =========================
      // REFRESH NAVBAR
      // =========================
      if (
        typeof renderNavbar ===
        "function"
      ) {

        renderNavbar();
      }

      // =========================
      // REFRESH MOBILE DRAWER
      // =========================
      if (
        typeof loadMobileDrawerUser ===
        "function"
      ) {

        loadMobileDrawerUser();
      }

      // =========================
      // CLOSE MOBILE DRAWER
      // =========================
      const drawer =
        document.getElementById(
          "mobileDrawer"
        );

      if (drawer) {

        drawer.classList.remove(
          "open"
        );
      }

      // =========================
      // SUCCESS
      // =========================
      showToast(
        "Logged out",
        "success"
      );

      // =========================
      // RETURN HOME
      // =========================
      navigate(
        "home"
      );

    } catch (err) {

      console.error(
        "Logout error:",
        err
      );
    }
  };
// =====================================
// CURRENT USER
// =====================================

window.getCurrentUser =
  async function () {

    const token =
      getToken();

    if (!token) {

      return null;
    }

    try {

      const response =
        await apiFetch(
          "/auth/me"
        );

      if (
        !response.ok
      ) {

        return null;
      }

      const user =
        await response.json();

      window.currentUser =
        user;

      return user;

    } catch (err) {

      console.error(
        "Get current user error:",
        err
      );

      return null;
    }
  };


// =====================================
// AUTH FORMS
// =====================================

window.bindAuthForms =
  function () {

    const loginForm =
      document.getElementById(
        "loginForm"
      );

    if (loginForm) {

      loginForm.onsubmit =
        async function (e) {

          e.preventDefault();

          try {

            const response =
              await apiFetch(
                "/auth/login",
                {
                  method: "POST",

                  body: JSON.stringify({

                    email:
                      document.getElementById(
                        "email"
                      ).value,

                    password:
                      document.getElementById(
                        "password"
                      ).value
                  })
                }
              );

            const data =
              await response.json();

            if (
              !response.ok
            ) {

              showToast(
                data.detail ||
                "Login failed",
                "error"
              );

              return;
            }

            await handleAuthSuccess(
              data
            );

          } catch (err) {

            console.error(
              "Login error:",
              err
            );

            showToast(
              "Login failed",
              "error"
            );
          }
        };
    }

    const registerForm =
      document.getElementById(
        "registerForm"
      );

    if (registerForm) {

      registerForm.onsubmit =
        async function (e) {

          e.preventDefault();

          try {

            const password =
              document.getElementById(
                "password"
              ).value;

            const confirm =
              document.getElementById(
                "confirmPassword"
              ).value;

            if (
              password !== confirm
            ) {

              showToast(
                "Passwords do not match",
                "error"
              );

              return;
            }

            const response =
              await apiFetch(
                "/auth/register",
                {
                  method: "POST",

                  body: JSON.stringify({

                    name:
                      document.getElementById(
                        "name"
                      ).value,

                    email:
                      document.getElementById(
                        "email"
                      ).value,

                    password
                  })
                }
              );

            const data =
              await response.json();

            if (
              !response.ok
            ) {

              showToast(
                data.detail ||
                "Registration failed",
                "error"
              );

              return;
            }

            showToast(
              "✅ Registration successful",
              "success"
            );

            // =========================
            // AUTO LOGIN
            // =========================
            const loginResponse =
              await apiFetch(
                "/auth/login",
                {
                  method: "POST",

                  body: JSON.stringify({

                    email:
                      document.getElementById(
                        "email"
                      ).value,

                    password
                  })
                }
              );

            const loginData =
              await loginResponse.json();

            await handleAuthSuccess(
              loginData
            );

          } catch (err) {

            console.error(
              "Register error:",
              err
            );

            showToast(
              "Registration failed",
              "error"
            );
          }
        };
    }
  };