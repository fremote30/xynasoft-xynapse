// ======================================================
// XYNASOFT MOBILE RUNTIME
// config.js
//
// Central platform detection.
//
// Used by:
//
//  - XynaFaith
//  - XynaLegal
//  - XynaSignal
//  - XynAssist
//
// Never hardcode platform logic anywhere else.
// ======================================================

(() => {

    const isCapacitor =
        !!window.Capacitor;

    const isAndroid =
        isCapacitor &&
        Capacitor.getPlatform() === "android";

    const isIOS =
        isCapacitor &&
        Capacitor.getPlatform() === "ios";

    const isWeb =
        !isCapacitor;

    window.XynaPlatform = {

        isWeb,

        isAndroid,

        isIOS,

        isMobile:
            isAndroid || isIOS,

        name:
            isAndroid
                ? "android"
                : isIOS
                    ? "ios"
                    : "web"

    };

    console.log(
        "📱 Platform:",
        window.XynaPlatform.name
    );

})();