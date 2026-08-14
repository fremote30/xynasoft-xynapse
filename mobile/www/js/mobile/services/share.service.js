/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Share Service
 * ==========================================================
 */

(() => {

    "use strict";

    class ShareService {

        constructor() {

            this.initialized = false;

        }

        async initialize() {

            if (this.initialized) {
                return;
            }

            console.log("📤 Initializing Share Service...");

            this.initialized = true;

            console.log("✅ Share Service Ready");

        }

        async share(options = {}) {

            if (!window.Capacitor) {

                console.warn("Browser mode.");

                return false;

            }

            try {

                const { Share } =
                    Capacitor.Plugins;

                if (!Share) {

                    console.warn("Share plugin unavailable.");

                    return false;

                }

                await Share.share({

                    title:
                        options.title || "XynaFaith",

                    text:
                        options.text || "",

                    url:
                        options.url || "",

                    dialogTitle:
                        options.dialogTitle ||
                        "Share"

                });

                return true;

            }

            catch (error) {

                console.error(error);

                return false;

            }

        }

        async shareSermon(title, body) {

            return this.share({

                title,

                text: body,

                dialogTitle:
                    "Share Sermon"

            });

        }

        async sharePrayer(title, body) {

            return this.share({

                title,

                text: body,

                dialogTitle:
                    "Share Prayer"

            });

        }

        async shareVerse(reference, verse) {

            return this.share({

                title: reference,

                text: verse,

                dialogTitle:
                    "Share Scripture"

            });

        }

    }

    window.ShareService =
        new ShareService();

})();