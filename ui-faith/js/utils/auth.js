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
            url,
            options.body
              ? JSON.parse(options.body)
              : null
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
    // SYNC MOBILE PUSH DEVICE
    // =========================
    if (
      window.NotificationService &&
      typeof NotificationService.syncToken === "function"
    ) {
      await NotificationService.syncToken();
    }

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
      // DEACTIVATE PUSH DEVICE
      // Must happen before access token removal.
      // =========================
      if (
        window.NotificationService &&
        typeof NotificationService.unregisterToken === "function"
      ) {
        await NotificationService.unregisterToken();
      }

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

// =====================================
// LOGIN IDENTITY FLOW
// Email or phone -> appropriate step
// =====================================

window.bindLoginIdentityFlow =
  function () {

    const identityForm =
      document.getElementById(
        "loginIdentityForm"
      );

    if (!identityForm) {
      return;
    }

    if (
      identityForm.dataset.bound ===
      "true"
    ) {
      return;
    }

    identityForm.dataset.bound =
      "true";

    const identityInput =
      document.getElementById(
        "loginIdentity"
      );

    const identityStep =
      document.getElementById(
        "loginIdentityStep"
      );

    const emailStep =
      document.getElementById(
        "loginEmailStep"
      );

    const phoneStep =
      document.getElementById(
        "loginPhoneStep"
      );

    const emailInput =
      document.getElementById(
        "email"
      );

    const emailDisplay =
      document.getElementById(
        "loginEmailDisplay"
      );

    const phoneDisplay =
      document.getElementById(
        "loginPhoneDisplay"
      );

    const identityError =
      document.getElementById(
        "loginIdentityError"
      );

    const emailBack =
      document.getElementById(
        "loginEmailBack"
      );

    const phoneBack =
      document.getElementById(
        "loginPhoneBack"
      );

    function showIdentityError(
      message
    ) {

      if (!identityError) {
        return;
      }

      identityError.textContent =
        message;

      identityError.style.display =
        message
          ? "block"
          : "none";
    }

    function returnToIdentity() {

      if (emailStep) {
        emailStep.hidden = true;
      }

      if (phoneStep) {
        phoneStep.hidden = true;
      }

      if (identityStep) {
        identityStep.hidden = false;
      }

      showIdentityError("");

      if (identityInput) {
        identityInput.focus();
      }
    }

    identityForm.addEventListener(
      "submit",
      function (event) {

        event.preventDefault();

        const identity =
          identityInput?.value
            ?.trim();

        if (!identity) {

          showIdentityError(
            "Enter your email address or phone number."
          );

          return;
        }

        showIdentityError("");

        // -----------------------------
        // EMAIL
        // -----------------------------

        if (identity.includes("@")) {

          if (emailInput) {
            emailInput.value =
              identity.toLowerCase();
          }

          if (emailDisplay) {
            emailDisplay.textContent =
              identity;
          }

          if (identityStep) {
            identityStep.hidden = true;
          }

          if (emailStep) {
            emailStep.hidden = false;
          }

          const password =
            document.getElementById(
              "password"
            );

          if (password) {
            password.focus();
          }

          return;
        }

        // -----------------------------
        // PHONE
        // -----------------------------

        const phoneCandidate =
          identity.replace(
            /[\s().-]/g,
            ""
          );

        if (
          /^\+?[0-9]{7,15}$/.test(
            phoneCandidate
          )
        ) {

          if (phoneDisplay) {
            phoneDisplay.textContent =
              identity;
          }

          if (identityStep) {
            identityStep.hidden = true;
          }

          if (phoneStep) {
            phoneStep.hidden = false;
          }

          return;
        }

        showIdentityError(
          "Enter a valid email address or phone number."
        );
      }
    );

    if (emailBack) {
      emailBack.addEventListener(
        "click",
        returnToIdentity
      );
    }

    if (phoneBack) {
      phoneBack.addEventListener(
        "click",
        returnToIdentity
      );
    }
  };


// =====================================
// PHONE LOGIN OTP FLOW
// =====================================

window.bindPhoneLoginFlow =
  function () {

    const sendButton =
      document.getElementById(
        "sendPhoneCodeButton"
      );

    if (!sendButton) {
      return;
    }

    if (
      sendButton.dataset.bound ===
      "true"
    ) {
      return;
    }

    sendButton.dataset.bound =
      "true";

    const verifyButton =
      document.getElementById(
        "verifyPhoneCodeButton"
      );

    const resendButton =
      document.getElementById(
        "resendPhoneCodeButton"
      );

    const phoneInput =
      document.getElementById(
        "loginIdentity"
      );

    const requestStep =
      document.getElementById(
        "phoneRequestStep"
      );

    const codeStep =
      document.getElementById(
        "phoneCodeStep"
      );

    const phoneDisplay =
      document.getElementById(
        "loginPhoneCodeDisplay"
      );

    const codeInput =
      document.getElementById(
        "phoneVerificationCode"
      );

    const errorElement =
      document.getElementById(
        "phoneLoginError"
      );


    function showError(message) {

      if (!errorElement) {
        return;
      }

      errorElement.textContent =
        message || "";

      errorElement.style.display =
        message
          ? "block"
          : "none";
    }


    function getPhone() {

      return String(
        phoneInput?.value || ""
      )
        .trim()
        .replace(
          /[\s().-]/g,
          ""
        );
    }


    async function sendCode() {

      showError("");

      const phone =
        getPhone();

      if (!phone.startsWith("+")) {

        showError(
          "Enter your phone number with country code, for example +1..."
        );

        return;
      }

      if (
        !window.XynaPhoneAuth
      ) {

        showError(
          "Phone authentication is unavailable."
        );

        return;
      }

      if (
        !window.XynaPhoneAuth
          .isAvailable()
      ) {

        showError(
          "Phone verification is available in the XynaFaith mobile app."
        );

        return;
      }

      sendButton.disabled =
        true;

      sendButton.textContent =
        "Sending Code...";

      try {

        await window.XynaPhoneAuth
          .sendCode(phone);

        if (requestStep) {
          requestStep.hidden =
            true;
        }

        if (codeStep) {
          codeStep.hidden =
            false;
        }

        if (phoneDisplay) {
          phoneDisplay.textContent =
            phone;
        }

        if (codeInput) {
          codeInput.value = "";
          codeInput.focus();
        }

      } catch (err) {

        console.error(
          "Phone code error:",
          err
        );

        showError(
          err?.message ||
          "Unable to send verification code."
        );

      } finally {

        sendButton.disabled =
          false;

        sendButton.textContent =
          "Send Verification Code";
      }
    }


    sendButton.addEventListener(
      "click",
      sendCode
    );


    if (resendButton) {

      resendButton.addEventListener(
        "click",
        async function () {

          resendButton.disabled =
            true;

          resendButton.textContent =
            "Sending...";

          try {

            showError("");

            await window.XynaPhoneAuth
              .sendCode(
                getPhone()
              );

          } catch (err) {

            showError(
              err?.message ||
              "Unable to resend verification code."
            );

          } finally {

            resendButton.disabled =
              false;

            resendButton.textContent =
              "Resend Code";
          }
        }
      );
    }


    if (verifyButton) {

      verifyButton.addEventListener(
        "click",
        async function () {

          const code =
            String(
              codeInput?.value || ""
            )
              .trim();

          if (
            !/^[0-9]{6}$/.test(
              code
            )
          ) {

            showError(
              "Enter the 6-digit verification code."
            );

            return;
          }

          verifyButton.disabled =
            true;

          verifyButton.textContent =
            "Verifying...";

          try {

            showError("");

            await window.XynaPhoneAuth
              .verifyCode(code);

            await window.XynaPhoneAuth
              .login();

          } catch (err) {

            console.error(
              "Phone login error:",
              err
            );

            if (
              err?.status === 404
            ) {

              showError(
                "No account is linked to this phone number. Create an account first."
              );

            } else {

              showError(
                err?.message ||
                "Phone verification failed."
              );
            }

          } finally {

            verifyButton.disabled =
              false;

            verifyButton.textContent =
              "Verify & Log In";
          }
        }
      );
    }

  };
