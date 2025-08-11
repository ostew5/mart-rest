import os
from llama_cpp import Llama

MODEL_PATH = os.getenv("MODEL_PATH", "/models/SmolLM3-3B-Q4_K_M.gguf")
N_THREADS = int(os.getenv("N_THREADS", "8"))
N_CTX = int(os.getenv("N_CTX", "4096"))

llm = Llama(
    model_path=MODEL_PATH,
    n_threads=N_THREADS,
    n_ctx=N_CTX,
)

resp = llm("Hello!", max_tokens=64, temperature=0.7)
print(resp["choices"][0]["text"])
