// ============================================================
// XYNAFAITH PHONE AUTHENTICATION
// Firebase Phone Auth -> XynaFaith API
// ============================================================

(() => {

  "use strict";

  // ----------------------------------------------------------
  // Helpers
  // ----------------------------------------------------------

  function normalizePhone(phone) {

    return String(phone || "")
      .trim()
      .replace(/[()\-\s]/g, "");
  }


  function isNativeApp() {

    return !!(
      window.Capacitor &&
      typeof window.Capacitor.isNativePlatform === "function" &&
      window.Capacitor.isNativePlatform()
    );
  }


  function getFirebaseAuthentication() {

    const plugin =
      window.Capacitor?.Plugins?.FirebaseAuthentication;

    if (!plugin) {

      throw new Error(
        "Firebase Authentication is not available"
      );
    }

    return plugin;
  }


  // ==========================================================
  // PHONE AUTH SERVICE
  // ==========================================================

  window.XynaPhoneAuth = {

    verificationId: null,
    phone: null,


    // --------------------------------------------------------
    // Availability
    // --------------------------------------------------------

    isAvailable() {

      return isNativeApp() &&
        !!window.Capacitor?.Plugins
          ?.FirebaseAuthentication;
    },


    // --------------------------------------------------------
    // SEND VERIFICATION CODE
    // --------------------------------------------------------

    async sendCode(phone) {

      const normalized =
        normalizePhone(phone);

      if (
        !normalized ||
        !normalized.startsWith("+")
      ) {

        throw new Error(
          "Enter your phone number with country code."
        );
      }

      const firebase =
        getFirebaseAuthentication();

      this.phone = normalized;
      this.verificationId = null;

      // Firebase phone authentication delivers the
      // verificationId through the phoneCodeSent event.
      const codeSentListener =
        await firebase.addListener(
          "phoneCodeSent",
          (event) => {

            if (event?.verificationId) {

              this.verificationId =
                event.verificationId;
            }
          }
        );

      try {

        await firebase.signInWithPhoneNumber({
          phoneNumber: normalized
        });

        // Wait briefly for phoneCodeSent.
        const timeoutAt =
          Date.now() + 15000;

        while (
          !this.verificationId &&
          Date.now() < timeoutAt
        ) {

          await new Promise(
            resolve =>
              setTimeout(resolve, 100)
          );
        }

        if (!this.verificationId) {

          throw new Error(
            "Verification code could not be started. Please try again."
          );
        }

        return {
          phoneNumber: normalized,
          verificationId:
            this.verificationId
        };

      } finally {

        if (
          codeSentListener &&
          typeof codeSentListener.remove ===
            "function"
        ) {

          await codeSentListener.remove();
        }
      }
    },



    // --------------------------------------------------------
    // VERIFY CODE
    // --------------------------------------------------------

    async verifyCode(code) {

      if (!this.verificationId) {

        throw new Error(
          "Phone verification has not been started."
        );
      }

      const verificationCode =
        String(code || "").trim();

      if (!verificationCode) {

        throw new Error(
          "Enter the verification code."
        );
      }

      const firebase =
        getFirebaseAuthentication();

      const result =
        await firebase.confirmVerificationCode({
          verificationId:
            this.verificationId,

          verificationCode
        });

      return result;
    },


    // --------------------------------------------------------
    // GET FIREBASE ID TOKEN
    // --------------------------------------------------------

    async getIdToken() {

      const firebase =
        getFirebaseAuthentication();

      const result =
        await firebase.getIdToken();

      if (!result?.token) {

        throw new Error(
          "Unable to create phone authentication token."
        );
      }

      return result.token;
    },


    // --------------------------------------------------------
    // LOGIN EXISTING XYNAFAITH USER
    // --------------------------------------------------------

    async login() {

      const idToken =
        await this.getIdToken();

      const response =
        await apiFetch(
          "/auth/phone",
          {
            method: "POST",

            body: JSON.stringify({
              id_token: idToken
            })
          }
        );

      const data =
        await response.json();

      if (!response.ok) {

        const error =
          new Error(
            data.detail ||
            "Phone login failed"
          );

        error.status =
          response.status;

        throw error;
      }

      await handleAuthSuccess(data);

      return data;
    },


    // --------------------------------------------------------
    // REGISTER NEW XYNAFAITH USER
    // --------------------------------------------------------

    async register({
      name,
      email = null
    }) {

      const idToken =
        await this.getIdToken();

      const body = {
        id_token: idToken,
        name: String(name || "").trim()
      };

      if (
        email &&
        String(email).trim()
      ) {

        body.email =
          String(email)
            .trim()
            .toLowerCase();
      }

      const response =
        await apiFetch(
          "/auth/phone/register",
          {
            method: "POST",
            body: JSON.stringify(body)
          }
        );

      const data =
        await response.json();

      if (!response.ok) {

        const error =
          new Error(
            data.detail ||
            "Phone registration failed"
          );

        error.status =
          response.status;

        throw error;
      }

      await handleAuthSuccess(data);

      return data;
    },


    // --------------------------------------------------------
    // RESET TEMPORARY STATE
    // --------------------------------------------------------

    reset() {

      this.verificationId = null;
      this.phone = null;
    }

  };

})();
