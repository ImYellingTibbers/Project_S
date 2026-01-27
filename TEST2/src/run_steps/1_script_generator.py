# File: src/run_steps/image_prompts_from_script.py
from __future__ import annotations

import os
import re
import json
import time
import random
import traceback
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# Optional deps (installed in most of your envs already)
try:
    import requests
except ImportError as e:
    raise RuntimeError("Missing dependency: requests. Install with: pip install requests") from e

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ============================================================
# Project bootstrap (SEARCH REF: "ROOT = Path(__file__)")
# ============================================================
ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "runs"
ENV_PATH = ROOT / ".env"
load_dotenv(ENV_PATH)

SCHEMA_VERSION = "1.0"

# ============================================================
# Config (SEARCH REF: "CONFIG_DEFAULTS")
# ============================================================
CONFIG_DEFAULTS = {
    # Chunking
    "CHUNK_WORDS": int(os.getenv("CHUNK_WORDS", "20")),          # words per section
    "MIN_CHUNK_WORDS": int(os.getenv("MIN_CHUNK_WORDS", "16")),
    "MAX_CHUNK_WORDS": int(os.getenv("MAX_CHUNK_WORDS", "26")),
    "IMAGES_PER_CHUNK": int(os.getenv("IMAGES_PER_CHUNK", "2")), # must be 2 for your requirement

    # Style anchor for prompts
    "STYLE_ANCHOR": os.getenv(
        "STYLE_ANCHOR",
        "found footage, VHS, analog distortion, low-light realism, grainy, subtle motion blur, "
        "harsh practical lighting, deep shadows, no CGI, no glow, no cinematic grading, believable"
    ),

    # Local (Ollama)
    "USE_LOCAL_FIRST": os.getenv("USE_LOCAL_FIRST", "1") == "1",
    "OLLAMA_URL": os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
    "OLLAMA_MODEL_MAIN": os.getenv("OLLAMA_MODEL_MAIN", "mistral-nemo"),
    "OLLAMA_MODEL_JUDGE": os.getenv("OLLAMA_MODEL_JUDGE", "gemma2:9b"),

    # OpenAI fallback
    "OPENAI_MODEL_FALLBACK": os.getenv("OPENAI_MODEL_FALLBACK", "gpt-4o-mini"),
    "OPENAI_TEMPERATURE": float(os.getenv("OPENAI_TEMPERATURE", "0.8")),
    "OPENAI_TOP_P": float(os.getenv("OPENAI_TOP_P", "0.95")),

    # Quality gate
    "MIN_SCORE_TO_ACCEPT": float(os.getenv("MIN_SCORE_TO_ACCEPT", "9.0")),  # "9/10"
    "MAX_RETRIES_LOCAL": int(os.getenv("MAX_RETRIES_LOCAL", "2")),
    "SLEEP_BETWEEN_RETRIES_SEC": float(os.getenv("SLEEP_BETWEEN_RETRIES_SEC", "0.3")),
}

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# ============================================================
# Helpers
# ============================================================
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def strip_code_fences(text: str) -> str:
    # Removes ```json ... ``` or ``` ... ```
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_first_json_object(text: str) -> Dict[str, Any]:
    """
    Best-effort JSON extractor for model outputs that may include extra text.
    """
    text = strip_code_fences(text)
    # Quick path
    try:
        return json.loads(text)
    except Exception:
        pass

    # Find first {...} block
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found (missing '{').")
    # naive brace matching
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                return json.loads(candidate)
    raise ValueError("No complete JSON object found (unbalanced braces).")


def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def words(s: str) -> List[str]:
    return re.findall(r"\S+", s.strip())


def join_words(ws: List[str]) -> str:
    return " ".join(ws)


def choose_sentence_boundary_end(ws: List[str], start_idx: int, min_len: int, max_len: int) -> int:
    """
    Attempt to end chunk at a punctuation boundary within [min_len, max_len].
    Returns end index (exclusive).
    """
    target_end = min(start_idx + max_len, len(ws))
    min_end = min(start_idx + min_len, len(ws))

    # Prefer a boundary near the upper end for better context
    boundary_chars = (".", "!", "?", "…")
    for end in range(target_end, min_end - 1, -1):
        token = ws[end - 1]
        if any(token.endswith(ch) for ch in boundary_chars):
            return end

    # Fall back to fixed target
    return min(start_idx + CONFIG_DEFAULTS["CHUNK_WORDS"], len(ws))


def chunk_script_by_words(script_text: str) -> List[str]:
    ws = words(script_text)
    chunks: List[str] = []
    i = 0
    while i < len(ws):
        end = choose_sentence_boundary_end(
            ws,
            start_idx=i,
            min_len=CONFIG_DEFAULTS["MIN_CHUNK_WORDS"],
            max_len=CONFIG_DEFAULTS["MAX_CHUNK_WORDS"],
        )
        chunk = join_words(ws[i:end]).strip()
        if chunk:
            chunks.append(chunk)
        i = end
    return chunks


# ============================================================
# Narrator canon (SEARCH REF: "def create_narrator_canon")
# ============================================================
def create_narrator_canon(rng: random.Random) -> str:
    hair_styles = ["short buzz-cut", "messy bedhead", "slicked-back", "wavy"]
    hair_colors = ["ash brown", "jet black", "salt-and-pepper", "dark blonde"]
    tops = ["charcoal grey hoodie", "black thermal shirt", "faded navy t-shirt", "brown canvas jacket"]
    bottoms = ["dark denim jeans", "black cargo pants", "grey sweatpants"]
    ages = ["mid-20s", "mid-30s", "early-40s"]

    canon = (
        f"Caucasian male in his {rng.choice(ages)}, "
        f"{rng.choice(hair_styles)} {rng.choice(hair_colors)} hair, "
        f"wearing a {rng.choice(tops)} and {rng.choice(bottoms)}."
    )
    return canon


# ============================================================
# LLM adapters
# ============================================================
@dataclass
class LLMResult:
    text: str
    provider: str
    model: str


class LLMClient:
    def __init__(self):
        self.ollama_url = CONFIG_DEFAULTS["OLLAMA_URL"].rstrip("/")
        self.use_local_first = CONFIG_DEFAULTS["USE_LOCAL_FIRST"]
        self.ollama_model_main = CONFIG_DEFAULTS["OLLAMA_MODEL_MAIN"]
        self.ollama_model_judge = CONFIG_DEFAULTS["OLLAMA_MODEL_JUDGE"]

        self.openai_model_fallback = CONFIG_DEFAULTS["OPENAI_MODEL_FALLBACK"]
        self.openai_enabled = bool(OPENAI_API_KEY) and (OpenAI is not None)
        self._openai = OpenAI(api_key=OPENAI_API_KEY) if self.openai_enabled else None

    # ---------- Ollama ----------
    def ollama_chat(
        self,
        system: str,
        user: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> LLMResult:
        model = model or self.ollama_model_main
        url = f"{self.ollama_url}/api/chat"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {
                "temperature": temperature,
            },
            "stream": False,
        }
        r = requests.post(url, json=payload, timeout=180)
        r.raise_for_status()
        data = r.json()
        text = data["message"]["content"]
        return LLMResult(text=text, provider="ollama", model=model)

    # ---------- OpenAI ----------
    def openai_chat(
        self,
        system: str,
        user: str,
        model: Optional[str] = None,
    ) -> LLMResult:
        if not self.openai_enabled:
            raise RuntimeError("OpenAI fallback requested but OPENAI_API_KEY/openai not available.")

        model = model or self.openai_model_fallback

        # Use Responses API (newer). Works with gpt-4o.
        resp = self._openai.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=CONFIG_DEFAULTS["OPENAI_TEMPERATURE"],
            top_p=CONFIG_DEFAULTS["OPENAI_TOP_P"],
        )
        # Extract text
        text_parts: List[str] = []
        for item in resp.output:
            if item.type == "message":
                for c in item.content:
                    if c.type == "output_text":
                        text_parts.append(c.text)
        text = "\n".join(text_parts).strip()
        return LLMResult(text=text, provider="openai", model=model)

    # ---------- Strategy ----------
    def call_best_effort_json(
        self,
        system: str,
        user: str,
        prefer_local: bool = True,
        local_temperature: float = 0.7,
        openai_model: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], LLMResult]:
        """
        Try local first (if enabled), parse JSON; if fails, fallback to OpenAI (if available).
        """
        last_err: Optional[Exception] = None

        if prefer_local and self.use_local_first:
            try:
                res = self.ollama_chat(system=system, user=user, temperature=local_temperature)
                obj = extract_first_json_object(res.text)
                return obj, res
            except Exception as e:
                last_err = e

        # Fallback
        try:
            res = self.openai_chat(system=system, user=user, model=openai_model)
            obj = extract_first_json_object(res.text)
            return obj, res
        except Exception as e:
            if last_err:
                raise RuntimeError(f"Local failed: {last_err}\nOpenAI failed: {e}") from e
            raise


# ============================================================
# LLM prompts
# ============================================================
def system_place_entity() -> str:
    return """
You extract grounded story anchors from a confessional horror script.

Rules:
- Return ONLY valid JSON.
- Keep outputs short, concrete, non-poetic.
- Do NOT add new story facts. Infer only what is strongly suggested.
- The "entity" must not be a fixed creature design. Describe it as an unseen threat behavior + the type of traces it leaves.
- Monetization-safe.
JSON schema:
{
  "place": "1 sentence: primary setting vibe (house/apartment/car/etc.) plus 1-2 tangible descriptors",
  "entity": "1 sentence: unseen invasive threat described by behavior + physical evidence it leaves"
}
""".strip()


def user_place_entity(script_text: str) -> str:
    return f"""
SCRIPT (read-only):
{script_text}

Extract the primary [place] and [entity] descriptions.
Return ONLY JSON.
""".strip()


def system_image_prompts() -> str:
    return """
You generate grounded, non-repetitive image prompts from a completed script.

Hard rules:
- The SCRIPT is immutable. Do NOT rewrite, escalate, or add new events.
- You must keep visuals believable: found footage / VHS / analog distortion / low-light realism.
- No glowing eyes, no CGI beams, no magical auras.
- Avoid repeated compositions. Each prompt must be clearly distinct.
- No clear faces unless unavoidable.
- Humans must never be centered, posed, or facing the camera.

CRITICAL RETENTION RULES:
- For the FIRST IMAGE ONLY (image 1 of chunk 1):
  - A male adult human MUST be partially visible (hands, legs, silhouette, reflection).
  - The visual MUST show an ACTIVE violation interacting with the human or their space.
  - The danger must be readable in under 1 second with no context.
  - Mood-only images are NOT allowed for this first image.
  
COGNITIVE LOAD RULES (first 2 chunks):
- One subject only.
- One visual violation only.
- No symbolic or layered meaning.
- Viewer should instantly answer: “What is wrong here?”

Placeholder rules:
- Use placeholders ONLY when that thing is on-screen:
  - [narrator] only if narrator is visible
  - [entity] only if the entity is visible (even partially) OR its physical trace is the focal reveal
  - [place] only if the environment is the focal frame (wide/room/street/car interior etc.)
- If only a part of narrator is visible, do NOT use [narrator]. Use: "adult male (what is visible)".
  Examples: "adult male hands", "adult male silhouette", "adult male torso in hoodie"
- If only a partial/indirect entity presence is visible, do NOT use [entity]. Use: "unseen presence suggested by (trace)".
- Prompts must be interesting and cinematic-REALISTIC (not cinematic-writing): practical lighting, messy realism, plausible camera angles.
- Prefer visuals where something physical is subtly incorrect: light direction, liquid behavior, shadows, spatial logic.

Return ONLY JSON in this schema:
{
  "images": [
    {
      "focus": "one short phrase: what this image focuses on",
      "prompt": "the full image prompt",
      "hook_hint": "plain-language danger summary for title/caption alignment (first image only)"
    },
    {
      "focus": "..."
      "prompt": "..."
    }
  ]
}
""".strip()


def user_image_prompts(
    full_script: str,
    chunk_text: str,
    chunk_index: int,
    total_chunks: int,
    narrator_canon: str,
    place_desc: str,
    entity_desc: str,
    prior_prompts: List[str],
) -> str:
    prior_block = "\n".join([f"- {p}" for p in prior_prompts[-40:]])  # last 40 to keep context tight
    return f"""
FULL SCRIPT (read-only context):
{full_script}

GLOBAL CANON (read-only):
- Narrator canon (for your understanding only): {narrator_canon}
- [place] description: {place_desc}
- [entity] description: {entity_desc}

CHUNK {chunk_index + 1}/{total_chunks} (your ONLY source for what happens now):
{chunk_text}

ALREADY USED IMAGE PROMPTS (do NOT repeat compositions):
{prior_block if prior_block else "- (none yet)"}

Task:
- Create EXACTLY {CONFIG_DEFAULTS["IMAGES_PER_CHUNK"]} distinct image prompts for this chunk.
- Each prompt MUST start with this style prefix (verbatim), then a comma:
  "{CONFIG_DEFAULTS["STYLE_ANCHOR"]}"
- Keep them grounded and varied. Different angle/location/object each time.

IMPORTANT RETENTION RULES:
{"For CHUNK 1 ONLY:" if chunk_index == 0 else ""}
{"- Image 1 MUST include partial human presence AND an active visual violation." if chunk_index == 0 else ""}
{"- The violation must interact with the human or their immediate space." if chunk_index == 0 else ""}
{"- The image must be readable in under 1 second without narration." if chunk_index == 0 else ""}
{"- Include a short 'hook_hint' summarizing the danger in plain language." if chunk_index == 0 else ""}

{"For CHUNKS 1–2:" if chunk_index <= 1 else ""}
{"- One subject only." if chunk_index <= 1 else ""}
{"- One visual violation only." if chunk_index <= 1 else ""}
{"- Avoid atmosphere-only shots." if chunk_index <= 1 else ""}

Return ONLY JSON.
""".strip()


def system_judge() -> str:
    return """
You are a strict quality rater for horror image prompts.

Score each prompt 0-10 for:
- grounded realism (no fantasy glow/CGI)
- visual specificity and interest
- non-repetition vs prior list
- respects placeholder rules
- fits found-footage/VHS vibe

Return ONLY JSON:
{
  "scores": [
    {"score": 0-10, "reason": "short"}
  ],
  "min_score": 0-10
}
""".strip()


def user_judge(prompts: List[str], prior_prompts: List[str]) -> str:
    prior_block = "\n".join([f"- {p}" for p in prior_prompts[-40:]])  # last 40
    p_block = "\n".join([f"{i+1}. {p}" for i, p in enumerate(prompts)])
    return f"""
PRIOR PROMPTS (for repetition check):
{prior_block if prior_block else "- (none yet)"}

NEW PROMPTS TO SCORE:
{p_block}

Score them.
Return ONLY JSON.
""".strip()


# ============================================================
# Pipeline
# ============================================================
def find_latest_run_folder() -> Path:
    if not RUNS_DIR.exists():
        raise RuntimeError(f"RUNS_DIR missing: {RUNS_DIR}")
    runs = [p for p in RUNS_DIR.iterdir() if p.is_dir() and (p / "script.json").exists()]
    if not runs:
        raise RuntimeError(f"No runs found in {RUNS_DIR}")
    # sort by mtime
    runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return runs[0]


def load_script_from_run(run_folder: Path) -> Tuple[str, Dict[str, Any]]:
    script_path = run_folder / "script.json"
    data = read_json(script_path)
    script_text = data.get("script")
    if not isinstance(script_text, str) or not script_text.strip():
        raise RuntimeError(f"script.json missing 'script' text: {script_path}")
    return script_text.strip(), data


def quality_gate_local(
    llm: LLMClient,
    new_prompts: List[str],
    prior_prompts: List[str],
) -> Tuple[float, str]:
    """
    Uses local judge model first if available; if judge call fails, returns 0 score to trigger fallback.
    """
    try:
        res = llm.ollama_chat(
            system=system_judge(),
            user=user_judge(new_prompts, prior_prompts),
            model=CONFIG_DEFAULTS["OLLAMA_MODEL_JUDGE"],
            temperature=0.2,
        )
        obj = extract_first_json_object(res.text)
        min_score = float(obj.get("min_score", 0.0))
        reason = ""
        scores = obj.get("scores", [])
        if scores and isinstance(scores, list):
            # gather low reasons
            lows = [s for s in scores if float(s.get("score", 0.0)) < CONFIG_DEFAULTS["MIN_SCORE_TO_ACCEPT"]]
            if lows:
                reason = "; ".join([normalize_whitespace(l.get("reason", "")) for l in lows][:3])
        return min_score, reason or "ok"
    except Exception as e:
        return 0.0, f"judge_failed: {e}"


def generate_place_entity(
    llm: LLMClient,
    script_text: str,
) -> Tuple[str, str, LLMResult]:
    obj, res = llm.call_best_effort_json(
        system=system_place_entity(),
        user=user_place_entity(script_text),
        prefer_local=True,
        local_temperature=0.4,
    )
    place = normalize_whitespace(str(obj.get("place", "")).strip()) or "a private indoor space with practical lighting"
    entity = normalize_whitespace(str(obj.get("entity", "")).strip()) or "an unseen invasive presence leaving measurable traces"
    return place, entity, res


def generate_prompts_for_chunk(
    llm: LLMClient,
    full_script: str,
    chunk_text: str,
    chunk_index: int,
    total_chunks: int,
    narrator_canon: str,
    place_desc: str,
    entity_desc: str,
    prior_prompts: List[str],
) -> Tuple[List[Dict[str, str]], LLMResult, bool, str]:
    """
    Returns: (images[], llm_result, used_fallback, note)
    images[] contains {"focus": "...", "prompt": "..."} entries
    """
    sys = system_image_prompts()
    usr = user_image_prompts(
        full_script=full_script,
        chunk_text=chunk_text,
        chunk_index=chunk_index,
        total_chunks=total_chunks,
        narrator_canon=narrator_canon,
        place_desc=place_desc,
        entity_desc=entity_desc,
        prior_prompts=prior_prompts,
    )

    # Fallback: OpenAI (GPT-4o)
    res = llm.openai_chat(system=sys, user=usr)
    obj = extract_first_json_object(res.text)
    images = obj.get("images", [])
    # Enforce hook_hint for first chunk, first image
    if chunk_index == 0:
        first = images[0] if images else {}
        hook = normalize_whitespace(str(first.get("hook_hint", "")))
        if not hook or len(hook.split()) < 4:
            raise RuntimeError(
                "First image missing usable hook_hint (must be plain-language danger summary)."
            )
    if not isinstance(images, list) or len(images) != CONFIG_DEFAULTS["IMAGES_PER_CHUNK"]:
        raise RuntimeError(f"Fallback returned invalid images list for chunk {chunk_index+1}.")
    cleaned = []
    for it in images:
        cleaned.append({
            "focus": normalize_whitespace(str(it.get("focus", "")))[:140] or "scene beat",
            "prompt": normalize_whitespace(str(it.get("prompt", ""))),
            "hook_hint": normalize_whitespace(str(it.get("hook_hint", "")))[:120] if chunk_index == 0 else "",
        })
    return cleaned, res, True, "fallback_openai"


def build_outputs(
    run_folder: Path,
    original_script_json: Dict[str, Any],
    narrator_canon: str,
    place_desc: str,
    entity_desc: str,
    chunks: List[str],
    images_by_chunk: List[Dict[str, Any]],
    provenance: Dict[str, Any],
) -> None:
    out = {
        "schema": {"name": "image_prompts_from_script", "version": SCHEMA_VERSION},
        "run_folder": str(run_folder),
        "created_at": utc_now_iso(),
        "config": {
            k: (v if k not in {"OPENAI_API_KEY"} else "REDACTED")
            for k, v in CONFIG_DEFAULTS.items()
        },
        "narrator_canon": narrator_canon,
        "place_description": place_desc,
        "entity_description": entity_desc,
        "chunks": [
            {
                "chunk_index": i,
                "chunk_text": chunks[i],
                "images": images_by_chunk[i]["images"],
                "llm": images_by_chunk[i]["llm"],
                "note": images_by_chunk[i]["note"],
            }
            for i in range(len(chunks))
        ],
        "provenance": provenance,
    }

    write_json(run_folder / "image_prompts.json", out)

    # Also produce a merged file for convenience
    merged = dict(original_script_json)
    merged["narrator_canon"] = narrator_canon
    merged["place_description"] = place_desc
    merged["entity_description"] = entity_desc
    merged["image_prompt_chunks"] = out["chunks"]
    merged["_generated_at"] = utc_now_iso()
    write_json(run_folder / "script_with_prompts.json", merged)


# ============================================================
# CLI / main
# ============================================================
def parse_args() -> Dict[str, Any]:
    import argparse

    p = argparse.ArgumentParser(description="Generate image prompts from an existing script.json run.")
    p.add_argument("--run", type=str, default="", help="Path to a run folder containing script.json (e.g., runs/20260127_123000)")
    p.add_argument("--latest", action="store_true", help="Use latest run folder in runs/")
    p.add_argument("--seed", type=int, default=0, help="Optional RNG seed for narrator canon. 0 = derive from run id/time.")
    return vars(p.parse_args())


def main():
    args = parse_args()
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    if args["latest"]:
        run_folder = find_latest_run_folder()
    elif args["run"]:
        run_folder = Path(args["run"]).expanduser().resolve()
    else:
        run_folder = find_latest_run_folder()

    if not run_folder.exists():
        raise RuntimeError(f"Run folder does not exist: {run_folder}")
    if not (run_folder / "script.json").exists():
        raise RuntimeError(f"script.json not found in: {run_folder}")

    script_text, original = load_script_from_run(run_folder)

    # Seed: stable-ish per run folder
    seed = args["seed"]
    if seed == 0:
        # Derive from folder name
        seed = abs(hash(run_folder.name)) % (2**31 - 1)
    rng = random.Random(seed)

    narrator_canon = create_narrator_canon(rng)

    llm = LLMClient()

    # Place/entity
    place_desc, entity_desc, pe_res = generate_place_entity(llm, script_text)
    print(f"[place/entity] provider={pe_res.provider} model={pe_res.model}")
    print(f"[place]  {place_desc}")
    print(f"[entity] {entity_desc}")

    # Chunking
    chunks = chunk_script_by_words(script_text)
    total_chunks = len(chunks)
    if CONFIG_DEFAULTS["IMAGES_PER_CHUNK"] != 2:
        raise RuntimeError("IMAGES_PER_CHUNK must be 2 for your requirement.")
    print(f"[chunking] chunks={total_chunks} words_target={CONFIG_DEFAULTS['CHUNK_WORDS']} images_total={total_chunks*2}")

    prior_prompts: List[str] = []
    images_by_chunk: List[Dict[str, Any]] = []

    fallback_count = 0

    for i, ch in enumerate(chunks):
        try:
            images, res, used_fallback, note = generate_prompts_for_chunk(
                llm=llm,
                full_script=script_text,
                chunk_text=ch,
                chunk_index=i,
                total_chunks=total_chunks,
                narrator_canon=narrator_canon,
                place_desc=place_desc,
                entity_desc=entity_desc,
                prior_prompts=prior_prompts,
            )
            if used_fallback:
                fallback_count += 1

            for it in images:
                prior_prompts.append(it["prompt"])

            images_by_chunk.append({
                "images": images,
                "llm": {"provider": res.provider, "model": res.model},
                "note": note,
            })

            print(f"[chunk {i+1}/{total_chunks}] ok provider={res.provider} model={res.model} note={note}")

        except Exception as e:
            print(f"[chunk {i+1}/{total_chunks}] FAILED: {e}")
            traceback.print_exc()
            raise

    provenance = {
        "place_entity_llm": {"provider": pe_res.provider, "model": pe_res.model},
        "fallback_used_chunks": fallback_count,
        "seed": seed,
    }

    build_outputs(
        run_folder=run_folder,
        original_script_json=original,
        narrator_canon=narrator_canon,
        place_desc=place_desc,
        entity_desc=entity_desc,
        chunks=chunks,
        images_by_chunk=images_by_chunk,
        provenance=provenance,
    )

    print(f"✅ Wrote:\n- {run_folder / 'image_prompts.json'}\n- {run_folder / 'script_with_prompts.json'}")


if __name__ == "__main__":
    main()
