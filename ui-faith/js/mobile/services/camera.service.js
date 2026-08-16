/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Camera Service
 * ==========================================================
 *
 * Provides native Camera and Gallery access for Capacitor.
 * Returned media is converted into a File so the existing
 * XynaFaith profile upload pipeline can be reused.
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
        // Resolve Camera Plugin
        // =====================================================

        getCameraPlugin() {

            if (!window.Capacitor) {
                console.warn("Camera unavailable outside Capacitor.");
                return null;
            }

            const Camera =
                window.Capacitor?.Plugins?.Camera;

            if (!Camera) {
                console.warn("Camera plugin unavailable.");
                return null;
            }

            return Camera;
        }

        // =====================================================
        // Take Photo
        // =====================================================

        async takePhoto() {

            const Camera = this.getCameraPlugin();

            if (!Camera) {
                return {
                    success: false,
                    error: new Error("Camera plugin unavailable")
                };
            }

            try {

                const result = await Camera.takePhoto({
                    quality: 90,
                    saveToGallery: false,
                    includeMetadata: true
                });

                return await this.prepareResult(result);

            } catch (error) {

                console.error("Camera capture error:", error);

                return {
                    success: false,
                    error
                };
            }
        }

        // =====================================================
        // Choose From Gallery
        // =====================================================

        async choosePhoto() {

            const Camera = this.getCameraPlugin();

            if (!Camera) {
                return {
                    success: false,
                    error: new Error("Camera plugin unavailable")
                };
            }

            try {

                const galleryResult =
                    await Camera.chooseFromGallery({
                        quality: 90,
                        limit: 1,
                        includeMetadata: true
                    });

                const result =
                    galleryResult?.results?.[0];

                if (!result) {
                    return {
                        success: false,
                        cancelled: true
                    };
                }

                return await this.prepareResult(result);

            } catch (error) {

                console.error("Gallery selection error:", error);

                return {
                    success: false,
                    error
                };
            }
        }

        // =====================================================
        // Convert MediaResult Into File
        // =====================================================

        async prepareResult(result) {

            if (!result) {
                throw new Error("No image returned");
            }

            const source =
                result.webPath ||
                result.uri;

            if (!source) {
                throw new Error("Image URI unavailable");
            }

            const response =
                await fetch(source);

            if (!response.ok) {
                throw new Error("Could not read selected image");
            }

            const blob =
                await response.blob();

            const rawFormat =
                result.metadata?.format ||
                blob.type?.split("/")?.[1] ||
                "jpeg";

            const format =
                rawFormat === "jpg"
                    ? "jpeg"
                    : rawFormat.toLowerCase();

            const mimeType =
                blob.type ||
                `image/${format}`;

            const extension =
                format === "jpeg"
                    ? "jpg"
                    : format;

            const file =
                new File(
                    [blob],
                    `xynafaith-profile-${Date.now()}.${extension}`,
                    {
                        type: mimeType
                    }
                );

            return {
                success: true,
                file,
                uri: source,
                format
            };
        }
    }

    // =========================================================
    // Global Service
    // =========================================================

    window.CameraService =
        new CameraService();

    // =========================================================
    // Profile Helpers
    // =========================================================

    window.takeProfilePhoto = async () => {

        return window.CameraService.takePhoto();
    };

    window.chooseProfilePhoto = async () => {

        return window.CameraService.choosePhoto();
    };

    // =========================================================
    // Native Profile Upload Bridges
    // =========================================================

    function isNativeMobile() {

        try {

            if (!window.Capacitor) {
                return false;
            }

            if (typeof window.Capacitor.isNativePlatform === "function") {
                return window.Capacitor.isNativePlatform();
            }

            if (typeof window.Capacitor.getPlatform === "function") {
                return window.Capacitor.getPlatform() !== "web";
            }

            return false;

        } catch (error) {

            console.warn("Could not determine Capacitor platform:", error);

            return false;
        }
    }

    window.choosePastorProfilePhoto = async () => {

        if (!isNativeMobile()) {
            document.getElementById("profileImageFile")?.click();
            return;
        }

        const result =
            await window.CameraService.choosePhoto();

        if (result?.success && result.file) {
            await window.uploadPastorProfileImage?.(
                "profile",
                result.file
            );
        }
    };

    window.takePastorProfilePhoto = async () => {

        if (!isNativeMobile()) {
            document.getElementById("profileImageFile")?.click();
            return;
        }

        const result =
            await window.CameraService.takePhoto();

        if (result?.success && result.file) {
            await window.uploadPastorProfileImage?.(
                "profile",
                result.file
            );
        }
    };

    window.chooseMemberProfilePhoto = async () => {

        if (!isNativeMobile()) {
            document.getElementById("memberProfileImageFile")?.click();
            return;
        }

        const result =
            await window.CameraService.choosePhoto();

        if (result?.success && result.file) {
            await window.uploadMemberProfileImage?.(
                result.file
            );
        }
    };

    window.takeMemberProfilePhoto = async () => {

        if (!isNativeMobile()) {
            document.getElementById("memberProfileImageFile")?.click();
            return;
        }

        const result =
            await window.CameraService.takePhoto();

        if (result?.success && result.file) {
            await window.uploadMemberProfileImage?.(
                result.file
            );
        }
    };

})();
