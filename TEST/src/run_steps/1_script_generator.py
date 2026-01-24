import os
import random
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
    raise ImportError("Could not find _common_utils.py. Please check your file structure.")

# --- CONFIGURATION ---
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_ID = "gemini-flash-latest" 
RUNS_DIR = Path(__file__).resolve().parent.parent.parent / "runs"

# --- IDEA GENERATOR ---
def generate_viral_theme(client) -> str:
    """Generates a high-concept, high-retention horror theme using the AI."""
    print("🧠 THINKING OF A VIRAL CONCEPT...")
    
    system_instruction = """
    You are a viral content strategist for a major horror studio. Your job is to invent 'High-Concept' ideas for 60-second vertical videos.
    
    ### THE VIRAL FORMULA:
    1. THE ANCHOR: A modern, relatable piece of technology or a common social rule.
    2. THE GLITCH: The technology starts behaving in a physically impossible way.
    3. THE THREAT: A 'Double' (doppelgänger), a 'Lurk', or 'The System'.
    4. THE HOOK: A 'Rule-Based' opening.
    
    ### CONSTRAINTS:
    - Avoid complex crowds or heavy gore. Focus on 'Liminal Spaces'.
    - Ending: Must always include a 'Stare at the Viewer' or 'Check your surroundings' call to action.
    
    ### OUTPUT FORMAT:
    Return ONLY the following structure:
    THEME: [One sentence description]
    CORE REQUIREMENTS:
    - [Requirement 1]
    - [Requirement 2]
    - [The mandatory ending instruction]
    """

    response = client.models.generate_content(
        model=MODEL_ID,
        contents="Generate 3 unique viral horror themes. Pick the scariest one and output it.",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=1.0
        )
    )
    return response.text

# --- CHARACTER CANON GENERATOR ---
def create_narrator_canon() -> str:
    """Generates a randomized but fixed physical description for the white male narrator."""
    hair_styles = ["short buzz-cut", "messy bedhead", "slicked-back", "wavy"]
    hair_colors = ["ash brown", "jet black", "salt-and-pepper", "dark blonde"]
    tops = ["charcoal grey hoodie", "black thermal shirt", "faded navy t-shirt", "brown canvas jacket"]
    bottoms = ["dark denim jeans", "black cargo pants", "grey sweatpants"]
    ages = ["mid-20s", "mid-30s", "early-40s"]
    
    # Narrator is always a white male per project requirements
    canon = (
        f"A Caucasian male in his {random.choice(ages)}, "
        f"{random.choice(hair_styles)} {random.choice(hair_colors)} hair, "
        f"wearing a {random.choice(tops)} and {random.choice(bottoms)}."
    )
    return canon

def get_viral_system_instruction(canon_desc: str) -> str:
    return f"""
    You are an elite horror cinematographer. Your specialty is 'Visual Dread'—building terror through composition and the 'Uncanny Valley'.
    
    ### THE SUBJECT (VISUAL CANON):
    {canon_desc}
    
    ### TARGET DURATION: 60 SECONDS
    - You must generate EXACTLY between 17-21 segments.
    - Each segment's "text" MUST be extremely brief: 5 to 7 words maximum.
    - This ensures a fast visual pace of one new image every ~3 seconds.

    ### MANDATORY SHOT ROTATION (THE DIRECTORS TOOLKIT):
    To maintain high retention, you must never repeat the same shot type twice in a row. Every image_prompt MUST start with a [SHOT TAG]:

    1. [POV SHOT]: Seen directly through the character's eyes. Show only trembling hands, an object being held, or the ground moving. NO FACE.
    2. [DETAIL SHOT]: Extreme close-up on a relevant object, a texture, or a specific part of the setting. NO HUMANS.
    3. [ENVIRONMENTAL SHOT]: A wide-angle, high-contrast shot of the setting. The [PROTAGONIST] should be a tiny, distant silhouette, a reflection in the corner, or absent entirely. Focus on 'Liminal Space'.
    4. [CLOSE-UP / THE MIRROR]: Show the [PROTAGONIST] only through distorted glass, security monitors, or a tiny peephole. If a direct close-up is used, focus on a disturbing physical reaction (dilated eyes, sweat).

    ### WRITING RULES:
    - USE PLACEHOLDERS: Use [PROTAGONIST] and [ENTITY]. 
    - VISUAL ANCHORING: Prioritize the environment. If the narrator is talking about a sound, show the empty hallway where the sound is coming from, not the narrator's face.
    - ENTITY REVEAL: Segments 1-12: Use only shadows, reflections, or distorted shapes. Segments 13-20: Slow, disturbing reveal of parts.
    - BAN CLICHES: No 'Suddenly', 'Mysterious', 'Realized', 'Scary', 'Spooky'.
    - TENSE: 1st person, present tense.

    ### STORY BEAT COMPOSITION:
    - 0-25% (ESTABLISH): Heavily use [DETAIL] and [ENVIRONMENTAL] shots. Establish the geography.
    - 26-75% (ESCALATION): High rotation between [POV] and [ENVIRONMENTAL]. Create a sense of being trapped.
    - 76-100% (CLIMAX): Use [CLOSE-UP] and [POV] for a claustrophobic, direct confrontation.

    ### OUTPUT JSON SCHEMA:
    {{
      "entity_description": "Define 2 unique, disturbing physical traits relevant to the story",
      "title": "Script Title",
      "hook": "High-impact opening line",
      "segments": [
        {{
          "text": "Narrator speech", 
          "image_prompt": "[SHOT TAG]: A visual description prioritizing the setting. Include [PROTAGONIST] or [ENTITY] only as defined by the tag rules."
        }}
      ]
    }}
    """

def run():
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY missing.")

    # 1. Setup Folder & Canon
    timestamp = utc_now_iso().replace(":", "-").replace(".", "-")
    run_folder = RUNS_DIR / f"run_{timestamp}"
    run_folder.mkdir(parents=True, exist_ok=True)
    
    narrator_canon = create_narrator_canon()
    print(f"👤 Character Canon Generated: {narrator_canon}")

    # 2. Initialize AI and Generate Dynamic Theme
    with genai.Client(api_key=GEMINI_API_KEY) as client:
        try:
            # DYNAMIC THEME GENERATION
            user_theme = generate_viral_theme(client)
            print(f"🔥 THEME SELECTED:\n{user_theme}\n")

            print(f"🚀 GENERATING 10/10 CINEMATIC HORROR SCRIPT...")
            
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=user_theme, 
                config=types.GenerateContentConfig(
                    system_instruction=get_viral_system_instruction(narrator_canon),
                    response_mime_type="application/json",
                    temperature=0.9, 
                    top_p=0.95
                ) # Fixed missing closing config
            ) # Fixed missing closing generate_content
            
            data = extract_json_from_llm(response.text)
            
            # 3. THE INJECTION ENGINE (Visual Consistency Fix)
            entity_canon = data.get("entity_description", "A shadowy, distorted figure.")
            style_anchor = (
                "1994 VHS screengrab, heavy magnetic tape noise, horizontal tracking lines, "
                "chromatic aberration, overexposed fluorescent lighting, deep crushed blacks, "
                "unsettling liminal space, shot on a cheap 90s handcam, grainy low-bitrate."
            )
            
            print(f"👾 Entity Defined: {entity_canon}")

            for seg in data['segments']:
                p = seg['image_prompt']
                
                # Identify the shot type
                is_pov = "[POV SHOT]" in p
                is_detail = "[DETAIL SHOT]" in p
                is_environmental = "[ENVIRONMENTAL SHOT]" in p
                
                # Cleanup the Shot Tag for the Image Generator
                p = p.replace("[SHOT TAG]:", "").strip()
                
                # --- SELECTIVE INJECTION LOGIC ---
                if is_pov:
                    # Replace with first-person body parts only
                    p = p.replace("[PROTAGONIST]", "the character's trembling hands and arms")
                elif is_detail:
                    # Remove protagonist entirely from extreme close-ups of objects
                    p = p.replace("[PROTAGONIST]", "")
                elif is_environmental:
                    # Make him a tiny, distant figure to emphasize the liminal space
                    p = p.replace("[PROTAGONIST]", f"a tiny, distant silhouette of {narrator_canon}")
                else:
                    # Full injection for Close-ups or standard shots
                    p = p.replace("[PROTAGONIST]", narrator_canon)

                # Entity injection is usually safe as the entity is the threat
                p = p.replace("[ENTITY]", f"the horror entity ({entity_canon})")
                
                # Prepend the global style anchor
                seg['image_prompt'] = f"{style_anchor} {p}"

            # 4. Save
            write_json(run_folder / "script.json", data)
            print(f"✅ Success! Consistent 10/10 Script saved to: {run_folder}")
            
        except Exception as e:
            print(f"❌ API Error: {e}")
            import traceback
            traceback.print_exc() # This helps debug exactly where it fails

if __name__ == "__main__":
    run()