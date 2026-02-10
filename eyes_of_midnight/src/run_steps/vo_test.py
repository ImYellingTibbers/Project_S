from pathlib import Path
import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2] 
REFERENCE_WAV = ROOT / "src" / "assets" / "voice_ref" / "jacob_whisper_ref_2.wav"
OUTPUT_WAV = ROOT / "runs" / "audio" / "vo_test_clone.wav"

# ------------------------------------------------------------
# Model Loader
# ------------------------------------------------------------
_MODEL = None

def get_model():
    global _MODEL
    if _MODEL is None:
        print("Loading Qwen3-TTS-12Hz-1.7B-Base...")
        _MODEL = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            device_map="cuda",
            dtype=torch.bfloat16,
            # Change this line:
            attn_implementation="sdpa", 
        )
    return _MODEL

# ------------------------------------------------------------
# Main Script
# ------------------------------------------------------------
def main():
    model = get_model()
    OUTPUT_WAV.parent.mkdir(parents=True, exist_ok=True)

    print(f"Synthesizing voice clone ({len(TEST_TEXT.split())} words)...")
    
    wavs, sr = model.generate_voice_clone(
        text=TEST_TEXT,
        language="English",
        ref_audio=str(REFERENCE_WAV),
        x_vector_only_mode=True, 
        max_new_tokens=8192,
        temperature=0.5,
        top_p=0.9,
        repetition_penalty=1.1
    )

    audio_data = wavs[0]
    sf.write(str(OUTPUT_WAV), audio_data, sr)

    print(f"✅ Success! Output: {OUTPUT_WAV.resolve()}")

TEST_TEXT = (
    """I think that the stars are the most fantastic things in the whole wide world!""" + "            "
)

if __name__ == "__main__":
    main()