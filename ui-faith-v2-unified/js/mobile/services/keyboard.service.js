/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Keyboard Service
 * ==========================================================
 */

(() => {

    "use strict";

    class KeyboardService {

        constructor() {

            this.initialized = false;

        }

        async initialize() {

            if (this.initialized) {
                return;
            }

            console.log("⌨️ Initializing Keyboard Service...");

            if (!window.Capacitor) {

                this.initialized = true;
                return;

            }

            try {

                const { Keyboard } = Capacitor.Plugins;

                if (!Keyboard) {

                    console.warn("Keyboard plugin unavailable.");

                    this.initialized = true;
                    return;

                }

                Keyboard.addListener(
                    "keyboardWillShow",
                    () => {

                        document.body.classList.add("keyboard-open");

                    }
                );

                Keyboard.addListener(
                    "keyboardWillHide",
                    () => {

                        document.body.classList.remove("keyboard-open");

                    }
                );

                this.initialized = true;

                console.log("✅ Keyboard Service Ready");

            }

            catch (error) {

                console.error(error);

            }

        }

    }

    window.KeyboardService =
        new KeyboardService();

})();