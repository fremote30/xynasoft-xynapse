/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Camera Service
 * ==========================================================
 */

(() => {

    "use strict";

    class CameraService {

        constructor() {

            this.initialized = false;

        }

        // =====================================================
        // Initialize
        // =====================================================

        async initialize() {

            if (this.initialized) {
                return;
            }

            console.log("📷 Initializing Camera Service...");

            this.initialized = true;

            console.log("✅ Camera Service Ready");

        }

        // =====================================================
        // Take Photo
        // =====================================================

        async takePhoto() {

            return this.capture("CAMERA");

        }

        // =====================================================
        // Choose From Gallery
        // =====================================================

        async choosePhoto() {

            return this.capture("PHOTOS");

        }

        // =====================================================
        // Shared Capture Logic
        // =====================================================

        async capture(source) {

            if (!window.Capacitor) {

                console.warn("Browser mode.");

                return null;

            }

            try {

                const { Camera } =
                    Capacitor.Plugins;

                if (!Camera) {

                    console.warn("Camera plugin unavailable.");

                    return null;

                }

                const image =
                    await Camera.getPhoto({

                        quality: 90,

                        allowEditing: false,

                        resultType: "Uri",

                        source

                    });

                return {

                    success: true,

                    uri: image.webPath,

                    path: image.path,

                    format: image.format

                };

            }

            catch (error) {

                console.error(error);

                return {

                    success: false,

                    error

                };

            }

        }

    }

window.CameraService =
        new CameraService();


        window.takeProfilePhoto = async () => {

    return CameraService.takePhoto();

};

window.chooseProfilePhoto = async () => {

    return CameraService.choosePhoto();

};
})();