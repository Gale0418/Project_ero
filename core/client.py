# core/client.py
import requests
import time
from core.settings import WEBUI_API_URL, DT_DEFAULT_ARGS, CONTROLNET_MODULE
from core.utils import OtakuSpinner, EvaText

class SDClient:
    def __init__(self, base_url=WEBUI_API_URL):
        self.base_url = base_url
        self.api_url = f"{base_url}/sdapi/v1"
        self._cn_models_cache = []

    def check_connection(self):
        try:
            requests.get(f"{self.api_url}/progress", timeout=3)
            return True
        except Exception:
            return False

    def _post_with_retry(self, url, payload):
        while True:
            try:
                r = requests.post(url, json=payload, timeout=None)
                if r.status_code == 200:
                    return r.json()
                
                msg = f"{EvaText.FAIL}( >_< ) SERVER ERROR {r.status_code}... Retrying...{EvaText.ENDC}"
                with OtakuSpinner(msg) as _:
                    time.sleep(3)

            except requests.exceptions.ConnectionError:
                msg = f"{EvaText.WARNING}(´・ω・`) Huh... Sync Rate dropping... Is the Entry Plug missing???{EvaText.ENDC}"
                with OtakuSpinner(msg) as _:
                    time.sleep(3)
            
            except Exception as e:
                msg = f"{EvaText.FAIL}( O_o ) UNKNOWN ERROR: {e}{EvaText.ENDC}"
                with OtakuSpinner(msg) as _:
                    time.sleep(3)

    def get_options(self):
        try:
            return requests.get(f"{self.api_url}/options", timeout=None).json()
        except Exception:
            return {}

    def set_model(self, model_name):
        current = self.get_options().get("sd_model_checkpoint", "")
        if model_name in current:
            return True

        print(f"🔄 DEPLOYING UNIT: [{model_name}] ...")
        try:
            requests.post(f"{self.api_url}/options", json={"sd_model_checkpoint": model_name}, timeout=5)
        except Exception:
            pass

        while True:
            try:
                time.sleep(3)
                opts = requests.get(f"{self.api_url}/options", timeout=10).json()
                if model_name in opts.get("sd_model_checkpoint", ""):
                    print("\r                                         ", end="\r") 
                    return True
            except Exception:
                pass

    def interrogate(self, image_b64, model="deepdanbooru"):
        payload = {"image": image_b64, "model": model}
        try:
            r = requests.post(f"{self.api_url}/interrogate", json=payload, timeout=None)
            if r.status_code == 200:
                return r.json().get("caption", "")
        except Exception:
            pass
        return ""

    def find_controlnet_model(self, keywords):
        if not keywords:
            return None
        if "[" in keywords and "]" in keywords:
            return keywords
        if not self._cn_models_cache:
            try:
                res = requests.get(f"{self.base_url}/controlnet/model_list", timeout=10)
                if res.status_code == 200:
                    self._cn_models_cache = res.json().get("model_list", [])
            except Exception:
                pass
        for model in self._cn_models_cache:
            if keywords.lower() in model.lower():
                return model
        return keywords

    def txt2img(self, prompt, **kwargs):
        payload = {"prompt": prompt, **kwargs}
        return self._post_with_retry(f"{self.api_url}/txt2img", payload)

    def img2img(self, init_image_b64, prompt, adetailer_args=None, controlnet_name=None, controlnet_img=None, use_dt=False, cn_weight=1.0, cn_end=1.0, **kwargs):
        alwayson_scripts = kwargs.get("alwayson_scripts", {})
        if adetailer_args:
            alwayson_scripts["ADetailer"] = {"args": adetailer_args}
        
        if controlnet_name:
            real_model = self.find_controlnet_model(controlnet_name)
            alwayson_scripts["ControlNet"] = {
                "args": [{
                    "enabled": True,
                    "module": CONTROLNET_MODULE,
                    "model": real_model,
                    "weight": cn_weight,
                    "guidance_end": cn_end,
                    "image": controlnet_img or init_image_b64, 
                    "resize_mode": "Crop and Resize",
                    "pixel_perfect": True,
                    "control_mode": "Balanced",
                }]
            }
        
        if use_dt:
            alwayson_scripts["Dynamic Thresholding (CFG Scale Fix)"] = {"args": DT_DEFAULT_ARGS}
        
        payload = {"init_images": [init_image_b64], "prompt": prompt, "alwayson_scripts": alwayson_scripts, **kwargs}
        return self._post_with_retry(f"{self.api_url}/img2img", payload)