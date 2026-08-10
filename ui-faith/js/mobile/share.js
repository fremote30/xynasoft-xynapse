/**
 * ============================================================================
 * File: share.js
 *
 * Purpose:
 * Provides native sharing capabilities.
 *
 * Responsibilities:
 * - Share text
 * - Share links
 * - Share sermons
 * - Share prayer requests
 *
 * ============================================================================
 */

const XFShare = {

    /**
     * Share content.
     */
    async share(title, text, url = "") {

        XF.Logger.info("Preparing share request.");

        if (navigator.share) {

            return navigator.share({

                title,

                text,

                url

            });

        }

        XF.Logger.warn("Native sharing unavailable.");

    }

};