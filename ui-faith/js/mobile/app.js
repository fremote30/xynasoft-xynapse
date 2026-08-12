document.addEventListener("DOMContentLoaded", async () => {

    if (!window.XynaNative.ready)
        return;

    await XynaStatusBar.initialize();

    await XynaSplash.initialize();

    console.log("Mobile App Loaded");

});