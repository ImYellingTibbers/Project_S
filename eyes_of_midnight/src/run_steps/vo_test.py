from pathlib import Path
import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2] 
REFERENCE_WAV = ROOT / "src" / "assets" / "voice_ref" / "jacob_whisper_ref.wav"
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
    """I started getting coffee at the same place every morning, just a small shop around the corner from the office. A new person started working with me around then, and they quickly started asking a lot of questions—where I lived, what I did on weekends, that sort of thing. I mentioned I liked the cafe, and the next day they were there too, waving as I walked in.



The firm’s small, mostly glass building felt…exposed. Not structurally, but like anyone could see in. I started there last month. Mostly drafting, some site visits. It’s good work. I’d settled into a routine – coffee from the place on the corner, always a small black, then straight into the office. 

Mark started a couple of weeks after me. He’s…enthusiastic. Immediately wanted to know everything. Not in a rude way, just…thorough. How I got to work – bus, I said. Weekends? Hiking, mostly. He made notes, I remember thinking that was odd, a little notepad always open on his desk. I didn’t mention the cafe.

Then he started showing up there. Not *at* the same time, but close. I’d see him through the window, leaving just as I arrived, or waiting outside when I came out. He’d wave. I’d wave back. It felt…calculated. 

Yesterday, he asked if I ever walked home via the park. I said no, too out of the way. He said, “Oh, right. It’s not well lit at night, is it?” I didn't mention I sometimes did, just to clear my head after a long day. It felt like a test. Like he already knew. I didn’t tell anyone about it. Didn’t want to sound paranoid. But I locked the back door twice tonight.""" + "            "
)

if __name__ == "__main__":
    main()