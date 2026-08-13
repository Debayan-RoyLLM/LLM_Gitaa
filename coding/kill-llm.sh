# find the PID
ps aux | grep start_model.py

# kill it (this also stops vLLM since it's a child process)
kill <PID>

# Verify if the process is killed properly.

ps aux | grep vllm