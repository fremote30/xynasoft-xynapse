/**
 * ==========================================================
 * XYNASOFT MOBILE SDK
 * Network Banner
 * ==========================================================
 */

(() => {

    "use strict";

    function showOfflineBanner() {

        let banner = document.getElementById("networkBanner");

        if (!banner) {

            banner = document.createElement("div");

            banner.id = "networkBanner";

            banner.style.position = "fixed";
            banner.style.top = "0";
            banner.style.left = "0";
            banner.style.right = "0";
            banner.style.zIndex = "99999";
            banner.style.padding = "12px";
            banner.style.background = "#d32f2f";
            banner.style.color = "#fff";
            banner.style.fontWeight = "600";
            banner.style.textAlign = "center";

            document.body.appendChild(banner);

        }

        banner.innerHTML = "📶 You're offline. Some features may be unavailable.";

        banner.style.display = "block";

    }

    function hideOfflineBanner() {

        const banner = document.getElementById("networkBanner");

        if (banner) {

            banner.style.display = "none";

        }

    }

    window.NetworkBanner = {

        show: showOfflineBanner,

        hide: hideOfflineBanner

    };

})();