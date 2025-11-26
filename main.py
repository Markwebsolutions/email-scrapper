import asyncio
import subprocess
import sys
from fastapi import FastAPI, UploadFile, WebSocket, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

app.state.websocket = None

SERVICE_JSON = "service_account.json"
SHEET_ID = "storage/sheet_id.txt"

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
    with open(SHEET_ID, "w") as f:
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
# Stream logs: Windows-safe version
# ---------------------------------------
async def stream_logs(cmd):

    # Start subprocess normally (Windows safe)
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Read output line-by-line from a separate thread
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
        "python", "python_scripts/run_website_scraper.py"
    ]))
    return {"status": "started"}


# ---------------------------------------
# Run Facebook Scraper (Node.js)
# ---------------------------------------
@app.post("/run-facebook-scraper")
async def run_fb_scraper():

    sheet = open(SHEET_ID).read().strip()

    asyncio.create_task(stream_logs([
        "node", "node_scripts/facebook_scraper.js",
        "--key=service_account.json",
        f"--sheet={sheet}"
    ]))
    return {"status": "started"}


# ---------------------------------------
# Run Email Filter (Python)
# ---------------------------------------
@app.post("/run-email-filter")
async def run_filter():
    asyncio.create_task(stream_logs([
        "python", "python_scripts/run_email_filter.py"
    ]))
    return {"status": "started"}


import os
import uvicorn

if __name__ == "__main__":
    # Get port from environment variable set by Railway, default to 8080 for local testing
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
