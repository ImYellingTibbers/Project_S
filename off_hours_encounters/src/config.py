from pathlib import Path
import os

# ----------------------------
# Global project constants
# ----------------------------

PROJECT_NAME = "Project S"
PROJECT_VERSION = "1.0"

# Schema versions (lockstep for now)
SCHEMA_VERSION = "1.0"

# Common paths
RUNS_DIR = Path("runs")

# =========================
# LLM MODELS (by role)
# =========================

IDEA_GENERATOR_LLM_MODEL = "gpt-4o-mini"
IDEA_SELECTOR_LLM_MODEL = "gpt-4o"
SCRIPTWRITER_LLM_MODEL = "gpt-4.1"
IMAGE_PLANNER_LLM_MODEL = "gpt-4o"

# Future:
# TIMING_PLANNER_LLM_MODEL = "gpt-5-mini"
# METADATA_GENERATOR_LLM_MODEL = "gpt-4o-mini"

# =========================
# TTS Defaults
# =========================

ELEVENLABS_MODEL_ID = "eleven_turbo_v2_5"

# =========================
# Audio Defaults
# =========================

VO_SAMPLE_RATE_HZ = 24000


# Timing defaults
DEFAULT_VO_BUFFER_PRE = 0.15
DEFAULT_VO_BUFFER_POST = 0.15

# Image defaults
DEFAULT_ASPECT_RATIO = "9:16"

COMFY_URL = "http://127.0.0.1:8188"
COMFY_ROOT = Path(
    os.environ.get("COMFY_ROOT", "")
).expanduser().resolve()

if not COMFY_ROOT.exists():
    raise RuntimeError(
        "COMFY_ROOT is not set or invalid. "
        "Set COMFY_ROOT to your ComfyUI directory, e.g.\n"
        "E:\\ComfyUI_windows_portable_nvidia\\ComfyUI_windows_portable"
    )
    
COMFY_INPUT_DIR = COMFY_ROOT / "input"