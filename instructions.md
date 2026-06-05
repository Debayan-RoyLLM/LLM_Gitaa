conda create -n LLM python=3.11
conda activate LLM

pip install vllm
pip install litellm
pip install "litellm[proxy]"

##--------------------------------##

conda create -n gemma3 python=3.11
conda activate gemma3


pip install -U huggingface_hub
huggingface-cli login

huggingface-cli download google/gemma-3-12b-it \
    --local-dir /mnt/models/gemma-3-12b-it

CUDA_VISIBLE_DEVICES=0 vllm serve google/gemma-3-12b-it   --port 8002   --api-key not-needed   --enforce-eager   --max-model-len 8192   --dtype bfloat16  --gpu-memory-utilization 0.80

##--------------------------------##

conda create -n llama3 python=3.11
conda activate llama3

pip install -U huggingface_hub
huggingface-cli login

huggingface-cli download meta-llama/Llama-3.2-3B-Instruct \
    --local-dir /mnt/models/Llama-3.2-3B-Instruct

##-------------------------------##

conda create -n gemma4 python=3.11
conda activate gemma4

pip install -U huggingface_hub
huggingface-cli login

huggingface-cli download google/gemma-4-31B-it \
    --local-dir /mnt/models/gemma-4-31B-it
##--------------------------------##
Step 1 — Delete existing env
bashconda deactivate
conda env remove -n qwen -y
# Verify it's gone
conda env list
Step 2 — Create fresh env and install in the correct order
bash# Create
conda create -n qwen_v2 python=3.11 -y
conda activate qwen_v2

# Install torch FIRST with correct CUDA
pip install torch==2.6.0 torchvision torchaudio \
  --index-url https://download.pytorch.org/whl/cu124 \
  --no-cache-dir

# Gate check 1 — DO NOT proceed if False
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
# Must print: 2.6.0+cu124 / True
Step 3 — Install transformers (pinned to 4.x)
bashpip install "transformers==4.51.3" accelerate --no-cache-dir

# Gate check 2
python -c "import transformers; print(transformers.__version__)"
# Must print: 4.51.3
Step 4 — Install vLLM without letting it touch torch
bashpip install vllm==0.8.5 --no-cache-dir

# Re-pin torch immediately (vllm may have overwritten it)
rm -rf $(python -c "import site; print(site.getsitepackages()[0])")/torch
rm -rf $(python -c "import site; print(site.getsitepackages()[0])")/torch-*.dist-info
rm -rf $(python -c "import site; print(site.getsitepackages()[0])")/torchaudio
rm -rf $(python -c "import site; print(site.getsitepackages()[0])")/torchaudio-*.dist-info
rm -rf $(python -c "import site; print(site.getsitepackages()[0])")/torchvision
rm -rf $(python -c "import site; print(site.getsitepackages()[0])")/torchvision-*.dist-info

pip install torch==2.6.0 torchvision torchaudio \
  --index-url https://download.pytorch.org/whl/cu124 \
  --no-cache-dir
Step 5 — Final gate checks (all 3 must pass)
bashpython -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
# 2.6.0+cu124 / True ✅

python -c "import transformers; print(transformers.__version__)"
# 4.51.3 ✅

python -c "import vllm; print(vllm.__version__)"
# 0.8.5 ✅

CUDA_VISIBLE_DEVICES=0 python -m llama_cpp.server   --model /mnt/f_disk/gitaa/debayan/Internal_LLM/models/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf   --port 8006   --host 0.0.0.0   --n_gpu_layers 99   --n_ctx 8192   --chat_format chatml
##-------------------------------##
