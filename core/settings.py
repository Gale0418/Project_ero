# core/settings.py
from pathlib import Path

# ==========================================
# 📂 [系統路徑設定]
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
STORY_FILE = BASE_DIR / "data" / "story.json"
OUTPUT_DIR = BASE_DIR / "outputs"
INPUT_DIR = BASE_DIR / "inputs"

# WebUI 的 API 位址，若在雲端或區網請修改此處 IP
WEBUI_API_URL = "http://127.0.0.1:7860"

# ==========================================
# 🎨 [預設生成參數] (當 JSON 未指定時使用)
# ==========================================
DEFAULT_GEN_SETTINGS = {
    # Phase 1: 初稿 (Draft) 解析度
    # 建議 SDXL/Pony 使用 832x1216 (直) 或 1216x832 (橫)
    "draft_width": 832,
    "draft_height": 1216,

    # Phase 2: 完稿 (Final) 解析度 (建議比初稿大 1.5~2 倍)
    "final_width": 1024,
    "final_height": 1536,

    # 完稿階段的重繪幅度 (Denoising Strength)
    # 0.3~0.4: 微調，保留原圖細節
    # 0.5~0.6: 顯著優化，可能會改變臉部特徵
    # 0.7+: 幾乎重畫
    "final_denoise": 0.55,

    # 完稿階段的提示詞相關性 (CFG Scale)
    "final_cfg": 7.0,

    # 迭代步數
    "steps": 28,

    # 採樣器名稱 (需與 WebUI 內名稱一致)
    "sampler": "Euler a",
}

# ==========================================
# 📝 [提示詞預設模版] PS:我討厭大奶 都什麼邪教!
# ==========================================
PROMPT_PRESETS = {
    "draft": {
        "prefix": "masterpiece, best quality, very aesthetic, newest, absurdres, highres, ultra-detailed, intricate details, official art, anime style, cinematic lighting, warm lighting, vibrant colors, (depth of field, subtle background blur:1.2),",
        "negative": "score_4, score_3, score_2, score_1, source_furry, large breasts, thick thighs,",
    },
    "final": {
        "prefix": "masterpiece, best quality, very aesthetic, newest, absurdres, highres, ultra-detailed, intricate details, official art, anime style, cinematic lighting, warm lighting, vibrant colors, (depth of field, subtle background blur:1.2), very awa,",
        "negative": "large breasts, thick thighs, (worst quality, low quality:1.4), lowres, (bad), text, error, extra digits, extra limbs, missing limbs, bad hands, mutated hands, signature, watermark, username, old, early, jpeg artifacts, 3d, photorealistic, realistic, (dark:1.1), (shadow:1.1),",
    },
}

# ==========================================
# ⚔️ [Tag 衝突對映表] (Remix 模式專用)
# ==========================================
# 用於自動過濾反推出來的標籤。
# 邏輯：當 User Prompt 出現 [Key] 時，自動刪除反推結果中的 [Value]
TAG_CONFLICT_MAP = {
    "hair": ["hair", "ponytail", "twintails", "braid", "ahoge", "bangs", "long hair", "short hair"],
    "eye": ["eye", "heterochromia", "blue eyes", "red eyes", "green eyes"],
    "breast": ["breast", "chest", "cleavage"],
    "shirt": ["shirt", "blouse", "top", "camisole"],
    "skirt": ["skirt", "dress", "miniskirt"],
    "hat": ["hat", "cap", "headwear"],
}

# ==========================================
# 🚫 [強制黑名單]
# ==========================================
# 無論 Prompt 寫什麼，只要出現在反推結果中一律刪除
# 通常用於刪除「構圖類」標籤，以免干擾新的構圖
GLOBAL_TAG_BLACKLIST = [
    "1girl", "solo", "simple background", "white background", "comic", "monochrome", 
    "greyscale", "parody", "translated", "text", "speech bubble"
]

# ==========================================
# 🎮 [ControlNet 與 ADetailer 設定]
# ==========================================
CONTROLNET_MODULE = "dw_openpose_full"

# Remix 模式：權重較低，允許改變體型
CN_CONFIG_REMIX = {"weight": 0.5, "guidance_end": 0.5}

# Story 模式：權重較高，鎖定姿勢
CN_CONFIG_STORY = {"weight": 0.8, "guidance_end": 0.8}

# ADetailer 模型設定
AD_PRESETS = {
    "face": {"ad_model": "face_yolov8n.pt", "ad_prompt": "beautiful detailed face, anime eyes, blush", "ad_denoising_strength": 0.4},
    "hand": {"ad_model": "hand_yolov8n.pt", "ad_prompt": "perfect hands, 5 fingers", "ad_negative_prompt": "extra fingers, missing fingers, mutated hands", "ad_denoising_strength": 0.35},
    "person": {"ad_model": "person_yolov8n-seg.pt", "ad_prompt": "highly detailed outfit, masterpiece body", "ad_denoising_strength": 0.3},
}

DT_DEFAULT_ARGS = [True, 7.0, 99.5, "Cosine Up", 4, "Cosine Up", 4, 0, 100]

SPINNER_EMOJIS = ["(｀・ω・´)旦 ", "(｀・ω・´)a ", "(｀・ω・´)φ ", "(｀・ω・´)ゞ ", "(｀・ω・´)ﾉ "]