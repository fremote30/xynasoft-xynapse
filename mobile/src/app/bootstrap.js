/**
 * ============================================================================
 * XynaFaith Mobile
 * ============================================================================
 *
 * File:
 *      bootstrap.js
 *
 * Purpose:
 *      Coordinates application startup.
 *
 * Responsibilities:
 *      • Validate framework
 *      • Initialize application services
 *      • Restore previous user session
 *      • Initialize router
 *      • Launch the application
 *
 * Notes:
 *      This file contains NO business logic.
 *      It only orchestrates application startup.
 *
 * Author:
 *      Xynasoft
 *
 * ============================================================================
 */

"use strict";

/**
 * ============================================================================
 * Bootstrap Manager
 * ============================================================================
 */
const XFBootstrap = {

    /**
     * Indicates whether bootstrap has completed.
     *
     * @type {boolean}
     */
    initialized: false,

    /**
     * =========================================================================
     * Initialize application.
     *
     * @returns {Promise<void>}
     * =========================================================================
     */
    async initialize() {

        if (this.initialized) {

            XF.Logger.warn("Bootstrap already initialized.");

            return;

        }

        XF.Logger.info("======================================");
        XF.Logger.info("Starting XynaFaith Mobile...");
        XF.Logger.info("======================================");

        try {

            //------------------------------------------------------------
            // Verify required framework modules.
            //------------------------------------------------------------

            this.validateFramework();

            //------------------------------------------------------------
            // Display application information.
            //------------------------------------------------------------

            this.showApplicationInfo();

            //------------------------------------------------------------
            // Detect current platform.
            //------------------------------------------------------------

            this.initializePlatform();

            //------------------------------------------------------------
            // Register framework services.
            //------------------------------------------------------------

            this.registerServices();

            //------------------------------------------------------------
            // Initialize framework services.
            //------------------------------------------------------------

            await XFServiceRegistry.initializeAll();

            //------------------------------------------------------------
            // Restore previous session.
            //------------------------------------------------------------

            await this.restoreSession();

            //------------------------------------------------------------
            // Initialize application router.
            //------------------------------------------------------------

            this.initializeRouter();

            //------------------------------------------------------------
            // Bootstrap complete.
            //------------------------------------------------------------

            this.initialized = true;

            XF.Logger.info("Bootstrap completed successfully.");

        }

        catch (error) {

            XF.Logger.error("Bootstrap failed.");

            XF.Logger.error(error);

            throw error;

        }

    },

    /**
     * =========================================================================
     * Validate framework.
     * =========================================================================
     */
    validateFramework() {

        XF.Logger.info("Validating framework...");

        const requiredModules = [

            "Logger",
            "Platform",
            "Storage",
            "Session",
            "Network"

        ];

        requiredModules.forEach(module => {

            if (!XF[module]) {

                throw new Error(`Missing framework module: XF.${module}`);

            }

        });

        XF.Logger.info("Framework validation completed.");

    },

    /**
     * =========================================================================
     * Display application information.
     * =========================================================================
     */
    showApplicationInfo() {

        XF.Logger.info(`${XFConfig.APP.NAME} v${XFConfig.APP.VERSION}`);

        XF.Logger.info(XFConfig.APP.DESCRIPTION);

    },

    /**
     * =========================================================================
     * Detect application platform.
     * =========================================================================
     */
    initializePlatform() {

        const platform = XF.Platform.getPlatform();

        XF.Logger.info(`Running on: ${platform}`);

    },

    /**
     * =========================================================================
     * Register framework services.
     * =========================================================================
     */
    registerServices() {

        XF.Logger.info("Registering services...");

        XFServiceRegistry.register("Storage", XF.Storage);

        XFServiceRegistry.register("Network", XF.Network);

        if (XF.API) {

            XFServiceRegistry.register("API", XF.API);

        }

        XFServiceRegistry.register("Session", XF.Session);

    },

    /**
     * =========================================================================
     * Restore previous user session.
     * =========================================================================
     *
     * @returns {Promise<void>}
     */
    async restoreSession() {

        XF.Logger.info("Restoring previous session...");

        const user = XF.Session.restore();

        if (!user) {

            XF.Logger.info("Guest session detected.");

            return;

        }

        const displayName =

            user.full_name ||

            user.name ||

            user.username ||

            "User";

        XF.Logger.info(`Welcome back ${displayName}`);

    },

    /**
     * =========================================================================
     * Initialize application router.
     * =========================================================================
     */
    initializeRouter() {

        if (!XF.Router) {

            XF.Logger.warn("Router not available.");

            return;

        }

        XF.Logger.info("Initializing router...");

        XF.Router.initialize();

    }

};