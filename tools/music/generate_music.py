import sys
from pathlib import Path
import argparse
import torch

# Use your local heartlib repo
sys.path.insert(0, "/home/jcpix/heartlib/src")

from heartlib import HeartMuLaGenPipeline


MODEL_PATH = Path("/home/jcpix/heartlib/ckpt")


def generate_music(
    prompt: str,
    tags: str,
    output_path: Path,
    duration_ms: int = 180000,
    temperature: float = 0.85,
    cfg_scale: float = 1.8,
    topk: int = 60,
):
    structured_lyrics = f"""
[Intro]
{prompt}
""".strip()

    pipe = HeartMuLaGenPipeline.from_pretrained(
        MODEL_PATH,
        device={
            "mula": torch.device("cuda"),
            "codec": torch.device("cuda"),
        },
        dtype={
            "mula": torch.bfloat16,
            "codec": torch.float32,
        },
        version="3B",
        lazy_load=True,
    )

    with torch.no_grad():
        pipe(
            {
                "lyrics": structured_lyrics,
                "tags": tags,
            },
            max_audio_length_ms=duration_ms,
            save_path=str(output_path),
            topk=topk,
            temperature=temperature,
            cfg_scale=cfg_scale,
        )

    print(f"[MUSIC] Generated: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--prompt", required=True)
    parser.add_argument("--tags", required=True)
    parser.add_argument("--out", default="output.mp3")
    parser.add_argument("--duration", type=int, default=180000)
    parser.add_argument("--temperature", type=float, default=0.85)
    parser.add_argument("--cfg_scale", type=float, default=1.8)
    parser.add_argument("--topk", type=int, default=60)

    args = parser.parse_args()

    generate_music(
        prompt=args.prompt,
        tags=args.tags,
        output_path=Path(args.out),
        duration_ms=args.duration,
        temperature=args.temperature,
        cfg_scale=args.cfg_scale,
        topk=args.topk,
    )
