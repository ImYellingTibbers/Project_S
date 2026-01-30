import subprocess
import time

def _run(cmd):
    subprocess.run(
        cmd,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def kill_comfyui():
    print("[kill] Killing ComfyUI (Linux)")
    _run("pkill -f comfyui")
    _run("pkill -f 'python.*main.py'")
    time.sleep(1)

def kill_ollama():
    print("[kill] Killing Ollama (Linux)")
    _run("pkill -f ollama")
    time.sleep(1)

def kill_all():
    print("[kill] HARD reset of GPU / LLM stack")
    kill_comfyui()
    kill_ollama()
    print("[kill] GPU / LLM stack fully cleared")

if __name__ == "__main__":
    kill_all()
