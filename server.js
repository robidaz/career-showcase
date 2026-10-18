const compression = require("compression");
const express = require("express");
const fs = require("fs");
const path = require("path");

// Load a local .env (gitignored) before reading any configuration.
loadEnvFile(path.join(__dirname, ".env"));

const app = express();
const PORT = process.env.PORT || 3000;
const INDEX_FILE = path.join(__dirname, "index.html");
const ASSETS_DIR = path.join(__dirname, "assets");

app.disable("x-powered-by");
app.use(compression());

// Syncfusion license key for the résumé viewer. It comes from the environment
// (or .env) so the key never lives in this public repository.
app.get("/syncfusion-license.js", (req, res) => {
  const key = (process.env.SYNCFUSION_LICENSE_KEY || "").trim();
  res.set("Cache-Control", "no-store");
  // No key: an empty value (not a 404, which logs a console error) tells the
  // viewer to skip Syncfusion and show the preview image instead.
  res.set("Content-Type", "application/javascript; charset=utf-8");
  res.set("X-Content-Type-Options", "nosniff");
  res.send(`window.SYNCFUSION_LICENSE_KEY = ${JSON.stringify(key)};\n`);
});

// Only ./assets is public. Missing files get a real 404, never index.html.
app.use(
  "/assets",
  express.static(ASSETS_DIR, {
    dotfiles: "deny",
    fallthrough: false,
    index: false,
    redirect: false,
  })
);

// Plain-text errors for /assets (the default handler can echo stack traces).
app.use("/assets", (err, req, res, next) => {
  const status = err.status || err.statusCode || 500;
  const messages = { 403: "Forbidden", 404: "Not found" };
  res.status(status).type("text/plain").send(messages[status] || "Error");
});

app.get("*", (req, res) => {
  res.sendFile(INDEX_FILE);
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

// Minimal .env parser: KEY=VALUE lines, "#" comments, optional quotes.
// Variables that are already set in the environment always win.
function loadEnvFile(filePath) {
  let contents;
  try {
    contents = fs.readFileSync(filePath, "utf8");
  } catch (err) {
    return;
  }

  for (const rawLine of contents.replace(/^\uFEFF/, "").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }

    const match = line.match(/^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!match) {
      continue;
    }

    const name = match[1];
    let value = match[2];
    const quote = value.charAt(0);
    if ((quote === '"' || quote === "'") && value.length > 1 && value.endsWith(quote)) {
      value = value.slice(1, -1);
    } else {
      value = value.replace(/\s+#.*$/, "");
    }

    if (process.env[name] === undefined) {
      process.env[name] = value;
    }
  }
}
