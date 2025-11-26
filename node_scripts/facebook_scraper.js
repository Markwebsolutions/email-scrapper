const puppeteerExtra = require("puppeteer-extra");
const stealth = require("puppeteer-extra-plugin-stealth");
const puppeteer = require("puppeteer");
const { google } = require("googleapis");
const pLimit = require("p-limit").default;
const minimist = require("minimist");

puppeteerExtra.use(stealth());

const argv = minimist(process.argv.slice(2));

const SERVICE_JSON = argv.key || "service_account.json";
const SPREADSHEET_ID = argv.sheet;

if (!SPREADSHEET_ID) {
    console.error("Missing --sheet=GoogleSheetID");
    process.exit(1);
}

// -----------------------------------------
// Google Sheets Auth
// -----------------------------------------
async function getSheets() {
    const auth = new google.auth.GoogleAuth({
        keyFile: SERVICE_JSON,
        scopes: ["https://www.googleapis.com/auth/spreadsheets"],
    });
    const client = await auth.getClient();
    return google.sheets({ version: "v4", auth: client });
}

// -----------------------------------------
// Read Facebook Links
// -----------------------------------------
async function getFacebookLinks() {
    const sheets = await getSheets();

    const res = await sheets.spreadsheets.values.get({
        spreadsheetId: SPREADSHEET_ID,
        range: "Sheet1!A1:Z9999",
    });

    const rows = res.data.values || [];
    const header = rows[0] || [];

    const fbIndex = header.indexOf("Facebook Link");
    const emailIndex = header.indexOf("Business Email");

    if (fbIndex === -1) throw "Facebook Link column missing!";
    if (emailIndex === -1) throw "Business Email column missing!";

    let list = [];

    for (let i = 1; i < rows.length; i++) {
        let fb = rows[i][fbIndex];
        if (fb && fb.trim() !== "")
            list.push({ row: i + 1, url: fb });
    }

    console.log(`Found ${list.length} Facebook URLs`);
    return { list, emailIndex };
}

// -----------------------------------------
// Extract email with regex
// -----------------------------------------
function extractEmail(text) {
    const regex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
    const found = text.match(regex);
    return found ? found[0] : "";
}

// -----------------------------------------
// Scrape Facebook Email
// -----------------------------------------
async function scrapeFacebookEmail(url, browser) {
    try {
        const page = await browser.newPage();
        await page.setUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36"
        );

        console.log(`Visiting ${url}`);
        await page.goto(url, { waitUntil: "networkidle2" });
        await new Promise(res => setTimeout(res, 3000));

        const html = await page.content();
        await page.close();

        return extractEmail(html);

    } catch (err) {
        console.log("Error:", err.message);
        return "";
    }
}

// -----------------------------------------
// Convert column index to A1 notation
// -----------------------------------------
function colLetter(n) {
    let s = "";
    while (n > 0) {
        let mod = (n - 1) % 26;
        s = String.fromCharCode(65 + mod) + s;
        n = Math.floor((n - mod) / 26);
    }
    return s;
}

// -----------------------------------------
// Write email back to Google Sheets
// -----------------------------------------
async function writeEmail(row, email, emailIndex) {
    const sheets = await getSheets();

    const col = colLetter(emailIndex + 1);

    await sheets.spreadsheets.values.update({
        spreadsheetId: SPREADSHEET_ID,
        range: `Sheet1!${col}${row}`,
        valueInputOption: "RAW",
        requestBody: { values: [[email]] }
    });

    console.log(`Saved ${email} → row ${row}`);
}

// -----------------------------------------
// MAIN SCRIPT
// -----------------------------------------
async function main() {
    console.log("FB scraper started");

    const { list, emailIndex } = await getFacebookLinks();

    const browser = await puppeteerExtra.launch({
        headless: true,
        executablePath: puppeteer.executablePath(),
        args: ["--no-sandbox", "--disable-setuid-sandbox"]
    });

    const limit = pLimit(7);

    const tasks = list.map(item =>
        limit(async () => {
            console.log(`Row ${item.row} — ${item.url}`);

            const email = await scrapeFacebookEmail(item.url, browser);

            if (email)
                console.log(`Found email: ${email}`);
            else
                console.log(`No email found`);

            await writeEmail(item.row, email, emailIndex);

            await new Promise(res => setTimeout(res, 1500 + Math.random() * 1500));
        })
    );

    await Promise.all(tasks);

    await browser.close();
    console.log("Facebook scraper complete");
}

main();
