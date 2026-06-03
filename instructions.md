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

##-------------------------------##
