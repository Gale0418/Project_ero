import json
import sys
from pathlib import Path

import requests


BASE_DIR = Path(__file__).resolve().parent.parent
STORY_PATH = BASE_DIR / "data" / "story.json"
WEBUI_URL = "http://127.0.0.1:7860"


def get_json(path):
    response = requests.get(f"{WEBUI_URL}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def checkpoint_exists(checkpoints, filename):
    return any(
        item.get("title", "").startswith(filename)
        or item.get("filename", "").endswith(filename)
        for item in checkpoints
    )


def main():
    try:
        story = json.loads(STORY_PATH.read_text(encoding="utf-8"))
        models = story["models"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
        print(f"Failed to load story config: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    try:
        checkpoints = get_json("/sdapi/v1/sd-models")
        controlnet_models = get_json("/controlnet/model_list").get("model_list", [])
        adetailer_models = get_json("/adetailer/v1/ad_model").get("ad_model", [])
    except requests.RequestException as exc:
        print(f"Failed to query SD WebUI assets: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except (ValueError, KeyError) as exc:
        print(f"Failed to parse SD WebUI asset response: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    checks = {
        "draft_model": checkpoint_exists(checkpoints, models["draft_model"]),
        "final_model": checkpoint_exists(checkpoints, models["final_model"]),
        "controlnet_openpose": any(
            models["controlnet_openpose"].lower() in model.lower()
            for model in controlnet_models
        ),
        "adetailer": all(
            model in adetailer_models
            for model in ("face_yolov8n.pt", "hand_yolov8n.pt", "person_yolov8n-seg.pt")
        ),
    }
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
