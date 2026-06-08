Llama3.2 vision

conda create -n llama32v python=3.11 -y
conda activate llama32v

pip install --upgrade pip
pip install "vllm==0.10.2"
pip install "transformers==4.56.2"

huggingface-cli login
mkdir -p ~/models
huggingface-cli download meta-llama/Llama-3.2-11B-Vision-Instruct \
  --local-dir ~/models/Llama-3.2-11B-Vision-Instruct

  CUDA_VISIBLE_DEVICES=0 vllm serve ~/models/Llama-3.2-11B-Vision-Instruct \
  --served-model-name llama-3.2-11b-vision \
  --port 8002 \
  --api-key not-needed \
  --dtype bfloat16 \
  --max-model-len 32768 \
  --max-num-seqs 16 \
  --enforce-eager \
  --gpu-memory-utilization 0.90 \
  --limit-mm-per-prompt '{"image": 1}'
