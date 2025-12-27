# 🎨 自動色圖姬 (Project Ero)
### Your Personal 2D Assembly Line

> "Why fix images by hand one by one when you can code a factory to mass-produce your waifus?" (｀・ω・´)b

## 📖 Introduction
This is an automation script based on **Stable Diffusion WebUI (Forge/A1111)**.
It's designed to solve the fatigue of "manual clicking." utilizing a default **Two-Stage Pipeline**, it automatically handles the process from "Composition Draft" to "Polished Final," and supports batch processing for sequential storytelling images.

## ⚙️ Core Workflow

The system follows a **Draft -> Final** logic:

1.  **Phase 1: Draft**
    *   Quick generation for composition and general lighting.
    *   *Recommended Models:* Models with strong structural understanding (e.g., Pony based) to ensure the anatomy doesn't break.
2.  **Phase 2: Final**
    *   Uses the draft as a base, locks the skeleton with **ControlNet**, and performs an img2img refinement.
    *   *Recommended Models:* Aesthetic-focused models (e.g., NoobAI) to give it that polished, airy anime look.

> (｀・ω・´) **Pro Tip**: The default config is `Pony (Structure)` -> `NoobAI (Aesthetics)`. This combo yields accurate anatomy with a refined art style. However, you can swap these for ANY models you like in `story.json`. Check your WebUI, copy the full filename (e.g., `ponyDiffusionV6XL_v6StartWithThisOne.safetensors`), and paste it!

## 🖼️ Demo (SFW / Safe for Public Viewing -u-)

| Phase 1: Draft | Phase 2: Final |
| :---: | :---: |
| <img src="https://pimg.1px.tw/blog/gale/album/101348418/844824872680195389.png" width="400" alt="Draft Example"> | <img src="https://pimg.1px.tw/blog/gale/album/101348418/844824876677369019.png" width="400" alt="Final Example"> |
| *Composition & pose* | *The models you like* |

## 🧩 Auto Prompt Assembly & Story Flow

No need to write a wall of text every time! The script automatically assembles prompts from three sources:

    [1. Quality Tags] + [2. Character Config] + [3. Scene Description]

1.  **Quality Tags (Prefix)**: Defined in settings/json (handles `masterpiece, best quality...`).
2.  **Character Config (Header)**: Defined in `story.json` (handles `1girl, black hair...`).
3.  **Scene Description**: Defined in the `scenes` list. **This is the core workflow!**

### 🎬 How to write the story
You can define the flow of your image generation in the `scenes` list. Want a longer story? Just copy-paste the block and add more scenes!


    "scenes": [
    {
      "scene_id": "Scene_01_Wakeup",
      "num_images": 5,  // You can override the global count per scene
      "prompt": "waking up in bed, stretching, messy hair, morning light"
    },
    {
      "scene_id": "Scene_02_School",
      "num_images": 5,
      "prompt": "standing in classroom, holding a book, looking out the window"
    },
    {
      "scene_id": "Scene_03_Date",
      "prompt": "sitting in a cafe, drinking tea, smiling at viewer"
    }
    // (｀・ω・´)b Add as many scenes as you like! The factory never stops!
    ]
> **Note**: If you switch models (e.g., from Pony to SD1.5), remember to update `draft_prefix` or `final_prefix` in `story.json`. Old spells (like `score_9`) won't work on other models!

## 🚀 Getting Started

### 1. Requirements
*   **Python 3.10+** installed.
*   SD WebUI running with the `--api` argument.
*   ControlNet (recommend `dw_openpose_full`) & ADetailer installed.

### 2. Write Your Script
Open `data/story.json`. This is where the magic happens:
*   **`project_name`**: Output folder name (images go to `outputs/YourProject`).
*   **`models`**: Define your Draft and Final model filenames.
*   **`character_header`**: Define your waifu's appearance.
*   **`scenes`**: Describe the actions and environments.

### 3. One-Click Launch
Open your terminal in the project folder and run:

    python main.py

Then just stare at the screen until the images appear. (ﾟ∀。)

---

## 🧪 Experimental Feature: Remix Mode

Want to turn "3D photos" into "2D Waifus"? or perform a style transfer?

### How to use
1.  Drop reference images (one or many) into the **`inputs/`** folder.
2.  Run `python main.py`.
3.  The script will auto-detect them and engage **Remix Mode**.

### How it works
*   Auto-interrogate tags from the source image.
*   Auto-filter conflicting traits (e.g., source has blonde hair vs. your black hair setting).
*   Lock composition and pose using ControlNet.
*   High-denoise repainting using the Final model.

> (｀・ω・´)ゞ **Attention**: This mode skips the `story.json` plotlines and focuses solely on processing images in `inputs`. To run the story mode, empty the `inputs` folder.
>
> (｀・ω・´)a **Minor Detail**: Tuning this is a pain, so I kinda gave up on perfection. It lowers the weight of original tags to avoid contamination. It's great for style swapping, but full character replacement might still be tricky.
>
> (｀・ω・´)b **Even More Minor Detail**: This entire program was generated by AI. Do not trust a single punctuation mark.
>
> (｀・ω・´)σ **Least Important Detail**: Even this README is sponsored by AI. (X

---
(｀・ω・´)ﾉ OMEDETOU!
