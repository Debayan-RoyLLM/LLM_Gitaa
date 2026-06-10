#!/usr/bin/env python3

import yaml
import subprocess
import os
import time
import sys


CONFIG_FILE = "./litellm_config.yaml"


# ─── Step 1: Read models from litellm_config.yaml ────────────────
def load_models_from_config(config_file):
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    models = []
    for entry in config.get("model_list", []):
        name      = entry["model_name"]
        params    = entry["litellm_params"]
        api_base  = params.get("api_base", "")
        port      = api_base.rstrip("/").split(":")[-1].replace("/v1", "")
        model_str = params.get("model", "")
        max_tokens= params.get("max_tokens", 2048)

        models.append({
            "name"      : name,
            "port"      : port,
            "model_str" : model_str,
            "max_tokens": max_tokens,
        })

    return models


# ─── Step 2: Ask for base model directory ────────────────────────
def get_base_dir():
    base_dir = input("\nEnter base directory where models are stored\n"
                     "(e.g. /mnt/f_disk/gitaa/debayan/Internal_LLM/models): ").strip()
    if not os.path.isdir(base_dir):
        print(f"⚠️  Warning: '{base_dir}' does not exist. Proceeding anyway.")
    return base_dir


# ─── Step 3: Improved fuzzy match model name to folder ───────────
def normalize(s):
    """ strip everything except alphanumeric chars and lowercase """
    return ''.join(c for c in s.lower() if c.isalnum())

def guess_model_folder(model_name, base_dir):
    if not os.path.isdir(base_dir):
        return None

    folders     = os.listdir(base_dir)
    model_norm  = normalize(model_name)

    best_match  = None
    best_score  = 0

    for folder in folders:
        folder_norm = normalize(folder)

        # score = how many chars of model_name appear in folder_name
        # check both directions for partial overlap
        if model_norm in folder_norm:
            score = len(model_norm)
        elif folder_norm in model_norm:
            score = len(folder_norm)
        else:
            # count common leading characters
            score = sum(1 for a, b in zip(model_norm, folder_norm) if a == b)

        if score > best_score:
            best_score = score
            best_match = folder

    # only return if score is meaningful (at least 5 chars matched)
    if best_score >= 5:
        return os.path.join(base_dir, best_match)
    return None


# ─── Step 4: Show models as numbered table ───────────────────────
def show_models(models, base_dir):
    print("\n" + "="*65)
    print(f"  {'#':<4} {'Model Name':<30} {'Port':<8} {'Folder Found'}")
    print("="*65)
    for i, m in enumerate(models, 1):
        guessed = guess_model_folder(m["name"], base_dir)
        m["guessed_path"] = guessed
        folder  = os.path.basename(guessed) if guessed else "⚠️  not found"
        print(f"  {i:<4} {m['name']:<30} {m['port']:<8} {folder}")
    print("="*65)
    print("  Enter the number to select a model")
    print("="*65)


# ─── Step 5: Get user selection ──────────────────────────────────
def get_user_input(models, base_dir):

    while True:
        choice = input("\nEnter model number (1-{}): ".format(len(models))).strip()
        if choice.isdigit() and 1 <= int(choice) <= len(models):
            selected = models[int(choice) - 1]
            break
        print(f"❌ Invalid input. Enter a number between 1 and {len(models)}")

    print(f"\n✅ Selected: {selected['name']}")

    # port
    port_input = input(f"Enter vLLM port [press Enter for default: {selected['port']}]: ").strip()
    vllm_port  = port_input if port_input else selected["port"]

    # GPU
    gpu_index = input("Enter GPU index (e.g. 0, 1, 2): ").strip()

    # model path
    guessed    = selected.get("guessed_path", "")
    path_input = input(f"Enter model path [press Enter for: {guessed}]: ").strip()
    model_path = path_input if path_input else guessed

    if not model_path:
        print("❌ Model path is required!")
        sys.exit(1)

    return {
        "name"      : selected["name"],
        "vllm_port" : vllm_port,
        "gpu_index" : gpu_index,
        "model_path": model_path,
        "max_tokens": selected["max_tokens"],
    }


# ─── Step 6: Kill existing vLLM ──────────────────────────────────
def kill_existing_vllm():
    print("\n🔴 Stopping existing vLLM process...")
    result = subprocess.run(["pkill", "-f", "vllm serve"], capture_output=True)
    if result.returncode == 0:
        print("✅ Killed existing vLLM")
        time.sleep(2)
    else:
        print("ℹ️  No existing vLLM process found")


# ─── Step 7: Start vLLM ──────────────────────────────────────────
def start_vllm(selection):
    print(f"\n🚀 Starting vLLM...")
    print(f"   Model : {selection['name']}")
    print(f"   Port  : {selection['vllm_port']}")
    print(f"   GPU   : {selection['gpu_index']}")
    print(f"   Path  : {selection['model_path']}")

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = selection["gpu_index"]

    cmd = [
        "vllm", "serve", selection["model_path"],
        "--port"                  , selection["vllm_port"],
        "--api-key"               , "not-needed",
        "--enforce-eager",
        "--max-model-len"         , "8192",
        "--dtype"                 , "bfloat16",
        "--gpu-memory-utilization", "0.80",
        "--served-model-name"     , selection["name"],
    ]

    process = subprocess.Popen(cmd, env=env)
    print(f"\n✅ vLLM started (PID: {process.pid})")
    return process


# ─── Main ─────────────────────────────────────────────────────────
def main():
    models   = load_models_from_config(CONFIG_FILE)
    base_dir = get_base_dir()

    show_models(models, base_dir)
    selection = get_user_input(models, base_dir)

    print("\n" + "="*65)
    print("  Summary")
    print("="*65)
    for k, v in selection.items():
        print(f"  {k:<20}: {v}")
    print("="*65)

    confirm = input("\nProceed? (y/n): ").strip().lower()
    if confirm != "y":
        print("❌ Aborted.")
        sys.exit(0)

    kill_existing_vllm()
    start_vllm(selection)

    print(f"\n🟢 vLLM running. Press Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🔴 Stopping vLLM...")
        subprocess.run(["pkill", "-f", "vllm serve"])
        print("✅ Done.")


if __name__ == "__main__":
    main()
