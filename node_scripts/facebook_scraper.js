const puppeteerExtra = require("puppeteer-extra");
const stealth = require("puppeteer-extra-plugin-stealth");
const puppeteer = require("puppeteer");
const { google } = require("googleapis");
const pLimit = require("p-limit").default;
const minimist = require("minimist");
const path = require("path");
const fs = require("fs");

puppeteerExtra.use(stealth());

const argv = minimist(process.argv.slice(2));

const SERVICE_JSON = argv.key || path.join(__dirname, "service_account.json");
const SPREADSHEET_ID = argv.sheet;

if (!SPREADSHEET_ID) {
    console.error("❌ Missing --sheet=SheetID parameter");
    process.exit(1);
}

if (!fs.existsSync(SERVICE_JSON)) {
    console.error("❌ Service account JSON not found at", SERVICE_JSON);
    process.exit(1);
}

// ---------------------------
// Google Sheets Authentication
// ---------------------------
async function getSheets() {
    const auth = new google.auth.GoogleAuth({
        keyFile: SERVICE_JSON,
        scopes: ["https://www.googleapis.com/auth/spreadsheets"],
    });
    const client = await auth.getClient();
    return google.sheets({ version: "v4", auth: client });
}

// ---------------------------
// Read Links from Sheets
// ---------------------------
async function getFacebookLinks() {
    const sheets = await getSheets();
    const res = await sheets.spreadsheets.values.get({
        spreadsheetId: SPREADSHEET_ID,
        range: "Sheet1!A1:Z9999",
    });

    const rows = res.data.values || [];
    if (!rows.length) throw "Spreadsheet empty";

    const header = rows[0];
    const fbIndex = header.indexOf("Facebook Link");
    const emailIndex = header.indexOf("Business Email");

    if (fbIndex === -1) throw "Column 'Facebook Link' missing";
    if (emailIndex === -1) throw "Column 'Business Email' missing";

    const list = [];

    rows.slice(1).forEach((row, i) => {
        const fb = row[fbIndex];
        if (fb && fb.trim()) list.push({ row: i + 2, url: fb.trim() });
    });

    console.log(`Found ${list.length} URLs`);
    return { list, emailIndex };
}

// ---------------------------
// Extract Email From HTML
// ---------------------------
function extractEmail(text) {
    const regex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
    const found = text.match(regex);
    return found ? found[0] : "";
}

// ---------------------------
// Scrape Page
// ---------------------------
async function scrapeFacebookEmail(url, browser) {
    try {
        const page = await browser.newPage();

        await page.setUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36"
        );

        console.log(`Visiting → ${url}`);
        await page.goto(url, { waitUntil: "networkidle2", timeout: 35000 });
        await page.waitForTimeout(2500);

        const html = await page.content();
        await page.close();

        return extractEmail(html);
    } catch (err) {
        console.log("Error:", err.message);
        return "";
    }
}

// ---------------------------
// Convert column number to letter
// ---------------------------
function colLetter(n) {
    let s = "";
    while (n > 0) {
        let mod = (n - 1) % 26;
        s = String.fromCharCode(65 + mod) + s;
        n = Math.floor((n - mod) / 26);
    }
    return s;
}

// ---------------------------
// Write Back to Google Sheet
// ---------------------------
async function writeEmail(row, email, emailIndex) {
    const sheets = await getSheets();
    const col = colLetter(emailIndex + 1);

    await sheets.spreadsheets.values.update({
        spreadsheetId: SPREADSHEET_ID,
        range: `Sheet1!${col}${row}`,
        valueInputOption: "RAW",
        requestBody: { values: [[email]] },
    });

    console.log(`Saved ${email} → row ${row}`);
}

// ---------------------------
// MAIN FUNCTION
// ---------------------------
(async () => {
    console.log("🚀 FB Scraper Started");

    const { list, emailIndex } = await getFacebookLinks();

    const browser = await puppeteerExtra.launch({
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || puppeteer.executablePath(),
});

    const limit = pLimit(3);

    const tasks = list.map((item) =>
        limit(async () => {
            console.log(`Row ${item.row} — ${item.url}`);
            const email = await scrapeFacebookEmail(item.url, browser);
            await writeEmail(item.row, email, emailIndex);
            await new Promise((r) => setTimeout(r, 1000 + Math.random() * 1500));
        })
    );

    await Promise.all(tasks);

    await browser.close();
    console.log("🎉 Scraper Complete");
})();
