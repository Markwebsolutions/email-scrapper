import asyncio
import subprocess
import os
from fastapi import FastAPI, UploadFile, WebSocket, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()
app.state.websocket = None

# Paths
BASE_DIR = "/app"
SERVICE_JSON = f"{BASE_DIR}/service_account.json"
SHEET_ID_FILE = f"{BASE_DIR}/storage/sheet_id.txt"

# Env variable for Sheet ID
SHEET_ID_ENV = os.environ.get("SHEET_ID")

# Ensure storage dir exists
os.makedirs(f"{BASE_DIR}/storage", exist_ok=True)

# Serve static
app.mount("/static", StaticFiles(directory=f"{BASE_DIR}/static"), name="static")


# -------------------------
# Home
# -------------------------
@app.get("/")
def home():
    return FileResponse(f"{BASE_DIR}/static/index.html")


# -------------------------
# Upload service_account.json
# -------------------------
@app.post("/upload-json")
async def upload_json(file: UploadFile):
    content = await file.read()
    with open(SERVICE_JSON, "wb") as f:
        f.write(content)
    return {"status": "ok"}


# -------------------------
# Save sheet ID
# -------------------------
@app.post("/save-sheet-id")
async def save_sheet_id(sheet_id: str = Form(...)):
    if SHEET_ID_ENV is None:
        with open(SHEET_ID_FILE, "w") as f:
            f.write(sheet_id)
    return {"status": "ok"}


# -------------------------
# WebSocket for logs
# -------------------------
@app.websocket("/ws/logs")
async def logs_socket(ws: WebSocket):
    await ws.accept()
    app.state.websocket = ws
    try:
        while True:
            await ws.receive_text()
    except:
        app.state.websocket = None


# -------------------------
# Log streamer
# -------------------------
async def stream_logs(cmd):
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    while True:
        line = await asyncio.to_thread(process.stdout.readline)
        if not line:
            break
        if app.state.websocket:
            try:
                await app.state.websocket.send_text(line)
            except:
                pass

    process.wait()


# -------------------------
# Run Website Scraper (Python)
# -------------------------
@app.post("/run-website-scraper")
async def run_website_scraper():
    asyncio.create_task(stream_logs([
        "python", f"{BASE_DIR}/python_scripts/run_website_scraper.py"
    ]))
    return {"status": "started"}


# -------------------------
# Run Email Filter (Python)
# -------------------------
@app.post("/run-email-filter")
async def run_email_filter():
    asyncio.create_task(stream_logs([
        "python", f"{BASE_DIR}/python_scripts/run_email_filter.py"
    ]))
    return {"status": "started"}


# -------------------------
# Run Facebook Scraper (Node)
# -------------------------
@app.post("/run-facebook-scraper")
async def run_fb_scraper():
    # Determine Sheet ID
    sheet = SHEET_ID_ENV
    if not sheet and os.path.exists(SHEET_ID_FILE):
        with open(SHEET_ID_FILE) as f:
            sheet = f.read().strip()

    if not sheet:
        return {"status": "error", "message": "Sheet ID not set"}

    script = f"{BASE_DIR}/node_scripts/facebook_scraper.js"

    if not os.path.exists(script):
        return {"status": "error", "message": "FB script missing in container"}

    asyncio.create_task(stream_logs([
        "node", script,
        f"--key={SERVICE_JSON}",
        f"--sheet={sheet}"
    ]))

    return {"status": "started"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=port)
