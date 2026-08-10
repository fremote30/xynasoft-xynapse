/**
 * ============================================================================
 * XynaFaith Mobile Framework
 * ============================================================================
 *
 * File:
 *      session.js
 *
 * Purpose:
 *      Session lifecycle management.
 *
 * Responsibilities:
 *      - Save authenticated sessions
 *      - Restore previous sessions
 *      - Clear active sessions
 *
 * Notes:
 *      All session data is persisted through XF.Storage, allowing
 *      the implementation to work seamlessly across:
 *
 *          - Web Browser
 *          - Android
 *          - iOS
 *
 * Author:
 *      Xynasoft
 *
 * ============================================================================
 */

const XFSession = {

    /**
     * ==========================================================
     * Save the authenticated user session.
     * ==========================================================
     *
     * @param {Object} user
     * @param {string} accessToken
     * @param {string} refreshToken
     *
     * @returns {Promise<void>}
     */
    async save(user, accessToken, refreshToken) {

        try {

            await XF.Storage.save("user", user);

            await XF.Storage.save("access_token", accessToken);

            await XF.Storage.save("refresh_token", refreshToken);

            XF.Logger.info("User session saved.");

        }

        catch (error) {

            XF.Logger.error("Failed to save user session.");

            console.error(error);

        }

    },

    /**
     * ==========================================================
     * Restore a previously authenticated session.
     * ==========================================================
     *
     * @returns {Promise<Object|null>}
     */
    async restore() {

        try {

            const user = await XF.Storage.get("user");

            if (user) {

                XF.Logger.info("User session restored.");

                return user;

            }

            XF.Logger.info("No previous session found.");

            return null;

        }

        catch (error) {

            XF.Logger.error("Failed to restore user session.");

            console.error(error);

            return null;

        }

    },

    /**
     * ==========================================================
     * Clear the current authenticated session.
     * ==========================================================
     *
     * @returns {Promise<void>}
     */
    async clear() {

        try {

            await XF.Storage.remove("user");

            await XF.Storage.remove("access_token");

            await XF.Storage.remove("refresh_token");

            XF.Logger.info("Session cleared.");

        }

        catch (error) {

            XF.Logger.error("Failed to clear session.");

            console.error(error);

        }

    }

};