import sys
from pathlib import Path
import json
import time

# Add tools/project_ero/ to sys.path so we can import core modules
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import requests
from core.client import SDClient
from core.utils import ensure_dir, save_image, configure_utf8_console, extract_infotext

configure_utf8_console()

def main():
    print("Initializing final golden skin test for ALL models...")
    sd = SDClient()
    
    if not sd.check_connection():
        print("Error: WebUI not running or not responding at port 7860.")
        return

    # 1. Query all checkpoints from WebUI
    try:
        r = requests.get(f"{sd.api_url}/sd-models", timeout=10)
        r.raise_for_status()
        models_list = r.json()
    except Exception as e:
        print(f"Error querying models: {e}")
        return

    model_names = [m["title"] for m in models_list]
    print(f"Found {len(model_names)} models installed:")
    for idx, name in enumerate(model_names):
        print(f"  {idx+1}. {name}")

    output_dir = BASE_DIR / "outputs" / "all_models_automatic_vae_test"
    ensure_dir(output_dir)

    prompt_prefix = "masterpiece, anime style, 1girl, smile, bikini, looking at viewer, ocean, medium breasts, watery eyes, full body, long hair, pov,"
    scene_prompt = "beautiful beach, daytime, clear sky, bright sunlight, front lighting, well-lit, soft lighting, detailed background"
    negative_prompt = "backlighting, backlit, silhouette, sweat, sweaty, bodysuit, latex, bodypaint, leotard, dark skin, shadows, high contrast, large breasts, thick thighs, (deformed, distorted, disfigured:1.3), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, floating limbs, (mutated hands and fingers:1.4), disconnected limbs, mutation, mutated, ugly, disgusting, blurry, amputation, tattoo, lowres, bad hands, text, error, missing fingers, extra digits, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, out of focus, censorship, old, amateur drawing, odd"

    skin_prompts = [
        {"name": "var_1_fair_clear", "tags": "fair skin, smooth skin, water drops, clear skin"},
        {"name": "var_2_white_glistening", "tags": "white skin, glistening skin, light sweat"},
        {"name": "var_3_fair_wet", "tags": "fair skin, smooth skin, water drops, wet skin"},
        {"name": "var_4_natural_dewy", "tags": "natural skin, clean skin, dewy skin"},
        {"name": "var_5_fair_milky", "tags": "fair skin, smooth skin, water drops, soft skin, milky skin"},
        {"name": "var_6_fair_clean", "tags": "fair skin, smooth skin, water drops, clean skin"},
        {"name": "var_7_fair_delicate", "tags": "fair skin, smooth skin, water drops, delicate skin"},
        {"name": "var_8_creamy_fair", "tags": "creamy smooth fair skin, flawless skin"},
        {"name": "var_9_flawless_clear", "tags": "flawless creamy smooth skin, clear skin"},
        {"name": "var_10_fair_light_reflections", "tags": "fair skin, smooth skin, water drops, light reflections, clear skin"}
    ]

    print("\nStarting generation loop for each model...")
    for idx, model_name in enumerate(model_names):
        if "animagine" in model_name.lower():
            print(f"\n[{idx+1}/{len(model_names)}] Skipping animagine to avoid WebUI deadlock bug...")
            continue
            
        print(f"\n[{idx+1}/{len(model_names)}] Deploying and running: {model_name}")
        
        if not sd.set_model(model_name):
            print(f"Failed to set model {model_name}, skipping.")
            continue
            
        # Use Automatic VAE so WebUI can pick the correct one (or the baked-in one)
        target_vae = "Automatic"
        print(f"Setting VAE to: {target_vae}")

        for s_idx, sp in enumerate(skin_prompts):
            print(f"  Generating variation {s_idx+1}/10: {sp['name']}")
            
            full_prompt = f"{prompt_prefix} ({sp['tags']}:1.1), {scene_prompt}"
            
            try:
                resp = sd.txt2img(
                    prompt=full_prompt,
                    negative_prompt=negative_prompt,
                    steps=28,
                    width=832,
                    height=1216,
                    cfg_scale=5.0,
                    sampler_name="Euler a",
                    seed=-1,
                    override_settings={"sd_vae": target_vae}
                )
                
                imgs = resp.get("images", [])
                if imgs:
                    info_text = extract_infotext(resp.get("info"))
                    clean_filename = model_name.split(" [")[0].replace(".safetensors", "")
                    save_path = output_dir / f"{clean_filename}_{sp['name']}.png"
                    save_image(imgs[0], save_path, info_text=info_text)
                    print(f"    Saved: {save_path}")
                else:
                    print("    No image returned.")
            except Exception as e:
                print(f"    Error generating with {model_name}: {e}")

    print("\nAll models tested successfully! Check outputs in outputs/all_models_automatic_vae_test/")

if __name__ == "__main__":
    main()
