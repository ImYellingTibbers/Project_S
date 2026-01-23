import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Import your existing utilities
try:
    from _common_utils import (
        write_json, 
        extract_json_from_llm, 
        utc_now_iso
    )
except ImportError:
    raise ImportError("Could not find _common_utils.py.")

# --- CONFIGURATION ---
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_ID = "gemini-flash-latest" 
RUNS_DIR = Path(__file__).resolve().parent.parent.parent / "runs"

def get_viral_system_instruction() -> str:
    """
    This is the 'Hard-Coded Logic' that ensures 9/10 quality.
    It uses 'Chain of Density' and 'Structural Anchoring'.
    """
    return """
    You are an elite horror director specializing in high-retention 60-second psychological 'glitch' horror.
    
    ### CRITICAL WRITING CONSTRAINTS:
    - NO EXPOSITION: Do not explain how you found an object or why you are there.
    - NO CLICHES: Ban the following words: 'Suddenly', 'Mysterious', 'Attic', 'Found', 'Decided', 'Realized', 'Little did I know'.
    - SHOW, DON'T TELL: Instead of "He was scary," describe "The way his jaw unhinged while he hummed a lullaby."
    - TENSE: 1st person, present tense ("I am", "I see").
    
    ### THE BEAT MAP (MANDATORY):
    Segments 1-2: THE HOOK. A visceral, confusing threat. 
    Segments 3-6: THE GLITCH. Something physically impossible happens in a normal setting.
    Segments 7-12: THE TRAP. The protagonist tries to escape but realizes the environment has changed.
    Segments 13-17: THE TURNING POINT. The horror isn't 'out there'; it's inside or right behind them.
    Segments 18-20: THE FOURTH WALL. Force the viewer to feel like they are next.

    ### VISUAL STYLE (FOR IMAGE PROMPTS):
    - Aesthetic: 'Liminal Horror', 'Analog Horror', '35mm dirty film'.
    - NO MONSTERS: Use 'Uncanny Humans'—people who look 99% right but 1% terribly wrong (eyes too wide, limbs too long).
    - Focus on macro textures: wet skin, rusted metal, vibrating pupils.

    ### GOLD STANDARD EXAMPLE (9.5/10):
    {
      "title": "The GPS Reflection",
      "hook": "My GPS just told me to 'Exit into the river.' Then it whispered, 'He’s right behind you.'",
      "segments": [
        {"text": "I’m an Uber driver. The passenger in seat 4 hasn't breathed in twenty miles.", "image_prompt": "POV of car interior, dashboard glowing eerie blue, reflection in the rearview mirror shows an empty back seat despite a silhouette being visible in the window reflection."},
        {"text": "The GPS screen is bleeding. Red pixels dripping onto my gear shift.", "image_prompt": "Close-up of a smartphone screen with the map melting into liquid red streaks, staining the center console."},
        {"text": "I tried to brake. The pedal felt like stepping on a soft, wet sponge.", "image_prompt": "Close-up of a foot in a sneaker pressing down on a car pedal that is covered in a pulsating, organic moss-like growth."},
        {"text": "I looked at the passenger. It’s not a man. It’s a mannequin wearing my father's skin.", "image_prompt": "The back seat passenger: a plastic figure with hyper-realistic, sagging human skin draped over it, staring with glass eyes."},
        {"text": "The GPS voice isn't Siri anymore. It's my own voice, screaming in reverse.", "image_prompt": "The car speakers vibrating so violently they are cracking the plastic door panels."},
        {"text": "Don't check your backseat after this video ends.", "image_prompt": "A final shot of the viewer's own perspective—the back of a headrest in a dark car, with a long, pale hand slowly reaching over the top."}
      ]
    }
    """

def run():
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY missing.")

    timestamp = utc_now_iso().replace(":", "-").replace(".", "-")
    run_folder = RUNS_DIR / f"run_{timestamp}"
    run_folder.mkdir(parents=True, exist_ok=True)

    # 3. The Prompt that triggers the "9/10" logic
    user_theme = """
    THEME: The 'Smart Home' is keeping me safe from something that looks exactly like me.
    
    CORE REQUIREMENTS:
    - High-pacing (18-20 segments).
    - Use the 'Rules of the House' format.
    - The ending must make the viewer look at their own front door.
    """

    print(f"🚀 GENERATING 9/10 HORROR SCRIPT...")
    with genai.Client(api_key=GEMINI_API_KEY) as client:
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=user_theme,
                config=types.GenerateContentConfig(
                    system_instruction=get_viral_system_instruction(),
                    response_mime_type="application/json",
                    temperature=0.9, 
                    top_p=0.95
                )
            )
            data = extract_json_from_llm(response.text)
            
            # Save
            write_json(run_folder / "script.json", data)
            print(f"✅ Success! 9/10 Script saved to: {run_folder}")
            
        except Exception as e:
            print(f"❌ API Error: {e}")

if __name__ == "__main__":
    run()