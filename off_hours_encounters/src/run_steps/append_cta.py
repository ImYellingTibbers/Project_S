import argparse
import random
import subprocess
from pathlib import Path


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", "--run-id", dest="run_id", required=True)
    args = parser.parse_args()

    ROOT = Path(__file__).resolve().parents[2]
    RUNS_DIR = ROOT / "runs"
    CTA_DIR = ROOT / "src" / "assets" / "cta_mp4"

    run_dir = RUNS_DIR / args.run_id
    render_dir = run_dir / "render"

    story_vid = render_dir / "story_w_captions.mp4"
    out_vid = render_dir / "final_with_cta.mp4"

    if not story_vid.exists():
        raise FileNotFoundError(f"Missing {story_vid}")

    ctas = [p for p in CTA_DIR.iterdir() if p.suffix == ".mp4"]
    if not ctas:
        raise RuntimeError("No CTA mp4s found")

    cta_vid = random.choice(ctas)

    run([
        "ffmpeg",
        "-y",
        "-fflags", "+genpts",
        "-i", str(story_vid),
        "-i", str(cta_vid),
        "-filter_complex",
        (
            "[1:v]scale=1080:1920,setsar=1[cta_v];"
            "[0:v][cta_v]concat=n=2:v=1:a=0[v];"
            "[0:a][1:a]concat=n=2:v=0:a=1,"
            "aresample=48000,asetpts=N/SR/TB[a]"
        ),
        "-map", "[v]",
        "-map", "[a]",
        "-fps_mode", "cfr",
        "-r", "24",
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level", "4.2",
        "-c:a", "aac",
        "-ac", "2",
        "-ar", "48000",
        "-movflags", "+faststart",
        str(out_vid),
    ])

    print(f"[cta] Appended CTA -> {cta_vid.name}")
    print(f"[cta] Output -> {out_vid.name}")


if __name__ == "__main__":
    main()
