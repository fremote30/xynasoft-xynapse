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
// Rewrite static web asset paths
// for Capacitor.
//
// IMPORTANT:
// Do not globally remove "/faith/".
// API routes and public/share URLs may
// intentionally contain that prefix.
// -------------------------------------

function rewriteStaticPaths(filePath) {

    let content =
        fs.readFileSync(
            filePath,
            "utf8"
        );

    content = content
        .replaceAll(
            'href="/faith/',
            'href="'
        )
        .replaceAll(
            'src="/faith/',
            'src="'
        )
        .replaceAll(
            "url('/faith/assets/",
            "url('assets/"
        )
        .replaceAll(
            'url("/faith/assets/',
            'url("assets/'
        );

    fs.writeFileSync(
        filePath,
        content,
        "utf8"
    );
}


function walk(directory) {

    for (
        const entry of
        fs.readdirSync(
            directory,
            { withFileTypes: true }
        )
    ) {

        const fullPath =
            path.join(
                directory,
                entry.name
            );

        if (entry.isDirectory()) {

            walk(fullPath);
            continue;
        }

        const extension =
            path.extname(
                entry.name
            ).toLowerCase();

        if (
            extension === ".html" ||
            extension === ".css"
        ) {

            rewriteStaticPaths(
                fullPath
            );
        }
    }
}

walk(destination);

console.log("");
console.log("✅ Build Complete");
console.log("");