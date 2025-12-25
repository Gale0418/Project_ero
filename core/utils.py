# core/utils.py
import base64
import json
import sys
import time
import threading
import itertools
import os
from io import BytesIO
from pathlib import Path
from PIL import Image, PngImagePlugin
from core.settings import SPINNER_EMOJIS, GLOBAL_TAG_BLACKLIST, TAG_CONFLICT_MAP

os.system('')

class EvaText:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def slow_print(text, delay=0.01, end='\n'):
        for char in text:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(delay)
        sys.stdout.write(end)
        sys.stdout.flush()

    @staticmethod
    def print_system(text):
        EvaText.slow_print(f"{EvaText.CYAN}[SYSTEM]{EvaText.ENDC} {text}", delay=0.005)

    @staticmethod
    def print_heavy_warning(text):
        total_width = 58 
        border_pattern = "◢◤"
        border = border_pattern * (total_width // 2)
        inner_width = total_width - 2
        display_text = f"<<< {text} >>>"
        if len(display_text) > inner_width:
            display_text = display_text[:inner_width]
        left_pad = (inner_width - len(display_text)) // 2
        right_pad = inner_width - len(display_text) - left_pad
        
        print(f"\n{EvaText.FAIL}{border}")
        print(f"◤{' ' * inner_width}◢")
        print(f"◢{' ' * left_pad}{display_text}{' ' * right_pad}◤")
        print(f"◤{' ' * inner_width}◢")
        print(f"{border}{EvaText.ENDC}\n")

    @staticmethod
    def box_msg(lines, color=GREEN, title="MAGI SYSTEM"):
        width = 60
        print(f"{color}╔{'═'*width}╗")
        print(f"║{title.center(width)}║")
        print(f"╠{'═'*width}╣{EvaText.ENDC}")
        
        for line in lines:
            content = f"║ {line}"
            padding = 61 - len(content)
            if padding < 0:
                padding = 0
            print(f"{color}{content}{' ' * padding}║{EvaText.ENDC}")
            time.sleep(0.05)
        print(f"{color}╚{'═'*width}╝{EvaText.ENDC}")

def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)

def extract_infotext(response_info):
    if not response_info:
        return ""
    try:
        info_data = json.loads(response_info)
        if isinstance(info_data, dict) and "infotexts" in info_data:
            return info_data["infotexts"][0]
        return response_info
    except Exception:
        return response_info

def save_image(image_base64, path, info_text=None):
    try:
        img_data = base64.b64decode(image_base64)
        img = Image.open(BytesIO(img_data))
        pnginfo = PngImagePlugin.PngInfo()
        if info_text:
            pnginfo.add_text("parameters", info_text)
        img.save(path, pnginfo=pnginfo)
    except Exception as e:
        print(f"{EvaText.FAIL}❌ LOGIC GATE COLLAPSE (SAVE ERROR): {e}{EvaText.ENDC}")

def smart_process_tags(scanned_tags_str, user_prompt, weight, blocked_list=None):
    if not scanned_tags_str:
        return ""
    
    scanned_list = [t.strip() for t in scanned_tags_str.split(',')]
    user_prompt_lower = user_prompt.lower()
    
    active_blacklist = set(GLOBAL_TAG_BLACKLIST)
    if blocked_list:
        active_blacklist.update(blocked_list)
        
    for user_key, conflict_vals in TAG_CONFLICT_MAP.items():
        if user_key in user_prompt_lower:
            active_blacklist.update(conflict_vals)

    kept_tags = []
    for tag in scanned_list:
        is_blocked = False
        for block_word in active_blacklist:
            if block_word in tag:
                is_blocked = True
                break
        if not is_blocked:
            kept_tags.append(tag)
            
    if not kept_tags:
        return ""
    
    joined_tags = ", ".join(kept_tags)
    return f"({joined_tags}:{weight})"

class OtakuSpinner:
    def __init__(self, message=" Processing..."):
        self.message = message
        self.stop_running = False
        self.thread = None

    def spin(self):
        chars = itertools.cycle(SPINNER_EMOJIS)
        while not self.stop_running:
            sys.stdout.write(f"\r {EvaText.GREEN}{next(chars)}{EvaText.ENDC} {self.message}")
            sys.stdout.flush()
            time.sleep(2.0)

    def __enter__(self):
        sys.stdout.write("\n") 
        self.stop_running = False
        self.thread = threading.Thread(target=self.spin)
        self.thread.daemon = True
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_running = True
        if self.thread:
            self.thread.join()
        sys.stdout.write(f"\r {' ' * (len(self.message) + 20)} \r")
        sys.stdout.write("\033[F") 
        sys.stdout.flush()