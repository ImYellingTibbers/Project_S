import os
import random
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- CONFIGURATION ---
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_ID = "gemini-flash-latest"

def generate_viral_theme(client) -> str:
    """Generates a high-concept theme using a curated anchor and AI-derived threat."""
    
    # --- VIRAL READY ANCHORS ---
    # These are selected for 'Uncanny' potential and 'Liminal Space' compatibility.
    anchors = [
        "The way a pet (dog/cat) reacts to an empty corner of a room.",
        "A 24-hour laundromat where the machines are running but no one is there.",
        "A childhood game where the rules were slightly 'off' (e.g., Hide and Seek alone).",
        "The 'Property Lines' of a suburban backyard that don't match the map.",
        "A specific, recurring sound in the plumbing that rhythmically mimics speech.",
        "The 'unspoken rule' of a public space (e.g., 'Never look at the person in seat 4B').",
        "A physiological glitch (e.g., your reflection blinks a split second after you do).",
        "A piece of mail addressed to you, dated ten years in the future.",
        "The feeling of a 'cold spot' in a house that physically moves every night.",
        "An old family photo where a person you don't recognize is standing in the back."
    ]
    
    selected_anchor = random.choice(anchors)
    print(f"🎲 ANCHOR INJECTED: {selected_anchor}")

    system_instruction = f"""
    You are a viral horror strategist specializing in 'High-Concept Dread'. 
    Your job is to take a mundane 'Anchor' and invent a truly terrifying, original threat.

    ### YOUR ASSIGNED ANCHOR:
    {selected_anchor}

    ### THE THREAT REQUIREMENTS:
    - DO NOT use clichés: No ghosts, no zombies, no generic slashers.
    - GO FOR: 'The Uncanny Valley', 'Cosmic Horror', or 'Physiological Betrayal'.
    - The threat should be something that cannot be fought or run from—it is a glitch in reality.
    - It must be 'Viral Ready': This means it has a clear, terrifying visual 'hook' that stays in the viewer's mind.

    ### STORY STRUCTURE:
    1. THE HOOK: A rule or observation about the Anchor.
    2. THE GLITCH: The moment the mundane becomes impossible.
    3. THE REVEAL: A brief, disturbing glimpse of the logic behind the horror.

    ### OUTPUT FORMAT:
    Return ONLY:
    THEME: [One sentence description of the concept]
    CORE REQUIREMENTS:
    - [Specific visual requirement 1]
    - [Specific visual requirement 2]
    - [The mandatory 'Check your surroundings' ending]
    """

    response = client.models.generate_content(
        model=MODEL_ID,
        contents="Invent a groundbreaking horror concept for a 60-second video based on the anchor provided.",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=1.0 # Max creativity
        )
    )
    return response.text