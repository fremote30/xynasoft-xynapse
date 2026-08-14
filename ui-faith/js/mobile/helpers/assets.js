// ======================================================
// XYNASOFT MOBILE RUNTIME
// assets.js
//
// Central asset resolver.
//
// NEVER hardcode:
//
//     /faith/...
//
// anywhere else.
//
// ======================================================

(() => {

    function prefix() {

        return XynaPlatform.isMobile
            ? ""
            : "/faith/";

    }

    function normalize(path) {

        return path.replace(/^\/+/, "");

    }

    window.Assets = {

        root() {

            return prefix();

        },

        css(file) {

            return prefix() + normalize(file);

        },

        js(file) {

            return prefix() + normalize(file);

        },

        page(file) {

            return prefix() + "pages/" + normalize(file);

        },

        image(file) {

            return prefix() + "assets/" + normalize(file);

        },

        api(path = "") {

            return "/api/v1/" + normalize(path);

        }

    };

    console.log(
        "📦 Asset Root:",
        Assets.root()
    );

})();