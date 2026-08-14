const fs = require("fs");
const path = require("path");

const source = path.join(__dirname, "../../ui-faith");
const destination = path.join(__dirname, "../www");

console.log("");
console.log("=================================");
console.log("XynaFaith Mobile Builder");
console.log("=================================");
console.log("");

console.log("Source:");
console.log(source);

console.log("");

console.log("Destination:");
console.log(destination);

if (!fs.existsSync(source)) {
    console.error("❌ ui-faith folder not found.");
    process.exit(1);
}

fs.rmSync(destination, {
    recursive: true,
    force: true
});

fs.cpSync(source, destination, {
    recursive: true,
    filter(src) {

        const name = path.basename(src);

        if (name.startsWith(".")) return false;
        if (name.endsWith(".backup.html")) return false;
        if (name.endsWith(".bak")) return false;

        return true;
    }
});

// -------------------------------------
// Rewrite web paths for Capacitor
// -------------------------------------

const htmlFiles = [
    "layout.html",
    "index.html"
];

for (const file of htmlFiles) {

    const filePath = path.join(destination, file);

    if (!fs.existsSync(filePath))
        continue;

    let html = fs.readFileSync(filePath, "utf8");

    html = html.replaceAll('href="/faith/', 'href="');
    html = html.replaceAll('src="/faith/', 'src="');

    fs.writeFileSync(filePath, html, "utf8");
}

console.log("");
console.log("✅ Build Complete");
console.log("");