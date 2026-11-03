const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { spawnSync } = require("node:child_process");
const { test } = require("node:test");

test("amber branch warnings select their source line without blocking Canvas rendering", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "drakon-text-browser-"));
  try {
    const url = pathToFileURL(path.join(__dirname, "index.html")).href + "#s=2&k=3";
    const harness = path.join(dir, "check.html");
    fs.writeFileSync(harness, `<!doctype html>
<pre id="result">PENDING</pre>
<iframe style="width:1400px;height:1000px"></iframe>
<script>
const frame = document.querySelector("iframe");
const wait = () => new Promise(resolve => setTimeout(resolve, 800));
function check(condition, message) { if (!condition) throw new Error(message); }
frame.onload = async function () {
  try {
    await wait();
    const doc = frame.contentDocument;
    const win = frame.contentWindow;
    const text = doc.getElementById("text");
    const warnings = doc.querySelectorAll("#diags li.warning");
    check(warnings.length === 1, "Expected exactly one branch warning");
    check(warnings[0].textContent.includes("Branch “B” is never reached"), "Wrong warning");
    check(win.getComputedStyle(warnings[0]).backgroundColor === "rgb(255, 246, 214)", "Warning is not amber");
    const gutter = doc.querySelector("#gutter .warning");
    check(gutter && gutter.textContent === "9", "Branch declaration is not highlighted");
    check(win.getComputedStyle(gutter).color === "rgb(148, 98, 0)", "Gutter is not amber");
    warnings[0].click();
    check(doc.activeElement === text, "Warning did not focus the Text view");
    check(text.value.slice(text.selectionStart, text.selectionEnd) === "    branch B", "Wrong line selected");
    check(doc.getElementById("render-error").style.display === "none", "Warning blocked drawing");
    check(doc.querySelector("#canvas-host canvas"), "Canvas was not mounted");
    const canvasText = doc.getElementById("canvas-host").textContent;
    for (const name of ["A", "B", "C", "D"]) {
      check(canvasText.includes(name), "Canvas omitted branch " + name);
    }
    // Making B part of the default path removes the warning on the next edit.
    text.value = "drakon\\n  silhouette All reachable\\n    branch A\\n      Do A\\n    branch B\\n      Do B";
    text.dispatchEvent(new win.Event("input"));
    await wait();
    check(!doc.querySelector("#diags li.warning"), "Stale branch warning");
    check(!doc.querySelector("#gutter .warning"), "Stale gutter warning");
    check(doc.getElementById("render-error").style.display === "none", "Default transition did not draw");
    document.getElementById("result").textContent = "PASS";
  } catch (error) {
    document.getElementById("result").textContent = "FAIL: " + error.message;
  }
};
frame.src = ${JSON.stringify(url)};
</script>`);
    const chrome = spawnSync(process.env.CHROME_BIN || "google-chrome", [
      "--headless", "--disable-gpu", "--no-first-run", "--disable-background-networking",
      "--allow-file-access-from-files", "--user-data-dir=" + path.join(dir, "profile"),
      "--virtual-time-budget=7000", "--dump-dom", pathToFileURL(harness).href
    ], { encoding: "utf8", timeout: 30000, maxBuffer: 4 * 1024 * 1024 });
    assert.ifError(chrome.error);
    assert.equal(chrome.status, 0, chrome.stderr);
    assert.match(chrome.stdout, /<pre id="result">PASS<\/pre>/,
      chrome.stdout.match(/<pre id="result">([^<]*)<\/pre>/)?.[1] || chrome.stdout);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
