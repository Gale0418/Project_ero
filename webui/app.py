import sys
import os
from pathlib import Path
import threading
import time
import base64
import uuid
import json
import subprocess

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn
import requests

from core.client import SDClient
from core.utils import ensure_dir, save_image, extract_infotext, smart_process_tags
from core.settings import AD_PRESETS
from webui.job_history import normalize_loaded_job

APP_VERSION = "v2.1"
WEBUI_HOST = os.getenv("PROJECT_ERO_HOST", "127.0.0.1")
WEBUI_PORT = int(os.getenv("PROJECT_ERO_PORT", "8000"))

app = FastAPI(title=f"Project Ero WebUI {APP_VERSION}")

# Directory setup
STATIC_DIR = Path(__file__).resolve().parent / "static"
DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_DIR = BASE_DIR / "outputs" / "webui_jobs"
DRAFT_DIR = BASE_DIR / "outputs" / "draft_temp"
REMIX_DIR = BASE_DIR / "outputs" / "remix_inputs"

ensure_dir(STATIC_DIR)
ensure_dir(DATA_DIR)
ensure_dir(OUTPUT_DIR)
ensure_dir(DRAFT_DIR)
ensure_dir(REMIX_DIR)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

TEMPLATES_FILE = DATA_DIR / "templates.json"

# Job Queue & State
job_queue_list = []  # List of job_ids (replaces queue.Queue)
jobs = {}  # job_id -> dict with job details
jobs_lock = threading.Lock() # Protects jobs dict AND job_queue_list

sd = SDClient()

# Helper to load/save jobs with lock
def save_job_unlocked(job_id):
    if job_id not in jobs:
        return
    job_file = OUTPUT_DIR / f"{job_id}.json"
    # Never write massive base64 strings to history JSON
    job_copy = dict(jobs[job_id])
    req_copy = dict(job_copy["request"])
    if req_copy.get("init_image"):
        req_copy["init_image"] = "<saved_to_disk>"
    job_copy["request"] = req_copy
    
    with open(job_file, "w", encoding="utf-8") as f:
        json.dump(job_copy, f, ensure_ascii=False, indent=2)

def set_job_status(job_id, status, phase_text=None, error=None):
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id]["status"] = status
            if phase_text is not None:
                jobs[job_id]["phase_text"] = phase_text
            if error is not None:
                jobs[job_id]["error"] = error
            save_job_unlocked(job_id)

def load_history():
    print("Scanning for job history...")
    with jobs_lock:
        for json_file in OUTPUT_DIR.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    job_data, changed = normalize_loaded_job(json.load(f))
                    jobs[job_data["id"]] = job_data
                    if changed:
                        save_job_unlocked(job_data["id"])
            except Exception as e:
                print(f"Failed to load {json_file.name}: {e}")
    print(f"Loaded {len(jobs)} jobs from history.")

load_history()

class JobRequest(BaseModel):
    mode: str = "standard" # standard, twophase, remix
    task_name: str = "Task"
    model: str
    final_model: Optional[str] = None
    global_prompt: str
    char_prompt: str
    action_prompt: str
    negative_prompt: str
    steps: int = 28
    width: int = 832
    height: int = 1216
    cfg_scale: float = 5.0
    denoise_str: float = 0.5
    cn_weight: float = 0.7
    total_images: int = 1
    auto_hires: bool = True
    ad_modes: list[str] = []
    init_image: Optional[str] = None

class TemplateItem(BaseModel):
    name: str
    global_prompt: str
    char_prompt: str
    action_prompt: str
    negative_prompt: str

class MoveRequest(BaseModel):
    new_index: int

def is_sdxl_model(model_name):
    if not model_name: return False
    return any(kw in model_name.lower() for kw in ["xl", "pony", "noobai", "illustrious", "animagine"])

def get_vae_for_model(model_name):
    return "sdxl_vae.safetensors" if is_sdxl_model(model_name) else "anime.vae.pt"

def get_controlnet_model_for_base(model_name):
    is_xl = is_sdxl_model(model_name)
    try:
        res = requests.get(f"{sd.base_url}/controlnet/model_list", timeout=10)
        if res.status_code == 200:
            models = res.json().get("model_list", [])
            for m in models:
                m_lower = m.lower()
                if "openpose" in m_lower:
                    if is_xl and ("xl" in m_lower or "sdxl" in m_lower):
                        return m
                    elif not is_xl and "xl" not in m_lower and "sdxl" not in m_lower:
                        return m
    except Exception:
        pass
    return "thibaud_xl_openpose [...]" if is_xl else "control_v11p_sd15_openpose"

def worker():
    print("Worker thread started...")
    while True:
        job_id = None
        with jobs_lock:
            if job_queue_list:
                job_id = job_queue_list.pop(0)
        
        if job_id is None:
            time.sleep(1)
            continue
        
        # Double check if job still exists (could be deleted while in queue)
        with jobs_lock:
            if job_id not in jobs or jobs[job_id]["status"] != "Pending":
                continue
            req = jobs[job_id]["request"]
            
        set_job_status(job_id, "Running", "Starting...")
        
        try:
            mode = req.get("mode", "standard")
            task_name = req.get("task_name", "Task").strip() or "Task"
            # Ensure task name is safe for filesystem
            task_name = "".join(c for c in task_name if c.isalnum() or c in (' ', '-', '_')).rstrip() or "Task"
            
            full_prompt = ", ".join(filter(bool, [req["global_prompt"], req["char_prompt"], req["action_prompt"]]))
            ad_args = [AD_PRESETS[k] for k in req["ad_modes"] if k in AD_PRESETS]

            print(f"[{job_id}] Mode: {mode.upper()} | Model: {req['model']} | Total Images: {req.get('total_images', 1)}")

            # Load remix init_image
            init_img_b64 = None
            if mode == "remix":
                img_path = REMIX_DIR / f"{job_id}.png"
                if img_path.exists():
                    with open(img_path, "rb") as f:
                        init_img_b64 = base64.b64encode(f.read()).decode('utf-8')
                elif req.get("init_image") and req["init_image"] != "<saved_to_disk>":
                    init_img_b64 = req["init_image"]
                
                if not init_img_b64:
                    raise Exception("No init image found for Remix mode on disk or in request.")

            # ==============================
            # STANDARD MODE
            # ==============================
            if mode == "standard":
                if not sd.set_model(req["model"]): raise Exception("Failed to load model")
                target_vae = get_vae_for_model(req["model"])
                
                # Check Auto Hires limits
                is_xl = is_sdxl_model(req["model"])
                safe_pixels = 1200000 if is_xl else 500000
                current_pixels = req["width"] * req["height"]
                
                txt2img_kwargs = {}
                base_w = req["width"]
                base_h = req["height"]
                
                if req.get("auto_hires", True) and current_pixels > safe_pixels:
                    set_job_status(job_id, "Running", "Resolution exceeds safe limit. Engaging Auto Hires. fix...")
                    # Calculate safe base resolution (half size, rounded to nearest 8)
                    base_w = (req["width"] // 2) // 8 * 8
                    base_h = (req["height"] // 2) // 8 * 8
                    
                    txt2img_kwargs = {
                        "enable_hr": True,
                        "hr_scale": 2.0,
                        "hr_upscaler": "R-ESRGAN 4x+ Anime6B",
                        "hr_second_pass_steps": 15,
                        "denoising_strength": 0.55,
                        "hr_resize_x": req["width"],
                        "hr_resize_y": req["height"],
                        # SD WebUI bug workaround: hr_additional_modules=None causes
                        # TypeError: argument of type 'NoneType' is not iterable
                        "hr_additional_modules": [],
                    }
                
                resp = sd.txt2img(
                    prompt=full_prompt, negative_prompt=req["negative_prompt"],
                    steps=req["steps"], width=base_w, height=base_h,
                    cfg_scale=req["cfg_scale"], batch_size=1, n_iter=req.get("total_images", 1),
                    sampler_name="Euler a", seed=-1, override_settings={"sd_vae": target_vae},
                    adetailer_args=ad_args if ad_args else None,
                    **txt2img_kwargs
                )
                
                imgs = resp.get("images", [])
                info_text = extract_infotext(resp.get("info"))
                
                with jobs_lock:
                    for idx, b64_img in enumerate(imgs):
                        filename = f"{task_name}_{job_id}_{idx+1:04d}.png"
                        save_image(b64_img, OUTPUT_DIR / filename, info_text=info_text)
                        jobs[job_id]["image_urls"].append(f"/api/images/{filename}")

            # ==============================
            # TWO-PHASE MODE
            # ==============================
            elif mode == "twophase":
                # Phase 1
                if not req.get("final_model"): raise Exception("Final model not selected for Two-Phase mode.")
                if not sd.set_model(req["model"]): raise Exception("Failed to load Draft model")
                
                set_job_status(job_id, "Running", "Phase 1: Generating Draft...")
                
                draft_w = req["width"] // 2
                draft_h = req["height"] // 2
                
                draft_resp = sd.txt2img(
                    prompt=full_prompt, negative_prompt=req["negative_prompt"],
                    steps=20, width=draft_w, height=draft_h,
                    cfg_scale=req["cfg_scale"], batch_size=1, n_iter=req.get("total_images", 1),
                    sampler_name="Euler a", seed=-1, override_settings={"sd_vae": get_vae_for_model(req["model"])}
                )
                draft_imgs = draft_resp.get("images", [])
                
                set_job_status(job_id, "Running", "Phase 1 ✓ → Phase 2 Running...")
                
                # Check for cancellation before switching models
                with jobs_lock:
                    if jobs[job_id]["status"] == "Canceling":
                        raise Exception("Canceled by user")

                # Phase 2
                if not sd.set_model(req["final_model"]): raise Exception("Failed to load Final model")
                
                cn_model = get_controlnet_model_for_base(req["final_model"])

                for idx, draft_b64 in enumerate(draft_imgs):
                    with jobs_lock:
                        if jobs[job_id]["status"] == "Canceling":
                            raise Exception("Canceled by user")

                    draft_file = DRAFT_DIR / f"{job_id}_draft_{idx}.png"
                    save_image(draft_b64, draft_file)

                    refine_resp = sd.img2img(
                        init_image_b64=draft_b64,
                        prompt=full_prompt, negative_prompt=req["negative_prompt"],
                        steps=req["steps"], width=req["width"], height=req["height"],
                        cfg_scale=req["cfg_scale"], denoising_strength=req["denoise_str"],
                        sampler_name="Euler a", override_settings={"sd_vae": get_vae_for_model(req["final_model"])},
                        adetailer_args=ad_args if ad_args else None,
                        controlnet_name=cn_model,
                        controlnet_img=draft_b64,
                        cn_weight=req["cn_weight"],
                        cn_end=0.6,
                        batch_size=1, n_iter=1
                    )
                    imgs = refine_resp.get("images", [])
                    info_text = extract_infotext(refine_resp.get("info"))
                    
                    if imgs:
                        filename = f"{task_name}_{job_id}_{idx+1:04d}.png"
                        save_image(imgs[0], OUTPUT_DIR / filename, info_text=info_text)
                        with jobs_lock:
                            jobs[job_id]["image_urls"].append(f"/api/images/{filename}")
                    
                    if draft_file.exists():
                        try:
                            draft_file.unlink()
                        except Exception:
                            pass

            # ==============================
            # REMIX MODE
            # ==============================
            elif mode == "remix":
                set_job_status(job_id, "Running", "Interrogating image tags...")
                
                raw_tags = sd.interrogate(init_img_b64, model="deepdanbooru")
                processed_tags = smart_process_tags(raw_tags, req["char_prompt"], 1.0)
                remix_prompt = f"{req['global_prompt']}, {processed_tags}, {req['char_prompt']}, {req['action_prompt']}"
                
                set_job_status(job_id, "Running", f"Generating Remix (Total: {req.get('total_images', 1)})...")
                
                if not sd.set_model(req["model"]): raise Exception("Failed to load Target model")

                remix_resp = sd.img2img(
                    init_image_b64=init_img_b64,
                    prompt=remix_prompt, negative_prompt=req["negative_prompt"],
                    steps=req["steps"], width=req["width"], height=req["height"],
                    cfg_scale=req["cfg_scale"], denoising_strength=req["denoise_str"],
                    sampler_name="Euler a", seed=-1, override_settings={"sd_vae": get_vae_for_model(req["model"])},
                    adetailer_args=ad_args if ad_args else None,
                    batch_size=1, n_iter=req.get("total_images", 1)
                )
                imgs = remix_resp.get("images", [])
                info_text = extract_infotext(remix_resp.get("info"))
                
                for idx, b64_img in enumerate(imgs):
                    filename = f"{task_name}_{job_id}_{idx+1:04d}.png"
                    save_image(b64_img, OUTPUT_DIR / filename, info_text=info_text)
                    with jobs_lock:
                        jobs[job_id]["image_urls"].append(f"/api/images/{filename}")

            # Check if any images were saved or if it was canceled
            with jobs_lock:
                was_canceled = jobs[job_id]["status"] == "Canceling"
                success = len(jobs[job_id]["image_urls"]) > 0
                
            if was_canceled:
                set_job_status(job_id, "Canceled", error="Canceled by user")
            elif success:
                set_job_status(job_id, "Completed", phase_text="")
            else:
                set_job_status(job_id, "Failed", error="No image returned by SD WebUI")
                
        except Exception as e:
            with jobs_lock:
                if jobs[job_id]["status"] == "Canceling":
                    set_job_status(job_id, "Canceled", error="Canceled by user")
                else:
                    set_job_status(job_id, "Failed", error=str(e))
            print(f"[{job_id}] Error: {e}")

# Start background worker
worker_thread = threading.Thread(target=worker, daemon=True)
worker_thread.start()

@app.get("/")
def read_root():
    return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/api/status")
def get_status():
    if sd.check_connection():
        return {"status": "online"}
    return {"status": "offline"}

@app.get("/api/progress")
def get_progress():
    try:
        r = requests.get(f"{sd.api_url}/progress", timeout=2)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {"progress": 0.0, "eta_relative": 0.0, "current_image": None}

@app.get("/api/models")
def get_models():
    if not sd.check_connection():
        raise HTTPException(status_code=500, detail="WebUI is offline")
    try:
        r = requests.get(f"{sd.api_url}/sd-models", timeout=10)
        r.raise_for_status()
        models_list = r.json()
        return [m["title"] for m in models_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/templates")
def get_templates():
    if not TEMPLATES_FILE.exists():
        return []
    with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/templates")
def save_template(tmpl: TemplateItem):
    templates = []
    if TEMPLATES_FILE.exists():
        with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
            templates = json.load(f)
    
    for t in templates:
        if t["name"] == tmpl.name:
            t["global_prompt"] = tmpl.global_prompt
            t["char_prompt"] = tmpl.char_prompt
            t["action_prompt"] = tmpl.action_prompt
            t["negative_prompt"] = tmpl.negative_prompt
            break
    else:
        templates.append(tmpl.dict())

    with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)
    return {"status": "ok"}

@app.post("/api/jobs")
def create_job(req: JobRequest):
    job_id = str(uuid.uuid4())[:8]
    
    if req.init_image:
        try:
            img_data = base64.b64decode(req.init_image)
            with open(REMIX_DIR / f"{job_id}.png", "wb") as f:
                f.write(img_data)
            req.init_image = "<saved_to_disk>"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image format: {e}")

    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "status": "Pending",
            "phase_text": "",
            "request": req.dict(),
            "created_at": time.time(),
            "image_urls": [],
            "error": None
        }
        job_queue_list.append(job_id)
        save_job_unlocked(job_id)

    return {"job_id": job_id, "status": "Pending"}

@app.post("/api/jobs/{job_id}/retry")
def retry_job(job_id: str):
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        old_req = dict(jobs[job_id]["request"])
        
    new_job_id = str(uuid.uuid4())[:8]
    
    old_img_path = REMIX_DIR / f"{job_id}.png"
    new_img_path = REMIX_DIR / f"{new_job_id}.png"
    if old_img_path.exists():
        import shutil
        shutil.copy(old_img_path, new_img_path)
    
    with jobs_lock:
        jobs[new_job_id] = {
            "id": new_job_id,
            "status": "Pending",
            "phase_text": "",
            "request": old_req,
            "created_at": time.time(),
            "image_urls": [],
            "error": None
        }
        job_queue_list.append(new_job_id)
        save_job_unlocked(new_job_id)
        
    return {"job_id": new_job_id, "status": "Pending"}

@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        status = jobs[job_id]["status"]
        
        if status == "Pending":
            if job_id in job_queue_list:
                job_queue_list.remove(job_id)
            jobs[job_id]["status"] = "Canceled"
            jobs[job_id]["error"] = "Canceled by user"
            save_job_unlocked(job_id)
            return {"status": "canceled"}
            
        elif status == "Running":
            jobs[job_id]["status"] = "Canceling"
            save_job_unlocked(job_id)
            try:
                requests.post(f"{sd.api_url}/interrupt", timeout=5)
            except Exception:
                pass
            return {"status": "canceling"}
            
        else:
            # Delete completed/failed/canceled job from disk
            try:
                (OUTPUT_DIR / f"{job_id}.json").unlink()
            except Exception:
                pass
            del jobs[job_id]
            return {"status": "deleted"}

@app.post("/api/jobs/{job_id}/move")
def move_job(job_id: str, payload: MoveRequest):
    with jobs_lock:
        if job_id not in job_queue_list:
            raise HTTPException(status_code=400, detail="Job is not in pending queue")
        
        current_idx = job_queue_list.index(job_id)
        job_queue_list.pop(current_idx)
        
        new_idx = max(0, min(payload.new_index, len(job_queue_list)))
        job_queue_list.insert(new_idx, job_id)
        
    return {"status": "moved"}

@app.post("/api/open-folder")
def open_folder():
    if os.name == 'nt':
        os.startfile(str(OUTPUT_DIR))
    else:
        import subprocess
        subprocess.Popen(['xdg-open', str(OUTPUT_DIR)])
    return {"status": "opened"}

@app.get("/api/jobs")
def get_jobs():
    with jobs_lock:
        # Sort so pending jobs reflect queue order, others by creation time
        def get_sort_key(job):
            if job["status"] == "Pending" and job["id"] in job_queue_list:
                # Top priority, sort by queue index
                return (0, job_queue_list.index(job["id"]))
            return (1, -job["created_at"]) # Newest first for others
            
        return sorted(list(jobs.values()), key=get_sort_key)

@app.get("/api/images/{filename}")
def get_image(filename: str):
    output_root = OUTPUT_DIR.resolve()
    file_path = (OUTPUT_DIR / filename).resolve()
    if file_path.is_relative_to(output_root) and file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    raise HTTPException(status_code=404, detail="Image not found")

if __name__ == "__main__":
    uvicorn.run("app:app", host=WEBUI_HOST, port=WEBUI_PORT, reload=True)
