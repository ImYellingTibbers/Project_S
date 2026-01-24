import json
import os
import sys
import math
import subprocess
import shutil
import random
from pathlib import Path

# Path injection for tools
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from src.tools.kill_gpu_users import kill_comfyui

# --- CONFIGURATION (Matching your reference script) ---
ROOT = Path("/home/jcpix/projects/Project_S/TEST")
RUNS_DIR = ROOT / "runs"
TARGET_W, TARGET_H = 1080, 1920 
TARGET_FPS = 24
KB_ZOOM_PER_SEC = 0.010
KB_MAX_ZOOM = 1.06
XFADE_DUR = 0.0833  # ~2 frames xfade

def _run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {p.stderr}")

def get_latest_run():
    folders = sorted([f for f in RUNS_DIR.iterdir() if f.is_dir() and f.name.startswith("run_")])
    return folders[-1] if folders else None

def build_ken_burns_filter(duration_s):
    """The EXACT logic from your reference script."""
    frames = max(1, int(math.ceil(duration_s * TARGET_FPS)))
    inc = KB_ZOOM_PER_SEC / TARGET_FPS
    z = f"min(zoom+{inc:.8f},{KB_MAX_ZOOM})"
    
    # Handheld logic from your reference script
    x = "iw/2-(iw/zoom/2)+12*sin(2*PI*on/120)"
    y = "ih/2-(ih/zoom/2)+12*cos(2*PI*on/180)"

    filt = []
    # 1. Scale and Crop to ensure clean edges before zoompan
    filt.append(f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase")
    filt.append(f"crop={TARGET_W}:{TARGET_H}")
    
    # 2. The Zoompan (This is the 'Old Script' engine)
    filt.append(f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={TARGET_W}x{TARGET_H}:fps={TARGET_FPS}")
    
    # 3. Post-processing matching your reference
    filt.append("eq=contrast=1.08:saturation=1.12:brightness=-0.02") # Color Grade
    filt.append("noise=alls=10:allf=t+u")                           # Grain
    filt.append("vignette=PI/4")                                    # Vignette
    filt.append("format=yuv420p")

    return ",".join(filt)

def main():
    kill_comfyui()
    run_dir = get_latest_run()
    plan = json.loads((run_dir / "timing_plan.json").read_text())
    vo_path = run_dir / "vo" / "vo_clean.wav"
    out_dir = run_dir / "render"
    tmp_dir = out_dir / "tmp"
    
    if tmp_dir.exists(): shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    beat_clips = []
    print(f"🎬 [ASSEMBLER] Restoring Old Script Logic...")

    for i, beat in enumerate(plan['beats']):
        img_path = run_dir / "img" / f"image_{i+1:03d}.png"
        # We add a tiny buffer for the xfade overlap
        duration = (beat['end_time'] - beat['start_time']) + XFADE_DUR
        clip_path = tmp_dir / f"beat_{i:03d}.mp4"
        
        print(f"  ➜ Rendering Beat {i} ({duration:.2f}s)")
        
        _run([
            "ffmpeg", "-y", "-loop", "1", "-t", str(duration),
            "-i", str(img_path),
            "-vf", build_ken_burns_filter(duration),
            "-c:v", "libx264",    # Back to CPU encoding for exact quality match
            "-preset", "medium",  # Quality over speed
            "-crf", "18",         # High bitrate
            "-pix_fmt", "yuv420p",
            "-r", str(TARGET_FPS),
            str(clip_path)
        ])
        beat_clips.append(clip_path)

    # Crossfade Stitching (using your script's xfade logic)
    inputs = []
    filter_complex = []
    for i, p in enumerate(beat_clips):
        inputs += ["-i", str(p)]
        filter_complex.append(f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS[v{i}]")

    current = "v0"
    timeline = 0
    transitions = ["fade", "dissolve", "pixelize"]

    for i in range(1, len(beat_clips)):
        # Offset is the end of the previous clip minus the xfade duration
        prev_dur = plan['beats'][i-1]['end_time'] - plan['beats'][i-1]['start_time']
        timeline += prev_dur
        
        out_label = f"vx{i}"
        trans = random.choice(transitions)
        
        filter_complex.append(
            f"[{current}][v{i}]xfade=transition={trans}:duration={XFADE_DUR}:offset={timeline:.6f}[{out_label}]"
        )
        current = out_label

    stitched_v = tmp_dir / "stitched.mp4"
    _run(["ffmpeg", "-y"] + inputs + ["-filter_complex", ";".join(filter_complex), "-map", f"[{current}]", "-c:v", "libx264", "-crf", "18", str(stitched_v)])

    # Final Audio Marriage
    final_output = out_dir / "final_horror_short.mp4"
    _run(["ffmpeg", "-y", "-i", str(stitched_v), "-i", str(vo_path), "-c:v", "copy", "-c:a", "aac", "-shortest", str(final_output)])

    print(f"🚀 SUCCESS! Video rendered with original logic at: {final_output}")

if __name__ == "__main__":
    main()