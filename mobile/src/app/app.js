/**
 * ============================================================================
 * XynaFaith Mobile
 * ============================================================================
 *
 * File:
 *      app.js
 *
 * Purpose:
 *      Mobile application entry point.
 *
 * Responsibilities:
 *      - Start the application
 *      - Execute bootstrap
 *      - Handle fatal startup failures
 *
 * Author:
 *      Xynasoft
 *
 * ============================================================================
 */

"use strict";

/**
 * ============================================================================
 * Main Application
 * ============================================================================
 */

const XFApp = {

    /**
     * Start the application.
     *
     * @returns {Promise<void>}
     */
    async start() {

        try {

            XF.Logger.info("Launching XynaFaith Mobile...");

            await XFBootstrap.initialize();

            XF.Logger.info("Application started successfully.");

        }

        catch (error) {

            XF.Logger.error("Application startup failed.");

            XF.Logger.error(error);

            alert(
                "XynaFaith could not start. Please restart the application."
            );

        }

    }

};

/**
 * ============================================================================
 * Start application after DOM is ready.
 * ============================================================================
 */

document.addEventListener("DOMContentLoaded", async () => {

    await XFApp.start();

});