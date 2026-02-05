import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
RUNS_DIR = PROJECT_ROOT / "runs"

STEP_1 = {"label": "Step 1 - Generate Script", "script": "run_steps/generate_script.py"}

STEPS = [
    STEP_1,
]

def run_step(label, script_rel_path):
    script_path = (PROJECT_ROOT / script_rel_path).resolve()
    if not script_path.exists():
        print(f"❌ Error: {label} missing at {script_path}")
        return False

    print(f"\n=== {label} ===")
    cmd = [sys.executable, str(script_path)]
    env = {"PYTHONPATH": str(PROJECT_ROOT), "PYTHONUNBUFFERED": "1"}
    
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
    return result.returncode == 0

def main():
    RUNS_DIR.mkdir(exist_ok=True)
    start_time = time.time()

    for step in STEPS:
        success = run_step(step["label"], step["script"])
        if not success:
            print(f"\n🛑 Pipeline FAILED at {step['label']}")
            sys.exit(1)

    elapsed = time.time() - start_time
    print(f"\n✅ Pipeline completed successfully in {elapsed:.2f}s.")

if __name__ == "__main__":
    main()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
def generate_full_story() -> str:
    concept = generate_concept_and_hook()
    acts = generate_act_outline(concept)

    full_script = f"{concept['HOOK']}\n\n"
    
    # ============================================================
    # ACT 1
    # ============================================================

    act_1 = acts[0]
    arc = concept["ARC"]

    act_1_context = (
        f"{concept['HOOK']}\n\n"
        f"STORY ARC: {arc['name']}\n"
        f"ARC THEME: {arc['theme']}\n"
        f"ACT 1 RULES: {arc['act_1_rules']}\n"
        f"ACT 1 FOCUS: {arc['act_1_focus']}\n\n"
        "ACT 1 REQUIRED DEVICE:\n"
        "- Include ONE primary 'almost-right' detail (a copied habit/object/detail that is close but slightly wrong).\n"
        "- The narrator notices it but rationalizes it.\n"
        "ACT 1 REQUIRED COST:\n"
        "- Include ONE subtle personal cost (lost sleep, altered routine, withheld information, or avoidance).\n"
        "- The cost must occur WITHOUT proof or confrontation.\n"
        "- The narrator does not yet admit fear, but their behavior changes.\n\n"
    )

    act_1_text = None

    for _ in range(3):
        candidate = write_act(act_1, act_1_context, concept, act_number=1)
        if judge_act_scope(candidate, arc, act_number=1):
            act_1_text = candidate
            break

    if act_1_text is None:
        act_1_text = candidate  # fallback

    act_1_text = polish_act(act_1_text)
    full_script += "\n\n" + act_1_text
    
    # ============================================================
    # ACT 2
    # ============================================================

    act_2 = acts[1]

    act_2_context = (
        f"{full_script}\n\n"
        f"STORY ARC: {arc['name']}\n"
        f"ARC THEME: {arc['theme']}\n"
        f"ACT 2 RULES: {arc['act_2_rules']}\n"
        f"ACT 2 FOCUS: {arc['act_2_focus']}\n\n"
        "ACT 2 REQUIRED BEHAVIOR:\n"
        "- The anomaly repeats with increased specificity or accuracy.\n"
        "- The narrator notices timing, anticipation, or familiarity.\n\n"
        "ACT 2 REQUIRED COST:\n"
        "- The narrator changes behavior to test or manage the situation.\n"
        "- Anxiety or vigilance replaces casual rationalization.\n\n"
        "ACT 2 PROHIBITIONS:\n"
        "- No confrontation.\n"
        "- No proof.\n"
        "- The narrator may narrowly avoid a situation that feels physically dangerous\n"
        "- Avoidance must occur through chance, instinct, or interruption\n"
        "- No explicit surveillance or admissions.\n\n"
    )
    
    act_2_text = None

    for _ in range(3):
        candidate = write_act(act_2, act_2_context, concept, act_number=2)
        if judge_act_scope(candidate, arc, act_number=2):
            act_2_text = candidate
            break

    if act_2_text is None:
        act_2_text = candidate  # fallback, never hard-fail

    act_2_text = polish_act(act_2_text)
    full_script += "\n\n" + act_2_text
    
    # ============================================================
    # ACT 3
    # ============================================================

    act_3 = acts[2]

    act_3_context = (
        f"{full_script}\n\n"
        f"STORY ARC: {arc['name']}\n"
        f"ARC THEME: {arc['theme']}\n"
        f"ACT 3 RULES: {arc['act_3_rules']}\n"
        f"ACT 3 FOCUS: {arc['act_3_focus']}\n\n"
        "ACT 3 REQUIRED BEHAVIOR:\n"
        "- The anomaly becomes personal and targeted.\n"
        "- The narrator realizes it is not random.\n\n"
        "ACT 3 REQUIRED COST:\n"
        "- Sustained emotional or physical toll (sleep loss, isolation, stress symptoms).\n"
        "- The narrator withdraws from normal support.\n\n"
        "ACT 3 PROHIBITIONS:\n"
        "- No resolution.\n"
        "- No full confrontation.\n"
        "- No explicit proof or confession.\n\n"
    )

    act_3_text = None

    for _ in range(3):
        candidate = write_act(act_3, act_3_context, concept, act_number=3)
        if judge_act_scope(candidate, arc, act_number=3):
            act_3_text = candidate
            break

    if act_3_text is None:
        act_3_text = candidate

    act_3_text = polish_act(act_3_text)
    full_script += "\n\n" + act_3_text
    
    # ============================================================
    # ACT 4
    # ============================================================

    act_4 = acts[3]

    act_4_context = (
        f"{full_script}\n\n"
        f"STORY ARC: {arc['name']}\n"
        f"ARC THEME: {arc['theme']}\n"
        f"ACT 4 RULES: {arc['act_4_rules']}\n"
        f"ACT 4 FOCUS: {arc['act_4_focus']}\n\n"
        "ACT 4 REQUIRED BEHAVIOR:\n"
        "- The narrator takes a logical action meant to regain control.\n"
        "- This action directly worsens the situation.\n\n"
        "ACT 4 REQUIRED EVENT:\n"
        "- A confrontation, discovery, or exposure attempt that fails.\n\n"
        "ACT 4 PROHIBITIONS:\n"
        "- No clean resolution.\n"
        "- No removal of the threat.\n\n"
    )

    act_4_text = None

    for _ in range(3):
        candidate = write_act(act_4, act_4_context, concept, act_number=4)
        if judge_act_scope(candidate, arc, act_number=4):
            act_4_text = candidate
            break

    if act_4_text is None:
        act_4_text = candidate

    act_4_text = polish_act(act_4_text)
    full_script += "\n\n" + act_4_text

    # ============================================================
    # ACT 5
    # ============================================================

    act_5 = acts[4]

    act_5_context = (
        f"{full_script}\n\n"
        f"STORY ARC: {arc['name']}\n"
        f"ARC THEME: {arc['theme']}\n"
        f"ACT 5 RULES: {arc['act_5_rules']}\n"
        f"ACT 5 FOCUS: {arc['act_5_focus']}\n\n"
        "ACT 5 REQUIRED STATE:\n"
        "- The narrator is not safe, but is no longer resisting.\n"
        "- The situation is unresolved and permanent.\n\n"
        "ACT 5 ENDING RULE:\n"
        "- End on implication, not explanation.\n"
        "- The threat remains active.\n\n"
    )

    act_5_text = None

    for _ in range(3):
        candidate = write_act(act_5, act_5_context, concept, act_number=5)
        if judge_act_scope(candidate, arc, act_number=5):
            act_5_text = candidate
            break

    if act_5_text is None:
        act_5_text = candidate

    act_5_text = polish_act(act_5_text)
    full_script += "\n\n" + act_5_text


    return full_script