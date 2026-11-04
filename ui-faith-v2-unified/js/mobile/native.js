/* ==========================================================
   XynaFaith Native Bridge
   ----------------------------------------------------------
   Central bridge between the XynaFaith SPA and Capacitor.

   Version: 1.0
========================================================== */

(function () {

    "use strict";

    const XynaNative = {

        initialized: false,

        isNative() {
            return !!window.Capacitor;
        },

        platform() {

            if (!this.isNative()) {
                return "web";
            }

            return window.Capacitor.getPlatform();

        },

        async initialize() {

            if (this.initialized) {
                return;
            }

            console.log("====================================");
            console.log(" XynaFaith Native Bridge");
            console.log("====================================");

            console.log("Environment :", this.isNative() ? "Native App" : "Web Browser");
            console.log("Platform    :", this.platform());

            if (this.isNative()) {

                try {

                    const info = await window.Capacitor.Plugins?.Device?.getInfo?.();

                    if (info) {
                        console.log("Device:", info);
                    }

                } catch (err) {

                    console.warn("Device information unavailable.", err);

                }

            }

            this.initialized = true;

            console.log("Native Bridge Ready");

        }

    };

    window.XynaNative = XynaNative;

    document.addEventListener("DOMContentLoaded", async () => {

        await window.XynaNative.initialize();

    });

})();