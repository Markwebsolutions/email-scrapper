import asyncio
import subprocess
import os
from fastapi import FastAPI, UploadFile, WebSocket, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()
app.state.websocket = None

# Paths and environment
SERVICE_JSON = "service_account.json"
SHEET_ID_FILE = "storage/sheet_id.txt"
SHEET_ID_ENV = os.environ.get("SHEET_ID")  # optional env variable

# Ensure storage folder exists
os.makedirs("storage", exist_ok=True)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------------------------------------
# Home
# ---------------------------------------
@app.get("/")
def home():
    return FileResponse("static/index.html")

# ---------------------------------------
# Upload service account JSON
# ---------------------------------------
@app.post("/upload-json")
async def upload_json(file: UploadFile):
    content = await file.read()
    with open(SERVICE_JSON, "wb") as f:
        f.write(content)
    return {"status": "ok"}

# ---------------------------------------
# Save Sheet ID
# ---------------------------------------
@app.post("/save-sheet-id")
async def save_sheet_id(sheet_id: str = Form(...)):
    # Save to file only if env variable not set
    if SHEET_ID_ENV is None:
        with open(SHEET_ID_FILE, "w") as f:
            f.write(sheet_id)
    return {"status": "ok"}

# ---------------------------------------
# WebSocket for logs
# ---------------------------------------
@app.websocket("/ws/logs")
async def logs_socket(ws: WebSocket):
    await ws.accept()
    app.state.websocket = ws
    try:
        while True:
            await ws.receive_text()  # keep alive
    except:
        app.state.websocket = None

# ---------------------------------------
# Stream logs
# ---------------------------------------
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

# ---------------------------------------
# Run Website Scraper (Python)
# ---------------------------------------
@app.post("/run-website-scraper")
async def run_web_scraper():
    asyncio.create_task(stream_logs([
        "python", "/app/python_scripts/run_website_scraper.py"
    ]))
    return {"status": "started"}

# ---------------------------------------
# Run Facebook Scraper (Node.js)
# ---------------------------------------
@app.post("/run-facebook-scraper")
async def run_fb_scraper():
    sheet = None

    if SHEET_ID_ENV:
        sheet = SHEET_ID_ENV
    elif os.path.exists(SHEET_ID_FILE):
        with open(SHEET_ID_FILE) as f:
            sheet = f.read().strip()
    else:
        return {"status": "error", "message": "Sheet ID not set"}

    script = os.path.join("/app", "node_scripts", "facebook_scraper.js")
    key_file = os.path.join("/app", "service_account.json")

    if not os.path.exists(script):
        return {"status": "error", "message": "FB script missing in container"}

    asyncio.create_task(stream_logs([
        "node", script,
        f"--key={key_file}",
        f"--sheet={sheet}"
    ]))

    return {"status": "started"}


# ---------------------------------------
# Run Email Filter (Python)
# ---------------------------------------
@app.post("/run-email-filter")
async def run_filter():
    asyncio.create_task(stream_logs([
        "python", "/app/python_scripts/run_email_filter.py"
    ]))
    return {"status": "started"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=port)
