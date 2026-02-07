from pathlib import Path
import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
            device_map="cuda",
            dtype=torch.bfloat16,
        )
    return _MODEL


def generate_wav(
    text: str,
    output_path: str,
    speaker: str = "Ryan",
    language: str = "English",
    instruct: str | None = None,
) -> bool:
    """
    Generate a WAV file using Qwen3-TTS CustomVoice.

    Returns True on success.
    Raises on failure.
    """

    model = _get_model()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    wavs, sample_rate = model.generate_custom_voice(
        text=text,
        language=language,
        speaker=speaker,
        instruct=instruct or "",
    )

    sf.write(str(output_path), wavs[0], sample_rate)
    return True
