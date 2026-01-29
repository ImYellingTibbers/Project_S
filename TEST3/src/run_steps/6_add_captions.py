from pathlib import Path
import json
import tempfile
from pycaps import JsonConfigLoader

ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "runs"

INPUT_VIDEO_NAME = "story_only.mp4"
OUTPUT_VIDEO_NAME = "story_w_captions.mp4"

CAPTIONS_CSS = """
.word {
  font-family: "Cinzel", "Trajan Pro", "Cormorant SC", serif;
  font-size: 38px;
  line-height: 1.05;
  font-weight: 700;

  /* NON-NARRATED WORDS */
  color: #DAD4CC;

  text-transform: uppercase;
  letter-spacing: 1px;

  /* DARK EDGE ONLY — NO WHITE */
  text-shadow:
    0 0 4px rgba(0,0,0,0.95),
    0 0 8px rgba(0,0,0,0.85);
}

.word-being-narrated {
  /* ACTIVE WORD */
  color: #9B1C1C;

  /* CONTINUOUS SOFT OUTLINE (NO SQUEEZE) */
  text-shadow:
    0 0 2px #ffffff,
    0 0 4px #ffffff,

    /* separation */
    0 0 6px rgba(0,0,0,0.95),

    /* red energy */
    0 0 10px rgba(120, 20, 20, 0.85);
}
"""

def latest_run_dir() -> Path:
    runs = sorted(p for p in RUNS_DIR.iterdir() if p.is_dir())
    if not runs:
        raise RuntimeError("No runs found")
    return runs[-1]

def main():
    run_dir = latest_run_dir()

    vo_path = run_dir / "vo.json"
    if not vo_path.exists():
        raise RuntimeError(f"Missing vo.json in {run_dir}")

    vo = json.loads(vo_path.read_text(encoding="utf-8"))
    words = vo.get("alignment", {}).get("words", [])
    if not words:
        raise RuntimeError("vo.json missing alignment.words")

    render_dir = run_dir / "render"

    input_video = render_dir / INPUT_VIDEO_NAME
    if not input_video.exists():
        raise RuntimeError(f"Missing input video: {input_video}")

    output_video = render_dir / OUTPUT_VIDEO_NAME
    if output_video.exists():
        output_video.unlink()

    config = {
        "input": str(input_video),
        "output": str(output_video),

        "css": None,

        "splitters": [
            { "type": "limit_by_words", "limit": 3 }
        ],

        "layout": {
            "max_number_of_lines": 1,
            "max_width_ratio": 0.65,
            "x_words_space": 20,
            "vertical_align": {
                "align": "bottom",
                "offset": -0.22
            }
        },

        "animations": [
            {
                "type": "zoom_in_primitive",
                "when": "narration-starts",
                "what": "segment",
                "duration": 0.06
            },
            {
                "type": "fade_out",
                "when": "narration-ends",
                "what": "segment",
                "duration": 0.05
            }
        ]
    }

    # --- REQUIRED because pycaps only accepts file paths ---
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        css_path = tmp / "captions.css"
        css_path.write_text(CAPTIONS_CSS)

        config["css"] = str(css_path)

        config_path = tmp / "config.json"
        config_path.write_text(json.dumps(config, indent=2))

        pipeline = JsonConfigLoader(str(config_path)).load()
        pipeline.run()

    print(f"[captions] wrote {output_video}")


if __name__ == "__main__":
    main()
