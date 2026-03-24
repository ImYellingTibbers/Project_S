# Project S

An automated YouTube video production system. You run one command at night. By morning there's a finished video — script written, narrated, illustrated, and edited — sitting in the output folder.

No human writes a script, records audio, or touches a timeline.

The system manages multiple YouTube channels, each with its own content format and generation pipeline. Every channel handles the full stack: story concept → script → text-to-speech → AI-generated visuals → video assembly → YouTube metadata. Two channels are in active production, two are built for a different format.

---

## Active Channels

**Eyes of Midnight** — longform horror compilations (10–15 min). Three separate confessional horror stories generated, narrated, and illustrated, then stitched together with title cards into a single compilation video.

**The Rulebook** — rule-based workplace horror. Stories are structured around a set of strange rules a narrator discovers on a new job. The pipeline manages which rules have been introduced, which are active, and how their accumulation changes the story's options over time.

**Residual Fear / Off Hours Encounters** — shorter format channels sharing a similar pipeline but using a different model stack and adding burned-in captions for Shorts/TikTok format. Built and functional, run independently.

---

## Tech Stack

| Layer | What |
|---|---|
| Script generation | Google Gemma 3 27B (OpenRouter) |
| Planning / story seeding | Meta Llama 3.3 70B (OpenRouter) |
| Text-to-speech | Qwen3-TTS 1.7B — local, CUDA |
| Image generation | Stable Diffusion XL via ComfyUI — local, CUDA |
| Video encoding | FFmpeg + H264 NVENC (GPU) |
| Audio processing | pyloudnorm, scipy |
| Python environment | `.venv`, 3.11+ |

---

## Top-Level Structure

```
run_all.py                              ← master night runner
├── the_rulebook/src/run.py
├── eyes_of_midnight/src/batch_run.py
├── residual_fear/src/run.py
└── off_hours_encounters/src/run.py
```

`run_all.py` is intentionally minimal — it runs each enabled channel as a subprocess, logs timing, and stops the entire run on the first failure. You schedule it with cron and don't think about it.

---

## Eyes of Midnight

### Pipeline

```
Step 0  plan_video.py          Pick unused title, generate 3 story seeds → video_plan.json
Step 1  run.py STORY_INDEX=0   Full 4-step pipeline for story 1
Step 2  run.py STORY_INDEX=1   Full 4-step pipeline for story 2
Step 3  run.py STORY_INDEX=2   Full 4-step pipeline for story 3
Step 4  stitch_videos.py       Title cards + concat → compiled_final.mp4
Step 5  generate_metadata.py   YouTube SEO metadata
```

Each `run.py` call handles script → VO → images → video for one story and writes its output folder name back into `video_plan.json`, so the stitcher can find all three.

### Title Bank

`title_bank.json` holds 500 curated YouTube-style horror compilation titles. Step 0 picks one that hasn't been used, marks it consumed, and uses it as the creative brief for the whole batch. A separate generator script replenishes the bank when it runs low.

### Script Generation

Scripts are 5-act first-person confessional horror, written by Gemma 3 27B. Step 0 uses Llama 70B to generate three 2-sentence story seeds from the main title — each one a different setting and threat dynamic. Each `run.py` picks up its seed via a `STORY_INDEX` environment variable and hands it to the script generator.

The model receives the seed, a narrative structure, and voice guidelines, then writes the full script. The approach is deliberately light on constraint — over-prompting produces generic output faster than under-prompting does.

### Text-to-Speech

Narration runs through Qwen3-TTS locally on the GPU. The model is conditioned on a reference recording (`jacob_whisper_ref.wav`) for consistent speaker identity across the full video. Temperature is kept low (0.45) for the flat, controlled delivery that works well for horror narration.

TTS runs paragraph by paragraph, saving individual WAV files that later feed into image timing. After generation:
- **RMS compression** — gentle (2:1 ratio, -22dB threshold) to even out dynamics
- **LUFS normalization** — target -18 LUFS, -3dB true-peak ceiling (YouTube's loudness standard)

### Image Generation

ComfyUI runs as a background server with SD XL loaded. The script identifies visual chunks from the narration, builds a prompt for each, and sends jobs over WebSocket using a pre-built workflow graph. Prompts and seeds are injected dynamically; everything else (sampler, steps, CFG) stays fixed per channel.

Every image is anchored to a shared aesthetic — photorealistic nighttime photography, empty real-world locations, deep shadows, no people. The negative prompt specifically excludes faces, creatures, and anything overtly monstrous. The goal is unsettling by absence.

Image generation retries up to 6 times with exponential backoff to handle ComfyUI hiccups and API rate limits.

### Video Assembly

FFmpeg does everything in a single NVENC pass at 4K/30fps: zoom-pan with sinusoidal drift (so images don't feel static), vignetting, subtle grain, fade-in, full audio mix with narration + ambient music + bass sting. Image durations come directly from paragraph audio lengths — each visual holds on screen for exactly as long as the corresponding narration takes.

### Stitching Three Stories Together

`stitch_videos.py` pulls the three completed story videos from `video_plan.json`, generates title card images with Pillow (main title + per-story mini titles), and concatenates everything into the final compilation.

The tricky part was audio. FFmpeg's built-in AAC encoder occasionally produces malformed frames — a known "too many bits" bug — which causes the concat demuxer to crash. The fix was to pre-process each story individually before concatenation: extract audio to clean PCM WAV with error-tolerant flags, then remux with freshly encoded AAC. Trying to make the demuxer tolerate the bad frames through flags didn't work; the remux approach does.

---

## The Rulebook

### What Makes It Different

Eyes of Midnight is seed-driven — a 2-sentence idea becomes a script. The Rulebook is system-driven — a place plus a set of rules becomes a script. The story's structure is determined before any writing starts, and the generation engine has to track state as it goes.

### Assets

**`places_library.py`** — 50+ real-world workplace locations, each tagged with which rule types make sense for that setting.

**`rules_library.py`** — 20+ violation rules, each with a template (including bracketed placeholders like `[specific sound]`, `[specific location]`), a consequence tone, a suggested story moment, and compatibility tags that match against place types.

**`narrative_library.py`** — per-story randomization pools. Twelve opening approaches describing different ways the narrator could begin the story, ten handoff methods describing how they might first receive the rules, eight resolution ending types, and a pool of 130+ character names. One of each is sampled per story and injected into the prompts. The LLM only sees the one it's working with — never a menu.

This last file exists because any example you put in a prompt tends to become the default across all runs. Moving the selection to Python and injecting only the chosen option eliminates that problem.

### Story Generation

`idea_generator.py` assembles the story frame before writing starts:
1. Randomly selects a place
2. Samples compatible rules (8–10 per story), shuffles them to determine act order
3. Generates a narrator backstory via LLM — age, financial situation, reason for taking the job — and runs it through a separate judge call to verify it's specific enough before accepting it

Then `generate_script.py` writes the story one act at a time, maintaining a rules state object throughout:

```python
rules_state = {
    "established": [...],  # rules the narrator has already encountered
    "pending": [...]        # rules not yet triggered — LLM is told to ignore these
}
```

After each act, a second LLM call does two things in one JSON response: summarizes the act (3–5 sentences for early acts, updating a rolling 10-sentence summary for later ones) and records exactly how the primary rule manifested. The running summary becomes the context window for the next act — keeping the story coherent across 10+ acts without blowing the token budget.

### Structural Variation

Early versions of the Rulebook produced stories with the same shape every time: narrator notices something, dismisses it, notices it again, remembers the rule, complies. The prompt described a default structure so thoroughly that an appended "vary this" instruction couldn't override it.

The fix was to make the variation the frame itself, not an addendum. There are 5 distinct structural shapes for rule acts (preemptive compliance, near-miss, rule vs. urgent need, ambiguous trigger, perfect compliance that still witnesses something). At the start of each story, they're shuffled into a random order and assigned to acts in sequence — so each act gets a different shape, and the same act slot gets different shapes across runs.

### Banned Phrase Detection

Certain phrases kept showing up no matter what the prompt said — "I couldn't shake the feeling", "my heart hammered", "the smell of pennies". Listing them as banned in the system prompt made things worse, not better — long lists of forbidden phrases dilute attention, and the model stops registering them.

The solution was to move detection out of the prompt entirely. After each act is generated, a Python function scans the text. If banned phrases are found, the act gets one retry. Deterministic, free, and doesn't cost any of the model's attention.

---

## Residual Fear / Off Hours Encounters

Shorts-format channels with a slightly different tech stack — scripts generated via OpenAI + local Ollama, same ComfyUI image pipeline, plus a timing planner step that maps narration to visual beats and a caption-burning step for Shorts/TikTok format. They share the structural bones of the longform channels but run on their own schedule.

---

## Engineering Notes

**VRAM contention** — ComfyUI runs with `--normalvram` and keeps the SD model resident between jobs. The TTS model also needs ~4GB. On an 8GB GPU they can't coexist. The fix is to call ComfyUI's `/free` API endpoint before TTS starts, forcing it to evict cached models. Both production channels do this now.

**Rate limits during long runs** — A full Rulebook run (10+ acts × 2 LLM calls each, then TTS, then image generation) can run for several hours and hammer the OpenRouter API. Retry logic handles 429s and server errors with exponential backoff. The original code didn't catch network-level timeouts (`ReadTimeout`, `ConnectionError`) at all — those now go through the same retry path.

**LLM output coercion** — LLMs occasionally return a nested dict or list where a string is expected. Rather than crashing, the code has a small helper that knows how to unwrap common malformed shapes and raises cleanly if it still can't get a usable string.

**Opening repetition** — Any concrete example phrase in a prompt tends to become the LLM's default across all runs. The system originally had an example opening line in the setup directive and it showed up nearly verbatim in every story. Removing example phrases and describing intent instead of demonstrating it fixed it.

---

## Running It

```bash
# activate the environment
source .venv/bin/activate

# run all active channels (designed for nightly cron)
python run_all.py

# run a single channel
python eyes_of_midnight/src/batch_run.py
python the_rulebook/src/run.py
```

ComfyUI needs to be running before image generation. The pipeline starts it automatically if it isn't up. Each channel reads its API keys and config from its own `.env` file.

---

## Output Structure

```
eyes_of_midnight/
  runs/
    {timestamp}/              ← one story: script, audio, images, video_final.mp4
  {Sanitized_Title}/
    compiled_final.mp4        ← finished YouTube video
    metadata.json             ← title, description, tags

the_rulebook/
  runs/
    {timestamp}/
      script/                 ← full_script.txt, per-act files, paragraph index
      audio/                  ← full narration + per-paragraph WAVs
      img/                    ← 4K SD outputs + thumbnail variants
      video_final.mp4
```

Every intermediate artifact is saved. If a step fails partway through, you can restart from that step without regenerating everything before it.
