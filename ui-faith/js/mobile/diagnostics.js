/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Diagnostics
 * ==========================================================
 */

(() => {

    "use strict";

    window.XynaDiagnostics = {

        version() {
            return window.XynaVersion;
        },

        environment() {
            return window.XynaEnvironment;
        },

        platform() {
            return window.XynaPlatform || {};
        },

        online() {
            return navigator.onLine;
        },

        userAgent() {
            return navigator.userAgent;
        },

        print() {

            console.group("Xyna Diagnostics");

            console.table({

                App: window.XynaVersion?.appName,

                Version: window.XynaVersion?.version,

                Build: window.XynaVersion?.build,

                Environment: window.XynaEnvironment?.environment,

                API: window.XynaEnvironment?.apiBase,

                Online: navigator.onLine,

                Platform: window.XynaPlatform?.name || "Browser"

            });

            console.groupEnd();

        }

    };

})();