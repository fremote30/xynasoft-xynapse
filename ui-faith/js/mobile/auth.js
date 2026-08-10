/**
 * ============================================================================
 * File: auth.js
 *
 * Purpose:
 * Authentication service for the XynaFaith Mobile Framework.
 *
 * Responsibilities:
 * - Determine authentication state
 * - Manage JWT tokens
 * - Login
 * - Logout
 *
 * Author:
 * Xynasoft
 * ============================================================================
 */

const XFAuth = {

    /**
     * Returns the current JWT token.
     *
     * @returns {string|null}
     */
    async getToken() {

        return await XF.Storage.get("access_token");

    },

    /**
     * Save the JWT token.
     *
     * @param {string} token
     */
    async setToken(token) {

        await XF.Storage.save("access_token", token);

    },

    /**
     * Returns true when the user is authenticated.
     *
     * @returns {boolean}
     */
    async isAuthenticated() {

        return !!(await this.getToken());

    },

    /**
     * Logout the current user.
     */
    /**
 * Logout the current user.
 *
 * @returns {Promise<void>}
 */
async logout() {

    XF.Logger.info("Logging out user.");

    await XF.Storage.remove("access_token");

    await XF.Storage.remove("refresh_token");

    await XF.Storage.remove("user");

    XF.Logger.info("User logged out successfully.");

}

};