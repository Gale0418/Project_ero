import sys
from pathlib import Path

# Add tools/project_ero/ to sys.path so we can import core modules
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import requests
from core.client import SDClient
from core.utils import ensure_dir, save_image, configure_utf8_console, extract_infotext

configure_utf8_console()

def main():
    print("Initializing Animagine Skin Test script...")
    sd = SDClient()
    
    if not sd.check_connection():
        print("Error: WebUI not running or not responding at port 7860.")
        return

    output_dir = BASE_DIR / "outputs" / "animagine_skin_test"
    ensure_dir(output_dir)

    prompt_prefix = "masterpiece, anime style,"
    base_character = "1girl, smile, bikini, looking at viewer, ocean, medium breasts, watery eyes, full body, long hair, pov, lying,"
    scene_prompt = "beautiful beach, daytime, clear sky, bright sunlight, front lighting, well-lit, soft lighting, detailed background"
    negative_prompt = "backlighting, backlit, silhouette, sweat, sweaty, bodysuit, latex, bodypaint, leotard, dark skin, shadows, high contrast, large breasts, thick thighs, (deformed, distorted, disfigured:1.3), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, floating limbs, (mutated hands and fingers:1.4), disconnected limbs, mutation, mutated, ugly, disgusting, blurry, amputation, tattoo, lowres, bad hands, text, error, missing fingers, extra digits, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, out of focus, censorship, old, amateur drawing, odd"

    skin_prompts = [
        {"name": "61_lying_test_1", "tags": "fair skin, smooth skin, water drops, light reflections, clear skin"},
        {"name": "62_lying_test_2", "tags": "fair skin, smooth skin, water drops, light reflections, clear skin"},
        {"name": "63_lying_test_3", "tags": "fair skin, smooth skin, water drops, light reflections, clear skin"},
        {"name": "64_lying_test_4", "tags": "fair skin, smooth skin, water drops, light reflections, clear skin"},
        {"name": "65_lying_test_5", "tags": "fair skin, smooth skin, water drops, light reflections, clear skin"},
        {"name": "66_lying_test_6", "tags": "fair skin, smooth skin, water drops, light reflections, clear skin"},
        {"name": "67_lying_test_7", "tags": "fair skin, smooth skin, water drops, light reflections, clear skin"},
        {"name": "68_lying_test_8", "tags": "fair skin, smooth skin, water drops, light reflections, clear skin"},
        {"name": "69_lying_test_9", "tags": "fair skin, smooth skin, water drops, light reflections, clear skin"},
        {"name": "70_lying_test_10", "tags": "fair skin, smooth skin, water drops, light reflections, clear skin"}
    ]

    target_model = "animagine-xl-4.0-opt.safetensors"
    target_vae = "sdxl_vae.safetensors"

    print(f"\nDeploying model: {target_model}")
    if not sd.set_model(target_model):
        print(f"Failed to set model {target_model}, exiting.")
        return

    print("\nStarting generation loop (10 variations)...")
    for idx, sp in enumerate(skin_prompts):
        print(f"\n[{idx+1}/10] Testing skin style: {sp['name']}")
        print(f"Tags: {sp['tags']}")
        
        full_prompt = f"{prompt_prefix} {base_character} ({sp['tags']}:1.1), {scene_prompt}"
        
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
                save_path = output_dir / f"{sp['name']}.png"
                save_image(imgs[0], save_path, info_text=info_text)
                print(f"Successfully saved: {save_path}")
            else:
                print("No image returned from generation.")
        except Exception as e:
            print(f"Error generating {sp['name']}: {e}")

    print("\nSkin test completed successfully! Check outputs in tools/project_ero/outputs/animagine_skin_test/")

if __name__ == "__main__":
    main()
