import os
import random
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

from _common_utils import (
    write_json,
    extract_json_from_llm,
    utc_now_iso
)


# --- CONFIGURATION ---
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_ID = "gemini-flash-latest"
RUNS_DIR = Path(__file__).resolve().parent.parent.parent / "runs"

# --- IDEA GENERATOR ---
def generate_viral_theme(client) -> str:
    """You are a viral horror strategist specializing in 'High-Concept Dread'.
    Your job is to take a mundane 'Anchor' and invent a PREDATORY PHYSICAL or SUPERNATURAL ENTITY."""
    print("🧠 THINKING OF A VIRAL CONCEPT...")
   
    # --- ANCHORS ---
    anchors = [
    "Every night, your home Wi-Fi shows a device named 'Basement Cam'—you don’t have one.",
    "You wake up with fresh dirt under your fingernails—like you were digging in your sleep.",
    "Your front door deadbolt is locked from the inside… but you live alone.",
    "You find muddy footprints leading to your bed… and none leading away.",
    "Your ceiling vent cover is slightly bent outward—like it’s been pushed from inside the duct.",
    "Your camera footage skips exactly one minute every night—always the same minute.",
    "Your photo gallery has screenshots you never took… of your own front door at night.",
    "You keep finding wet handprints on the outside of your windows—second floor.",
    "You discover your attic hatch has fresh scratches around the latch from the inside.",
    "You hear someone slowly dragging something heavy across the floor above you—there is no second floor.",
    "You receive a voicemail that’s just your living room audio—recorded while you were asleep.",
    "A neighbor says they saw you outside last night—standing still in the yard for an hour.",
    "Your locked car trunk is open in the morning, and it smells like warm breath.",
    "Your laptop webcam light turns on for one second… at the same time every night.",
    "Your closet door is open every morning, but you always keep it closed at night.",
    "Your doorbell camera shows someone standing at your door… perfectly still… for 12 minutes.",
    "You discover a second set of fingerprints on the inside of your bedroom window.",
    "Every time you lock the door, you hear quiet scratching from *inside* the house.",
    "You hear a soft whisper repeating the last thing you said… from another room.",
    "A new fingerprint lock profile appears: 'Guest 2'—registered at 4:44 AM.",
    "You find scratches on the wall that progressively get worse each night.",
    "You hear something whispering your name from outside your room, but you live alone."
]
   
    selected_anchor = random.choice(anchors)
    print(f"🎲 ANCHOR INJECTED: {selected_anchor}")

    system_instruction = f"""
    You are a viral horror strategist specializing in 'High-Concept Dread'.
    Your job is to take a mundane 'Anchor' and invent a truly terrifying, original threat.

    ### YOUR ASSIGNED ANCHOR:
    {selected_anchor}

    ### THE ENTITY/THREAT REQUIREMENTS:
    - PHYSICALITY: It has a body, a texture, and a horrifying way of moving. No 'glitches' or 'feelings'.
    - THE HUNT: The entity is actively stalking, invading, or claiming the narrator's space. The stakes are physical and immediate.
    - BAN CLICHÉS: No generic ghosts or slashers. Think 'Biological Horror' or 'Stalking Cryptid'.

    ### OUTPUT FORMAT:
    Return ONLY:
    THEME: [One sentence: The entity is (description) and it is (action) the narrator.]
    CORE REQUIREMENTS:
    - [Specific physical trait of the entity's body]
    - [The mandatory 'Check your surroundings' or 'I cannot escape this, and it is getting worse' ending]
    """

    response = client.models.generate_content(
        model=MODEL_ID,
        contents="Invent a groundbreaking horror concept for a 60-second video based on the anchor provided.",
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

    canon = (
        f"A Caucasian male in his {random.choice(ages)}, "
        f"{random.choice(hair_styles)} {random.choice(hair_colors)} hair, "
        f"wearing a {random.choice(tops)} and {random.choice(bottoms)}."
    )
    return canon

def extract_location(theme_text: str) -> str:
    """Simple helper to extract a location keyword from the generated theme."""
    return theme_text.split("THEME:")[1].split(".")[0] if "THEME:" in theme_text else "dark liminal space"


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
    2. [DETAIL SHOT]: Extreme close-up on a specific object, texture, or anomaly. BANNED: No faces, no eyes. Focus on the "Anchor".
    3. [ENVIRONMENTAL SHOT]: A wide-angle view of the empty architecture. The [PROTAGONIST] should be a tiny, out-of-focus silhouette or partially obscured by shadows.
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
      "environment_anchor": "One sentence describing the primary physical setting",
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

    timestamp = utc_now_iso().replace(":", "-").replace(".", "-")
    run_folder = RUNS_DIR / f"run_{timestamp}"
    run_folder.mkdir(parents=True, exist_ok=True)
   
    narrator_canon = create_narrator_canon()
    print(f"👤 Character Canon: {narrator_canon}")

    with genai.Client(api_key=GEMINI_API_KEY) as client:
        try:
            user_theme = generate_viral_theme(client)
            print(f"🔥 THEME: {user_theme}")

            response = client.models.generate_content(
                model=MODEL_ID,
                contents=user_theme,
                config=types.GenerateContentConfig(
                    system_instruction=get_viral_system_instruction(narrator_canon),
                    response_mime_type="application/json",
                    temperature=0.8,
                )
            )
           
            data = extract_json_from_llm(response.text)
           
            entity_canon = data.get("entity_description", "a twitching, distorted shadow")
           
            style_anchor = (
                "Found footage, 1990s VHS tape, security camera footage, grainy, "
                "heavy motion blur, analog distortion, low-resolution, "
                "harsh flash photography, deep shadows, gritty realism. "
                "NO digital polish, NO CGI, NO high-definition."
            )
            
            location_lock = data.get("environment_anchor", "unsettling liminal space")

            for seg in data['segments']:
                p = seg['image_prompt']
               
                is_pov = "[POV SHOT]" in p
                is_detail = "[DETAIL SHOT]" in p
                is_environmental = "[ENVIRONMENTAL SHOT]" in p
               
                p = p.replace("[SHOT TAG]:", "").strip()
               
                if is_pov:
                    p = p.replace("[PROTAGONIST]", "male pale trembling hands")
                elif is_detail:
                    p = p.replace("[PROTAGONIST]", "distorted male human texture")
                elif is_environmental:
                    p = p.replace("[PROTAGONIST]", f"tiny distant blurry silhouette of {narrator_canon}")
                else:
                    p = p.replace("[PROTAGONIST]", narrator_canon)

                p = p.replace("[ENTITY]", entity_canon)

                seg['image_prompt'] = f"{style_anchor}, Area: {location_lock}, {p}"

            write_json(run_folder / "script.json", data)
            print(f"✅ Consistent Script saved to: {run_folder}")
           
        except Exception as e:
            print(f"❌ Error: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    run()