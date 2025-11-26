const terminal = document.getElementById("terminal");

function appendLog(msg) {
    terminal.textContent += msg + "\n";
    terminal.scrollTop = terminal.scrollHeight;
}

const ws = new WebSocket(`ws://${window.location.host}/ws/logs`);

ws.onmessage = (event) => appendLog(event.data);

// Upload JSON
async function uploadJSON() {
    let file = document.getElementById("jsonFile").files[0];
    let formData = new FormData();
    formData.append("file", file);

    await fetch("/upload-json", { method: "POST", body: formData });
    appendLog("JSON Uploaded");
}

// Save sheet ID
async function saveSheetID() {
    let id = document.getElementById("sheetId").value;
    let form = new FormData();
    form.append("sheet_id", id);

    await fetch("/save-sheet-id", { method: "POST", body: form });
    appendLog("Sheet ID Saved");
}

// Run scrapers
async function runWebsiteScraper() {
    await fetch("/run-website-scraper", { method: "POST" });
    appendLog("Website Scraper Started");
}

async function runFacebookScraper() {
    await fetch("/run-facebook-scraper", { method: "POST" });
    appendLog("Facebook Scraper Started");
}

async function runEmailFilter() {
    await fetch("/run-email-filter", { method: "POST" });
    appendLog("Email Filter Started");
}
ss