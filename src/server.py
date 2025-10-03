# main.py
import os
import json
import threading
from typing import Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from pathlib import Path
import traceback

#bin/uvicorn server:app --port 8080 --host 127.0.0.1 --reload

IMAGES_DIR = Path("src/static")
PLOT_PATH = IMAGES_DIR / "plot.png"
METADATA_FILE = Path("metadata.json")
JOB_ID = "image_job"


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in production set to specific origins
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# serve static files (index.html should be placed at ./static/index.html or adjust accordingly)
app.mount("/static", StaticFiles(directory="static"), name="static")

# thread-safe metadata access & interval
_meta_lock = threading.Lock()
_interval_lock = threading.Lock()
CURRENT_INTERVAL = 10  # default seconds

if not METADATA_FILE.exists():
    with METADATA_FILE.open("w") as f:
        json.dump([], f)


def read_metadata():
    with _meta_lock:
        with METADATA_FILE.open("r") as f:
            return json.load(f)


def append_metadata(record: Dict):
    with _meta_lock:
        data = read_metadata()
        data.insert(0, record)  # newest first
        with METADATA_FILE.open("w") as f:
            json.dump(data, f, indent=2)


def generate_plot_file():
    try:
        # If you can call your generator directly:
        # app_run()  # uncomment this if available and it writes static/plot.png

        # fallback: write a simple placeholder PNG if plot doesn't exist
        # (you probably have a real generator — remove fallback)
        if not PLOT_PATH.exists():
            PLOT_PATH.parent.mkdir(parents=True, exist_ok=True)
            # create an empty file so the frontend won't 404 (replace this with real generation)
            with PLOT_PATH.open("wb") as f:
                f.write(b"")  # empty; replace with real image bytes
        else:
            # touch to update timestamp so clients with cache-busting can still notice changes
            PLOT_PATH.touch()
    except Exception:
        traceback.print_exc()


def job_generate():
    """Scheduler job wrapper that calls your generator and records metadata."""
    try:
        generate_plot_file()

        fname = str(PLOT_PATH)
        record = {
            "filename": os.path.basename(fname),
            "path": fname,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        #append_metadata(record)
        print("Generated image:", record["path"])
    except Exception as e:
        print("Generation failed:", e)
        traceback.print_exc()


scheduler = BackgroundScheduler()
scheduler.add_job(job_generate, "interval", seconds=CURRENT_INTERVAL, id=JOB_ID, next_run_time=None)
scheduler.start()


@app.on_event("startup")
async def startup_event():
    # ensure at least one plot exists and metadata has an entry
    if len(read_metadata()) == 0:
        job_generate()


@app.get("/", response_class=HTMLResponse)
async def index():
    """
    Serve the single-page UI. If you store index.html in static/index.html, you can return it:
    """
    index_file = Path("static/index.html")
    if index_file.exists():
        return HTMLResponse(index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<html><body><h1>Place index.html in ./static/index.html</h1></body></html>")


@app.get("/images")
async def list_images():
    """Return metadata list."""
    return JSONResponse(read_metadata())


@app.get("/images/latest")
async def latest_image():
    data = read_metadata()
    if not data:
        raise HTTPException(status_code=404, detail="No images yet")
    return JSONResponse(data[0])


@app.get("/static_plot")
async def static_plot():
    """Convenience endpoint that serves the common plot path."""
    if not PLOT_PATH.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(PLOT_PATH), media_type="image/png")


@app.get("/status")
async def status():
    job = scheduler.get_job(JOB_ID)
    next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
    return {"running": bool(job), "next_run": next_run, "interval_seconds": CURRENT_INTERVAL}


@app.post("/api/settings")
async def set_settings(payload: Dict):
    """
    Change generation interval.
    Payload example: {"interval_seconds": 30}
    """
    global CURRENT_INTERVAL
    interval = payload.get("interval_seconds")
    if not isinstance(interval, (int, float)) or interval <= 0:
        raise HTTPException(status_code=400, detail="interval_seconds must be a positive number")

    with _interval_lock:
        CURRENT_INTERVAL = int(interval)
        try:
            scheduler.reschedule_job(JOB_ID, trigger="interval", seconds=CURRENT_INTERVAL)
        except Exception:
            # if job doesn't exist, create it
            scheduler.add_job(job_generate, "interval", seconds=CURRENT_INTERVAL, id=JOB_ID)
    return {"status": "ok", "interval_seconds": CURRENT_INTERVAL}


@app.get("/api/settings")
async def get_settings():
    return {"interval_seconds": CURRENT_INTERVAL}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run('server:app', host='127.0.0.1', port=8080, reload=True)
