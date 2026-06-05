# core/client.py
import requests
import time
from core.settings import WEBUI_API_URL, DT_DEFAULT_ARGS, CONTROLNET_MODULE
from core.utils import OtakuSpinner, EvaText

class SDClient:
    def __init__(self, base_url=WEBUI_API_URL, request_timeout=None, max_retries=3, retry_delay=3, model_timeout=300):
        self.base_url = base_url
        self.api_url = f"{base_url}/sdapi/v1"
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.model_timeout = model_timeout
        self._cn_models_cache = []

    def check_connection(self):
        try:
            return requests.get(f"{self.api_url}/progress", timeout=3).ok
        except Exception:
            return False

    def _post_with_retry(self, url, payload):
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                r = requests.post(url, json=payload, timeout=self.request_timeout)
                if r.status_code == 200:
                    return r.json()

                response_body = r.text[:500].replace("\n", " ")
                last_error = RuntimeError(f"SERVER ERROR {r.status_code}: {response_body}")
            except requests.exceptions.ReadTimeout as e:
                raise RuntimeError(
                    "Generation timed out. The WebUI job may still be running, so the request was not retried."
                ) from e
            except requests.exceptions.ConnectionError as e:
                last_error = RuntimeError("WEBUI connection failed")
            except requests.exceptions.RequestException as e:
                last_error = e

            if attempt < self.max_retries:
                msg = (
                    f"{EvaText.WARNING}(´・ω・`) WEBUI request failed "
                    f"({attempt}/{self.max_retries}). Retrying...{EvaText.ENDC}"
                )
                with OtakuSpinner(msg) as _:
                    time.sleep(self.retry_delay)

        raise RuntimeError(f"WEBUI request failed after {self.max_retries} attempts: {last_error}")

    def get_options(self):
        try:
            r = requests.get(f"{self.api_url}/options", timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException:
            return {}

    def set_model(self, model_name):
        current = self.get_options().get("sd_model_checkpoint", "")
        model_clean = model_name.split(" [")[0].strip()
        current_clean = current.split(" [")[0].strip()
        if model_clean == current_clean or model_clean in current or current_clean in model_name:
            try:
                requests.post(f"{self.api_url}/options", json={"sd_vae": "Automatic"}, timeout=5)
            except Exception:
                pass
            return True

        print(f"🔄 DEPLOYING UNIT: [{model_name}] ...")
        try:
            r = requests.post(f"{self.api_url}/options", json={"sd_model_checkpoint": model_name, "sd_vae": "Automatic"}, timeout=10)
            r.raise_for_status()
        except requests.exceptions.ReadTimeout:
            # Model loading may outlive the HTTP response window. Poll below.
            pass
        except requests.exceptions.RequestException as e:
            print(f"{EvaText.FAIL}MODEL DEPLOY FAILED: {e}{EvaText.ENDC}")
            return False

        deadline = time.monotonic() + self.model_timeout
        while time.monotonic() < deadline:
            try:
                time.sleep(3)
                r = requests.get(f"{self.api_url}/options", timeout=10)
                r.raise_for_status()
                opts = r.json()
                opt_checkpoint = opts.get("sd_model_checkpoint", "")
                opt_clean = opt_checkpoint.split(" [")[0].strip()
                if model_clean == opt_clean or model_clean in opt_checkpoint or opt_clean in model_name:
                    print("\r                                         ", end="\r") 
                    return True
            except requests.exceptions.RequestException:
                pass
        print(f"{EvaText.FAIL}MODEL DEPLOY TIMEOUT: [{model_name}]{EvaText.ENDC}")
        return False

    def interrogate(self, image_b64, model="deepdanbooru"):
        payload = {"image": image_b64, "model": model}
        try:
            r = requests.post(f"{self.api_url}/interrogate", json=payload, timeout=self.request_timeout)
            if r.status_code == 200:
                return r.json().get("caption", "")
        except requests.exceptions.RequestException:
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
        return None

    def _build_alwayson_scripts(self, adetailer_args=None, controlnet_name=None, controlnet_img=None, use_dt=False, cn_weight=1.0, cn_end=1.0, alwayson_scripts=None):
        alwayson_scripts = dict(alwayson_scripts or {})
        if adetailer_args:
            alwayson_scripts["ADetailer"] = {"args": adetailer_args}

        if controlnet_name:
            real_model = self.find_controlnet_model(controlnet_name)
            if not real_model:
                raise ValueError(f"ControlNet model not found: {controlnet_name}")
            if not controlnet_img:
                raise ValueError("ControlNet image is required")
            alwayson_scripts["ControlNet"] = {
                "args": [{
                    "enabled": True,
                    "module": CONTROLNET_MODULE,
                    "model": real_model,
                    "weight": cn_weight,
                    "guidance_end": cn_end,
                    "image": controlnet_img,
                    "resize_mode": "Crop and Resize",
                    "pixel_perfect": True,
                    "control_mode": "Balanced",
                }]
            }

        if use_dt:
            alwayson_scripts["Dynamic Thresholding (CFG Scale Fix)"] = {"args": DT_DEFAULT_ARGS}

        return alwayson_scripts

    def txt2img(self, prompt, adetailer_args=None, controlnet_name=None, controlnet_img=None, use_dt=False, cn_weight=1.0, cn_end=1.0, **kwargs):
        alwayson_scripts = self._build_alwayson_scripts(
            adetailer_args=adetailer_args, controlnet_name=controlnet_name,
            controlnet_img=controlnet_img, use_dt=use_dt,
            cn_weight=cn_weight, cn_end=cn_end,
            alwayson_scripts=kwargs.pop("alwayson_scripts", {}),
        )
        payload = {"prompt": prompt, "alwayson_scripts": alwayson_scripts, **kwargs}
        return self._post_with_retry(f"{self.api_url}/txt2img", payload)

    def img2img(self, init_image_b64, prompt, adetailer_args=None, controlnet_name=None, controlnet_img=None, use_dt=False, cn_weight=1.0, cn_end=1.0, **kwargs):
        alwayson_scripts = dict(kwargs.pop("alwayson_scripts", {}))
        alwayson_scripts = self._build_alwayson_scripts(
            adetailer_args=adetailer_args, controlnet_name=controlnet_name,
            controlnet_img=controlnet_img or init_image_b64, use_dt=use_dt,
            cn_weight=cn_weight, cn_end=cn_end,
            alwayson_scripts=alwayson_scripts,
        )
        payload = {"init_images": [init_image_b64], "prompt": prompt, "alwayson_scripts": alwayson_scripts, **kwargs}
        return self._post_with_retry(f"{self.api_url}/img2img", payload)
