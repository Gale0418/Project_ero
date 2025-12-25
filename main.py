# main.py
import json
import base64
import sys
import subprocess
import os
import time
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from PIL import Image

from core.settings import (
    STORY_FILE, OUTPUT_DIR, INPUT_DIR, DEFAULT_GEN_SETTINGS, 
    AD_PRESETS, PROMPT_PRESETS, CN_CONFIG_REMIX, CN_CONFIG_STORY
)
from core.client import SDClient 
from core.utils import ensure_dir, save_image, extract_infotext, smart_process_tags, OtakuSpinner, EvaText

class SystemScanner:
    def __init__(self):
        self.vram_gb = 8.0 
        self.gpu_name = "Generic/Apple GPU (Auto-Detected)"
        self.cpu_cores = os.cpu_count() or 4
        self._scan_gpu()

    def _scan_gpu(self):
        try:
            cmd = ['nvidia-smi', '--query-gpu=memory.total,name', '--format=csv,noheader,nounits']
            if sys.platform == "win32":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                output = subprocess.check_output(cmd, encoding='utf-8', startupinfo=si)
            else:
                output = subprocess.check_output(cmd, encoding='utf-8')
            
            self.vram_gb = float(output.split(',')[0].strip()) / 1024
            self.gpu_name = output.split(',')[1].strip()
        except Exception:
            pass

    def get_optimization_strategy(self):
        strategy = {"batch_size": 1, "save_workers": 2}
        if self.vram_gb - 4 > 0:
            strategy["batch_size"] = max(1, min(int((self.vram_gb - 4) / 3.5), 4))
        strategy["save_workers"] = max(2, min(self.cpu_cores - 2, 4))
        return strategy

def main():
    start_time = time.time()
    EvaText.print_system("INITIALIZING MAGI SYSTEM...")
    time.sleep(0.5)
    
    print(r"""
   ╔═══════════════════════════════════════════╗
   ║   ❖ PROJECT ERO 7.0 : OPERATION START     ║
   ║   (｀・ω・´)b  COMMAND CONSOLE ONLINE     ║
   ╚═══════════════════════════════════════════╝
    """)

    if not STORY_FILE.exists():
        EvaText.print_alert("CRITICAL ERROR: SCRIPT NOT FOUND")
        return

    with open(STORY_FILE, "r", encoding="utf-8") as f:
        story = json.load(f)
        
    gen_opts = {**DEFAULT_GEN_SETTINGS, **story.get("generation_settings", {})}
    models = story.get("models", {})
    seed_strategy = story.get("seed_strategy", {})
    global_num = seed_strategy.get("global_num_images", 2)
    base_seed = seed_strategy.get("base_seed", -1)
    
    remix_cfg = story.get("remix_settings", {})
    user_weight = remix_cfg.get("user_prompt_weight", 1.5)
    original_weight = remix_cfg.get("original_tags_weight", 0.5)
    remix_denoise = remix_cfg.get("denoising_strength", 0.6)
    conflict_keys = remix_cfg.get("conflict_keywords", [])
    
    project_name = story.get("project_name", "Untitled_Project")
    project_root = OUTPUT_DIR / project_name
    draft_root = project_root / "draft"
    example_root = project_root / "example"
    remix_root = OUTPUT_DIR / "remix"
    
    ensure_dir(draft_root)
    ensure_dir(example_root)
    ensure_dir(INPUT_DIR)

    scanner = SystemScanner()
    opt = scanner.get_optimization_strategy()
    sd = SDClient()

    EvaText.print_system("ESTABLISHING NEURAL LINKAGE...")
    EvaText.print_system("PINGING CORE SECTOR (WEBUI)...")
    
    if sd.check_connection():
        sync_rate = "100.0%"
        batch_level = opt['batch_size']
        worker_count = opt['save_workers']
        
        EvaText.box_msg([
            f"▷ TACTICAL UNIT    : {scanner.gpu_name}",
            f"▷ NEURAL CAPACITY  : {scanner.vram_gb:.1f} GB VRAM",
            f"▷ SYNCHRONIZATION  : {sync_rate}",
            f"▷ LIMITER RELEASE  : LEVEL {batch_level} (MAX OUTPUT)",
            f"▷ LOGISTICS WING   : {worker_count} DRONES ONLINE"
        ], color=EvaText.GREEN, title="STATUS REPORT")
    else:
        EvaText.print_heavy_warning("SYNC LOST: WEBUI NOT RESPONDING")
        print(f"{EvaText.FAIL}Please ensure WebUI is running with API enabled.{EvaText.ENDC}")
        return
    
    io_executor = ThreadPoolExecutor(max_workers=opt['save_workers'])

    def format_lora(items):
        res = ""
        for x in items:
            if not x:
                continue
            if "lora:" not in x and not x.startswith("<"):
                res += f" <lora:{x}:1>"
            elif x.startswith("<"):
                res += f" {x}"
            else:
                res += f" <{x}>"
        return res

    final_loras = format_lora(story.get("final_loras", []))
    header = story.get("character_header", "")
    bar_fmt = "{desc:8}: {percentage:3.0f}%|{bar:50}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"

    # =======================================================
    # 🕵️ Remix Mode (PATTERN BLUE)
    # =======================================================
    EvaText.print_system("SCANNING EXTERNAL INPUTS...")
    
    exts = ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]
    files = set()
    for ext in exts:
        files.update(INPUT_DIR.glob(ext))
    input_images = sorted(list(files))
    
    if not input_images:
        EvaText.slow_print(">> NO ANOMALIES DETECTED. RESUMING STANDARD PROTOCOL.", delay=0.02)
    
    if input_images:
        EvaText.print_heavy_warning("CRITICAL: UNKNOWN PATTERN DETECTED")
        EvaText.box_msg([
            f"▷ TARGETS     : {len(input_images)} HOSTILES",
            "▷ PRIORITY    : ALPHA",
            "▷ OPERATION   : SMART REMIX",
            f"▷ CONFIG      : USER={user_weight} | ORIG={original_weight}"
        ], color=EvaText.WARNING, title="EMERGENCY MISSION")
        print("")

        ensure_dir(remix_root)
        print(f"{EvaText.CYAN}<<< UNIT-FINAL EMERGENCY LAUNCH >>>{EvaText.ENDC}")
        if not sd.set_model(models["final_model"]):
            return

        prefix = story.get('final_prefix', PROMPT_PRESETS['final']['prefix'])
        negative = story.get('final_negative', PROMPT_PRESETS['final']['negative'])
        ad_keys = story.get("ad_modes", story.get("active_adetailers", ["face"]))
        ad_args = [AD_PRESETS[k] for k in ad_keys if k in AD_PRESETS]

        pbar = tqdm(total=len(input_images), desc="REMIXING", bar_format=bar_fmt, ncols=120, leave=True)
        
        for idx, img_path in enumerate(input_images):
            try:
                with Image.open(img_path) as pil_img:
                    orig_w, orig_h = pil_img.size
                with open(img_path, "rb") as f:
                    init_img_b64 = base64.b64encode(f.read()).decode()

                with OtakuSpinner(f" ENGAGING TARGET ({img_path.name})...") as _:
                    raw_tags = sd.interrogate(init_img_b64, model="deepdanbooru")
                
                processed_tags = smart_process_tags(raw_tags, header, original_weight, blocked_list=conflict_keys)
                full_prompt = f"{prefix} ({header}:{user_weight}), {processed_tags} {final_loras}"

                with OtakuSpinner(" OVERCLOCKING NEURAL CIRCUITRY...") as _:
                    resp = sd.img2img(
                        init_image_b64=init_img_b64, prompt=full_prompt, negative_prompt=negative,
                        width=orig_w, height=orig_h, steps=gen_opts["steps"],
                        cfg=gen_opts["final_cfg"], denoising_strength=remix_denoise,
                        sampler_name=gen_opts["sampler"], use_dt=story.get("use_dt", True),
                        adetailer_args=ad_args, controlnet_name=models.get("controlnet_openpose", None),
                        controlnet_img=init_img_b64,
                        cn_weight=CN_CONFIG_REMIX["weight"], cn_end=CN_CONFIG_REMIX["guidance_end"]
                    )
                
                imgs = resp.get("images", [])
                info = extract_infotext(resp.get("info", ""))
                if imgs:
                    save_name = f"Remix_{img_path.stem}.png"
                    io_executor.submit(save_image, imgs[0], remix_root / save_name, info)
            except Exception as e:
                print(f"\n{EvaText.FAIL}❌ IMPACT FAILED: {e}{EvaText.ENDC}")
            pbar.update(1)
        pbar.close()

    # =======================================================
    # 📖 Story Mode (HUMAN INSTRUMENTALITY)
    # =======================================================
    else:
        EvaText.print_system("REALITY ANCHOR: STABLE.")
        EvaText.print_system(f"EXECUTING \"GENESIS\" SCRIPT: {project_name}")
        draft_loras = format_lora(story.get("draft_loras", []))
        
        # === Phase 1: Draft ===
        print(f"\n{EvaText.CYAN}┌────────────────────────────────────────────────────────────┐{EvaText.ENDC}")
        print(f"{EvaText.CYAN}│  PHASE 1 : CONCEPTUALIZATION (DRAFT)                       │{EvaText.ENDC}")
        print(f"{EvaText.CYAN}└────────────────────────────────────────────────────────────┘{EvaText.ENDC}")
        
        print(f"{EvaText.CYAN}<<< UNIT-01 LAUNCH >>>{EvaText.ENDC}")
        if not sd.set_model(models["draft_model"]):
            return

        scenes = story.get("scenes", [])
        for s_idx, scene in enumerate(scenes):
            scene_id = scene["scene_id"]
            num_imgs = scene.get("num_images", global_num)
            
            prefix = story.get('draft_prefix', PROMPT_PRESETS['draft']['prefix'])
            negative = story.get('draft_negative', PROMPT_PRESETS['draft']['negative'])
            prompt = f"{prefix} {header} {draft_loras}, {scene['prompt']}"
            
            scene_seed_start = base_seed + (s_idx * 10000) if base_seed != -1 else -1

            pbar = tqdm(total=num_imgs, desc=scene_id[:8], bar_format=bar_fmt, ncols=120, leave=True)
            cnt = 0
            while cnt < num_imgs:
                batch = min(opt['batch_size'], num_imgs - cnt)
                target_filename = f"{scene_id}_{cnt+batch:03}.png"
                if (draft_root / target_filename).exists():
                    pbar.update(batch)
                    cnt += batch
                    continue
                
                current_seed = scene_seed_start + cnt if scene_seed_start != -1 else -1

                with OtakuSpinner(" COMPILING KINETIC VECTORS...") as _:
                    resp = sd.txt2img(
                        prompt=prompt, negative_prompt=negative, seed=current_seed,
                        steps=20, width=gen_opts["draft_width"], height=gen_opts["draft_height"],
                        batch_size=batch, cfg=7, sampler_name="Euler a"
                    )
                
                imgs = resp.get("images", [])
                info = extract_infotext(resp.get("info", ""))
                for idx, b64 in enumerate(imgs):
                    fname = f"{scene_id}_{cnt+idx+1:03}.png"
                    io_executor.submit(save_image, b64, draft_root / fname, info)
                
                cnt += batch
                pbar.update(batch)
            pbar.close()

        print(f"\n{EvaText.WARNING}[SYSTEM] ENTROPY CASCADE IMMINENT.{EvaText.ENDC}")
        print(f"{EvaText.WARNING}[SYSTEM] ENGAGING REFINEMENT PROTOCOL.{EvaText.ENDC}")

        # === Phase 2: Refine ===
        print(f"\n{EvaText.CYAN}┌────────────────────────────────────────────────────────────┐{EvaText.ENDC}")
        print(f"{EvaText.CYAN}│  PHASE 2 : REALITY ANCHORING (REFINE)                      │{EvaText.ENDC}")
        print(f"{EvaText.CYAN}└────────────────────────────────────────────────────────────┘{EvaText.ENDC}")
        
        print(f"{EvaText.CYAN}<<< UNIT-02 LAUNCH >>>{EvaText.ENDC}")
        
        # 修正: 斷行處理
        if not sd.set_model(models["final_model"]):
            return

        ad_keys = story.get("ad_modes", story.get("active_adetailers", ["face"]))
        ad_args = [AD_PRESETS[k] for k in ad_keys if k in AD_PRESETS]

        for s_idx, scene in enumerate(scenes):
            scene_id = scene["scene_id"]
            num_imgs = scene.get("num_images", global_num)
            prefix = story.get('final_prefix', PROMPT_PRESETS['final']['prefix'])
            negative = story.get('final_negative', PROMPT_PRESETS['final']['negative'])
            prompt = f"{prefix} {header} {final_loras}, {scene['prompt']}"
            
            scene_seed_start = base_seed + (s_idx * 10000) if base_seed != -1 else -1

            pbar = tqdm(total=num_imgs, desc=scene_id[:8], bar_format=bar_fmt, ncols=120, leave=True)
            for i in range(num_imgs):
                filename = f"{scene_id}_{i+1:03}.png"
                src = draft_root / filename
                dst = example_root / filename
                if not src.exists() or dst.exists():
                    pbar.update(1)
                    continue
                
                current_seed = scene_seed_start + i if scene_seed_start != -1 else -1
                    
                with open(src, "rb") as f:
                    init_img = base64.b64encode(f.read()).decode()

                with OtakuSpinner(f" #{i+1} REWRITING HISTORY LOGS...") as _:
                    resp = sd.img2img(
                        init_image_b64=init_img, prompt=prompt, negative_prompt=negative, seed=current_seed,
                        width=gen_opts["final_width"], height=gen_opts["final_height"],
                        steps=gen_opts["steps"], cfg=gen_opts["final_cfg"],
                        denoising_strength=gen_opts["final_denoise"], sampler_name=gen_opts["sampler"],
                        use_dt=story.get("use_dt", True), adetailer_args=ad_args,
                        controlnet_name=models.get("controlnet_openpose", None), controlnet_img=init_img,
                        cn_weight=CN_CONFIG_STORY["weight"], cn_end=CN_CONFIG_STORY["guidance_end"]
                    )
                
                imgs = resp.get("images", [])
                info = extract_infotext(resp.get("info", ""))
                if imgs: 
                    io_executor.submit(save_image, imgs[0], dst, info)
                pbar.update(1)
            pbar.close()

    EvaText.print_system("SAVING BATTLE DATA...")
    io_executor.shutdown(wait=True)
    elapsed = time.time() - start_time
    m, s = divmod(elapsed, 60)
    
    print("")
    EvaText.box_msg([
        f"ELAPSED TIME : {int(m)}m {int(s)}s",
        f"OUTPUT DIR   : {project_root}",
        "STATUS       : MISSION COMPLETED"
    ], color=EvaText.BLUE, title="MISSION REPORT")
    
    print("\n" + EvaText.GREEN + "(｀・ω・´)ゞ OMEDETOU! (Congratulations!)" + EvaText.ENDC)

if __name__ == "__main__":
    main()