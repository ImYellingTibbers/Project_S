import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# --- CONFIGURATION ---
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)
HF_TOKEN = os.getenv("HF_TOKEN")

# SWITCHING TO THE STABLE, HIGH-AVAILABILITY MODEL
MODEL_ID = "black-forest-labs/FLUX.1-schnell"

RUNS_DIR = Path(__file__).resolve().parent.parent.parent / "runs"
SAMPLING_MODE = False 

def get_latest_run():
    if not RUNS_DIR.exists(): return None
    folders = [f for f in RUNS_DIR.iterdir() if f.is_dir() and f.name.startswith("run_")]
    return max(folders, key=os.path.getmtime) if folders else None

def generate_images():
    if not HF_TOKEN:
        print("❌ Error: HF_TOKEN not found.")
        return

    client = InferenceClient(api_key=HF_TOKEN)
    run_folder = get_latest_run()
    
    if not run_folder:
        print("❌ No run folder found.")
        return

    with open(run_folder / "script.json", "r") as f:
        data = json.load(f)

    segments = data.get("segments", [])
    indices = [0, 4, 14] if SAMPLING_MODE else range(len(segments))

    print(f"🚀 Using Stable Model: {MODEL_ID}")

    for i in indices:
        if i >= len(segments): continue
        
        # THE TEXTURE INJECTOR (STYLIZED HORROR FIX)
        # These keywords trick the high-def FLUX model into rendering grit.
        raw_prompt = segments[i]['image_prompt']
        texture_injector = (
            "photorealistic raw vhs footage, grainy 1990s video, "
            "security camera distortion, low resolution, motion blur, "
            "sickly indoor lighting, high contrast, crushed blacks, "
        )
        horror_prompt = f"{texture_injector} {raw_prompt}"
        
        filename = f"image_{i+1:03d}.png"
        output_path = run_folder / filename

        try:
            print(f"🎨 Rendering {filename}...", end=" ", flush=True)
            # FLUX is fast; usually no retry loop needed
            image = client.text_to_image(
                horror_prompt,
                model=MODEL_ID
            )
            image.save(output_path)
            print("✅ [SAVED]")

        except Exception as e:
            print(f"❌ [ERROR]: {e}")

        if not SAMPLING_MODE and i != indices[-1]:
            wait_time = 30
            print(f"⏳ Cooling down {wait_time} seconds to avoid rate limits...")
            time.sleep(wait_time) 
        else:
            time.sleep(1)

    print(f"\n📁 Batch complete! Images saved to: {run_folder}")

if __name__ == "__main__":
    generate_images()